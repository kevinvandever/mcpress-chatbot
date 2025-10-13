"""
Code File Validation Service
Story: STORY-006
Created: 2025-10-13

Validates code file uploads for:
- File type/extension
- File size limits
- Content security (credentials, malicious patterns)
- Character encoding
"""

import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from pydantic import BaseModel

# Allowed file extensions for IBM i code files
ALLOWED_EXTENSIONS = {
    '.rpg',      # RPG II/III
    '.rpgle',    # RPG IV (ILE)
    '.sqlrpgle', # RPG with embedded SQL
    '.cl',       # Control Language
    '.clle',     # Control Language (ILE)
    '.sql',      # SQL scripts
    '.txt'       # Generic text (for IBM i source)
}

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES_PER_SESSION = 10
MAX_FILES_PER_USER_PER_DAY = 50
MAX_STORAGE_PER_USER = 100 * 1024 * 1024  # 100MB

# Security patterns to detect
CREDENTIAL_PATTERNS = [
    (r'password\s*=\s*["\']([^"\']+)["\']', 'Password in plain text'),
    (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', 'API key in plain text'),
    (r'secret\s*=\s*["\']([^"\']+)["\']', 'Secret key in plain text'),
    (r'token\s*=\s*["\']([^"\']+)["\']', 'Token in plain text'),
    (r'aws[_-]?access[_-]?key', 'AWS credentials'),
    (r'private[_-]?key', 'Private key reference'),
]

# Malicious patterns (basic security checks)
MALICIOUS_PATTERNS = [
    (r'<script[^>]*>.*?</script>', 'JavaScript code detected'),
    (r'eval\s*\(', 'Eval function detected'),
    (r'exec\s*\(', 'Exec function detected'),
]


class ValidationResult(BaseModel):
    """Result of file validation"""
    valid: bool
    filename: str
    file_size: int
    file_type: str
    errors: List[str] = []
    warnings: List[str] = []
    credential_warnings: List[str] = []
    encoding: Optional[str] = None


class FileValidator:
    """Validates code file uploads for security and correctness"""

    @staticmethod
    def validate_extension(filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file extension

        Returns:
            (is_valid, file_extension or error_message)
        """
        path = Path(filename)
        ext = path.suffix.lower()

        if not ext:
            return False, "File has no extension"

        if ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            return False, f"File type '{ext}' not allowed. Allowed types: {allowed}"

        return True, ext

    @staticmethod
    def validate_size(file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file size

        Returns:
            (is_valid, error_message if invalid)
        """
        if file_size <= 0:
            return False, "File is empty"

        if file_size > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File size ({actual_mb:.2f}MB) exceeds limit of {max_mb:.0f}MB"

        return True, None

    @staticmethod
    def detect_encoding(file_content: bytes) -> str:
        """
        Detect file encoding (UTF-8, EBCDIC, etc.)

        Returns:
            Detected encoding name
        """
        # Try UTF-8 first
        try:
            file_content.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass

        # Try Latin-1 (common for older IBM i files)
        try:
            file_content.decode('latin-1')
            return 'latin-1'
        except UnicodeDecodeError:
            pass

        # Try CP037 (EBCDIC)
        try:
            file_content.decode('cp037')
            return 'ebcdic'
        except UnicodeDecodeError:
            pass

        return 'unknown'

    @staticmethod
    def scan_for_credentials(file_content: str) -> List[str]:
        """
        Scan file content for hardcoded credentials

        Returns:
            List of warning messages
        """
        warnings = []
        content_lower = file_content.lower()

        for pattern, description in CREDENTIAL_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                warnings.append(f"⚠️ {description} detected on line(s)")

        return warnings

    @staticmethod
    def scan_for_malicious_content(file_content: str) -> List[str]:
        """
        Scan file content for potentially malicious patterns

        Returns:
            List of error messages
        """
        errors = []

        for pattern, description in MALICIOUS_PATTERNS:
            if re.search(pattern, file_content, re.IGNORECASE):
                errors.append(f"❌ {description}")

        return errors

    @staticmethod
    def validate_content(file_content: bytes) -> Tuple[bool, str, List[str], List[str]]:
        """
        Validate file content for security issues

        Returns:
            (is_valid, encoding, errors, warnings)
        """
        errors = []
        warnings = []

        # Detect encoding
        encoding = FileValidator.detect_encoding(file_content)

        if encoding == 'unknown':
            errors.append("Could not detect file encoding")
            return False, encoding, errors, warnings

        # Decode content
        try:
            if encoding == 'utf-8':
                content = file_content.decode('utf-8')
            elif encoding == 'latin-1':
                content = file_content.decode('latin-1')
            elif encoding == 'ebcdic':
                content = file_content.decode('cp037')
            else:
                errors.append(f"Unsupported encoding: {encoding}")
                return False, encoding, errors, warnings
        except Exception as e:
            errors.append(f"Failed to decode file: {str(e)}")
            return False, encoding, errors, warnings

        # Scan for malicious content
        malicious_errors = FileValidator.scan_for_malicious_content(content)
        errors.extend(malicious_errors)

        # Scan for credentials
        credential_warnings = FileValidator.scan_for_credentials(content)
        warnings.extend(credential_warnings)

        is_valid = len(errors) == 0
        return is_valid, encoding, errors, warnings

    @staticmethod
    def validate_file(filename: str, file_size: int, file_content: bytes) -> ValidationResult:
        """
        Complete file validation

        Args:
            filename: Original filename
            file_size: File size in bytes
            file_content: Raw file content

        Returns:
            ValidationResult with all validation checks
        """
        result = ValidationResult(
            valid=True,
            filename=filename,
            file_size=file_size,
            file_type='',
            errors=[],
            warnings=[],
            credential_warnings=[]
        )

        # Validate extension
        ext_valid, ext_or_error = FileValidator.validate_extension(filename)
        if not ext_valid:
            result.valid = False
            result.errors.append(ext_or_error)
            return result

        result.file_type = ext_or_error

        # Validate size
        size_valid, size_error = FileValidator.validate_size(file_size)
        if not size_valid:
            result.valid = False
            result.errors.append(size_error)
            return result

        # Validate content
        content_valid, encoding, content_errors, content_warnings = FileValidator.validate_content(file_content)
        result.encoding = encoding
        result.errors.extend(content_errors)
        result.warnings.extend(content_warnings)
        result.credential_warnings = [w for w in content_warnings if 'credential' in w.lower() or 'password' in w.lower() or 'key' in w.lower()]

        if not content_valid:
            result.valid = False

        return result

    @staticmethod
    def validate_session_limits(
        existing_files_count: int,
        new_files_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate session file count limits

        Returns:
            (is_valid, error_message if invalid)
        """
        total = existing_files_count + new_files_count

        if total > MAX_FILES_PER_SESSION:
            return False, f"Session limit exceeded. Maximum {MAX_FILES_PER_SESSION} files per session. Current: {existing_files_count}, Attempting: {new_files_count}"

        return True, None

    @staticmethod
    def validate_daily_quota(
        daily_uploads: int,
        daily_storage: int,
        new_file_size: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate daily upload quota

        Returns:
            (is_valid, error_message if invalid)
        """
        # Check file count quota
        if daily_uploads >= MAX_FILES_PER_USER_PER_DAY:
            return False, f"Daily upload limit reached. Maximum {MAX_FILES_PER_USER_PER_DAY} files per day"

        # Check storage quota
        new_total_storage = daily_storage + new_file_size
        if new_total_storage > MAX_STORAGE_PER_USER:
            max_mb = MAX_STORAGE_PER_USER / (1024 * 1024)
            return False, f"Daily storage quota exceeded. Maximum {max_mb:.0f}MB per day"

        return True, None


# Convenience functions for common validations

def quick_validate_extension(filename: str) -> bool:
    """Quick check if file extension is allowed"""
    valid, _ = FileValidator.validate_extension(filename)
    return valid


def quick_validate_size(file_size: int) -> bool:
    """Quick check if file size is within limits"""
    valid, _ = FileValidator.validate_size(file_size)
    return valid


def get_allowed_extensions() -> List[str]:
    """Get list of allowed extensions"""
    return sorted(list(ALLOWED_EXTENSIONS))


def get_file_limits() -> Dict[str, int]:
    """Get all file upload limits"""
    return {
        "max_file_size_bytes": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "max_files_per_session": MAX_FILES_PER_SESSION,
        "max_files_per_day": MAX_FILES_PER_USER_PER_DAY,
        "max_storage_per_day_bytes": MAX_STORAGE_PER_USER,
        "max_storage_per_day_mb": MAX_STORAGE_PER_USER // (1024 * 1024)
    }
