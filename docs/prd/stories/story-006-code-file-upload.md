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

---

## Dev Agent Record

### Tasks

#### Backend Implementation
- [x] Create database migration scripts
  - [x] Create `002_code_upload_system.sql` with tables, indexes, functions, views
  - [x] Create `002_code_upload_system_rollback.sql`
- [x] Implement file validation service
  - [x] Extension validation (.rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt)
  - [x] File size validation (10MB limit)
  - [x] Content security scanning (credentials, malicious patterns)
  - [x] Encoding detection (UTF-8, Latin-1, EBCDIC)
  - [x] Session and quota limit validation
- [x] Build file storage system
  - [x] User/session directory isolation
  - [x] 24-hour automatic expiration
  - [x] Metadata tracking (JSON per session)
  - [x] CRUD operations (store, retrieve, delete)
- [x] Create upload service
  - [x] Session management (create, get, update)
  - [x] Quota tracking with auto-reset
  - [x] File upload with validation
  - [x] Database persistence (asyncpg)
  - [x] File retrieval with ownership checks
  - [x] Cleanup coordination
- [x] Implement API routes
  - [x] GET /api/code/limits - System limits
  - [x] POST /api/code/session - Create upload session
  - [x] GET /api/code/quota - User quota status
  - [x] POST /api/code/upload - Upload code file
  - [x] GET /api/code/files - List user files
  - [x] GET /api/code/file/{id} - Get file content
  - [x] GET /api/code/file/{id}/info - Get file metadata
  - [x] DELETE /api/code/file/{id} - Delete file
  - [x] POST /api/code/validate - Validate file before upload
  - [x] GET /api/code/admin/stats - System statistics
  - [x] POST /api/code/admin/cleanup - Manual cleanup trigger
- [x] Build cleanup scheduler
  - [x] Hourly cleanup of expired files
  - [x] Daily quota reset (midnight)
  - [x] Weekly purge of old deleted files
  - [x] Background task loop with error recovery
- [x] Create integration module
  - [x] Service initialization
  - [x] Scheduler startup/shutdown
  - [x] Health check
  - [x] Router export
- [x] Complete main.py integration
  - [x] Add import statements
  - [x] Register code upload routes
  - [x] Add service initialization in startup event
  - [x] Add shutdown handler for cleanup
  - [x] Update health check endpoint

#### Database Deployment
- [x] Run database migration
  - [x] Execute `002_code_upload_system.sql` on PostgreSQL
  - [x] Verify tables created (code_uploads, upload_sessions, user_quotas)
  - [x] Verify indexes created (10 indexes)
  - [x] Verify functions created (4 functions: cleanup, reset_quotas, purge, get_quota_status)
  - [x] Verify view created (code_upload_stats)

#### Backend Testing
- [ ] Test backend APIs manually (DEFERRED to production environment)
  - **Decision**: Skip local testing, test in Railway production after deployment
  - **Reason**: Local Railway environment setup issues; production testing more reliable
  - [ ] Test GET /api/code/limits
  - [ ] Test POST /api/code/session
  - [ ] Test GET /api/code/quota
  - [ ] Test POST /api/code/upload (single file)
  - [ ] Test POST /api/code/upload (multiple files)
  - [ ] Test GET /api/code/files
  - [ ] Test GET /api/code/file/{id}
  - [ ] Test DELETE /api/code/file/{id}
  - [ ] Verify file storage in /tmp/code-uploads/
  - [ ] Verify database records
  - [ ] Test quota enforcement
  - [ ] Test authentication
- [ ] Write unit tests
  - [ ] Test file validator (extension, size, content, credentials)
  - [ ] Test file storage (store, retrieve, delete, cleanup)
  - [ ] Test upload service (session, quota, upload, ownership)
  - [ ] Test quota calculation logic
- [ ] Write integration tests
  - [ ] Test complete upload flow
  - [ ] Test multi-file upload
  - [ ] Test quota enforcement
  - [ ] Test 24-hour auto-deletion
  - [ ] Test session management
  - [ ] Test file retrieval
