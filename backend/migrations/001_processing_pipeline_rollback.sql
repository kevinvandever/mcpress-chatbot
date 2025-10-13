-- Rollback Migration 001: Document Processing Pipeline Tables
-- Story: STORY-005

-- Drop functions
DROP FUNCTION IF EXISTS cleanup_old_processing_jobs(INTEGER);
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop tables (CASCADE will drop foreign key constraints)
DROP TABLE IF EXISTS processing_events CASCADE;
DROP TABLE IF EXISTS processing_jobs CASCADE;
DROP TABLE IF NOT EXISTS storage_metrics CASCADE;

-- Note: This rollback preserves the existing 'documents' table
-- and does not affect existing document data
