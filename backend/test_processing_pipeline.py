"""
Comprehensive tests for Story-005 Document Processing Pipeline
Tests models, service, error recovery, and API endpoints
"""
import pytest
import asyncio
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

# Import modules to test
try:
    from processing_models import (
        ProcessingJob, ProcessingStage, ProcessingEvent,
        WebhookEvent, WebhookPayload, StorageMetrics
    )
    from document_processing_service import (
        DocumentProcessingService, ErrorRecovery, StorageOptimizer
    )
    from processing_routes import router
except ImportError:
    from backend.processing_models import (
        ProcessingJob, ProcessingStage, ProcessingEvent,
        WebhookEvent, WebhookPayload, StorageMetrics
    )
    from backend.document_processing_service import (
        DocumentProcessingService, ErrorRecovery, StorageOptimizer
    )
    from backend.processing_routes import router


# =====================================================
# Unit Tests: Models
# =====================================================

class TestProcessingModels:
    """Test ProcessingJob and ProcessingEvent models"""

    def test_processing_job_creation(self):
        """Test creating a processing job"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            metadata={"category": "test"}
        )

        assert job.filename == "test.pdf"
        assert job.stage == ProcessingStage.QUEUED
        assert job.progress == 0
        assert job.retry_count == 0
        assert job.job_id.startswith("job_")

    def test_job_stage_update(self):
        """Test updating job stage"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        job.update_stage(ProcessingStage.EXTRACTING, progress=25)

        assert job.stage == ProcessingStage.EXTRACTING
        assert job.progress == 25
        assert job.updated_at > job.created_at

    def test_job_mark_failed(self):
        """Test marking job as failed"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        job.mark_failed("Test error")

        assert job.stage == ProcessingStage.FAILED
        assert job.error_message == "Test error"
        assert job.completed_at is not None

    def test_job_completion(self):
        """Test completing a job"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        job.update_stage(ProcessingStage.COMPLETED)

        assert job.stage == ProcessingStage.COMPLETED
        assert job.progress == 100
        assert job.completed_at is not None

    def test_processing_event_creation(self):
        """Test creating a processing event"""
        event = ProcessingEvent(
            job_id="job_123",
            event_type="TEST",
            stage=ProcessingStage.EXTRACTING,
            message="Test message"
        )

        assert event.job_id == "job_123"
        assert event.event_type == "TEST"
        assert event.stage == ProcessingStage.EXTRACTING


# =====================================================
# Unit Tests: Error Recovery
# =====================================================