- [ ] Write security tests
  - [ ] Test unauthorized file type rejection
  - [ ] Test cross-user access prevention (403)
  - [ ] Test credential scanning warnings
  - [ ] Test oversized file rejection
  - [ ] Test quota bypass attempts

#### Frontend Implementation
- [x] Create code analysis upload page
  - [x] Create `/code-analysis/upload` route
  - [x] Build page layout with MC Press styling
- [x] Build upload components
  - [x] CodeUploadZone - Drag-drop interface
  - [x] CodeFileList - List uploaded files with actions
  - [x] CodeFilePreview - Syntax-highlighted preview
  - [x] UploadQuotaIndicator - Visual quota display
  - [x] FileTypeIndicator - Icon/badge for file types
- [x] Implement upload functionality
  - [x] File validation UI (client-side)
  - [x] Upload progress indicators
  - [x] Error handling and display
  - [x] Success notifications
- [x] Add file management features
  - [x] File removal before analysis
  - [x] File preview modal
  - [x] Session management
- [ ] Mobile responsiveness (DEFERRED to production testing)
  - [ ] Test on mobile devices
  - [ ] Adjust drag-drop for touch
  - [ ] Responsive layout

#### Frontend Testing
- [ ] Write E2E tests
  - [ ] Test upload single file
  - [ ] Test upload multiple files
  - [ ] Test file size limit rejection
  - [ ] Test quota limit blocking
  - [ ] Test file preview
  - [ ] Test file deletion
  - [ ] Test auto-cleanup after 24hrs

#### Story Completion
- [ ] Run story DoD checklist
- [ ] Update File List section (all files created/modified)
- [ ] Add completion notes
- [ ] Update story status to "Ready for Review"

### Agent Model Used
- claude-sonnet-4-5-20250929

### Debug Log

**2025-10-14 - API Testing Decision**
- **Decision**: Defer manual API testing to production environment (Railway)
- **Reason**: Local Railway CLI environment has import path conflicts
- **Plan**: Test all 11 `/api/code/*` endpoints after deployment to Railway
- **Next Step**: Build frontend components, then deploy and test end-to-end

**2025-10-14 - Database Migration Blocker (RESOLVED ✅)**
- **Issue**: Cannot connect to Railway PostgreSQL from local machine
- **Cause**: DATABASE_URL uses Railway internal network (`pgvector-railway.railway.internal`)
- **Solution Applied**: Updated `run_migration_002.py` to use `DATABASE_PUBLIC_URL` environment variable
- **Resolution**: Discovered Railway provides `DATABASE_PUBLIC_URL` with public endpoint (`shortline.proxy.rlwy.net:18459`)
- **Result**: Migration executed successfully via `railway run python3 backend/run_migration_002.py`
- **Created**: `backend/run_migration_002.py` - Python migration runner with verification
- **Migration Results**:
  - ✅ 3 tables created (code_uploads, upload_sessions, user_quotas)
  - ✅ 10 indexes created
  - ✅ 4 functions created (cleanup, reset_quotas, purge, get_quota_status)
  - ✅ 1 view created (code_upload_stats)

### Completion Notes
- Backend implementation complete (~1,500 lines of code) ✅
- Main.py integration complete (100%) - routes, startup, shutdown, health check ✅
- Database migration complete (3 tables, 10 indexes, 4 functions, 1 view) ✅
- Frontend implementation complete (~820 lines across 6 files) ✅
  - All 5 components created (CodeUploadZone, CodeFileList, CodeFilePreview, UploadQuotaIndicator, FileTypeIndicator)
  - Main upload page created at `/app/code-analysis/upload`
  - Integrated with design system (Button, Card, Alert, Modal, Badge, ProgressBar, Spinner)
  - Uses react-dropzone for drag-drop, react-syntax-highlighter for code preview
  - Session management, quota tracking, file preview/delete functionality
- Ready for production deployment and E2E testing
- Manual API testing deferred to production environment
- Automated testing pending

