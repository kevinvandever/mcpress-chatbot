"""
Authentication module for admin users
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import hmac

import bcrypt
import jwt
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds


class AdminUser(BaseModel):
    id: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self):
        # Get secret key from environment or generate a secure one
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=24)
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    def create_access_token(self, user_id: str, email: str) -> str:
        """Create a JWT access token"""
        expires_at = datetime.utcnow() + self.token_expiry
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password meets security requirements"""
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_upper:
            return False, "Password must contain at least one uppercase letter"
        if not has_lower:
            return False, "Password must contain at least one lowercase letter"
        if not has_digit:
            return False, "Password must contain at least one number"
        if not has_special:
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"


class RateLimiter:
    """Simple in-memory rate limiter for login attempts"""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self.attempts: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if an attempt is allowed for the given identifier"""
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts
        self.attempts[identifier] = [
            timestamp for timestamp in self.attempts[identifier]
            if now - timestamp < self.window
        ]
        
        # Check if under limit
        if len(self.attempts[identifier]) >= self.max_attempts:
            return False
        
        # Record this attempt
        self.attempts[identifier].append(now)
        return True
    
    def reset(self, identifier: str):
        """Reset attempts for an identifier (e.g., after successful login)"""
        if identifier in self.attempts:
            del self.attempts[identifier]