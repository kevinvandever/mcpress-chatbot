"""
Code File Storage System
Story: STORY-006
Created: 2025-10-13

Manages temporary storage of uploaded code files with:
- User/session isolation
- Automatic cleanup after 24 hours
- Metadata tracking
- File retrieval and deletion
"""

import os
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StoredFile(BaseModel):
    """Metadata for a stored file"""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    encoding: Optional[str] = None
    uploaded_at: datetime
    expires_at: datetime
    user_id: str
    session_id: str


class CodeFileStorage:
    """
    Manages temporary storage of code files with automatic cleanup

    Directory Structure:
        /tmp/code-uploads/
            /{user_id}/
                /{session_id}/
                    /{file_id}_{filename}
                    metadata.json
    """

    def __init__(self, base_dir: str = "/tmp/code-uploads"):
        """
        Initialize storage manager

        Args:
            base_dir: Base directory for code file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> Path:
        """Get user-specific directory"""
        user_dir = self.base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_session_dir(self, user_id: str, session_id: str) -> Path:
        """Get session-specific directory"""
        session_dir = self._get_user_dir(user_id) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _get_metadata_path(self, user_id: str, session_id: str) -> Path:
        """Get path to session metadata file"""
        return self._get_session_dir(user_id, session_id) / "metadata.json"

    def _load_session_metadata(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Load session metadata from JSON file"""
        metadata_path = self._get_metadata_path(user_id, session_id)

        if not metadata_path.exists():
            return {"files": [], "created_at": datetime.now().isoformat()}

        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {"files": [], "created_at": datetime.now().isoformat()}

    def _save_session_metadata(self, user_id: str, session_id: str, metadata: Dict[str, Any]):
        """Save session metadata to JSON file"""
        metadata_path = self._get_metadata_path(user_id, session_id)

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving metadata: {e}")
            raise

    def store_file(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        file_content: bytes,
        file_type: str,
        encoding: Optional[str] = None,
        expiration_hours: int = 24
    ) -> StoredFile:
        """
        Store a code file in temporary storage

        Args:
            user_id: User identifier
            session_id: Upload session identifier
            filename: Original filename
            file_content: File content as bytes
            file_type: File extension (e.g., '.rpg')
            encoding: Detected encoding (e.g., 'utf-8')
            expiration_hours: Hours until auto-deletion (default 24)

        Returns:
            StoredFile with metadata
        """
        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Get session directory
        session_dir = self._get_session_dir(user_id, session_id)

        # Create file path with unique ID
        safe_filename = f"{file_id}_{filename}"
        file_path = session_dir / safe_filename

        # Write file to disk
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            print(f"Error writing file: {e}")
            raise

        # Create metadata
        now = datetime.now()
        expires_at = now + timedelta(hours=expiration_hours)

        stored_file = StoredFile(
            file_id=file_id,
            filename=filename,
            file_path=str(file_path),
            file_size=len(file_content),
            file_type=file_type,
            encoding=encoding,
            uploaded_at=now,
            expires_at=expires_at,
            user_id=user_id,
            session_id=session_id
        )

        # Update session metadata
        session_metadata = self._load_session_metadata(user_id, session_id)
        session_metadata['files'].append(stored_file.dict())
        self._save_session_metadata(user_id, session_id, session_metadata)

        return stored_file

    def get_file(self, user_id: str, session_id: str, file_id: str) -> Optional[StoredFile]:
        """
        Get file metadata by ID

        Args:
            user_id: User identifier
            session_id: Session identifier
            file_id: File identifier

        Returns:
            StoredFile or None if not found
        """
        session_metadata = self._load_session_metadata(user_id, session_id)

        for file_data in session_metadata.get('files', []):
            if file_data.get('file_id') == file_id:
                return StoredFile(**file_data)

        return None

    def get_file_content(self, user_id: str, session_id: str, file_id: str) -> Optional[bytes]:
        """
        Read file content from storage

        Args:
            user_id: User identifier
            session_id: Session identifier
            file_id: File identifier

        Returns:
            File content as bytes or None if not found
        """
        stored_file = self.get_file(user_id, session_id, file_id)

        if not stored_file:
            return None

        file_path = Path(stored_file.file_path)

        if not file_path.exists():
            print(f"File not found on disk: {file_path}")
            return None

        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def list_session_files(self, user_id: str, session_id: str) -> List[StoredFile]:
        """
        List all files in a session

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            List of StoredFile objects
        """
        session_metadata = self._load_session_metadata(user_id, session_id)

        files = []
        for file_data in session_metadata.get('files', []):
            try:
                files.append(StoredFile(**file_data))
            except Exception as e:
                print(f"Error parsing file metadata: {e}")

        return files

    def list_user_files(self, user_id: str) -> List[StoredFile]:
        """
        List all files for a user across all sessions

        Args:
            user_id: User identifier

        Returns:
            List of StoredFile objects
        """
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            return []

        all_files = []

        # Iterate through all session directories
        for session_dir in user_dir.iterdir():
            if session_dir.is_dir():
                session_id = session_dir.name
                files = self.list_session_files(user_id, session_id)
                all_files.extend(files)

        return all_files

    def delete_file(self, user_id: str, session_id: str, file_id: str) -> bool:
        """
        Delete a file from storage

        Args:
            user_id: User identifier
            session_id: Session identifier
            file_id: File identifier

        Returns:
            True if deleted, False if not found
        """
        stored_file = self.get_file(user_id, session_id, file_id)

        if not stored_file:
            return False

        # Delete file from disk
        file_path = Path(stored_file.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Error deleting file: {e}")
                return False

        # Update metadata
        session_metadata = self._load_session_metadata(user_id, session_id)
        session_metadata['files'] = [
            f for f in session_metadata['files']
            if f.get('file_id') != file_id
        ]
        self._save_session_metadata(user_id, session_id, session_metadata)

        return True

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete an entire session (all files + metadata)

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        session_dir = self._get_session_dir(user_id, session_id)

        if not session_dir.exists():
            return False

        try:
            shutil.rmtree(session_dir)
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

    def cleanup_expired_files(self) -> Dict[str, int]:
        """
        Clean up all expired files across all users

        Returns:
            Statistics: {
                'sessions_cleaned': count,
                'files_deleted': count,
                'bytes_freed': bytes
            }
        """
        now = datetime.now()
        stats = {
            'sessions_cleaned': 0,
            'files_deleted': 0,
            'bytes_freed': 0
        }

        if not self.base_dir.exists():
            return stats

        # Iterate through all user directories
        for user_dir in self.base_dir.iterdir():
            if not user_dir.is_dir():
                continue

            user_id = user_dir.name

            # Iterate through all session directories
            for session_dir in user_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                session_id = session_dir.name
                files = self.list_session_files(user_id, session_id)

                # Check if any files are expired
                expired_files = [f for f in files if f.expires_at < now]

                if expired_files:
                    for file in expired_files:
                        file_path = Path(file.file_path)
                        if file_path.exists():
                            stats['bytes_freed'] += file.file_size
                            file_path.unlink()
                            stats['files_deleted'] += 1

                    # If all files expired, delete the session
                    if len(expired_files) == len(files):
                        self.delete_session(user_id, session_id)
                        stats['sessions_cleaned'] += 1
                    else:
                        # Update metadata to remove expired files
                        session_metadata = self._load_session_metadata(user_id, session_id)
                        session_metadata['files'] = [
                            f for f in session_metadata['files']
                            if f.get('file_id') not in [ef.file_id for ef in expired_files]
                        ]
                        self._save_session_metadata(user_id, session_id, session_metadata)

        return stats

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Statistics about current storage usage
        """
        stats = {
            'total_users': 0,
            'total_sessions': 0,
            'total_files': 0,
            'total_bytes': 0,
            'expired_files': 0,
            'expired_bytes': 0
        }

        if not self.base_dir.exists():
            return stats

        now = datetime.now()

        for user_dir in self.base_dir.iterdir():
            if not user_dir.is_dir():
                continue

            stats['total_users'] += 1
            user_id = user_dir.name

            for session_dir in user_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                stats['total_sessions'] += 1
                session_id = session_dir.name
                files = self.list_session_files(user_id, session_id)

                for file in files:
                    stats['total_files'] += 1
                    stats['total_bytes'] += file.file_size

                    if file.expires_at < now:
                        stats['expired_files'] += 1
                        stats['expired_bytes'] += file.file_size

        # Add human-readable sizes
        stats['total_mb'] = round(stats['total_bytes'] / (1024 * 1024), 2)
        stats['expired_mb'] = round(stats['expired_bytes'] / (1024 * 1024), 2)

        return stats
