# Design Document: ChatMaster Password Authentication

## Overview

This design adds a local password authentication layer to the existing Appstle subscription-based login. The modified login flow becomes: email + password → verify password locally (bcrypt) → verify subscription via Appstle API → issue JWT. The existing JWT session management, token refresh, and Appstle integration remain unchanged.

## Architecture

### System Context Diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Browser     │────▶│  Next.js Frontend │────▶│  FastAPI Backend │────▶│ Appstle API │
│  (Login/     │◀────│  (Proxy Routes)   │◀────│  (Auth Service)  │◀────│ (Unchanged) │
│   Reset)     │     └──────────────────┘     │                  │     └─────────────┘
└─────────────┘                                │                  │
                                               │  ┌────────────┐ │     ┌─────────────┐
                                               │  │ Password   │ │     │ SMTP Server │
                                               │  │ Store (PG) │ │     │ (Email)     │
                                               │  └────────────┘ │     └─────────────┘
                                               └──────────────────┘
```

### Login Flow Sequence

```
User          Frontend         Backend            Password DB      Appstle API
 │               │                │                    │                │
 │─email+pass──▶│                │                    │                │
 │               │──POST /login─▶│                    │                │
 │               │                │──lookup email────▶│                │
 │               │                │◀─record/null──────│                │
 │               │                │                    │                │
 │               │                │  [record exists]   │                │
 │               │                │──bcrypt verify────▶│                │
 │               │                │◀─match/no match───│                │
 │               │                │                    │                │
 │               │                │  [no record: first-time user]      │
 │               │                │──validate rules───▶│                │
 │               │                │                    │                │
 │               │                │──verify subscription──────────────▶│
 │               │                │◀─active/inactive──────────────────│
 │               │                │                    │                │
 │               │                │  [first-time + active subscription]│
 │               │                │──create record────▶│                │
 │               │                │                    │                │
 │               │                │──issue JWT─────────│                │
 │               │◀─set cookie───│                    │                │
 │◀──redirect───│                │                    │                │
```

### Password Reset Flow

```
User          Frontend         Backend            Password DB      SMTP
 │               │                │                    │              │
 │─forgot email─▶│                │                    │              │
 │               │──POST forgot──▶│                    │              │
 │               │                │──check email──────▶│              │
 │               │                │──gen token────────▶│              │
 │               │                │──send email───────────────────────▶│
 │               │◀─200 OK───────│                    │              │
 │◀─"check email"│                │                    │              │
 │               │                │                    │              │
 │─click link───▶│                │                    │              │
 │               │──POST reset───▶│                    │              │
 │               │                │──validate token───▶│              │
 │               │                │──validate rules────│              │
 │               │                │──update hash──────▶│              │
 │               │                │──mark used────────▶│              │
 │               │◀─200 OK───────│                    │              │
 │◀─"success"───│                │                    │              │