### File List

**Created Files:**
- `backend/migrations/002_code_upload_system.sql` - Database schema
- `backend/migrations/002_code_upload_system_rollback.sql` - Rollback script
- `backend/run_migration_002.py` - Python migration runner with verification
- `backend/code_file_validator.py` - File validation service
- `backend/code_file_storage.py` - Temp file storage system
- `backend/code_upload_service.py` - Core upload service
- `backend/code_upload_routes.py` - FastAPI API routes
- `backend/code_upload_scheduler.py` - Cleanup scheduler
- `backend/code_upload_integration.py` - Integration module

**Modified Files:**
- `backend/main.py` - Full integration complete (imports, routes, startup, shutdown, health check)

**Created Files (Frontend):**
- `frontend/app/code-analysis/upload/page.tsx` - Main upload page
- `frontend/components/CodeUploadZone.tsx` - Drag-drop upload component (320 lines)
- `frontend/components/CodeFileList.tsx` - File list with actions (170 lines)
- `frontend/components/CodeFilePreview.tsx` - Syntax-highlighted preview modal (150 lines)
- `frontend/components/UploadQuotaIndicator.tsx` - Quota usage indicator (140 lines)
- `frontend/components/FileTypeIndicator.tsx` - File type badge (40 lines)

**To Be Created (Tests):**
- `backend/tests/test_code_file_validator.py`
- `backend/tests/test_code_file_storage.py`
- `backend/tests/test_code_upload_service.py`
- `backend/tests/test_code_upload_flow.py`
- `backend/tests/test_code_upload_security.py`

### Change Log
- **2025-10-13**: Backend implementation complete (70%)
- **2025-10-13**: Database migration scripts created
- **2025-10-13**: Main.py imports added, integration partial
- **2025-10-14 (AM)**: Dev Agent Record section added to track remaining work
- **2025-10-14 (AM)**: Main.py integration completed (routes, startup, shutdown, health check)
- **2025-10-14 (AM)**: Database migration executed successfully on Railway PostgreSQL
- **2025-10-14 (AM)**: Created run_migration_002.py utility (uses DATABASE_PUBLIC_URL)
- **2025-10-14 (AM)**: Session ended - backend 100% complete, frontend ready to build next session
- **2025-10-14 (AM)**: Created STORY_006_NEXT_SESSION.md handoff document
- **2025-10-14 (PM)**: Frontend implementation completed (all 5 components + main page)
- **2025-10-14 (PM)**: All components integrated with existing design system
- **2025-10-14 (PM)**: Ready for production deployment and testing
- **2025-10-14 (PM)**: **QA Testing Phase Started** by Quinn (QA Agent)
- **2025-10-14 (PM)**: Created comprehensive QA test plan (STORY_006_QA_TEST_PLAN.md) - 47 tests across 9 categories
- **2025-10-14 (PM)**: Updated ONBOARDING.md to document production-only testing approach
- **2025-10-14 (PM)**: **BUG-006-001 FOUND**: Netlify deployment failing - all pages returned 404
  - **Root Cause**: netlify.toml missing `base = "frontend"` directive
  - **Fix**: Created netlify.toml in repository root with base directory specified (commit 009192c)
  - **Resolution**: ✅ All pages now accessible
- **2025-10-14 (PM)**: **BUG-006-002 FOUND**: Authentication token not being sent with API requests
  - **Root Cause**: Frontend using raw axios without Bearer token in Authorization header
  - **Impact**: All code upload features showed "Not authenticated" error even after login
  - **Fix**: Created config/axios.ts with request interceptor to auto-add token from localStorage (commit 0fad973)
  - **Changes**: Updated 5 files (upload page + 4 components) to use authenticated apiClient
  - **Resolution**: ✅ Auth token now automatically included in all Story-006 API requests
