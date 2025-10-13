"""
Code Upload Service
Story: STORY-006
Created: 2025-10-13

Comprehensive service for managing code file uploads:
- Session management
- Quota tracking
- File validation and storage
- Database persistence
"""

import uuid
import asyncpg
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel

try:
    from code_file_validator import FileValidator, ValidationResult
    from code_file_storage import CodeFileStorage, StoredFile
except ImportError:
    from backend.code_file_validator import FileValidator, ValidationResult
    from backend.code_file_storage import CodeFileStorage, StoredFile


class UploadSession(BaseModel):
    """Upload session information"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    total_files: int
    total_size: int
    status: str  # 'active', 'completed', 'expired'


class UserQuota(BaseModel):
    """User quota information"""
    user_id: str
    daily_uploads: int
    daily_storage: int
    last_reset: str
    lifetime_uploads: int
    can_upload: bool
    uploads_remaining: int
    storage_remaining: int


class CodeUpload(BaseModel):
    """Code file upload record"""
    id: str
    user_id: str
    session_id: str
    filename: str
    file_type: str
    file_size: int
    file_path: str
    uploaded_at: datetime
    expires_at: datetime
    analyzed: bool
    analysis_id: Optional[str] = None


class CodeUploadService:
    """
    Service for managing code file uploads

    Handles:
    - Upload sessions
    - User quotas
    - File validation and storage
    - Database persistence
    """

    def __init__(self, database_url: str, storage_dir: str = "/tmp/code-uploads"):
        """
        Initialize upload service

        Args:
            database_url: PostgreSQL connection string
            storage_dir: Directory for file storage
        """
        self.database_url = database_url
        self.storage = CodeFileStorage(storage_dir)
        self.validator = FileValidator()
        self.pool: Optional[asyncpg.Pool] = None

    async def init_database(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        print("✅ Code Upload Service: Database pool created")

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            print("📦 Code Upload Service: Database pool closed")

    # ==================== Session Management ====================

    async def create_session(self, user_id: str, expiration_hours: int = 24) -> UploadSession:
        """
        Create a new upload session

        Args:
            user_id: User identifier
            expiration_hours: Hours until session expires

        Returns:
            UploadSession object
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(hours=expiration_hours)

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO upload_sessions
                (session_id, user_id, created_at, expires_at, total_files, total_size, status)
                VALUES ($1, $2, $3, $4, 0, 0, 'active')
            """, session_id, user_id, now, expires_at)

        return UploadSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
            total_files=0,
            total_size=0,
            status='active'
        )

    async def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get session by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT session_id, user_id, created_at, expires_at, total_files, total_size, status
                FROM upload_sessions
                WHERE session_id = $1
            """, session_id)

            if not row:
                return None

            return UploadSession(
                session_id=row['session_id'],
                user_id=row['user_id'],
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                total_files=row['total_files'],
                total_size=row['total_size'],
                status=row['status']
            )

    async def update_session_stats(self, session_id: str, file_count_delta: int, size_delta: int):
        """Update session file count and size"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE upload_sessions
                SET total_files = total_files + $1,
                    total_size = total_size + $2
                WHERE session_id = $3
            """, file_count_delta, size_delta, session_id)

    # ==================== Quota Management ====================

    async def get_user_quota(self, user_id: str) -> UserQuota:
        """
        Get user's current quota status (auto-resets if needed)

        Args:
            user_id: User identifier

        Returns:
            UserQuota with current usage and limits
        """
        async with self.pool.acquire() as conn:
            # Call database function that handles auto-reset
            row = await conn.fetchrow("""
                SELECT * FROM get_user_quota_status($1)
            """, user_id)

            daily_uploads_used = row['daily_uploads_used']
            daily_uploads_limit = row['daily_uploads_limit']
            daily_storage_used = row['daily_storage_used']
            daily_storage_limit = row['daily_storage_limit']
            can_upload = row['can_upload']

            # Get lifetime uploads
            lifetime_row = await conn.fetchrow("""
                SELECT lifetime_uploads FROM user_quotas WHERE user_id = $1
            """, user_id)
            lifetime_uploads = lifetime_row['lifetime_uploads'] if lifetime_row else 0

            return UserQuota(
                user_id=user_id,
                daily_uploads=daily_uploads_used,
                daily_storage=daily_storage_used,
                last_reset=datetime.now().date().isoformat(),
                lifetime_uploads=lifetime_uploads,
                can_upload=can_upload,
                uploads_remaining=max(0, daily_uploads_limit - daily_uploads_used),
                storage_remaining=max(0, daily_storage_limit - daily_storage_used)
            )

    async def check_quota(self, user_id: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Check if user has quota available for upload

        Args:
            user_id: User identifier
            file_size: Size of file to upload

        Returns:
            (can_upload, error_message)
        """
        quota = await self.get_user_quota(user_id)

        if not quota.can_upload:
            return False, "Daily upload quota exceeded"

        if quota.uploads_remaining <= 0:
            return False, f"Daily upload limit reached ({quota.daily_uploads} files)"

        if file_size > quota.storage_remaining:
            storage_mb = quota.storage_remaining / (1024 * 1024)
            return False, f"Daily storage quota exceeded (remaining: {storage_mb:.1f}MB)"

        return True, None

    async def increment_quota(self, user_id: str, file_size: int):
        """Increment user's quota usage"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_quotas (user_id, daily_uploads, daily_storage, lifetime_uploads, last_reset)
                VALUES ($1, 1, $2, 1, CURRENT_DATE)
                ON CONFLICT (user_id) DO UPDATE
                SET
                    daily_uploads = user_quotas.daily_uploads + 1,
                    daily_storage = user_quotas.daily_storage + $2,
                    lifetime_uploads = user_quotas.lifetime_uploads + 1
            """, user_id, file_size)

    # ==================== File Upload ====================

    async def upload_file(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        file_content: bytes
    ) -> Tuple[bool, Optional[CodeUpload], Optional[str], Optional[ValidationResult]]:
        """
        Upload and validate a code file

        Args:
            user_id: User identifier
            session_id: Upload session ID
            filename: Original filename
            file_content: File content as bytes

        Returns:
            (success, CodeUpload or None, error_message or None, ValidationResult)
        """
        file_size = len(file_content)

        # Validate file
        validation = self.validator.validate_file(filename, file_size, file_content)

        if not validation.valid:
            error_msg = "; ".join(validation.errors)
            return False, None, f"Validation failed: {error_msg}", validation

        # Check quota
        can_upload, quota_error = await self.check_quota(user_id, file_size)
        if not can_upload:
            return False, None, quota_error, validation

        # Store file in filesystem
        try:
            stored_file = self.storage.store_file(
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                file_content=file_content,
                file_type=validation.file_type,
                encoding=validation.encoding,
                expiration_hours=24
            )
        except Exception as e:
            return False, None, f"Storage error: {str(e)}", validation

        # Save to database
        try:
            upload_id = stored_file.file_id

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO code_uploads
                    (id, user_id, session_id, filename, file_type, file_size, file_path,
                     uploaded_at, expires_at, analyzed, analysis_id, deleted_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE, NULL, NULL)
                """, upload_id, user_id, session_id, filename, validation.file_type,
                    file_size, stored_file.file_path, stored_file.uploaded_at, stored_file.expires_at)

            # Update session stats
            await self.update_session_stats(session_id, 1, file_size)

            # Update quota
            await self.increment_quota(user_id, file_size)

            code_upload = CodeUpload(
                id=upload_id,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                file_type=validation.file_type,
                file_size=file_size,
                file_path=stored_file.file_path,
                uploaded_at=stored_file.uploaded_at,
                expires_at=stored_file.expires_at,
                analyzed=False,
                analysis_id=None
            )

            return True, code_upload, None, validation

        except Exception as e:
            # Rollback: delete from filesystem
            self.storage.delete_file(user_id, session_id, stored_file.file_id)
            return False, None, f"Database error: {str(e)}", validation

    # ==================== File Retrieval ====================

    async def get_file(self, file_id: str, user_id: str) -> Optional[CodeUpload]:
        """Get file metadata by ID (with user ownership check)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, user_id, session_id, filename, file_type, file_size, file_path,
                       uploaded_at, expires_at, analyzed, analysis_id
                FROM code_uploads
                WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
            """, file_id, user_id)

            if not row:
                return None

            return CodeUpload(
                id=row['id'],
                user_id=row['user_id'],
                session_id=row['session_id'],
                filename=row['filename'],
                file_type=row['file_type'],
                file_size=row['file_size'],
                file_path=row['file_path'],
                uploaded_at=row['uploaded_at'],
                expires_at=row['expires_at'],
                analyzed=row['analyzed'],
                analysis_id=row['analysis_id']
            )

    async def get_file_content(self, file_id: str, user_id: str) -> Optional[bytes]:
        """Get file content by ID (with user ownership check)"""
        file_meta = await self.get_file(file_id, user_id)

        if not file_meta:
            return None

        return self.storage.get_file_content(user_id, file_meta.session_id, file_id)

    async def list_session_files(self, session_id: str, user_id: str) -> List[CodeUpload]:
        """List all files in a session"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, session_id, filename, file_type, file_size, file_path,
                       uploaded_at, expires_at, analyzed, analysis_id
                FROM code_uploads
                WHERE session_id = $1 AND user_id = $2 AND deleted_at IS NULL
                ORDER BY uploaded_at DESC
            """, session_id, user_id)

            return [CodeUpload(**dict(row)) for row in rows]

    async def list_user_files(self, user_id: str, limit: int = 100) -> List[CodeUpload]:
        """List all files for a user"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, session_id, filename, file_type, file_size, file_path,
                       uploaded_at, expires_at, analyzed, analysis_id
                FROM code_uploads
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY uploaded_at DESC
                LIMIT $2
            """, user_id, limit)

            return [CodeUpload(**dict(row)) for row in rows]

    # ==================== File Deletion ====================

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file (soft delete in DB, hard delete in storage)"""
        file_meta = await self.get_file(file_id, user_id)

        if not file_meta:
            return False

        # Delete from filesystem
        self.storage.delete_file(user_id, file_meta.session_id, file_id)

        # Soft delete in database
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE code_uploads
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, file_id)

        # Update session stats
        await self.update_session_stats(file_meta.session_id, -1, -file_meta.file_size)

        return True

    # ==================== Cleanup ====================

    async def cleanup_expired_files(self) -> Dict[str, int]:
        """
        Clean up expired files from database and storage

        Returns:
            Statistics about cleanup operation
        """
        # Cleanup in database
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM cleanup_expired_code_files()
            """)

            db_stats = {
                'deleted_count': result['deleted_count'],
                'freed_bytes': result['freed_bytes']
            }

        # Cleanup in filesystem
        storage_stats = self.storage.cleanup_expired_files()

        return {
            'database_files_deleted': db_stats['deleted_count'],
            'database_bytes_freed': db_stats['freed_bytes'],
            'storage_files_deleted': storage_stats['files_deleted'],
            'storage_bytes_freed': storage_stats['bytes_freed'],
            'sessions_cleaned': storage_stats['sessions_cleaned']
        }

    # ==================== Statistics ====================

    async def get_stats(self) -> Dict[str, Any]:
        """Get upload system statistics"""
        async with self.pool.acquire() as conn:
            db_stats = await conn.fetchrow("""
                SELECT * FROM code_upload_stats
            """)

        storage_stats = self.storage.get_storage_stats()

        return {
            'database': dict(db_stats),
            'storage': storage_stats
        }


# Global service instance
_upload_service: Optional[CodeUploadService] = None


def init_upload_service(database_url: str, storage_dir: str = "/tmp/code-uploads") -> CodeUploadService:
    """Initialize global upload service"""
    global _upload_service
    _upload_service = CodeUploadService(database_url, storage_dir)
    return _upload_service


def get_upload_service() -> CodeUploadService:
    """Get global upload service instance"""
    if _upload_service is None:
        raise RuntimeError("Upload service not initialized. Call init_upload_service first.")
    return _upload_service
