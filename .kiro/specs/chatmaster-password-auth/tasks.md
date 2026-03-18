# Implementation Tasks: ChatMaster Password Authentication

## Task 1: Database Migration
- [x] 1.1 Create `backend/migrations/004_customer_password_auth.sql` with idempotent CREATE TABLE IF NOT EXISTS for `customer_passwords` (id, email unique, password_hash, created_at, updated_at) and `password_reset_tokens` (id, email, token unique, expires_at, used, created_at) tables with indexes
- [x] 1.2 Create `backend/run_migration_004.py` API endpoint to execute the migration via HTTP (following existing pattern from run_migration_003)
- [x] 1.3 Register the migration endpoint in `backend/main.py`

## Task 2: Password Service
- [x] 2.1 Create `backend/password_service.py` with `PasswordService` class containing: `validate_password()` returning list of failed rules, `hash_password()` using bcrypt with work factor 12, `verify_password()` for bcrypt comparison, `get_customer()` DB lookup by email, `create_customer()` to insert new record, `update_password()` to update hash
- [x] 2.2 Implement password validation rules: min 8 chars, uppercase, lowercase, digit, special character from set `!@#$%^&*()_+-=[]{}|;:,.<>?` — each rule returns a specific failure message

## Task 3: Reset Token Service
- [x] 3.1 Create `backend/reset_token_service.py` with `ResetTokenService` class containing: `create_reset_token()` using `secrets.token_urlsafe`, `validate_token()` checking existence/expiry/used status, `mark_token_used()`, `check_rate_limit()` enforcing 3 requests per email per hour
- [x] 3.2 Implement token invalidation: when creating a new token for an email, mark all previous tokens for that email as used

## Task 4: Email Service
- [x] 4.1 Create `backend/email_service.py` with `EmailService` class: SMTP configuration from env vars (EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_FROM_ADDRESS, EMAIL_SMTP_PASSWORD, FRONTEND_URL), `enabled` flag based on config presence, `send_reset_email()` method, `_build_reset_url()`, `_build_email_html()` with MC ChatMaster branding
- [x] 4.2 Add graceful degradation: log warning at startup if email env vars missing, return 503 for forgot-password when disabled

## Task 5: Modify Login Flow
- [x] 5.1 Update `CustomerLoginRequest` in `backend/subscription_auth.py` to add `password: str` field
- [x] 5.2 Modify `SubscriptionAuthService.login()` to: lookup customer_passwords by email → if record exists, verify password (401 on mismatch) → proceed to Appstle check → if no record + valid password + active subscription, create record → issue JWT
- [x] 5.3 Update login route in `backend/subscription_auth_routes.py` to pass `body.password` to `auth_service.login()`

## Task 6: Add Password Reset Routes
- [x] 6.1 Add `POST /api/auth/forgot-password` route: validate rate limit → generate token → send email → return generic success message (same response for existing and non-existing emails)
- [x] 6.2 Add `POST /api/auth/reset-password` route: validate token → validate password rules → update hash → mark token used → return success
- [x] 6.3 Add `POST /api/auth/validate-reset-token` route: check token validity → return valid/invalid with masked email
- [x] 6.4 Add Pydantic models `ForgotPasswordRequest` and `ResetPasswordRequest` to subscription_auth.py

## Task 7: Environment Configuration
- [x] 7.1 Update `backend/config.py` to load EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_FROM_ADDRESS, EMAIL_SMTP_PASSWORD, and FRONTEND_URL from environment
- [x] 7.2 Update `.env.example` with the new email-related environment variables

## Task 8: Frontend Login Page Update
- [x] 8.1 Modify `frontend/app/login/page.tsx`: add password input field below email, add "Forgot Password?" link pointing to `/forgot-password`, update form submission to include password in POST body
- [x] 8.2 Handle first-time setup response: when backend returns `needs_password_setup`, display password requirements and "Create Password" button
- [x] 8.3 Update error handling for new response codes (401 password mismatch, 400 password validation errors with specific rule failures)

## Task 9: Frontend Forgot Password Page
- [x] 9.1 Create `frontend/app/forgot-password/page.tsx` with email input form, submit to `/api/auth/forgot-password`, success message "Check your email for a reset link", rate limit error handling (429), MC ChatMaster branding consistent with login page
- [x] 9.2 Create `frontend/app/api/auth/forgot-password/route.ts` proxy to backend `/api/auth/forgot-password`

## Task 10: Frontend Reset Password Page
- [x] 10.1 Create `frontend/app/reset-password/page.tsx`: read token from URL query params, validate token on mount via `/api/auth/validate-reset-token`, show password form with rules displayed, submit to `/api/auth/reset-password`, success confirmation with link to login, error handling for expired/invalid tokens
- [x] 10.2 Create `frontend/app/api/auth/reset-password/route.ts` proxy to backend `/api/auth/reset-password`

## Task 11: Property-Based Tests
- [x] 11.1 Write property test for Password Validation Completeness (Property 2): for any string, validate_password returns empty list iff all rules satisfied, and failed list length equals number of violated rules
- [x] 11.2 Write property test for Password Hash Irreversibility (Property 1): for any password, hash differs from plaintext and bcrypt.checkpw confirms match
- [x] 11.3 Write property test for Reset Token Single Use (Property 5): after successful reset, same token returns error
- [x] 11.4 Write property test for Reset Token Expiry (Property 6): tokens older than 1 hour are rejected
- [x] 11.5 Write property test for Password Rule Specificity (Property 13): error response contains exactly the failed rules, not generic messages