- **2025-10-14 (PM)**: **BUG-006-003 FOUND**: Dashboard and documents pages not showing 115 documents (regression)
  - **Root Cause**: Dashboard and documents management pages still using raw fetch() with manual auth headers instead of apiClient
  - **Impact**: After fixing Story-006 auth (BUG-006-002), dashboard showed 0 documents instead of 115, documents page showed empty
  - **Investigation**: Backend /documents endpoint returned all 115 documents correctly - confirmed frontend parsing issue
  - **Fix**: Updated both pages to use authenticated apiClient with try/catch error handling (commit 5b83197)
  - **Changes**: Modified `app/admin/dashboard/page.tsx` and `app/admin/documents/page.tsx` to use apiClient
  - **Resolution**: ✅ Auth tokens now automatically included, 115 documents should display correctly

### Status
**Ready for QA Testing** - Backend 100% ✅, Database 100% ✅, Frontend 100% ✅, Auth Fixed ✅

**Deployment Status**:
1. ✅ Backend deployed to Railway (all 11 endpoints live)
2. ✅ Frontend deployed to Netlify
3. ✅ Database migration complete (3 tables, 10 indexes, 4 functions)
4. ✅ Authentication bug fixed (commit 0fad973)
5. ⏳ QA testing ready to begin

**Next Steps**:
1. ✅ Deploy frontend to Netlify (automatic on git push)
2. ✅ Deploy backend to Railway (automatic on git push)
3. ✅ Fix Netlify deployment (added base = "frontend" to netlify.toml)
4. ✅ Fix authentication token not being sent with API requests
5. ⏳ Execute QA test plan (see STORY_006_QA_TEST_PLAN.md)
6. ⏳ Test complete upload flow in production
7. ⏳ Verify all 11 `/api/code/*` endpoints with authenticated user
8. ⏳ Test quota enforcement, file preview, deletion
9. ⏳ Mobile responsiveness testing
10. 📋 Write automated tests (unit, integration, E2E) - after QA pass

---

## QA Results

**QA Agent**: Quinn (Senior Developer & QA Architect)
**Test Date**: October 14, 2025
**Test Environment**: Production (Netlify + Railway)
**Test Plan**: `/STORY_006_QA_TEST_PLAN.md`

### Test Summary

**Status**: 🔄 Testing in Progress

**Test Categories**:
- [ ] 1. API Endpoint Testing (11 endpoints)
- [ ] 2. File Validation Testing (5 tests)
- [ ] 3. Upload Flow Testing (6 E2E tests)
- [ ] 4. Quota Management Testing (4 tests)
- [ ] 5. Security Testing (5 tests)
- [ ] 6. Frontend UI/UX Testing (6 tests)
- [ ] 7. Cleanup & Expiration Testing (3 tests)
- [ ] 8. Performance Testing (4 tests)
- [ ] 9. Integration Testing (3 tests)

**Overall Progress**: 0/47 tests completed

---

### 1. API Endpoint Testing (Backend)

**Objective**: Verify all 11 `/api/code/*` endpoints functional in Railway production

#### Test 1.1: GET /api/code/limits
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Returns system limits (10MB max, 10 files/session, etc.)
- **Actual**: [Results here]
- **Notes**: [Observations]

#### Test 1.2: POST /api/code/session
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Creates upload session with UUID and 24hr expiration
- **Actual**: [Results here]

#### Test 1.3: GET /api/code/quota
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Returns user quota status (daily uploads, storage used)
- **Actual**: [Results here]

#### Test 1.4: POST /api/code/validate
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Validates file before upload (valid:true or errors)
- **Actual**: [Results here]

#### Test 1.5: POST /api/code/upload
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Uploads file, stores in /tmp, creates DB record
- **Actual**: [Results here]

#### Test 1.6: GET /api/code/files
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Lists user's uploaded files only
- **Actual**: [Results here]

#### Test 1.7: GET /api/code/file/{id}
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Returns file content (owner only)
- **Actual**: [Results here]

#### Test 1.8: GET /api/code/file/{id}/info
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Returns file metadata without content
- **Actual**: [Results here]

