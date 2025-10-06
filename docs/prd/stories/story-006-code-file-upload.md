# Story: File Upload for Code Analysis

**Story ID**: STORY-006
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P0 (Critical)
**Points**: 5
**Sprint**: 4
**Status**: Ready for Development

## User Story

**As a** developer
**I want** to upload my RPG/CL code files
**So that** I can get AI-powered code review and analysis

## Context

This is the first major feature that differentiates the MC Press Chatbot from a basic Q&A system. By allowing developers to upload their actual code files, we enable personalized analysis, modernization suggestions, and security audits based on MC Press best practices.

## Current State

### Existing System
- **Chat Interface**: Basic Q&A with MC Press book content
- **File Handling**: Only PDFs supported (admin upload only)
- **Storage**: Railway filesystem with 500MB limit
- **Database**: PostgreSQL with books and embeddings tables
- **Frontend**: Next.js on Netlify
- **Backend**: Python/FastAPI on Railway

### Gap Analysis
- No support for code file formats (.rpg, .rpgle, .sqlrpgle, .cl, .sql)
- No user-facing file upload (only admin can upload PDFs)
- No temporary file storage system
- No automatic cleanup of uploaded files
- No file type validation for code files
- No size limits or quota management

## Acceptance Criteria

- [ ] Support code file types: .rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt
- [ ] File size limit: 10MB per file
- [ ] Multiple file upload: Up to 10 files simultaneously
- [ ] File type validation with clear error messages
- [ ] Temporary storage with 24-hour auto-deletion
- [ ] Upload progress indicators
- [ ] File preview before analysis
- [ ] Drag-and-drop interface
- [ ] File list management (remove before analysis)
- [ ] User quota tracking (prevent abuse)
- [ ] Mobile-responsive upload interface

## Technical Design

### File Upload Flow

```
User selects files → Validation → Upload to temp storage → Display preview → Ready for analysis
                                        ↓
                                  Auto-delete after 24hrs
```

### Frontend Components

#### Code Upload Page (`/code-analysis/upload`)
```typescript
interface CodeFile {
  id: string
  name: string
  size: number
  type: string
  content?: string  // For preview
  uploadedAt: Date
  expiresAt: Date
  status: 'uploading' | 'ready' | 'analyzing' | 'error'
}

interface UploadState {
  files: CodeFile[]
  uploading: boolean
  quota: {
    filesUploaded: number
    maxFiles: number
    storageUsed: number
    maxStorage: number
  }
}
```

#### Components
- `CodeUploadZone` - Drag-drop upload area
- `CodeFileList` - List of uploaded files with actions
- `CodeFilePreview` - Syntax-highlighted preview
- `UploadQuotaIndicator` - Visual quota usage
- `FileTypeIndicator` - Icon/badge for file types

### Backend Implementation

#### API Endpoints
```python
POST   /api/code/upload              # Upload code files
GET    /api/code/files                # List user's uploaded files
GET    /api/code/file/{file_id}       # Get file details/content
DELETE /api/code/file/{file_id}       # Delete file
POST   /api/code/validate             # Validate files before upload
GET    /api/code/quota                # Get user quota info
```

#### File Storage Structure
```
/tmp/code-uploads/
  /{user_id}/
    /{session_id}/
      /{file_id}_{filename}
      metadata.json
```

#### File Validation
```python
ALLOWED_EXTENSIONS = {
    '.rpg', '.rpgle', '.sqlrpgle',
    '.cl', '.clle',
    '.sql',
    '.txt'  # For generic IBM i source
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_SESSION = 10
MAX_FILES_PER_USER_PER_DAY = 50
MAX_STORAGE_PER_USER = 100 * 1024 * 1024  # 100MB

class FileValidator:
    def validate_extension(file_name: str) -> bool
    def validate_size(file_size: int) -> bool
    def validate_content(file_content: bytes) -> bool
    def scan_for_credentials(file_content: str) -> List[str]  # Security
```

#### Code File Model
```python
class CodeFileUpload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    filename: str
    file_type: str
    file_size: int
    file_path: str
    uploaded_at: datetime
    expires_at: datetime
    analyzed: bool = False
    analysis_id: Optional[str] = None

class UploadSession(BaseModel):
    session_id: str
    user_id: str
    files: List[CodeFileUpload]
    created_at: datetime
    expires_at: datetime
    total_size: int
```

### Database Schema

```sql
-- Code uploads tracking
CREATE TABLE IF NOT EXISTS code_uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    analyzed BOOLEAN DEFAULT FALSE,
    analysis_id TEXT,
    deleted_at TIMESTAMP
);

-- Upload sessions
CREATE TABLE IF NOT EXISTS upload_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    total_files INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- User quotas
CREATE TABLE IF NOT EXISTS user_quotas (
    user_id TEXT PRIMARY KEY,
    daily_uploads INTEGER DEFAULT 0,
    daily_storage BIGINT DEFAULT 0,
    last_reset DATE DEFAULT CURRENT_DATE,
    lifetime_uploads INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_code_uploads_user
ON code_uploads(user_id, uploaded_at);

CREATE INDEX IF NOT EXISTS idx_code_uploads_session
ON code_uploads(session_id);

CREATE INDEX IF NOT EXISTS idx_code_uploads_expires
ON code_uploads(expires_at) WHERE deleted_at IS NULL;
```

### Auto-Cleanup System

