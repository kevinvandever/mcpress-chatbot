"""
Code Upload API Routes
Story: STORY-006
Created: 2025-10-13

FastAPI router for code file upload endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import Response
from typing import List, Optional
from pydantic import BaseModel

try:
    from code_upload_service import get_upload_service, CodeUploadService
    from code_file_validator import get_file_limits, get_allowed_extensions
    from auth_routes import get_current_user
except ImportError:
    from backend.code_upload_service import get_upload_service, CodeUploadService
    from backend.code_file_validator import get_file_limits, get_allowed_extensions
    from backend.auth_routes import get_current_user

router = APIRouter(prefix="/api/code", tags=["code-upload"])


# ==================== Request/Response Models ====================

class UploadResponse(BaseModel):
    """Response for file upload"""
    success: bool
    file_id: Optional[str] = None
    filename: str
    message: str
    warnings: List[str] = []
    credential_warnings: List[str] = []


class SessionResponse(BaseModel):
    """Response for session creation"""
    session_id: str
    user_id: str
    expires_at: str
    message: str


class FileInfo(BaseModel):
    """File information for list responses"""
    id: str
    filename: str
    file_type: str
    file_size: int
    uploaded_at: str
    expires_at: str
    analyzed: bool


class QuotaResponse(BaseModel):
    """User quota information"""
    daily_uploads_used: int
    daily_uploads_remaining: int
    daily_uploads_limit: int
    daily_storage_used_bytes: int
    daily_storage_remaining_bytes: int
    daily_storage_limit_bytes: int
    can_upload: bool
    lifetime_uploads: int


class LimitsResponse(BaseModel):
    """System limits"""
    allowed_extensions: List[str]
    max_file_size_bytes: int
    max_file_size_mb: int
    max_files_per_session: int
    max_files_per_day: int
    max_storage_per_day_mb: int


# ==================== Dependency: Get Current User ====================

async def get_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """Extract user ID from authenticated user"""
    return current_user.get("user_id") or current_user.get("email") or "anonymous"


# ==================== API Endpoints ====================

@router.get("/limits", response_model=LimitsResponse)
async def get_limits():
    """Get system limits and allowed file types"""
    limits = get_file_limits()
    extensions = get_allowed_extensions()

    return LimitsResponse(
        allowed_extensions=extensions,
        max_file_size_bytes=limits['max_file_size_bytes'],
        max_file_size_mb=limits['max_file_size_mb'],
        max_files_per_session=limits['max_files_per_session'],
        max_files_per_day=limits['max_files_per_day'],
        max_storage_per_day_mb=limits['max_storage_per_day_mb']
    )


@router.post("/session", response_model=SessionResponse)
async def create_upload_session(user_id: str = Depends(get_user_id)):
    """Create a new upload session"""
    service = get_upload_service()

    try:
        session = await service.create_session(user_id)

        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            expires_at=session.expires_at.isoformat(),
            message="Upload session created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(user_id: str = Depends(get_user_id)):
    """Get user's current quota status"""
    service = get_upload_service()

    try:
        quota = await service.get_user_quota(user_id)
        limits = get_file_limits()

        return QuotaResponse(
            daily_uploads_used=quota.daily_uploads,
            daily_uploads_remaining=quota.uploads_remaining,
            daily_uploads_limit=limits['max_files_per_day'],
            daily_storage_used_bytes=quota.daily_storage,
            daily_storage_remaining_bytes=quota.storage_remaining,
            daily_storage_limit_bytes=limits['max_storage_per_day_bytes'],
            can_upload=quota.can_upload,
            lifetime_uploads=quota.lifetime_uploads
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quota: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_code_file(
    session_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Upload a code file

    - **session_id**: Upload session ID (create one first via /session)
    - **file**: Code file to upload (.rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt)
    """
    service = get_upload_service()

    # Verify session exists and belongs to user
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")

    if session.status != 'active':
        raise HTTPException(status_code=400, detail=f"Session is {session.status}")

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    # Upload file
    try:
        success, code_upload, error_msg, validation = await service.upload_file(
            user_id=user_id,
            session_id=session_id,
            filename=file.filename,
            file_content=file_content
        )

        if not success:
            return UploadResponse(
                success=False,
                filename=file.filename,
                message=error_msg or "Upload failed",
                warnings=validation.warnings if validation else [],
                credential_warnings=validation.credential_warnings if validation else []
            )

        return UploadResponse(
            success=True,
            file_id=code_upload.id,
            filename=file.filename,
            message=f"Successfully uploaded {file.filename}",
            warnings=validation.warnings if validation else [],
            credential_warnings=validation.credential_warnings if validation else []
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files", response_model=List[FileInfo])
async def list_user_files(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
    user_id: str = Depends(get_user_id)
):
    """List user's uploaded files (optionally filtered by session)"""
    service = get_upload_service()

    try:
        if session_id:
            # Verify session belongs to user
            session = await service.get_session(session_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized")

            files = await service.list_session_files(session_id, user_id)
        else:
            files = await service.list_user_files(user_id, limit)

        return [
            FileInfo(
                id=f.id,
                filename=f.filename,
                file_type=f.file_type,
                file_size=f.file_size,
                uploaded_at=f.uploaded_at.isoformat(),
                expires_at=f.expires_at.isoformat(),
                analyzed=f.analyzed
            )
            for f in files
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/file/{file_id}")
async def get_file_content(
    file_id: str,
    user_id: str = Depends(get_user_id)
):
    """Get file content by ID"""
    service = get_upload_service()

    try:
        # Get file metadata
        file_meta = await service.get_file(file_id, user_id)
        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Get file content
        content = await service.get_file_content(file_id, user_id)
        if content is None:
            raise HTTPException(status_code=404, detail="File content not found")

        # Determine media type based on file extension
        media_type_map = {
            '.rpg': 'text/plain',
            '.rpgle': 'text/plain',
            '.sqlrpgle': 'text/plain',
            '.cl': 'text/plain',
            '.clle': 'text/plain',
            '.sql': 'text/plain',
            '.txt': 'text/plain'
        }
        media_type = media_type_map.get(file_meta.file_type, 'application/octet-stream')

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_meta.filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.get("/file/{file_id}/info", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    user_id: str = Depends(get_user_id)
):
    """Get file metadata by ID"""
    service = get_upload_service()

    try:
        file_meta = await service.get_file(file_id, user_id)
        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        return FileInfo(
            id=file_meta.id,
            filename=file_meta.filename,
            file_type=file_meta.file_type,
            file_size=file_meta.file_size,
            uploaded_at=file_meta.uploaded_at.isoformat(),
            expires_at=file_meta.expires_at.isoformat(),
            analyzed=file_meta.analyzed
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.delete("/file/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_user_id)
):
    """Delete a file"""
    service = get_upload_service()

    try:
        success = await service.delete_file(file_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="File not found")

        return {"message": "File deleted successfully", "file_id": file_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/validate")
async def validate_file_before_upload(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Validate a file before uploading (without actually uploading)

    Useful for client-side validation feedback
    """
    from backend.code_file_validator import FileValidator

    try:
        file_content = await file.read()
        file_size = len(file_content)

        validation = FileValidator.validate_file(file.filename, file_size, file_content)

        return {
            "valid": validation.valid,
            "filename": validation.filename,
            "file_size": validation.file_size,
            "file_type": validation.file_type,
            "encoding": validation.encoding,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "credential_warnings": validation.credential_warnings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# ==================== Admin/Monitoring Endpoints ====================

@router.get("/admin/stats")
async def get_upload_stats(user_id: str = Depends(get_user_id)):
    """Get upload system statistics (admin only in production)"""
    # TODO: Add admin permission check
    service = get_upload_service()

    try:
        stats = await service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/admin/cleanup")
async def run_cleanup(user_id: str = Depends(get_user_id)):
    """Manually trigger cleanup of expired files (admin only in production)"""
    # TODO: Add admin permission check
    service = get_upload_service()

    try:
        stats = await service.cleanup_expired_files()
        return {
            "message": "Cleanup completed successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
