"""
Customer subscription authentication API routes.

Handles login, logout, refresh, and session info for customers
authenticated via the Appstle subscription API.

This module handles CUSTOMER authentication only.
Admin authentication (backend/auth_routes.py at /api/admin/*) is completely separate.
"""
import logging
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

try:
    from backend.subscription_auth import (
        SubscriptionAuthService, CustomerLoginRequest,
        ForgotPasswordRequest, ResetPasswordRequest,
    )
except ImportError:
    from subscription_auth import (
        SubscriptionAuthService, CustomerLoginRequest,
        ForgotPasswordRequest, ResetPasswordRequest,
    )

try:
    from backend.reset_token_service import ResetTokenService
except ImportError:
    from reset_token_service import ResetTokenService

try:
    from backend.password_service import PasswordService
except ImportError:
    from password_service import PasswordService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router & service
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["customer-auth"])

auth_service = SubscriptionAuthService()

# Lazy-initialized services for password reset (avoids startup failures)
_reset_token_service = None
_password_service = None


def _get_reset_token_service() -> ResetTokenService:
    """Lazy-initialize ResetTokenService on first use."""
    global _reset_token_service
    if _reset_token_service is None:
        _reset_token_service = ResetTokenService()
    return _reset_token_service


def _get_password_service() -> PasswordService:
    """Lazy-initialize PasswordService on first use."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service

# Cookie configuration
COOKIE_CONFIG = {
    "key": "session_token",
    "httponly": True,
    "secure": True,
    "samesite": "lax",
    "max_age": 3600,
    "path": "/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """Extract client IP, checking X-Forwarded-For first."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(body: CustomerLoginRequest, request: Request):
    """
    Verify email subscription via Appstle API.
    On success, sets an HTTP-only session_token cookie and returns user info.
    """
    client_ip = _get_client_ip(request)

    result = await auth_service.login(
        email=body.email,
        password=body.password,
        client_ip=client_ip,
    )

    status_code = result["status_code"]
    response_body = result["body"]

    response = JSONResponse(content=response_body, status_code=status_code)

    # Set cookie only on successful login
    if status_code == 200 and response_body.get("token"):
        response.set_cookie(
            value=response_body["token"],
            **COOKIE_CONFIG,
        )

    return response


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout():
    """Clear the session_token cookie."""
    response = JSONResponse(content={"success": True, "message": "Logged out"})
    response.delete_cookie(
        key=COOKIE_CONFIG["key"],
        path=COOKIE_CONFIG["path"],
        httponly=COOKIE_CONFIG["httponly"],
        secure=COOKIE_CONFIG["secure"],
        samesite=COOKIE_CONFIG["samesite"],
    )
    return response


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh(request: Request):
    """
    Re-verify subscription and issue a new session token.
    Reads the existing session_token from cookies.
    """
    token = request.cookies.get("session_token")
    if not token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "No session token provided"},
        )

    result = await auth_service.refresh(token)

    status_code = result["status_code"]
    response_body = result["body"]

    response = JSONResponse(content=response_body, status_code=status_code)

    # Set new cookie on successful refresh
    if status_code == 200 and response_body.get("token"):
        response.set_cookie(
            value=response_body["token"],
            **COOKIE_CONFIG,
        )

    return response


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_current_user(request: Request):
    """
    Return the current user's email and subscription status
    from the session token (no grace window).
    """
    token = request.cookies.get("session_token")
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    claims = auth_service.verify_token(token, allow_grace=False)
    if claims is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    return {
        "email": claims.get("sub"),
        "subscription_status": claims.get("subscription_status"),
        "subscription_expires_at": claims.get("subscription_expires_at"),
        "exp": claims.get("exp"),
    }


# ---------------------------------------------------------------------------
# Helpers for password reset
# ---------------------------------------------------------------------------