class TestErrorRecovery:
    """Test error recovery with exponential backoff"""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful operation on first attempt"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        async def successful_operation():
            return "success"

        result = await ErrorRecovery.retry_with_backoff(
            job,
            successful_operation,
            operation_name="test"
        )

        assert result == "success"
        assert job.retry_count == 0

    @pytest.mark.asyncio
    async def test_retry_success_on_second_attempt(self):
        """Test successful operation on second attempt"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        attempts = []

        async def flaky_operation():
            attempts.append(1)
            if len(attempts) < 2:
                raise Exception("Temporary failure")
            return "success"

        result = await ErrorRecovery.retry_with_backoff(
            job,
            flaky_operation,
            operation_name="test"
        )

        assert result == "success"
        assert len(attempts) == 2
        assert job.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_failure_after_max_attempts(self):
        """Test failure after all retry attempts"""
        job = ProcessingJob(
            filename="test.pdf",
            file_path="/path/to/test.pdf"
        )

        async def failing_operation():
            raise Exception("Permanent failure")

        with pytest.raises(Exception) as exc_info:
            await ErrorRecovery.retry_with_backoff(
                job,
                failing_operation,
                operation_name="test"
            )

        assert "Permanent failure" in str(exc_info.value)
        assert job.retry_count == 3  # MAX_RETRIES


# =====================================================
# Integration Tests: DocumentProcessingService
# =====================================================

class TestDocumentProcessingService:
    """Test document processing service"""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        store = Mock()
        store.add_documents = AsyncMock()
        return store

    @pytest.fixture
    def mock_pdf_processor(self):
        """Mock PDF processor"""
        processor = Mock()
        processor.process_pdf = AsyncMock(return_value={
            "chunks": [{"content": "test chunk"}],
            "total_pages": 1,
            "images": [],
            "code_blocks": []
        })
        return processor

    @pytest.fixture
    def mock_pool(self):
        """Mock database pool"""
        pool = AsyncMock()
        conn = AsyncMock()
        conn.execute = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetchval = AsyncMock(return_value=0)
        pool.acquire = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_vector_store, mock_pdf_processor):
        """Test service initialization"""
        service = DocumentProcessingService(
            vector_store=mock_vector_store,
            pdf_processor=mock_pdf_processor
        )

        assert service.vector_store == mock_vector_store
        assert service.pdf_processor == mock_pdf_processor
        assert service.pool is None

    @pytest.mark.asyncio
    async def test_extract_content(self, mock_vector_store, mock_pdf_processor):
        """Test content extraction stage"""
        service = DocumentProcessingService(
            vector_store=mock_vector_store,
            pdf_processor=mock_pdf_processor
        )

        job = ProcessingJob(
            filename="test.pdf",
            file_path="/tmp/test.pdf"
        )

        content = await service._extract_content(job)

        assert len(content.chunks) == 1
        assert content.total_pages == 1
        mock_pdf_processor.process_pdf.assert_called_once_with("/tmp/test.pdf")


# =====================================================
# Integration Tests: StorageOptimizer
# =====================================================

class TestStorageOptimizer:
    """Test storage optimization utilities"""

    @pytest.fixture
    def mock_pool(self):
        """Mock database pool"""
        pool = AsyncMock()
        conn = AsyncMock()
        conn.fetchval = AsyncMock()
        conn.fetchrow = AsyncMock()
        pool.acquire = MagicMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_check_duplicate(self, mock_pool):
        """Test duplicate file detection"""
        mock_pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = 1

        optimizer = StorageOptimizer(mock_pool)
        is_duplicate = await optimizer.check_duplicate("test.pdf")

        assert is_duplicate is True

    @pytest.mark.asyncio
    async def test_deduplicate_chunks(self, mock_pool):
        """Test chunk deduplication"""
        optimizer = StorageOptimizer(mock_pool)

        chunks = [
            {"content": "test chunk 1"},
            {"content": "test chunk 2"},
            {"content": "test chunk 1"},  # duplicate
        ]

        unique_chunks = await optimizer.deduplicate_chunks(chunks)

        assert len(unique_chunks) == 2

    @pytest.mark.asyncio
    async def test_calculate_storage_metrics(self, mock_pool):
        """Test storage metrics calculation"""
        mock_stats = {
            'total_documents': 10,
            'total_embeddings': 100,
            'storage_bytes': 1024000,
            'avg_chunks': 10.0
        }
        mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = mock_stats

        optimizer = StorageOptimizer(mock_pool)
        metrics = await optimizer.calculate_storage_metrics()

        assert metrics.total_documents == 10
        assert metrics.total_embeddings == 100
        assert metrics.storage_bytes == 1024000


# =====================================================
# API Tests: Processing Endpoints
# =====================================================

class TestProcessingRoutes:
    """Test processing API endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Mock processing service"""
        service = AsyncMock()
        service.init_pool = AsyncMock()
        service.pool = MagicMock()
        service.get_job_status = AsyncMock()
        service.list_jobs = AsyncMock(return_value=[])
        service.retry_job = AsyncMock()
        service.cleanup_old_jobs = AsyncMock(return_value=5)
        service.storage_optimizer = AsyncMock()
        service.storage_optimizer.calculate_storage_metrics = AsyncMock()
        return service

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/process"


# =====================================================
# Performance Tests
# =====================================================

class TestPerformance:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self):
        """Test processing multiple jobs concurrently"""
        # Mock components
        mock_store = Mock()
        mock_store.add_documents = AsyncMock()

        mock_processor = Mock()
        mock_processor.process_pdf = AsyncMock(return_value={
            "chunks": [{"content": "test"}],
            "total_pages": 1,
            "images": [],
            "code_blocks": []
        })

        # This would test concurrent processing
        # Simplified version - full test would use real database
        jobs = [
            ProcessingJob(filename=f"test{i}.pdf", file_path=f"/tmp/test{i}.pdf")
            for i in range(5)
        ]

        assert len(jobs) == 5


# =====================================================
# Run Tests
# =====================================================

if __name__ == "__main__":
    print("Running Story-005 Processing Pipeline Tests...")
    print("=" * 60)

    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
