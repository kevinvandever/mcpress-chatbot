"""
Processing Pipeline Models for Story-005
Tracks document processing jobs with persistent state
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ProcessingStage(str, Enum):
    """Processing pipeline stages"""
    QUEUED = "queued"
    EXTRACTING = "extracting"      # PDF text/image/code extraction
    CHUNKING = "chunking"           # Text splitting
    EMBEDDING = "embedding"         # Vector generation (if applicable)
    STORING = "storing"             # Database persistence
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookEvent(str, Enum):
    """Webhook event types"""
    PROCESSING_STARTED = "processing.started"
    PROCESSING_PROGRESS = "processing.progress"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"


class ProcessingJob(BaseModel):
    """
    Represents a document processing job
    Persisted to processing_jobs table
    """
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex}")
    filename: str
    file_path: str
    stage: ProcessingStage = ProcessingStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    retry_count: int = Field(default=0, ge=0)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    webhook_url: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_stage(self, stage: ProcessingStage, progress: int = None):
        """Update job stage and progress"""
        self.stage = stage
        if progress is not None:
            self.progress = progress
        self.updated_at = datetime.now()

        if stage == ProcessingStage.COMPLETED:
            self.completed_at = datetime.now()
            self.progress = 100

    def mark_failed(self, error: str):
        """Mark job as failed"""
        self.stage = ProcessingStage.FAILED
        self.error_message = error
        self.updated_at = datetime.now()
        self.completed_at = datetime.now()

    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1
        self.updated_at = datetime.now()


class ProcessingEvent(BaseModel):
    """
    Represents a processing event for audit trail
    Persisted to processing_events table
    """
    job_id: str
    event_type: str
    stage: ProcessingStage
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookPayload(BaseModel):
    """Payload sent to webhook endpoints"""
    event: WebhookEvent
    job_id: str
    filename: str
    stage: ProcessingStage
    progress: int
    metadata: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExtractedContent(BaseModel):
    """Content extracted from PDF"""
    chunks: List[Dict[str, Any]]
    total_pages: int
    images: List[Dict[str, Any]] = Field(default_factory=list)
    code_blocks: List[Dict[str, Any]] = Field(default_factory=list)


class StorageMetrics(BaseModel):
    """Storage usage metrics"""
    total_documents: int
    total_embeddings: int
    storage_bytes: int
    avg_chunks_per_doc: float
    recorded_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobListResponse(BaseModel):
    """Response for listing jobs"""
    jobs: List[ProcessingJob]
    total: int
    page: int
    page_size: int


class JobStatusResponse(BaseModel):
    """Response for job status endpoint"""
    job: ProcessingJob
    recent_events: List[ProcessingEvent] = Field(default_factory=list)


# API Request/Response Models

class StartProcessingRequest(BaseModel):
    """Request to start processing a document"""
    file_path: str
    filename: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    webhook_url: Optional[str] = None


class RetryJobRequest(BaseModel):
    """Request to retry a failed job"""
    job_id: str
    reset_retry_count: bool = False