def _mask_email(email: str) -> str:
    """Mask email: show first char + *** + @domain. E.g. u***@example.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if local:
        return f"{local[0]}***@{domain}"
    return f"***@{domain}"



async def _get_token_failure_reason(token_str: str) -> str:
    """
    Determine why a token is invalid by querying the DB directly.
    Returns an appropriate error message.
    """
    try:
        rts = _get_reset_token_service()
    except Exception:
        return "Invalid reset link. Please request a new one."
    try:
        await rts._ensure_pool()
        async with rts.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT email, expires_at, used FROM password_reset_tokens WHERE token = $1",
                token_str,
            )
        if not row:
            return "Invalid reset link. Please request a new one."
        if row["used"]:
            return "Invalid reset link. Please request a new one."
        from datetime import datetime
        expires_at = row["expires_at"]
        if expires_at < datetime.utcnow():
            return "Reset link has expired. Please request a new one."
        return "Invalid reset link. Please request a new one."
    except Exception as exc:
        logger.error("Error checking token failure reason: %s", exc)
        return "Invalid reset link. Please request a new one."



# ---------------------------------------------------------------------------
# POST /api/auth/forgot-password
# ---------------------------------------------------------------------------


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """
    Verify subscription ownership and issue a reset token directly.
    No email required — the Appstle subscription check proves identity.
    """
    email = body.email.lower().strip()

    # 1. Initialize services lazily
    try:
        rts = _get_reset_token_service()
        ps = _get_password_service()
    except Exception as exc:
        logger.error("Failed to initialize password reset services: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"error": f"Password reset service init failed: {exc}"},
        )

    # 2. Check rate limit
    try:
        rate_ok = await rts.check_rate_limit(email)
    except Exception as exc:
        logger.error("Rate limit check failed for email=%s: %s", email, exc)
        return JSONResponse(
            status_code=503,
            content={"error": f"Rate limit check failed: {exc}"},
        )

    if not rate_ok:
        logger.info("Rate limit exceeded for forgot-password email=%s", email)
        return JSONResponse(
            status_code=429,
            content={"error": "Too many reset requests. Please try again later."},
        )

    # 3. Verify the email has an active Appstle subscription (proves identity)
    try:
        appstle_resp = await auth_service.verify_subscription(email)
    except Exception as exc:
        logger.error("Appstle verification failed for forgot-password email=%s: %s", email, exc)
        return JSONResponse(
            status_code=503,
            content={"error": "Subscription verification temporarily unavailable. Please try again later."},
        )

    if not appstle_resp.is_valid:
        logger.info("Forgot-password: no active subscription for email=%s", email)
        return JSONResponse(
            status_code=403,
            content={"error": "No active subscription found for this email address."},
        )

    # 4. Check if email exists in customer_passwords
    try:
        customer = await ps.get_customer(email)
    except Exception as exc:
        logger.error("Error looking up customer for forgot-password email=%s: %s", email, exc)
        return JSONResponse(
            status_code=500,
            content={"error": f"Customer lookup failed: {exc}"},
        )

    if not customer:
        logger.info("Forgot-password: no password record for email=%s (never set a password)", email)
        return JSONResponse(
            status_code=404,
            content={"error": "No password has been set for this account. Please log in to create one."},
        )

    # 5. Generate reset token and return it directly (no email needed)
    try:
        token = await rts.create_reset_token(email)
        logger.info("Reset token issued for email=%s (subscription-verified)", email)
        return JSONResponse(
            status_code=200,
            content={"token": token},
        )
    except Exception as exc:
        logger.error("Error creating reset token for email=%s: %s", email, exc)
        return JSONResponse(
            status_code=500,
            content={"error": f"Token creation failed: {exc}"},
        )



# ---------------------------------------------------------------------------
# POST /api/auth/reset-password
# ---------------------------------------------------------------------------


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """
    Reset password using a valid reset token.
    """
    token_str = body.token
    new_password = body.new_password

    try:
        rts = _get_reset_token_service()
        ps = _get_password_service()
    except Exception as exc:
        logger.error("Failed to initialize services for reset-password: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"error": "Password reset is temporarily unavailable"},
        )

    # 1. Validate token
    try:
        email = await rts.validate_token(token_str)
    except Exception as exc:
        logger.error("Error validating reset token: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid reset link. Please request a new one."},
        )

    # 2. If token invalid/expired/used: return 400 with appropriate message
    if not email:
        error_msg = await _get_token_failure_reason(token_str)
        return JSONResponse(
            status_code=400,
            content={"error": error_msg},
        )

    # 3. Validate new password rules
    failed_rules = ps.validate_password(new_password)
    if failed_rules:
        return JSONResponse(
            status_code=400,
            content={"error": "Password validation failed", "failed_rules": failed_rules},
        )

    # 4. Update password
    try:
        updated = await ps.update_password(email, new_password)
        if not updated:
            logger.error("Password update failed — no record found for email=%s", email)
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid reset link. Please request a new one."},
            )
    except Exception as exc:
        logger.error("Error updating password for email=%s: %s", email, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred. Please try again."},
        )

    # 5. Mark token used
    try:
        await rts.mark_token_used(token_str)
    except Exception as exc:
        logger.error("Error marking token used: %s", exc)

    logger.info("Password reset successful for email=%s", email)

    # 6. Return success
    return JSONResponse(
        status_code=200,
        content={"message": "Password reset successful"},
    )



# ---------------------------------------------------------------------------
# POST /api/auth/validate-reset-token
# ---------------------------------------------------------------------------


@router.post("/validate-reset-token")
async def validate_reset_token(body: dict):
    """
    Check if a reset token is valid (for frontend pre-validation).
    Returns masked email if valid.
    """
    token_str = body.get("token", "")

    if not token_str:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": "Token expired or invalid"},
        )

    try:
        rts = _get_reset_token_service()
    except Exception as exc:
        logger.error("Failed to initialize ResetTokenService: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": "Token expired or invalid"},
        )

    try:
        email = await rts.validate_token(token_str)
    except Exception as exc:
        logger.error("Error validating reset token: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": "Token expired or invalid"},
        )

    if not email:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": "Token expired or invalid"},
        )

    return JSONResponse(
        status_code=200,
        content={"valid": True, "email": _mask_email(email)},
    )

