"""
Admin authentication API routes
"""
import os
from fastapi import APIRouter, HTTPException, Depends, Request, Response, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any

from .auth import AuthService, LoginRequest, TokenResponse, RateLimiter
from .admin_db import AdminDatabase, InMemoryAdminDatabase


# Initialize router
router = APIRouter(prefix="/api/admin", tags=["admin"])

# Initialize services
auth_service = AuthService()
rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)

# Initialize database based on environment
if os.getenv('DATABASE_URL'):
    admin_db = AdminDatabase()
else:
    # Use in-memory database for local development
    print("⚠️ Using in-memory database for admin auth (development mode)")
    admin_db = InMemoryAdminDatabase()

# Security scheme for JWT bearer tokens
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials
    
    # Verify the JWT token
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user from database
    user = await admin_db.get_admin_by_id(payload["sub"])
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


@router.on_event("startup")
async def startup():
    """Initialize database pool on startup"""
    await admin_db.init_pool()
    
    # Create default admin user for development/initial setup if needed
    if os.getenv("ADMIN_EMAIL") and os.getenv("ADMIN_PASSWORD"):
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        
        # Check if user exists
        existing = await admin_db.get_admin_by_email(email)
        if not existing:
            # Validate password
            valid, message = auth_service.validate_password_strength(password)
            if valid:
                password_hash = auth_service.hash_password(password)
                user = await admin_db.create_admin_user(email, password_hash)
                if user:
                    print(f"✅ Created default admin user: {email}")
                else:
                    print(f"⚠️ Failed to create default admin user")
            else:
                print(f"⚠️ Default admin password too weak: {message}")
        else:
            print(f"ℹ️ Admin user already exists: {email}")


@router.on_event("shutdown")
async def shutdown():
    """Close database pool on shutdown"""
    await admin_db.close()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, client_request: Request):
    """
    Authenticate admin user and return JWT token
    """
    # Check rate limiting
    client_ip = client_request.client.host
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later."
        )
    
    # Get user from database
    user = await admin_db.get_admin_by_email(request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not auth_service.verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Create access token
    access_token = auth_service.create_access_token(str(user["id"]), user["email"])
    
    # Create session in database
    await admin_db.create_session(str(user["id"]), access_token)
    
    # Update last login
    await admin_db.update_last_login(str(user["id"]))
    
    # Reset rate limiter on successful login
    rate_limiter.reset(client_ip)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400  # 24 hours
    )


@router.post("/logout")
async def logout(
    response: Response,
    authorization: Optional[str] = Header(None)
):
    """
    Logout current user by invalidating their session
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    
    # Delete session from database
    await admin_db.delete_session(token)
    
    return {"message": "Successfully logged out"}


@router.get("/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify if the current token is valid and return user info
    """
    return {
        "valid": True,
        "user": {
            "id": str(current_user["id"]),
            "email": current_user["email"],
            "created_at": current_user.get("created_at"),
            "last_login": current_user.get("last_login")
        }
    }


@router.post("/refresh")
async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Refresh an expiring token with a new one
    """
    # Create new access token
    new_token = auth_service.create_access_token(
        str(current_user["id"]),
        current_user["email"]
    )
    
    # Create new session
    await admin_db.create_session(str(current_user["id"]), new_token)
    
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=86400  # 24 hours
    )


@router.post("/create-user")
async def create_admin_user(
    email: str,
    password: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new admin user (requires existing admin authentication)
    """
    # Validate password strength
    valid, message = auth_service.validate_password_strength(password)
    if not valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Hash password
    password_hash = auth_service.hash_password(password)
    
    # Create user
    user = await admin_db.create_admin_user(email, password_hash)
    if not user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    return {
        "message": "Admin user created successfully",
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "created_at": user.get("created_at")
        }
    }


# Protected route example
@router.get("/protected")
async def protected_route(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Example protected route that requires authentication
    """
    return {
        "message": "This is a protected route",
        "user": current_user["email"]
    }