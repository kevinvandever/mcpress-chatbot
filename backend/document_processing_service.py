"""
Document Processing Service for Story-005
Unified, robust document processing pipeline with error recovery
"""
import asyncio
import asyncpg
import os
import json
import aiohttp
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path

try:
    from processing_models import (
        ProcessingJob, ProcessingEvent, ProcessingStage,
        WebhookEvent, WebhookPayload, ExtractedContent, StorageMetrics
    )
    from pdf_processor import PDFProcessor
except ImportError:
    from backend.processing_models import (
        ProcessingJob, ProcessingEvent, ProcessingStage,
        WebhookEvent, WebhookPayload, ExtractedContent, StorageMetrics
    )
    from backend.pdf_processor import PDFProcessor


class ErrorRecovery:
    """Error recovery with exponential backoff"""
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 60]  # seconds (exponential backoff)

    @classmethod
    async def retry_with_backoff(
        cls,
        job: ProcessingJob,
        operation: Callable,
        operation_name: str = "operation"
    ):
        """Retry failed operations with exponential backoff"""
        last_error = None

        for attempt in range(cls.MAX_RETRIES):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                job.increment_retry()

                if attempt < cls.MAX_RETRIES - 1:
                    delay = cls.RETRY_DELAYS[attempt]
                    print(f"⚠️  {operation_name} failed (attempt {attempt + 1}/{cls.MAX_RETRIES}): {e}")
                    print(f"   Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    print(f"❌ {operation_name} failed after {cls.MAX_RETRIES} attempts")
                    raise last_error


class StorageOptimizer:
    """Optimize database storage and prevent duplicates"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def check_duplicate(self, filename: str) -> bool:
        """Check if file already processed"""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM documents WHERE filename = $1",
                filename
            )
            return count > 0

    async def deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks within document"""
        seen = set()
        unique_chunks = []

        for chunk in chunks:
            content = chunk.get('content', '')
            # Use hash of content as deduplication key
            chunk_hash = hash(content)

            if chunk_hash not in seen:
                seen.add(chunk_hash)
                unique_chunks.append(chunk)

        if len(unique_chunks) < len(chunks):
            print(f"   Deduplicated: {len(chunks)} → {len(unique_chunks)} chunks")

        return unique_chunks

    async def cleanup_orphaned_embeddings(self) -> int:
        """Remove embeddings for deleted documents"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM documents
                WHERE filename NOT IN (
                    SELECT DISTINCT filename FROM documents WHERE content IS NOT NULL
                )
            """)
            return int(result.split()[-1]) if result else 0

    async def calculate_storage_metrics(self) -> StorageMetrics:
        """Calculate current storage usage"""
        async with self.pool.acquire() as conn:
            # Get document and embedding counts
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT filename) as total_documents,
                    COUNT(*) as total_embeddings,
                    COALESCE(SUM(LENGTH(content)), 0) as storage_bytes
                FROM documents
            """)

            # Calculate average chunks per document
            avg_chunks = 0.0
            if stats['total_documents'] and stats['total_documents'] > 0:
                avg_chunks = float(stats['total_embeddings']) / float(stats['total_documents'])

            return StorageMetrics(
                total_documents=stats['total_documents'] or 0,
                total_embeddings=stats['total_embeddings'] or 0,
                storage_bytes=stats['storage_bytes'] or 0,
                avg_chunks_per_doc=avg_chunks
            )


class DocumentProcessingService:
    """
    Unified document processing service with error recovery
    Replaces the fragmented async_upload.py approach
    """

    def __init__(self, vector_store, pdf_processor: PDFProcessor = None):
        self.vector_store = vector_store
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.pool: Optional[asyncpg.Pool] = None
        self.storage_optimizer: Optional[StorageOptimizer] = None

    async def init_pool(self):
        """Initialize database connection pool"""
        if not self.pool:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            self.pool = await asyncpg.create_pool(database_url)
            self.storage_optimizer = StorageOptimizer(self.pool)

    async def process_document(
        self,
        file_path: str,
        filename: str,
        metadata: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> ProcessingJob:
        """
        Main processing entry point
        Creates job and processes through all stages
        """
        await self.init_pool()

        # Create processing job
        job = ProcessingJob(
            filename=filename,
            file_path=file_path,
            metadata=metadata,
            webhook_url=webhook_url
        )

        # Save job to database
        await self._save_job(job)
        await self._log_event(job, "JOB_CREATED", "Job created and queued")
        await self._send_webhook(job, WebhookEvent.PROCESSING_STARTED)

        # Process through stages
        try:
            # Stage 1: Extract content from PDF
            job.update_stage(ProcessingStage.EXTRACTING, progress=10)
            await self._save_job(job)
            extracted_content = await self._extract_content(job)
            await self._log_event(job, "EXTRACTION_COMPLETE", f"Extracted {len(extracted_content.chunks)} chunks")

            # Stage 2: Deduplicate chunks
            job.update_stage(ProcessingStage.CHUNKING, progress=40)
            await self._save_job(job)
            unique_chunks = await self.storage_optimizer.deduplicate_chunks(extracted_content.chunks)
            await self._log_event(job, "CHUNKING_COMPLETE", f"Deduplicated to {len(unique_chunks)} chunks")

            # Stage 3: Store in database
            job.update_stage(ProcessingStage.STORING, progress=70)
            await self._save_job(job)
            await self._store_in_database(job, extracted_content, unique_chunks)
            await self._log_event(job, "STORING_COMPLETE", "Stored in vector database")

            # Complete
            job.update_stage(ProcessingStage.COMPLETED, progress=100)
            await self._save_job(job)
            await self._log_event(job, "JOB_COMPLETED", "Processing completed successfully")
            await self._send_webhook(job, WebhookEvent.PROCESSING_COMPLETED)

            return job

        except Exception as e:
            await self._handle_error(job, e)
            raise

    async def _extract_content(self, job: ProcessingJob) -> ExtractedContent:
        """Stage 1: Extract text, images, code from PDF"""
        async def extract_operation():
            result = await self.pdf_processor.process_pdf(job.file_path)
            return ExtractedContent(
                chunks=result.get('chunks', []),
                total_pages=result.get('total_pages', 0),
                images=result.get('images', []),
                code_blocks=result.get('code_blocks', [])
            )

        return await ErrorRecovery.retry_with_backoff(
            job,
            extract_operation,
            operation_name="PDF extraction"
        )

    async def _store_in_database(
        self,
        job: ProcessingJob,
        extracted_content: ExtractedContent,
        chunks: List[Dict[str, Any]]
    ) -> None:
        """Stage 4: Persist to PostgreSQL/vector store"""
        async def store_operation():
            # Prepare metadata
            doc_metadata = {
                **job.metadata,
                "total_pages": extracted_content.total_pages,
                "has_images": len(extracted_content.images) > 0,
                "has_code": len(extracted_content.code_blocks) > 0,
                "processing_job_id": job.job_id,
                "processed_at": datetime.now().isoformat()
            }

            # Store in vector database
            await self.vector_store.add_documents(
                documents=chunks,
                metadata=doc_metadata
            )

        await ErrorRecovery.retry_with_backoff(
            job,
            store_operation,
            operation_name="Database storage"
        )

    async def _handle_error(self, job: ProcessingJob, error: Exception) -> None:
        """Error recovery with retry logic"""
        error_message = str(error)
        job.mark_failed(error_message)
        await self._save_job(job)
        await self._log_event(job, "JOB_FAILED", f"Error: {error_message}")
        await self._send_webhook(job, WebhookEvent.PROCESSING_FAILED)

    async def _send_webhook(self, job: ProcessingJob, event: WebhookEvent) -> None:
        """Notify external systems of processing events"""
        if not job.webhook_url:
            return

        payload = WebhookPayload(
            event=event,
            job_id=job.job_id,
            filename=job.filename,
            stage=job.stage,
            progress=job.progress,
            metadata=job.metadata,
            error_message=job.error_message
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    job.webhook_url,
                    json=payload.dict(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"⚠️  Webhook delivery failed: {response.status}")
        except Exception as e:
            print(f"⚠️  Webhook error: {e}")
            # Don't fail the job if webhook fails

    async def _save_job(self, job: ProcessingJob) -> None:
        """Save job state to database"""
        await self.init_pool()

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_jobs
                (job_id, filename, file_path, stage, progress, retry_count, error_message,
                 metadata, created_at, updated_at, completed_at, webhook_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (job_id) DO UPDATE SET
                    stage = $4,
                    progress = $5,
                    retry_count = $6,
                    error_message = $7,
                    metadata = $8,
                    updated_at = $10,
                    completed_at = $11
            """,
                job.job_id, job.filename, job.file_path, job.stage.value,
                job.progress, job.retry_count, job.error_message,
                json.dumps(job.metadata), job.created_at, job.updated_at,
                job.completed_at, job.webhook_url
            )

    async def _log_event(
        self,
        job: ProcessingJob,
        event_type: str,
        message: str,
        details: Dict[str, Any] = None
    ) -> None:
        """Log processing event for audit trail"""
        event = ProcessingEvent(
            job_id=job.job_id,
            event_type=event_type,
            stage=job.stage,
            message=message,
            details=details or {}
        )

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_events
                (job_id, event_type, stage, message, details, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                event.job_id, event.event_type, event.stage.value,
                event.message, json.dumps(event.details), event.created_at
            )

    async def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job status by ID"""
        await self.init_pool()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM processing_jobs WHERE job_id = $1",
                job_id
            )

            if not row:
                return None

            return ProcessingJob(
                job_id=row['job_id'],
                filename=row['filename'],
                file_path=row['file_path'],
                stage=ProcessingStage(row['stage']),
                progress=row['progress'],
                retry_count=row['retry_count'],
                error_message=row['error_message'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at'],
                webhook_url=row['webhook_url']
            )

    async def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        stage_filter: Optional[ProcessingStage] = None
    ) -> List[ProcessingJob]:
        """List processing jobs with pagination"""
        await self.init_pool()

        query = "SELECT * FROM processing_jobs"
        params = []

        if stage_filter:
            query += " WHERE stage = $1"
            params.append(stage_filter.value)

        query += " ORDER BY created_at DESC LIMIT $%d OFFSET $%d" % (
            len(params) + 1, len(params) + 2
        )
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [
                ProcessingJob(
                    job_id=row['job_id'],
                    filename=row['filename'],
                    file_path=row['file_path'],
                    stage=ProcessingStage(row['stage']),
                    progress=row['progress'],
                    retry_count=row['retry_count'],
                    error_message=row['error_message'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    completed_at=row['completed_at'],
                    webhook_url=row['webhook_url']
                )
                for row in rows
            ]

    async def retry_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Retry a failed job"""
        job = await self.get_job_status(job_id)
        if not job or job.stage != ProcessingStage.FAILED:
            return None

        # Reset job state
        job.stage = ProcessingStage.QUEUED
        job.progress = 0
        job.error_message = None
        job.retry_count = 0
        await self._save_job(job)

        # Restart processing
        return await self.process_document(
            job.file_path,
            job.filename,
            job.metadata,
            job.webhook_url
        )

    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Remove completed/failed jobs older than specified days"""
        await self.init_pool()

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "SELECT cleanup_old_processing_jobs($1)",
                days_old
            )
            return int(result) if result else 0

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
