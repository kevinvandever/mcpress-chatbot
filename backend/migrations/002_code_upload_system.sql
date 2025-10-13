-- Migration 002: Code Upload System Tables
-- Story: STORY-006
-- Created: 2025-10-13

-- =====================================================
-- Code Uploads Table
-- Tracks individual code file uploads with metadata
-- =====================================================
CREATE TABLE IF NOT EXISTS code_uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    analyzed BOOLEAN DEFAULT FALSE,
    analysis_id TEXT,
    deleted_at TIMESTAMP
);

-- Indexes for code_uploads
CREATE INDEX IF NOT EXISTS idx_code_uploads_user
ON code_uploads(user_id, uploaded_at);

CREATE INDEX IF NOT EXISTS idx_code_uploads_session
ON code_uploads(session_id);

CREATE INDEX IF NOT EXISTS idx_code_uploads_expires
ON code_uploads(expires_at) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_code_uploads_user_active
ON code_uploads(user_id) WHERE deleted_at IS NULL;

COMMENT ON TABLE code_uploads IS 'Individual code file uploads with 24-hour expiration';
COMMENT ON COLUMN code_uploads.file_type IS 'File extension: .rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt';
COMMENT ON COLUMN code_uploads.expires_at IS 'Auto-deletion timestamp (24 hours from upload)';
COMMENT ON COLUMN code_uploads.deleted_at IS 'Soft delete timestamp - NULL means active';

