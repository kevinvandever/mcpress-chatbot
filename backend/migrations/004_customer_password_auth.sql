-- Migration 004: Customer Password Authentication
-- Feature: chatmaster-password-auth
-- Created: 2025-01-01

-- =====================================================
-- Customer Passwords Table
-- Stores customer email-password records (bcrypt hashed)
-- =====================================================
CREATE TABLE IF NOT EXISTS customer_passwords (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_passwords_email ON customer_passwords(email);

COMMENT ON TABLE customer_passwords IS 'Stores customer password hashes for local authentication';
COMMENT ON COLUMN customer_passwords.email IS 'Customer email - unique, used as login identifier';
COMMENT ON COLUMN customer_passwords.password_hash IS 'bcrypt hashed password (work factor 12)';

-- =====================================================
-- Password Reset Tokens Table
-- Stores time-limited tokens for password reset flow
-- =====================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_email ON password_reset_tokens(email);

COMMENT ON TABLE password_reset_tokens IS 'Stores password reset tokens with expiry and usage tracking';
COMMENT ON COLUMN password_reset_tokens.token IS 'Cryptographically secure reset token (secrets.token_urlsafe)';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Token expiry time (1 hour from creation)';
COMMENT ON COLUMN password_reset_tokens.used IS 'Whether token has been consumed for a reset';

-- =====================================================
-- Trigger to auto-update updated_at on customer_passwords
-- =====================================================
CREATE OR REPLACE FUNCTION update_customer_passwords_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_customer_passwords_updated_at_trigger ON customer_passwords;
CREATE TRIGGER update_customer_passwords_updated_at_trigger
    BEFORE UPDATE ON customer_passwords
    FOR EACH ROW
    EXECUTE FUNCTION update_customer_passwords_updated_at();

-- =====================================================
-- Migration Complete
-- =====================================================
