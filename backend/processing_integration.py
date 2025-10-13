"""
Integration code for Story-005 Processing Pipeline
Wires DocumentProcessingService into main.py
"""
import os
import asyncio
from typing import Optional

try:
    from document_processing_service import DocumentProcessingService
    from processing_routes import router as processing_router, set_processing_service
    from pdf_processor import PDFProcessor
except ImportError:
    from backend.document_processing_service import DocumentProcessingService
    from backend.processing_routes import router as processing_router, set_processing_service
    from backend.pdf_processor import PDFProcessor


# Global processing service instance
_processing_service: Optional[DocumentProcessingService] = None


def init_processing_service(vector_store, pdf_processor: PDFProcessor = None):
    """
    Initialize the document processing service

    Call this from main.py on startup after vector_store is initialized

    Example:
        from processing_integration import init_processing_service, processing_router

        # In main.py startup:
        processing_service = init_processing_service(vector_store, pdf_processor)
        app.include_router(processing_router)
    """
    global _processing_service

    if not _processing_service:
        _processing_service = DocumentProcessingService(
            vector_store=vector_store,
            pdf_processor=pdf_processor
        )
        set_processing_service(_processing_service)
        print("✅ Document Processing Service initialized (Story-005)")

    return _processing_service


def get_processing_service() -> Optional[DocumentProcessingService]:
    """Get the global processing service instance"""
    return _processing_service


async def migrate_old_jobs_to_new_system():
    """
    Migration helper: convert old in-memory jobs to new database-backed jobs

    This can be called once to migrate existing jobs from async_upload.py
    to the new processing_jobs table
    """
    try:
        from async_upload import upload_jobs
    except ImportError:
        from backend.async_upload import upload_jobs

    service = get_processing_service()
    if not service or not upload_jobs:
        return 0

    migrated = 0
    for job_id, old_job in upload_jobs.items():
        try:
            # Create new ProcessingJob from old format
            from processing_models import ProcessingJob, ProcessingStage

            stage_mapping = {
                'queued': ProcessingStage.QUEUED,
                'processing': ProcessingStage.EXTRACTING,
                'completed': ProcessingStage.COMPLETED,
                'failed': ProcessingStage.FAILED
            }

            new_job = ProcessingJob(
                job_id=old_job['job_id'],
                filename=old_job['filename'],
                file_path=old_job.get('file_path', ''),
                stage=stage_mapping.get(old_job['status'], ProcessingStage.QUEUED),
                metadata=old_job.get('metadata', {})
            )

            await service._save_job(new_job)
            migrated += 1

        except Exception as e:
            print(f"⚠️  Failed to migrate job {job_id}: {e}")

    print(f"📦 Migrated {migrated} jobs from old system")
    return migrated


# Export router for easy import
__all__ = [
    'init_processing_service',
    'get_processing_service',
    'processing_router',
    'migrate_old_jobs_to_new_system'
]
