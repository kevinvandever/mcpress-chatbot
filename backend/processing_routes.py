"""
API Routes for Document Processing Pipeline (Story-005)
New endpoints for job management and monitoring
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

try:
    from processing_models import (
        ProcessingJob, ProcessingStage, JobListResponse,
        JobStatusResponse, StartProcessingRequest, RetryJobRequest
    )
    from document_processing_service import DocumentProcessingService
except ImportError:
    from backend.processing_models import (
        ProcessingJob, ProcessingStage, JobListResponse,
        JobStatusResponse, StartProcessingRequest, RetryJobRequest
    )
    from backend.document_processing_service import DocumentProcessingService

router = APIRouter(prefix="/api/process", tags=["processing"])

# Global service instance (set by main.py)
_processing_service: Optional[DocumentProcessingService] = None


def set_processing_service(service: DocumentProcessingService):
    """Set the global processing service instance"""
    global _processing_service
    _processing_service = service


def get_service() -> DocumentProcessingService:
    """Get the processing service or raise error"""
    if not _processing_service:
        raise HTTPException(
            status_code=500,
            detail="Processing service not initialized"
        )
    return _processing_service


@router.post("/document", response_model=ProcessingJob)
async def start_processing(request: StartProcessingRequest):
    """
    Start a new document processing job

    This endpoint creates a new processing job and processes it asynchronously
    through the pipeline: extract → chunk → embed → store
    """
    service = get_service()

    try:
        job = await service.process_document(
            file_path=request.file_path,
            filename=request.filename,
            metadata=request.metadata,
            webhook_url=request.webhook_url
        )
        return job
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job

    Returns job details and recent events for monitoring progress
    """
    service = get_service()

    job = await service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Get recent events
    await service.init_pool()
    async with service.pool.acquire() as conn:
        event_rows = await conn.fetch("""
            SELECT event_type, stage, message, details, created_at
            FROM processing_events
            WHERE job_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, job_id)

        from processing_models import ProcessingEvent
        import json

        recent_events = [
            ProcessingEvent(
                job_id=job_id,
                event_type=row['event_type'],
                stage=ProcessingStage(row['stage']),
                message=row['message'],
                details=json.loads(row['details']) if row['details'] else {},
                created_at=row['created_at']
            )
            for row in event_rows
        ]

    return JobStatusResponse(job=job, recent_events=recent_events)


@router.post("/retry/{job_id}", response_model=ProcessingJob)
async def retry_job(job_id: str, request: RetryJobRequest = None):
    """
    Retry a failed processing job

    Resets the job state and restarts processing from the beginning
    """
    service = get_service()

    job = await service.retry_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not in failed state"
        )

    return job


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a processing job

    Marks the job as failed and stops processing
    Note: Cannot cancel already completed jobs
    """
    service = get_service()

    job = await service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.stage == ProcessingStage.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel completed job"
        )

    job.mark_failed("Cancelled by user")
    await service._save_job(job)
    await service._log_event(job, "JOB_CANCELLED", "Job cancelled by user request")

    return {"status": "success", "message": f"Job {job_id} cancelled"}


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    stage: Optional[ProcessingStage] = None
):
    """
    List all processing jobs with pagination

    Optionally filter by processing stage
    """
    service = get_service()

    offset = (page - 1) * page_size
    jobs = await service.list_jobs(
        limit=page_size,
        offset=offset,
        stage_filter=stage
    )

    # Get total count
    await service.init_pool()
    async with service.pool.acquire() as conn:
        if stage:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM processing_jobs WHERE stage = $1",
                stage.value
            )
        else:
            total = await conn.fetchval("SELECT COUNT(*) FROM processing_jobs")

    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/cleanup")
async def cleanup_old_jobs(days_old: int = Query(30, ge=1, le=365)):
    """
    Cleanup old completed/failed jobs

    Removes jobs older than specified days (default 30)
    """
    service = get_service()

    deleted_count = await service.cleanup_old_jobs(days_old)

    return {
        "status": "success",
        "message": f"Cleaned up {deleted_count} old jobs",
        "deleted_count": deleted_count
    }


@router.get("/metrics")
async def get_storage_metrics():
    """
    Get current storage metrics

    Returns document counts, storage size, and other statistics
    """
    service = get_service()

    if not service.storage_optimizer:
        await service.init_pool()

    metrics = await service.storage_optimizer.calculate_storage_metrics()

    return {
        "total_documents": metrics.total_documents,
        "total_embeddings": metrics.total_embeddings,
        "storage_bytes": metrics.storage_bytes,
        "storage_mb": round(metrics.storage_bytes / (1024 * 1024), 2),
        "avg_chunks_per_doc": round(metrics.avg_chunks_per_doc, 2),
        "recorded_at": metrics.recorded_at.isoformat()
    }


@router.get("/health")
async def processing_health_check():
    """
    Health check for processing service

    Verifies database connectivity and service status
    """
    service = get_service()

    try:
        await service.init_pool()

        # Test database query
        async with service.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        # Get job counts
        async with service.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE stage = 'queued') as queued,
                    COUNT(*) FILTER (WHERE stage = 'processing') as processing,
                    COUNT(*) FILTER (WHERE stage = 'completed') as completed,
                    COUNT(*) FILTER (WHERE stage = 'failed') as failed
                FROM processing_jobs
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)

        return {
            "status": "healthy",
            "database": "connected",
            "last_24h_stats": {
                "queued": stats['queued'] or 0,
                "processing": stats['processing'] or 0,
                "completed": stats['completed'] or 0,
                "failed": stats['failed'] or 0
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )
