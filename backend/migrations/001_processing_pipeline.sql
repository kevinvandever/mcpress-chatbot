-- Migration 001: Document Processing Pipeline Tables
-- Story: STORY-005
-- Created: 2025-10-13

-- =====================================================
-- Processing Jobs Table
-- Persistent tracking of document processing jobs
-- =====================================================
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

-- Indexes for processing_jobs
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
ON processing_jobs(stage, created_at);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_job_id
ON processing_jobs(job_id);

COMMENT ON TABLE processing_jobs IS 'Tracks document processing jobs with persistent state';
COMMENT ON COLUMN processing_jobs.stage IS 'Current processing stage: queued, extracting, chunking, embedding, storing, completed, failed';
COMMENT ON COLUMN processing_jobs.progress IS 'Progress percentage: 0-100';

-- =====================================================
-- Processing Events Table
-- Audit trail of processing events
-- =====================================================
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

-- Indexes for processing_events
CREATE INDEX IF NOT EXISTS idx_processing_events_job
ON processing_events(job_id, created_at);

CREATE INDEX IF NOT EXISTS idx_processing_events_type
ON processing_events(event_type, created_at);

COMMENT ON TABLE processing_events IS 'Audit trail of all processing events for debugging and monitoring';

-- =====================================================
-- Storage Metrics Table
-- Track storage usage over time
-- =====================================================
CREATE TABLE IF NOT EXISTS storage_metrics (
    id SERIAL PRIMARY KEY,
    total_documents INTEGER,
    total_embeddings INTEGER,
    storage_bytes BIGINT,
    avg_chunks_per_doc FLOAT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for storage_metrics
CREATE INDEX IF NOT EXISTS idx_storage_metrics_recorded_at
ON storage_metrics(recorded_at DESC);

COMMENT ON TABLE storage_metrics IS 'Historical storage usage metrics for monitoring and optimization';

-- =====================================================
-- Functions
-- =====================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for processing_jobs
DROP TRIGGER IF EXISTS update_processing_jobs_updated_at ON processing_jobs;
CREATE TRIGGER update_processing_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Cleanup function for old jobs
-- =====================================================
CREATE OR REPLACE FUNCTION cleanup_old_processing_jobs(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM processing_jobs
        WHERE created_at < CURRENT_TIMESTAMP - (days_old || ' days')::INTERVAL
        AND stage IN ('completed', 'failed')
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_processing_jobs IS 'Remove completed/failed jobs older than specified days (default 30)';