```python
class FileCleanupService:
    """Automatic cleanup of expired files"""

    async def cleanup_expired_files(self):
        """Run every hour via cron/scheduler"""
        # Find expired files
        expired = await get_expired_files()

        for file in expired:
            # Delete from filesystem
            os.remove(file.file_path)

            # Mark as deleted in DB
            await mark_file_deleted(file.id)

        # Cleanup empty directories
        await cleanup_empty_dirs()

    async def reset_daily_quotas(self):
        """Reset quotas daily at midnight"""
        await db.execute("""
            UPDATE user_quotas
            SET daily_uploads = 0, daily_storage = 0
            WHERE last_reset < CURRENT_DATE
        """)
```

### Security Considerations

1. **File Content Scanning**
   - Scan for credentials (passwords, API keys)
   - Check for malicious patterns
   - Validate file encoding (UTF-8, EBCDIC)

2. **Access Control**
   - User can only access their own files
   - Session-based isolation
   - JWT authentication required

3. **Storage Isolation**
   - User-specific directories
   - Session-specific subdirectories
   - No file listing across users

4. **Quota Enforcement**
   - Per-file size limits
   - Per-session file count limits
   - Daily upload limits per user
   - Total storage limits

## Implementation Tasks

### Frontend Tasks
- [ ] Create `/code-analysis/upload` page
- [ ] Build drag-drop upload component
- [ ] Implement file validation UI
- [ ] Add upload progress indicators
- [ ] Create file list with preview
- [ ] Build quota usage display
- [ ] Add syntax highlighting for preview
- [ ] Implement file removal functionality
- [ ] Add mobile-responsive design
- [ ] Create error handling UI

### Backend Tasks
- [ ] Create code upload endpoints
- [ ] Implement file validation service
- [ ] Build temporary file storage system
- [ ] Add quota tracking and enforcement
- [ ] Create cleanup scheduler/cron job
- [ ] Implement session management
- [ ] Add file content scanning
- [ ] Build file metadata extraction
- [ ] Add authentication/authorization
- [ ] Create monitoring and logging

### Database Tasks
- [ ] Create code_uploads table
- [ ] Create upload_sessions table
- [ ] Create user_quotas table
- [ ] Add indexes for performance
- [ ] Create migration script
- [ ] Set up automated cleanup queries

### DevOps Tasks
- [ ] Configure Railway temp storage
- [ ] Set up cron job for cleanup
- [ ] Add monitoring for storage usage
- [ ] Configure file upload limits in nginx/proxy
- [ ] Set up alerts for quota violations

## Testing Requirements

### Unit Tests
- [ ] File validation logic
- [ ] Quota calculation
- [ ] File type detection
- [ ] Content scanning
- [ ] Cleanup logic

### Integration Tests
- [ ] Complete upload flow
- [ ] Multi-file upload
- [ ] Quota enforcement
- [ ] Auto-deletion after 24hrs
- [ ] Session management
- [ ] File preview retrieval

### E2E Tests
- [ ] Upload single file
- [ ] Upload multiple files
- [ ] Exceed file size limit (verify rejection)
- [ ] Exceed quota limit (verify blocking)
- [ ] Preview uploaded file
- [ ] Delete file manually
- [ ] Verify auto-cleanup after 24hrs

### Security Tests
- [ ] Upload unauthorized file type (verify rejection)
- [ ] Access another user's file (verify 403)
- [ ] Upload file with credentials (verify warning)
- [ ] Upload oversized file (verify rejection)
- [ ] Quota bypass attempts (verify blocking)

## UX Considerations

### Upload Interface
- Clear file type requirements
- Drag-drop with visual feedback
- Progress bars for large files
- Preview panel with syntax highlighting
- Easy file removal
- Clear quota indicators

### Error Messages
- "File type not supported. Please upload .rpg, .rpgle, .sqlrpgle, .cl, .clle, or .sql files"
- "File size exceeds 10MB limit. Please upload a smaller file"
- "Maximum 10 files per session. Please analyze current files first"
- "Daily upload limit reached. Please try again tomorrow"

### Success States
- "✓ {filename} uploaded successfully (expires in 24 hours)"
- "Ready to analyze {count} files"
- Quota indicator: "5/50 files uploaded today"

## Success Metrics

- **Upload Success Rate**: >95%
- **Average Upload Time**: <3 seconds for 1MB file
- **File Preview Load Time**: <1 second
- **Storage Cleanup**: 100% of expired files deleted within 1 hour
- **Quota Violations**: <1% of upload attempts

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing (unit, integration, E2E, security)
- [ ] Code reviewed and approved
- [ ] Security review completed
- [ ] Performance tested with max file size/count
- [ ] Auto-cleanup verified working
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- User authentication system (existing)
- Railway filesystem storage
- PostgreSQL database
- Frontend routing structure

## Risks

- **Risk**: Railway storage limits exceeded
  - **Mitigation**: Aggressive cleanup, user quotas, monitor usage

- **Risk**: Large files causing timeouts
  - **Mitigation**: Chunked upload, size limits, progress feedback

- **Risk**: Malicious file uploads
  - **Mitigation**: Content scanning, type validation, sandboxing

- **Risk**: Users uploading sensitive data
  - **Mitigation**: Credential scanning, warnings, automatic redaction

## Future Enhancements

- Cloud storage integration (S3/R2) for scalability
- Syntax validation during upload
- Automatic character set detection (EBCDIC → UTF-8)
- Folder/project upload support
- Version control for uploaded files
- Comparison between file versions

---

## Notes

This story enables the core value proposition of Phase 1 - personalized code analysis. Must be production-ready and secure before moving to STORY-007 (AI Code Analysis Engine).
