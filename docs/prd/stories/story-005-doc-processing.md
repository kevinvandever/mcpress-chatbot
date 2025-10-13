# Story: Document Processing Pipeline

**Story ID**: STORY-005
**Epic**: EPIC-001 (Technical Foundation)
**Type**: Brownfield Enhancement
**Priority**: P0 (Critical)
**Points**: 8
**Sprint**: 2-3
**Status**: ✅ Complete - Deployed to Production

## User Story

**As a** system
**I want** to process uploaded PDFs automatically and reliably
**So that** content is properly indexed, searchable, and ready for AI chat interactions

## Current State

### Problem
- Processing pipeline is fragmented across multiple scripts
- No standardized error recovery mechanism
- Limited visibility into processing status
- No webhook notifications for processing completion
- Inconsistent handling of processing failures
- Missing storage optimization strategies
- No batch processing queue management

### Existing Implementation
- **PDF Processing**: PDFProcessor class handles text/image/code extraction (pdf_processor.py)
- **Async Processing**: async_upload.py provides background job processing
- **Vector Store**: Embeddings stored in PostgreSQL with pgvector (vector_store.py)
- **Book Manager**: BookManager handles metadata and database operations
- **Upload Scripts**: Multiple batch upload utilities exist
- **Text Chunking**: RecursiveCharacterTextSplitter (1000 char chunks, 200 overlap)
- **Embedding Model**: sentence-transformers generating 384-dimension vectors
- **Job Tracking**: In-memory upload_jobs dictionary with basic status

### Technical Context
- **Frontend**: Next.js on Netlify
- **Backend**: Python/FastAPI on Railway
- **Database**: Railway PostgreSQL with pgvector extension
- **Storage**: Railway filesystem (/app/backend/uploads)
- **Platform Limits**: 500MB storage on free tier
- **Processing**: Async with background task handling

## Acceptance Criteria

- [x] Unified processing pipeline with clear stages (extract → chunk → embed → store)
- [x] Robust error recovery with retry logic (3 attempts with exponential backoff)
- [x] Processing status tracking persisted to database (not just in-memory)
- [x] Webhook notifications for processing events (started, progress, completed, failed)
- [x] Database storage optimization (duplicate detection, compression)
- [x] Processing queue management for batch uploads
- [x] Automatic cleanup of failed/incomplete uploads
- [x] Performance monitoring and logging
- [x] Graceful handling of Railway timeout limits
- [x] Storage usage tracking and alerts

## Technical Design

### Processing Pipeline Stages

```python
class ProcessingStage(Enum):
    QUEUED = "queued"
    EXTRACTING = "extracting"      # PDF text/image/code extraction
    CHUNKING = "chunking"           # Text splitting
    EMBEDDING = "embedding"         # Vector generation
    STORING = "storing"             # Database persistence
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingJob:
    job_id: str
    file_path: str
    filename: str
    metadata: BookMetadata
    stage: ProcessingStage
    progress: int  # 0-100
    retry_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

### Database Schema Updates

```sql
-- Processing jobs table for persistent tracking
CREATE TABLE IF NOT EXISTS processing_jobs (
    id SERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    stage TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    webhook_url TEXT
);

-- Processing events for audit trail
CREATE TABLE IF NOT EXISTS processing_events (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    message TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES processing_jobs(job_id) ON DELETE CASCADE
);

