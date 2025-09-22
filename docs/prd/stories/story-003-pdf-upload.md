# Story: PDF Upload Interface

**Story ID**: STORY-003  
**Epic**: EPIC-001 (Technical Foundation)  
**Type**: Brownfield Enhancement  
**Priority**: P0 (Critical)  
**Points**: 8  
**Sprint**: 2  
**Status**: Ready for Testing  

## User Story

**As an** admin  
**I want** to upload PDFs with metadata through a web interface  
**So that** I can add new books to the chatbot knowledge base without using command-line scripts  

## Current State

### Problem
- No web interface to add new book content (only scripts exist)
- Manual command-line operations required for content updates
- No way to associate metadata with documents via UI
- Cannot batch upload multiple PDFs through the web
- No validation or processing feedback in the UI

### Existing Implementation
- **Database**: Books table exists with fields: id, filename, title, author, category, total_pages, file_hash, processed_at
- **Embeddings**: Embeddings table with pgvector support (vector(384))
- **Processing**: PDFProcessor class handles text extraction and embedding generation
- **Upload Scripts**: Multiple batch upload scripts exist (railway_batch_upload.py, etc.)
- **BookManager**: Manages metadata with BookMetadata dataclass
- **API Endpoints**: /upload, /batch-upload, /complete-upload exist in backend
- **Admin Dashboard**: Links to /admin/upload (page doesn't exist yet)

### Technical Context
- Frontend: Next.js on Netlify
- Backend: Python/FastAPI on Railway  
- Database: Railway PostgreSQL with pgvector extension
- Storage: Local filesystem in /app/backend/uploads on Railway
- Vector DB: pgvector embeddings (384 dimensions) using sentence-transformers
- Existing upload processing pipeline works well

## Acceptance Criteria

- [x] Single file upload with drag-drop interface at /admin/upload
- [x] Batch upload supporting up to 10 files simultaneously
- [x] Real-time progress indicators during upload and processing
- [x] Metadata form matching existing BookMetadata fields:
  - [x] Title (required, auto-generated from filename if not provided)
  - [x] Author (optional)
  - [x] Category (required, select from predefined categories)
  - [x] Subcategory (optional, based on category selection)
  - [x] MC Press URL (optional, validated URL format)
  - [x] Description (optional, text area)
  - [x] Tags (optional, comma-separated)
- [x] File validation:
  - [x] PDF format only
  - [x] Maximum 100MB per file (matching MAX_FILE_SIZE_MB env var)
  - [ ] Duplicate detection using file hash (backend handles this)
- [x] Success/failure notifications with details
- [x] Processing status display (pending/processing/completed/failed)
- [x] Integration with existing upload endpoints

## Technical Design

### Frontend Components

#### Upload Page (`/admin/upload`)
```typescript
// Match existing BookMetadata from backend
interface BookMetadata {
  filename: string
  title: string
  category: string
  subcategory?: string
  author?: string
  year?: number
  tags?: string[]
  description?: string
  mc_press_url?: string
}

interface UploadState {
  files: File[]
  metadata: BookMetadata[]
  uploadProgress: Record<string, number>
  processingStatus: Record<string, 'pending' | 'processing' | 'completed' | 'failed'>
}
```

#### Components Structure
- `FileDropzone` - Drag-drop area with file selection
- `MetadataForm` - Form matching BookMetadata fields with category selector
- `UploadProgress` - Real-time progress using existing endpoints
- `CategorySelector` - Dropdown with predefined categories from BookManager

### Backend Integration

#### Use Existing Endpoints
- `POST /upload` - Single file upload (existing)
- `POST /batch-upload` - Multiple file upload (existing)
- `POST /complete-upload` - Submit metadata after upload (existing)
- `GET /documents` - Get list of uploaded documents (existing)

### Database Schema (Existing)

```sql
-- Existing books table (Railway PostgreSQL)
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    filename TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    total_pages INTEGER,
    file_hash TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Existing embeddings table with pgvector
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    content TEXT,
    embedding vector(384),
    page_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Existing indexes
CREATE INDEX IF NOT EXISTS idx_books_filename ON books(filename);
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
CREATE INDEX IF NOT EXISTS idx_embeddings_book_id ON embeddings(book_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Processing Pipeline (Uses Existing)

1. **File Upload Stage**
   - Use existing `/upload` or `/batch-upload` endpoints
   - Validate file format (PDF only) and size (100MB limit)
   - Generate file hash using existing logic
   - Store in /app/backend/uploads directory

2. **Metadata Stage**
   - Use BookManager.add_book() for metadata storage
   - Category suggestion using BookManager.suggest_category()
   - URL validation using BookManager.validate_url()
   - Submit via `/complete-upload` endpoint

3. **Processing Stage (Existing)**
   - PDFProcessor.process_pdf() for text extraction
   - Generate embeddings using sentence-transformers (384 dimensions)
   - Store in PostgreSQL with pgvector
   - Update book stats with BookManager.update_book_stats()

4. **Completion**
   - Book automatically available for chat queries
   - Update displayed statistics
   - Show success notification

### Security Considerations

- Authentication required (using existing admin auth from STORY-002)
- File type validation (PDF only)
- File size limits enforced
- Sanitize file names
- Use existing admin session management

## Implementation Tasks

### Frontend Tasks
- [x] Create /admin/upload page component
- [x] Implement FileDropzone component with drag-drop support
- [x] Build MetadataForm with category selector
- [x] Add file validation (PDF only, 100MB limit)
- [x] Create progress indicators for upload status
- [x] Connect to existing upload endpoints
- [x] Add error handling and user feedback
- [x] Ensure mobile responsive design

### Backend Tasks (Minimal - Use Existing)
- [ ] Ensure /batch-upload endpoint handles multiple files properly
- [ ] Verify /complete-upload works with frontend metadata
- [ ] Add any missing CORS headers for admin routes
- [ ] Test existing processing pipeline with UI uploads

### Integration Tasks
- [x] Wire up frontend to existing endpoints
- [ ] Test file upload flow end-to-end
- [ ] Verify metadata is properly stored
- [ ] Confirm embeddings are generated correctly

## Testing Requirements

### Unit Tests
- [ ] File validation logic
- [ ] Metadata validation
- [ ] PDF text extraction
- [ ] Embedding generation

### Integration Tests
- [ ] Complete upload flow
- [ ] Batch upload handling
- [ ] Error recovery
- [ ] Progress tracking

### E2E Tests
- [ ] Upload single PDF with metadata
- [ ] Batch upload multiple PDFs
- [ ] Handle upload failures gracefully
- [ ] Verify processed content searchable

## Dev Notes

- Leverage existing upload infrastructure extensively
- The backend already has robust PDF processing - just need UI
- Use existing BookManager for metadata operations
- Processing pipeline is proven and works well with pgvector
- Focus on creating a clean, intuitive admin interface
- Consider adding a document management page in future stories

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code reviewed and approved
- [ ] Security review completed
- [ ] Performance tested with large PDFs (50MB)
- [ ] Deployed to staging environment
- [ ] UAT completed by David
- [ ] Documentation updated
- [ ] Deployed to production
- [ ] Monitoring confirms stable uploads

## Rollback Plan

1. Feature flag to disable upload interface
2. Preserve uploaded files in storage
3. Maintain processing queue for retry
4. Rollback database migrations if needed
5. Notify admin users of temporary unavailability

## Dependencies

- STORY-002 (Admin Authentication) - ✅ COMPLETED
- Existing backend infrastructure - ✅ Already in place
- PostgreSQL with pgvector - ✅ Already configured
- PDF processing pipeline - ✅ Already working

## Risks

- **Risk**: Large PDF processing timeout
  - **Mitigation**: Implement chunked processing with progress tracking

- **Risk**: Storage costs for many large PDFs
  - **Mitigation**: Implement storage quotas and compression

- **Risk**: Malicious file uploads
  - **Mitigation**: Virus scanning and sandboxed processing

---

## Dev Agent Record

### Agent Model Used
claude-opus-4-1-20250805 (Dexter)

### Debug Log References
- Implemented drag-drop PDF upload interface with react-dropzone
- Connected to existing /batch-upload and /complete-upload endpoints
- Fixed SSR issues for Netlify deployment (localStorage checks)
- Metadata form matches existing BookMetadata structure
- Category selector uses predefined categories from backend
- Progress indicators show upload/processing status

### Completion Notes
- Full upload interface implemented at /admin/upload
- Drag-drop supports up to 10 PDFs simultaneously
- Metadata editing for each file with all BookMetadata fields
- Real-time status updates (pending/uploading/processing/completed/failed)
- Mobile responsive design
- Integration with existing authentication from STORY-002
- Ready for deployment to Netlify

### File List
**Frontend:**
- `frontend/app/admin/upload/page.tsx` - Main upload page component with dropzone and metadata form

**Dependencies:**
- Added react-dropzone for file upload UI

### Change Log
- 2025-09-22 1:18 PM: Story created and ready for development
- 2025-09-22 1:41 PM: Implemented upload interface with existing backend integration