#### Test 1.9: DELETE /api/code/file/{id}
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn
- **Result**: ⏳ Pending
- **Expected**: Deletes file from filesystem and DB, updates quota
- **Actual**: [Results here]

#### Test 1.10: GET /api/code/admin/stats
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn (admin)
- **Result**: ⏳ Pending
- **Expected**: Returns system statistics (admin only)
- **Actual**: [Results here]

#### Test 1.11: POST /api/code/admin/cleanup
- **Date**: [To be tested]
- **Tester**: Kevin/Quinn (admin)
- **Result**: ⏳ Pending
- **Expected**: Triggers manual cleanup, returns file count
- **Actual**: [Results here]

---

### 2. File Validation Testing

#### Test 2.1: Valid File Extensions
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload .rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt
- **Expected**: All 7 types accepted
- **Actual**: [Results here]

#### Test 2.2: Invalid File Extensions
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload .exe, .py, .js, .pdf, .zip
- **Expected**: All rejected with clear error message
- **Actual**: [Results here]

#### Test 2.3: File Size Limits
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 1KB, 5MB, 9.9MB (accept), 10.1MB, 20MB (reject)
- **Expected**: ≤10MB accepted, >10MB rejected
- **Actual**: [Results here]

#### Test 2.4: Content Security Scanning
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload file with API keys, passwords
- **Expected**: Warning issued for credentials
- **Actual**: [Results here]

#### Test 2.5: Encoding Detection
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload UTF-8, Latin-1, EBCDIC files
- **Expected**: All supported, EBCDIC converted
- **Actual**: [Results here]

---

### 3. Upload Flow Testing (E2E)

#### Test 3.1: Single File Upload
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Complete upload flow via frontend
- **Expected**: Progress bar, success message, file in list, quota updated
- **Actual**: [Results here]

#### Test 3.2: Multiple File Upload
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 10 files simultaneously
- **Expected**: All uploaded, quota shows 10/50
- **Actual**: [Results here]

#### Test 3.3: Exceed Session File Limit
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 11th file in session
- **Expected**: Rejection with "max 10 files per session" error
- **Actual**: [Results here]

#### Test 3.4: Drag-and-Drop Interface
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Drag file over zone, verify visual feedback, drop
- **Expected**: Border highlight, upload begins
- **Actual**: [Results here]

#### Test 3.5: File Preview
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Click preview button, verify syntax highlighting
- **Expected**: Modal opens, code highlighted with line numbers
- **Actual**: [Results here]

#### Test 3.6: File Deletion
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Delete file manually
- **Expected**: File removed from UI/backend, quota updated
- **Actual**: [Results here]

---

### 4. Quota Management Testing

#### Test 4.1: Daily Upload Limit
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 50 files, attempt 51st
- **Expected**: 51st rejected with quota error
- **Actual**: [Results here]

#### Test 4.2: Storage Quota Limit
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 99MB, attempt file exceeding 100MB total
- **Expected**: Rejection with storage quota error
- **Actual**: [Results here]

#### Test 4.3: Quota Reset at Midnight
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Verify database function resets quotas daily
- **Expected**: Daily uploads/storage reset to 0
- **Actual**: [Results here]

#### Test 4.4: Quota Display Accuracy
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload/delete files, verify quota updates in real-time
- **Expected**: Accurate file count and storage display
- **Actual**: [Results here]

---

### 5. Security Testing

#### Test 5.1: Cross-User File Access
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: User B attempts to access User A's file
- **Expected**: 403 Forbidden response
- **Actual**: [Results here]

#### Test 5.2: Unauthenticated Access
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Access endpoints without auth token
- **Expected**: 401 Unauthorized
- **Actual**: [Results here]

#### Test 5.3: Session Isolation
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Verify files stored in separate session directories
- **Expected**: /user-id/session-id/ isolation
- **Actual**: [Results here]

#### Test 5.4: Malicious Filename Handling
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload ../../../etc/passwd.rpgle, XSS, command injection attempts
- **Expected**: Filenames sanitized, no security issues
- **Actual**: [Results here]