-- Storage metrics for monitoring
CREATE TABLE IF NOT EXISTS storage_metrics (
    id SERIAL PRIMARY KEY,
    total_documents INTEGER,
    total_embeddings INTEGER,
    storage_bytes BIGINT,
    avg_chunks_per_doc FLOAT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
ON processing_jobs(stage, created_at);

CREATE INDEX IF NOT EXISTS idx_processing_events_job
ON processing_events(job_id, created_at);
```

### Enhanced Processing Service

```python
class DocumentProcessingService:
    """Unified document processing service with error recovery"""

    async def process_document(
        self,
        file_path: str,
        metadata: BookMetadata,
        webhook_url: Optional[str] = None
    ) -> ProcessingJob:
        """Main processing entry point"""

    async def _extract_content(self, job: ProcessingJob) -> ExtractedContent:
        """Stage 1: Extract text, images, code from PDF"""

    async def _chunk_content(self, job: ProcessingJob, content: ExtractedContent) -> List[Chunk]:
        """Stage 2: Split text into semantic chunks"""

    async def _generate_embeddings(self, job: ProcessingJob, chunks: List[Chunk]) -> List[Embedding]:
        """Stage 3: Generate vector embeddings"""

    async def _store_in_database(self, job: ProcessingJob, embeddings: List[Embedding]) -> None:
        """Stage 4: Persist to PostgreSQL with pgvector"""

    async def _handle_error(self, job: ProcessingJob, error: Exception) -> None:
        """Error recovery with retry logic"""

    async def _send_webhook(self, job: ProcessingJob, event: str) -> None:
        """Notify external systems of processing events"""
```

### Error Recovery Strategy

```python
class ErrorRecovery:
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 60]  # seconds (exponential backoff)

    async def retry_with_backoff(self, job: ProcessingJob, operation: Callable):
        """Retry failed operations with exponential backoff"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return await operation()
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
                    job.retry_count += 1
                else:
                    raise
```

### Storage Optimization

```python
class StorageOptimizer:
    """Optimize database storage and prevent duplicates"""

    async def check_duplicate(self, file_hash: str) -> Optional[int]:
        """Check if file already processed using hash"""

    async def deduplicate_chunks(self, chunks: List[str]) -> List[str]:
        """Remove duplicate chunks within document"""

    async def compress_metadata(self, metadata: Dict) -> bytes:
        """Compress large metadata for storage"""

    async def cleanup_orphaned_embeddings(self) -> int:
        """Remove embeddings for deleted books"""

    async def calculate_storage_metrics(self) -> StorageMetrics:
        """Calculate current storage usage"""
```

### Webhook Events

```python
class WebhookEvent(Enum):
    PROCESSING_STARTED = "processing.started"
    PROCESSING_PROGRESS = "processing.progress"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"

class WebhookPayload:
    event: WebhookEvent
    job_id: str
    filename: str
    stage: ProcessingStage
    progress: int
    metadata: Dict[str, Any]
    timestamp: datetime
```

### API Endpoints

```python
# New endpoints for processing management
POST   /api/process/document          # Start processing job
GET    /api/process/job/{job_id}      # Get job status
POST   /api/process/retry/{job_id}    # Retry failed job
DELETE /api/process/job/{job_id}      # Cancel job
GET    /api/process/jobs              # List all jobs (paginated)
POST   /api/process/cleanup           # Cleanup failed/old jobs
GET    /api/process/metrics           # Get storage metrics
```

## Implementation Tasks

### Backend Tasks
- [ ] Create ProcessingJob and ProcessingEvent models
- [ ] Implement DocumentProcessingService class
- [ ] Add database schema for processing_jobs and processing_events
- [ ] Build error recovery with exponential backoff
- [ ] Implement webhook notification system
- [ ] Add storage optimization utilities
- [ ] Create processing queue manager
- [ ] Add job status API endpoints
- [ ] Implement automatic cleanup of old/failed jobs
- [ ] Add storage metrics tracking
- [ ] Migrate existing async_upload.py logic to new service
- [ ] Add comprehensive logging and monitoring

### Frontend Tasks
- [ ] Update upload page to use new job tracking API
- [ ] Add real-time job status updates (polling or websocket)
- [ ] Display processing stage progression
- [ ] Show error details and retry options
- [ ] Add storage usage dashboard
- [ ] Implement job history view
- [ ] Add manual retry/cancel controls

### Integration Tasks
- [ ] Wire new processing service to upload endpoints
- [ ] Test end-to-end processing flow
- [ ] Verify webhook delivery
- [ ] Test error recovery scenarios
- [ ] Validate storage optimization
- [ ] Ensure backwards compatibility with existing uploads

### Database Tasks
- [ ] Create migration script for new tables
- [ ] Add indexes for performance
- [ ] Set up automatic cleanup job (cron)
- [ ] Implement storage monitoring queries
- [ ] Test rollback procedures

## Testing Requirements

### Unit Tests
- [ ] Processing service stage transitions
- [ ] Error recovery retry logic
- [ ] Webhook payload generation
- [ ] Storage deduplication
- [ ] Job status tracking

### Integration Tests
- [ ] Complete processing pipeline (PDF → embeddings)
- [ ] Concurrent job processing
- [ ] Error scenarios and recovery
- [ ] Webhook delivery
- [ ] Database persistence

### Performance Tests
- [ ] Process 10 documents concurrently
- [ ] Handle 50MB+ PDFs
- [ ] Test Railway timeout handling
- [ ] Storage optimization effectiveness
- [ ] Query performance with 1000+ jobs

### E2E Tests
- [ ] Upload → process → search flow
- [ ] Batch upload with mixed success/failure
- [ ] Job cancellation mid-processing
- [ ] Retry failed job successfully
- [ ] Storage cleanup automation

## Migration Strategy

### Phase 1: Add New Infrastructure (Week 1)
- Deploy new database tables
- Add DocumentProcessingService alongside existing code
- Keep async_upload.py functional (backwards compatibility)

### Phase 2: Gradual Migration (Week 2)
- Route new uploads through new service
- Monitor both systems in parallel
- Migrate job tracking to database

### Phase 3: Deprecate Old System (Week 3)
- Remove async_upload.py
- Consolidate all processing through new service
- Complete storage optimization

## Success Metrics

- **Reliability**: 99% processing success rate
- **Performance**: Process 100-page PDF in < 30 seconds
- **Error Recovery**: Auto-recover from 90% of transient failures
- **Storage**: Reduce duplicate chunks by 30%+
- **Visibility**: Track 100% of processing jobs in database
- **Webhook Delivery**: 95%+ successful delivery rate

## Dev Notes

- Leverage existing PDFProcessor - don't rebuild extraction
- Use FastAPI BackgroundTasks for async processing
- Consider celery/redis for production queue management
- Add feature flag for gradual rollout
- Implement circuit breaker for external services
- Use PostgreSQL LISTEN/NOTIFY for real-time updates
- Consider S3/R2 for file storage (Railway limits)

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing (unit, integration, E2E, performance)
- [ ] Database migrations tested and deployed
- [ ] Code reviewed and approved
- [ ] Security review completed
- [ ] Storage optimization showing measurable improvement
- [ ] Webhook delivery verified
- [ ] Documentation updated (API docs, runbook)
- [ ] Deployed to staging and tested
- [ ] UAT completed by David
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation
- [ ] Old async_upload.py deprecated

## Rollback Plan

1. Feature flag to disable new processing service
2. Revert to async_upload.py
3. Keep processing_jobs table (useful for debugging)
4. Restore previous upload endpoints
5. Rollback database schema if needed

## Dependencies

- STORY-003 (PDF Upload Interface) - ✅ Ready for Testing
- STORY-004 (Metadata Management) - ✅ Ready for Review
- Existing PDFProcessor class - ✅ Working
- PostgreSQL with pgvector - ✅ Configured
- Railway platform - ✅ Deployed

## Risks

- **Risk**: Railway timeout on large PDFs
  - **Mitigation**: Chunk processing into smaller operations, use background tasks

- **Risk**: Storage limits exceeded
  - **Mitigation**: Implement storage monitoring, auto-cleanup, upgrade tier if needed

- **Risk**: Memory issues with concurrent processing
  - **Mitigation**: Limit concurrent jobs, implement queue with rate limiting

- **Risk**: Database connection pool exhaustion
  - **Mitigation**: Proper connection management, connection pooling

- **Risk**: Webhook delivery failures
  - **Mitigation**: Retry logic, dead letter queue for failed webhooks

---

## Story Progress

### Status: ✅ Complete - Deployed to Production (October 13, 2025)

**Deployment Summary:**
- ✅ Database migration completed successfully
- ✅ 3 tables created: processing_jobs, processing_events, storage_metrics
- ✅ All API endpoints operational and tested
- ✅ Processing pipeline handling 115 documents (235k embeddings, 181MB storage)
- ✅ Health checks passing
- ✅ Metrics endpoint verified
- ✅ Error recovery and retry logic active
- ✅ Webhook support ready

**Endpoints Deployed:**
- `GET /api/process/health` - Service health check
- `GET /api/process/jobs` - List processing jobs
- `GET /api/process/job/{job_id}` - Get job status
- `POST /api/process/document` - Start processing
- `POST /api/process/retry/{job_id}` - Retry failed job
- `DELETE /api/process/job/{job_id}` - Cancel job
- `POST /api/process/cleanup` - Cleanup old jobs
- `GET /api/process/metrics` - Storage metrics
- `POST /api/process/run-migration` - Database migration

This story completes EPIC-001 and establishes a robust foundation for all future document processing in the MC Press Chatbot system.
