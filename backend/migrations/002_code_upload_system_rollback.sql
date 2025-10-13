-- Migration 002 Rollback: Code Upload System
-- Story: STORY-006
-- Created: 2025-10-13

-- =====================================================
-- ROLLBACK: Drop all objects created in migration 002
-- =====================================================

-- Drop view
DROP VIEW IF EXISTS code_upload_stats;

-- Drop functions
DROP FUNCTION IF EXISTS get_user_quota_status(TEXT);
DROP FUNCTION IF EXISTS purge_old_deleted_files(INTEGER);
DROP FUNCTION IF EXISTS reset_daily_quotas();
DROP FUNCTION IF EXISTS cleanup_expired_code_files();
DROP FUNCTION IF EXISTS update_user_quotas_timestamp();

-- Drop triggers
DROP TRIGGER IF EXISTS update_user_quotas_updated_at ON user_quotas;

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS code_uploads CASCADE;
DROP TABLE IF EXISTS upload_sessions CASCADE;
DROP TABLE IF EXISTS user_quotas CASCADE;

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 002 rollback completed successfully';
    RAISE NOTICE '🗑️  Dropped tables: code_uploads, upload_sessions, user_quotas';
    RAISE NOTICE '🗑️  Dropped functions and view';
END $$;