```

## Data Models

### Database Tables

#### customer_passwords

```sql
CREATE TABLE IF NOT EXISTS customer_passwords (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_passwords_email ON customer_passwords(email);
```

#### password_reset_tokens

```sql
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
```

### Pydantic Models (Backend)

```python
class CustomerLoginRequest(BaseModel):
    email: str          # existing field
    password: str       # NEW field (optional for backward compat during rollout)

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class PasswordValidationError(BaseModel):
    error: str
    failed_rules: list[str]
```

## Component Design

### 1. PasswordService (NEW: `backend/password_service.py`)

Handles all password-related operations. Keeps password logic separate from subscription auth.

```python
class PasswordService:
    BCRYPT_ROUNDS = 12
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    MIN_LENGTH = 8

    async def validate_password(self, password: str) -> list[str]:
        """Returns list of failed rule descriptions. Empty = valid."""

    async def hash_password(self, password: str) -> str:
        """Hash with bcrypt, work factor 12."""

    async def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against stored bcrypt hash."""

    async def get_customer(self, email: str) -> Optional[dict]:
        """Lookup customer_passwords record by email."""

    async def create_customer(self, email: str, password: str) -> dict:
        """Create new customer_passwords record with hashed password."""

    async def update_password(self, email: str, new_password: str) -> bool:
        """Update password hash for existing customer."""
```

### 2. ResetTokenService (NEW: `backend/reset_token_service.py`)

Handles password reset token lifecycle.

```python
class ResetTokenService:
    TOKEN_EXPIRY_HOURS = 1
    MAX_REQUESTS_PER_HOUR = 3

    async def create_reset_token(self, email: str) -> str:
        """Generate secure token, invalidate previous tokens, store in DB."""

    async def validate_token(self, token: str) -> Optional[str]:
        """Validate token exists, not expired, not used. Returns email or None."""

    async def mark_token_used(self, token: str) -> bool:
        """Mark token as used after successful reset."""

    async def check_rate_limit(self, email: str) -> bool:
        """Check if email has exceeded 3 requests/hour. Returns True if allowed."""
```

### 3. EmailService (NEW: `backend/email_service.py`)

Sends password reset emails via SMTP.

```python
class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("EMAIL_SMTP_HOST")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.from_address = os.getenv("EMAIL_FROM_ADDRESS")
        self.smtp_password = os.getenv("EMAIL_SMTP_PASSWORD")
        self.frontend_url = os.getenv("FRONTEND_URL")
        self.enabled = all([self.smtp_host, self.from_address, self.smtp_password])

    async def send_reset_email(self, email: str, token: str) -> bool:
        """Send password reset email with branded HTML template."""

    def _build_reset_url(self, token: str) -> str:
        """Build: {FRONTEND_URL}/reset-password?token={token}"""

    def _build_email_html(self, reset_url: str) -> str:
        """MC ChatMaster branded HTML email template."""
```

### 4. Modified SubscriptionAuthService (`backend/subscription_auth.py`)

Minimal changes to the existing service — add password verification step before Appstle check.

Changes to `login()` method:
1. Accept `password` parameter
2. Lookup `customer_passwords` record by email
3. If record exists: verify password → if fail, return 401
4. If record exists + password valid: proceed to Appstle verification (existing flow)
5. If no record: validate password rules → proceed to Appstle verification → if active, create record
6. Return `needs_password_setup: true` response when no record and no password provided

Changes to `CustomerLoginRequest`:
- Add `password: str` field

No changes to: `refresh()`, `verify_token()`, `create_token()`, `verify_subscription()`

### 5. New Routes (`backend/subscription_auth_routes.py`)

Add to existing router:

```python
# POST /api/auth/forgot-password
@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Request password reset email."""

# POST /api/auth/reset-password
@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset password using valid token."""

# POST /api/auth/validate-reset-token
@router.post("/validate-reset-token")
async def validate_reset_token(body: dict):
    """Check if a reset token is valid (for frontend pre-validation)."""
```

Existing `/login` route: updated to pass `body.password` to `auth_service.login()`.

### 6. Frontend Pages

#### Modified: `frontend/app/login/page.tsx`

- Add password input field below email
- Add "Forgot Password?" link → navigates to `/forgot-password`
- Handle `needs_password_setup` response: show password rules + "Create Password" button
- Handle new error states (401 with password mismatch)
- Preserve existing branding, gradient, logo

#### New: `frontend/app/forgot-password/page.tsx`

- Email input form
- Submit → POST `/api/auth/forgot-password`
- Success: "Check your email for a reset link"
- Error handling for rate limits (429)

#### New: `frontend/app/reset-password/page.tsx`

- Read `token` from URL query params
- Validate token on mount via `/api/auth/validate-reset-token`
- Show new password form with rules displayed
- Submit → POST `/api/auth/reset-password`
- Success: "Password reset successful" + link to login
- Error handling for expired/invalid tokens

#### New Frontend API Proxies

```
frontend/app/api/auth/forgot-password/route.ts  → POST backend /api/auth/forgot-password
frontend/app/api/auth/reset-password/route.ts   → POST backend /api/auth/reset-password
```

### 7. Database Migration (`backend/migrations/004_customer_password_auth.sql`)

Single idempotent migration file creating both tables with indexes. Executed via API endpoint pattern (consistent with existing migration approach).

## API Contracts

### POST /api/auth/login (Modified)

Request:
```json
{ "email": "user@example.com", "password": "MyP@ssw0rd" }
```

Responses:
- `200`: `{ "token": "jwt...", "email": "...", "subscription_status": "ACTIVE" }`
- `400`: `{ "error": "Password validation failed", "failed_rules": ["Must contain uppercase"] }`
- `401`: `{ "error": "Invalid email or password" }`
- `403`: `{ "error": "Subscription expired", "subscription_status": "EXPIRED", "redirect_url": "..." }`
- `429`: `{ "error": "Too many login attempts. Please try again later." }`
- `503`: `{ "error": "Subscription service temporarily unavailable" }`

### POST /api/auth/forgot-password (New)

Request:
```json
{ "email": "user@example.com" }
```

Responses:
- `200`: `{ "message": "If an account exists, a reset email has been sent." }`
- `429`: `{ "error": "Too many reset requests. Please try again later." }`
- `503`: `{ "error": "Password reset is temporarily unavailable" }`

### POST /api/auth/reset-password (New)

Request:
```json
{ "token": "abc123...", "new_password": "NewP@ssw0rd" }
```

Responses:
- `200`: `{ "message": "Password reset successful" }`
- `400`: `{ "error": "Reset link has expired. Please request a new one." }`
- `400`: `{ "error": "Invalid reset link. Please request a new one." }`
- `400`: `{ "error": "Password validation failed", "failed_rules": ["..."] }`

### POST /api/auth/validate-reset-token (New)

Request:
```json
{ "token": "abc123..." }
```

Responses:
- `200`: `{ "valid": true, "email": "u***@example.com" }`
- `400`: `{ "valid": false, "error": "Token expired or invalid" }`

## File Changes Summary

### New Files
| File | Purpose |
|------|---------|
| `backend/password_service.py` | Password hashing, validation, CRUD |
| `backend/reset_token_service.py` | Reset token lifecycle management |
| `backend/email_service.py` | SMTP email delivery |
| `backend/migrations/004_customer_password_auth.sql` | DB migration |
| `frontend/app/forgot-password/page.tsx` | Forgot password page |
| `frontend/app/reset-password/page.tsx` | Reset password page |
| `frontend/app/api/auth/forgot-password/route.ts` | API proxy |
| `frontend/app/api/auth/reset-password/route.ts` | API proxy |

### Modified Files
| File | Changes |
|------|---------|
| `backend/subscription_auth.py` | Add password param to login(), add PasswordService integration |
| `backend/subscription_auth_routes.py` | Add forgot-password, reset-password, validate-reset-token routes |
| `frontend/app/login/page.tsx` | Add password field, forgot password link, first-time setup UI |
| `backend/config.py` | Add EMAIL_* environment variable loading |

### Unchanged Files
| File | Reason |
|------|--------|
| `backend/auth.py` | Admin auth — completely separate |
| `backend/auth_routes.py` | Admin routes — completely separate |
| `frontend/app/admin/login/page.tsx` | Admin login — completely separate |

## Error Handling Strategy

| Scenario | HTTP Status | Error Message |
|----------|-------------|---------------|
| Wrong password | 401 | "Invalid email or password" |
| Password rules failed | 400 | Specific rule failures listed |
| No subscription | 403 | Status-specific message + redirect URL |
| Appstle API down | 503 | "Subscription service temporarily unavailable" |
| Too many login attempts | 429 | "Too many login attempts. Please try again later." |
| Too many reset requests | 429 | "Too many reset requests. Please try again later." |
| Expired reset token | 400 | "Reset link has expired. Please request a new one." |
| Invalid/used reset token | 400 | "Invalid reset link. Please request a new one." |
| Email send failure | 500 | "Unable to send reset email. Please try again later." |
| Email service disabled | 503 | "Password reset is temporarily unavailable" |

## Security Considerations

1. Passwords hashed with bcrypt (work factor 12) — never stored in plaintext
2. Generic "Invalid email or password" message prevents email enumeration on login
3. Forgot-password returns same response whether email exists or not (prevents enumeration)
4. Reset tokens are cryptographically random (secrets.token_urlsafe), 1-hour expiry
5. Previous reset tokens invalidated when new one is requested
6. Rate limiting on both login (5/IP/15min) and forgot-password (3/email/hour)
7. JWT stored in HTTP-only secure cookie (not localStorage)
8. Password rules enforce minimum complexity

## Environment Variables

### Existing (Unchanged)
- `APPSTLE_API_URL`, `APPSTLE_API_KEY`, `SUBSCRIPTION_SIGNUP_URL`, `JWT_SECRET_KEY`

### New (Required for email)
- `EMAIL_SMTP_HOST` — SMTP server hostname
- `EMAIL_SMTP_PORT` — SMTP port (default: 587)
- `EMAIL_FROM_ADDRESS` — Sender email address
- `EMAIL_SMTP_PASSWORD` — SMTP authentication password
- `FRONTEND_URL` — Frontend base URL for reset links

### Graceful Degradation
If any EMAIL_* variable is missing, the system logs a warning at startup and disables forgot-password. Login with email+password continues to work normally.

## Correctness Properties

### Property 1: Password Hash Irreversibility
For any password P, given hash H = bcrypt(P, rounds=12), it is computationally infeasible to derive P from H. Verified by: hashing a password and confirming the hash differs from the plaintext and that `bcrypt.checkpw(P, H)` returns True.

### Property 2: Password Validation Completeness
For any password P, `validate_password(P)` returns an empty list if and only if P satisfies ALL rules: length ≥ 8, has uppercase, has lowercase, has digit, has special character. For any P that violates k rules, the returned list has exactly k entries.

### Property 3: Login Requires Both Factors
For any email E with a stored password record, a login attempt succeeds (200) only when BOTH: (a) the provided password matches the stored hash, AND (b) the Appstle API confirms an active subscription for E.

### Property 4: First-Time Account Creation Atomicity
When a user with no password record submits a valid password and has an active subscription, the system creates exactly one password record. If the Appstle check fails, no record is created.

### Property 5: Reset Token Single Use
A reset token T can be used to reset a password at most once. After successful use, any subsequent attempt with T returns an error.

### Property 6: Reset Token Expiry
A reset token T created at time t is valid only for requests made before t + 1 hour. Requests after expiry return a 400 error.

### Property 7: Reset Token Invalidation on New Request
When a new reset token is requested for email E, all previously issued tokens for E become invalid, regardless of their expiry time.

### Property 8: Rate Limit Enforcement (Login)
For any IP address, after 5 failed login attempts within a 15-minute window, subsequent attempts return 429 until the window expires or a successful login resets the counter.

### Property 9: Rate Limit Enforcement (Forgot Password)
For any email address, after 3 forgot-password requests within a 1-hour window, subsequent requests return 429 until the window expires.

### Property 10: Email Enumeration Prevention
The forgot-password endpoint returns identical response structure and timing for both existing and non-existing email addresses.

### Property 11: Admin Auth Isolation
No changes to the admin authentication system. Admin routes (`/api/admin/*`) continue to function identically before and after this feature is deployed.

### Property 12: Session Continuity
Existing JWT token refresh flow continues to work without requiring password re-entry. Only subscription re-verification occurs during refresh.

### Property 13: Password Rule Specificity
When a password fails validation, the error response contains exactly the list of specific rules that failed — not a generic message.

### Property 14: Idempotent Migration
Running the database migration multiple times produces the same result as running it once (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS).