-- =====================================================
-- Upload Sessions Table
-- Groups related file uploads into sessions
-- =====================================================
CREATE TABLE IF NOT EXISTS upload_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    total_files INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Indexes for upload_sessions
CREATE INDEX IF NOT EXISTS idx_upload_sessions_user
ON upload_sessions(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_status
ON upload_sessions(status, expires_at);

COMMENT ON TABLE upload_sessions IS 'Groups of code files uploaded together for analysis';
COMMENT ON COLUMN upload_sessions.status IS 'Session status: active, completed, expired';
COMMENT ON COLUMN upload_sessions.total_files IS 'Number of files in session (max 10)';
COMMENT ON COLUMN upload_sessions.total_size IS 'Total bytes of all files in session';

-- =====================================================
-- User Quotas Table
-- Track daily upload limits per user
-- =====================================================
CREATE TABLE IF NOT EXISTS user_quotas (
    user_id TEXT PRIMARY KEY,
    daily_uploads INTEGER DEFAULT 0,
    daily_storage BIGINT DEFAULT 0,
    last_reset DATE DEFAULT CURRENT_DATE,
    lifetime_uploads INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for user_quotas
CREATE INDEX IF NOT EXISTS idx_user_quotas_last_reset
ON user_quotas(last_reset);

COMMENT ON TABLE user_quotas IS 'Daily upload quotas per user to prevent abuse';
COMMENT ON COLUMN user_quotas.daily_uploads IS 'Files uploaded today (resets daily, max 50)';
COMMENT ON COLUMN user_quotas.daily_storage IS 'Bytes uploaded today (resets daily)';
COMMENT ON COLUMN user_quotas.last_reset IS 'Last date quotas were reset';
COMMENT ON COLUMN user_quotas.lifetime_uploads IS 'Total files ever uploaded by user';

-- =====================================================
-- Triggers
-- =====================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_quotas_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for user_quotas
DROP TRIGGER IF EXISTS update_user_quotas_updated_at ON user_quotas;
CREATE TRIGGER update_user_quotas_updated_at
    BEFORE UPDATE ON user_quotas
    FOR EACH ROW
    EXECUTE FUNCTION update_user_quotas_timestamp();

-- =====================================================
-- Cleanup Functions
-- =====================================================

-- Function to cleanup expired code files (run hourly)
CREATE OR REPLACE FUNCTION cleanup_expired_code_files()
RETURNS TABLE(deleted_count INTEGER, freed_bytes BIGINT) AS $$
DECLARE
    deleted_files INTEGER;
    freed_storage BIGINT;
BEGIN
    -- Mark expired files as deleted
    WITH deleted AS (
        UPDATE code_uploads
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE expires_at < CURRENT_TIMESTAMP
        AND deleted_at IS NULL
        RETURNING id, file_size
    )
    SELECT COUNT(*), COALESCE(SUM(file_size), 0)
    INTO deleted_files, freed_storage
    FROM deleted;

    RETURN QUERY SELECT deleted_files, freed_storage;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_code_files IS 'Mark expired code files as deleted (run hourly via cron)';

-- Function to reset daily quotas (run daily at midnight)
CREATE OR REPLACE FUNCTION reset_daily_quotas()
RETURNS INTEGER AS $$
DECLARE
    reset_count INTEGER;
BEGIN
    WITH updated AS (
        UPDATE user_quotas
        SET
            daily_uploads = 0,
            daily_storage = 0,
            last_reset = CURRENT_DATE
        WHERE last_reset < CURRENT_DATE
        RETURNING user_id
    )
    SELECT COUNT(*) INTO reset_count FROM updated;

    RETURN reset_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reset_daily_quotas IS 'Reset daily upload quotas for all users (run daily at midnight)';

-- Function to purge old deleted files (run weekly)
CREATE OR REPLACE FUNCTION purge_old_deleted_files(days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    purged_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM code_uploads
        WHERE deleted_at < CURRENT_TIMESTAMP - (days_old || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO purged_count FROM deleted;

    RETURN purged_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION purge_old_deleted_files IS 'Permanently delete soft-deleted files older than specified days (default 7)';

-- Function to get user quota status
CREATE OR REPLACE FUNCTION get_user_quota_status(p_user_id TEXT)
RETURNS TABLE(
    daily_uploads_used INTEGER,
    daily_uploads_limit INTEGER,
    daily_storage_used BIGINT,
    daily_storage_limit BIGINT,
    can_upload BOOLEAN
) AS $$
DECLARE
    v_daily_uploads INTEGER;
    v_daily_storage BIGINT;
    v_uploads_limit INTEGER := 50;
    v_storage_limit BIGINT := 104857600; -- 100MB
BEGIN
    -- Get or create user quota
    INSERT INTO user_quotas (user_id, daily_uploads, daily_storage, last_reset)
    VALUES (p_user_id, 0, 0, CURRENT_DATE)
    ON CONFLICT (user_id) DO UPDATE
    SET
        daily_uploads = CASE
            WHEN user_quotas.last_reset < CURRENT_DATE THEN 0
            ELSE user_quotas.daily_uploads
        END,
        daily_storage = CASE
            WHEN user_quotas.last_reset < CURRENT_DATE THEN 0
            ELSE user_quotas.daily_storage
        END,
        last_reset = CURRENT_DATE
    RETURNING user_quotas.daily_uploads, user_quotas.daily_storage
    INTO v_daily_uploads, v_daily_storage;

    RETURN QUERY SELECT
        v_daily_uploads,
        v_uploads_limit,
        v_daily_storage,
        v_storage_limit,
        (v_daily_uploads < v_uploads_limit AND v_daily_storage < v_storage_limit);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_quota_status IS 'Get current quota usage for a user (auto-resets if needed)';

-- =====================================================
-- Statistics View
-- =====================================================
CREATE OR REPLACE VIEW code_upload_stats AS
SELECT
    COUNT(*) FILTER (WHERE deleted_at IS NULL) as active_files,
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) as deleted_files,
    COUNT(DISTINCT user_id) FILTER (WHERE deleted_at IS NULL) as active_users,
    COUNT(DISTINCT session_id) FILTER (WHERE deleted_at IS NULL) as active_sessions,
    COALESCE(SUM(file_size) FILTER (WHERE deleted_at IS NULL), 0) as total_storage_bytes,
    ROUND(AVG(file_size) FILTER (WHERE deleted_at IS NULL), 0) as avg_file_size_bytes,
    COUNT(*) FILTER (WHERE uploaded_at > CURRENT_TIMESTAMP - INTERVAL '24 hours' AND deleted_at IS NULL) as uploads_last_24h,
    COUNT(*) FILTER (WHERE expires_at < CURRENT_TIMESTAMP AND deleted_at IS NULL) as files_pending_cleanup
FROM code_uploads;

COMMENT ON VIEW code_upload_stats IS 'Real-time statistics for code upload system monitoring';

-- =====================================================
-- Initial Data / Verification
-- =====================================================

-- Verify tables were created
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 002 completed successfully';
    RAISE NOTICE '📊 Created tables: code_uploads, upload_sessions, user_quotas';
    RAISE NOTICE '🔧 Created functions: cleanup_expired_code_files, reset_daily_quotas, purge_old_deleted_files, get_user_quota_status';
    RAISE NOTICE '📈 Created view: code_upload_stats';
END $$;