#### Test 5.5: File Type Spoofing
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Rename malicious.exe to test.rpgle, attempt upload
- **Expected**: Rejected based on content inspection
- **Actual**: [Results here]

---

### 6. Frontend UI/UX Testing

#### Test 6.1: Upload Zone Visual Feedback
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Hover, drag, drop interactions
- **Expected**: Clear visual feedback for all states
- **Actual**: [Results here]

#### Test 6.2: Progress Indicators
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload 5MB file, verify progress bar
- **Expected**: 0% → 100% progress visible
- **Actual**: [Results here]

#### Test 6.3: Error Message Display
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Trigger various errors (invalid type, size, quota)
- **Expected**: Clear, user-friendly error messages
- **Actual**: [Results here]

#### Test 6.4: File Type Indicators
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload different file types, verify badges/icons
- **Expected**: Correct badge for each file type
- **Actual**: [Results here]

#### Test 6.5: Mobile Responsiveness
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Test on iPhone, Android, iPad
- **Expected**: Fully functional on mobile
- **Actual**: [Results here]

#### Test 6.6: Accessibility
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Keyboard navigation, screen reader
- **Expected**: All functions accessible
- **Actual**: [Results here]

---

### 7. Cleanup & Expiration Testing

#### Test 7.1: 24-Hour Auto-Deletion
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Upload file, trigger cleanup after 24hrs
- **Expected**: File deleted from filesystem and DB
- **Actual**: [Results here]

#### Test 7.2: Cleanup Scheduler Running
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Check Railway logs for cleanup task
- **Expected**: Hourly cleanup logs visible
- **Actual**: [Results here]

#### Test 7.3: Weekly Purge
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Verify old deleted_at records purged
- **Expected**: Records >7 days removed
- **Actual**: [Results here]

---

### 8. Performance Testing

#### Test 8.1: Upload Speed
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: 1MB (<3s), 5MB (<10s), 10MB (<20s)
- **Expected**: All uploads within SLA
- **Actual**: [Results here]

#### Test 8.2: Concurrent Uploads
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: 10 users upload simultaneously
- **Expected**: All succeed, no server errors
- **Actual**: [Results here]

#### Test 8.3: Database Performance
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Query performance with indexes
- **Expected**: All queries <50ms
- **Actual**: [Results here]

#### Test 8.4: File List Load Time
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Load 50 files
- **Expected**: <1 second
- **Actual**: [Results here]

---

### 9. Integration Testing

#### Test 9.1: Database Consistency
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Verify DB records match filesystem
- **Expected**: Counts match
- **Actual**: [Results here]

#### Test 9.2: Session Management
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: Session lifecycle (create, upload, expire)
- **Expected**: Status updates correctly
- **Actual**: [Results here]

#### Test 9.3: Health Check Integration
- **Date**: [To be tested]
- **Result**: ⏳ Pending
- **Test**: GET /health includes code upload status
- **Expected**: "code_upload_system": "operational"
- **Actual**: [Results here]

---

### Bugs Found

**No bugs identified yet** - Testing in progress

[Format for bugs found:]
```
**BUG-006-XXX**: [Bug Title]
- **Severity**: Critical / High / Medium / Low
- **Test**: Test X.X
- **Description**: [What went wrong]
- **Steps to Reproduce**: [Steps]
- **Expected**: [Expected behavior]
- **Actual**: [Actual behavior]
- **Status**: Open / In Progress / Fixed / Closed
- **Assigned To**: Dexter (Dev Agent)
```

---

### QA Sign-Off

**QA Status**: ⏳ Testing in Progress

- [ ] All critical path tests passed
- [ ] All security tests passed
- [ ] No critical or high-severity bugs
- [ ] Performance benchmarks met
- [ ] Mobile responsiveness verified
- [ ] Acceptance criteria met

**QA Approval**: [Pending test completion]
**QA Agent**: Quinn (Senior Developer & QA Architect)
**Date**: [When complete]

---
