"""
Reset Token Service for ChatMaster Password Authentication
Feature: chatmaster-password-auth

Manages password reset token lifecycle:
- Token generation using secrets.token_urlsafe
- Token validation (existence, expiry, used status)
- Token usage marking
- Rate limiting (3 requests per email per hour)
- Previous token invalidation on new request
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import asyncpg


class ResetTokenService:
    """Service for managing password reset tokens"""

    TOKEN_EXPIRY_HOURS = 1
    MAX_REQUESTS_PER_HOUR = 3

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize reset token service.

        Args:
            database_url: PostgreSQL database URL (defaults to DATABASE_URL env var)
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.pool = None

    async def init_database(self):
        """Initialize database connection pool"""
        if self.pool:
            return
        self.pool = await asyncpg.create_pool(
            self.database_url,
            statement_cache_size=0,
            min_size=1,
            max_size=10,
            command_timeout=60
        )

    async def _ensure_pool(self):
        """Ensure connection pool is initialized (lazy initialization)"""
        if not self.pool:
            await self.init_database()

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create_reset_token(self, email: str) -> str:
        """
        Generate a secure reset token for the given email.

        Invalidates all previous tokens for this email before creating
        a new one (Task 3.2: token invalidation).

        Args:
            email: Customer email address

        Returns:
            The generated token string
        """
        await self._ensure_pool()
        normalized_email = email.lower().strip()
        token = secrets.token_urlsafe()
        expires_at = datetime.utcnow() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Invalidate all previous tokens for this email
                await conn.execute(
                    "UPDATE password_reset_tokens SET used = TRUE "
                    "WHERE email = $1 AND used = FALSE",
                    normalized_email
                )

                # Create new token
                await conn.execute(
                    "INSERT INTO password_reset_tokens (email, token, expires_at, created_at) "
                    "VALUES ($1, $2, $3, CURRENT_TIMESTAMP)",
                    normalized_email,
                    token,
                    expires_at
                )

        return token

    async def validate_token(self, token: str) -> Optional[str]:
        """
        Validate a reset token.

        Checks that the token exists, has not been used, and has not expired.

        Args:
            token: The reset token string

        Returns:
            The associated email if valid, None otherwise
        """
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT email, expires_at, used FROM password_reset_tokens "
                "WHERE token = $1",
                token
            )

            if not row:
                return None

            if row['used']:
                return None

            if row['expires_at'] < datetime.utcnow():
                return None

            return row['email']

    async def mark_token_used(self, token: str) -> bool:
        """
        Mark a token as used after a successful password reset.

        Args:
            token: The reset token string

        Returns:
            True if a token was marked, False if token not found
        """
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE token = $1",
                token
            )
            return result.split()[-1] != '0'

    async def check_rate_limit(self, email: str) -> bool:
        """
        Check if the email is within the rate limit for reset requests.

        Allows up to MAX_REQUESTS_PER_HOUR (3) tokens created per email
        within the last hour.

        Args:
            email: Customer email address

        Returns:
            True if the request is allowed, False if rate limited
        """
        await self._ensure_pool()
        normalized_email = email.lower().strip()
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM password_reset_tokens "
                "WHERE email = $1 AND created_at > $2",
                normalized_email,
                one_hour_ago
            )

            return count < self.MAX_REQUESTS_PER_HOUR
