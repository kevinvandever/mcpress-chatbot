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
    from backend.subscription_auth import SubscriptionAuthService, CustomerLoginRequest
except ImportError:
    from subscription_auth import SubscriptionAuthService, CustomerLoginRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router & service
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["customer-auth"])

auth_service = SubscriptionAuthService()

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
