"""
API routes for conversation export (Story-012)
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

try:
    from export_models import ExportRequest, BulkExportRequest, ExportOptions
    from export_service import ConversationExportService
except ImportError:
    from backend.export_models import ExportRequest, BulkExportRequest, ExportOptions
    from backend.export_service import ConversationExportService

router = APIRouter(prefix="/api/conversations", tags=["exports"])
security = HTTPBearer(auto_error=False)

# Global export service instance (will be set by main.py)
_export_service: Optional[ConversationExportService] = None


def set_export_service(service: ConversationExportService):
    """Set the export service instance"""
    global _export_service
    _export_service = service


def get_export_service() -> ConversationExportService:
    """Get export service or raise error"""
    if _export_service is None:
        raise HTTPException(
            status_code=503,
            detail="Export service not initialized"
        )
    return _export_service


async def get_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Extract user ID from JWT token or return guest"""
    if credentials:
        try:
            # Try to get user from JWT
            try:
                from auth_routes import get_current_user
            except ImportError:
                from backend.auth_routes import get_current_user

            user = await get_current_user(credentials)
            return str(user.get("id", "guest"))
        except Exception as e:
            print(f"⚠️ JWT auth failed: {e}")
            return "guest"
    return "guest"


@router.post("/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    request: ExportRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Export a single conversation to PDF or Markdown

    - **conversation_id**: ID of conversation to export
    - **format**: Export format (pdf or markdown)
    - **options**: Export customization options
    """
    try:
        export_service = get_export_service()

        # Validate format
        if request.format not in ['pdf', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail="Format must be 'pdf' or 'markdown'"
            )

        # Ensure conversation_id matches
        if request.conversation_id != conversation_id:
            raise HTTPException(
                status_code=400,
                detail="Conversation ID mismatch"
            )

        # Export conversation
        result = await export_service.export_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            format=request.format,
            options=request.options
        )

        # Return file as download
        return Response(
            content=result.file_data,
            media_type=result.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={result.filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/bulk-export")
async def bulk_export_conversations(
    request: BulkExportRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Export multiple conversations to a ZIP file

    - **conversation_ids**: List of conversation IDs to export
    - **format**: Export format (pdf or markdown)
    - **options**: Export customization options
    """
    try:
        export_service = get_export_service()

        # Validate format
        if request.format not in ['pdf', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail="Format must be 'pdf' or 'markdown'"
            )

        # Validate conversation count
        if not request.conversation_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one conversation ID required"
            )

        if len(request.conversation_ids) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 conversations per bulk export"
            )

        # Export conversations
        result = await export_service.bulk_export(
            conversation_ids=request.conversation_ids,
            user_id=user_id,
            format=request.format,
            options=request.options
        )

        # Return file as download
        return Response(
            content=result.file_data,
            media_type=result.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={result.filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Bulk export failed: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Bulk export failed: {str(e)}"
        )


@router.get("/exports")
async def list_exports(user_id: str = Depends(get_user_id)):
    """
    List user's export history

    Returns list of previous exports with metadata
    """
    try:
        export_service = get_export_service()
        exports = await export_service.list_exports(user_id)

        return {
            "exports": exports,
            "total": len(exports)
        }

    except Exception as e:
        print(f"❌ Failed to list exports: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list exports: {str(e)}"
        )


@router.delete("/exports/{export_id}")
async def delete_export(
    export_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Delete an export record

    - **export_id**: ID of export to delete
    """
    try:
        export_service = get_export_service()
        success = await export_service.delete_export_record(export_id, user_id)

        if success:
            return {"status": "success", "message": "Export deleted"}
        else:
            raise HTTPException(status_code=404, detail="Export not found")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to delete export: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete export: {str(e)}"
        )
