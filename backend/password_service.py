"""
Password Service for ChatMaster Password Authentication
Feature: chatmaster-password-auth

Manages password-related operations including:
- Password validation against complexity rules
- Password hashing and verification using bcrypt
- Customer password record CRUD via asyncpg
"""

import os
import re
from typing import List, Optional, Dict, Any

import asyncpg
import bcrypt


class PasswordService:
    """Service for managing customer password operations"""

    BCRYPT_ROUNDS = 12
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    MIN_LENGTH = 8

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize password service.

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

    def validate_password(self, password: str) -> List[str]:
        """
        Validate password against complexity rules.
        Returns list of failed rule descriptions. Empty list means valid.

        Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character from SPECIAL_CHARS
        """
        failures: List[str] = []

        if len(password) < self.MIN_LENGTH:
            failures.append("Password must be at least 8 characters long")

        if not re.search(r'[A-Z]', password):
            failures.append("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            failures.append("Password must contain at least one lowercase letter")

        if not re.search(r'\d', password):
            failures.append("Password must contain at least one digit")

        if not any(ch in self.SPECIAL_CHARS for ch in password):
            failures.append("Password must contain at least one special character")

        return failures

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with work factor 12.

        Args:
            password: Plaintext password

        Returns:
            Bcrypt hash string
        """
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a stored bcrypt hash.

        Args:
            password: Plaintext password to check
            hashed: Stored bcrypt hash

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    async def get_customer(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Lookup customer_passwords record by email.

        Args:
            email: Customer email address

        Returns:
            Dict with customer record or None if not found
        """
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, password_hash, created_at, updated_at "
                "FROM customer_passwords WHERE email = $1",
                email.lower().strip()
            )
            if row:
                return dict(row)
            return None

    async def create_customer(self, email: str, password: str) -> Dict[str, Any]:
        """
        Create new customer_passwords record with hashed password.

        Args:
            email: Customer email address
            password: Plaintext password (will be hashed)

        Returns:
            Dict with the created customer record
        """
        await self._ensure_pool()
        password_hash = self.hash_password(password)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO customer_passwords (email, password_hash, created_at, updated_at) "
                "VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "RETURNING id, email, password_hash, created_at, updated_at",
                email.lower().strip(),
                password_hash
            )
            return dict(row)

    async def update_password(self, email: str, new_password: str) -> bool:
        """
        Update password hash for existing customer.

        Args:
            email: Customer email address
            new_password: New plaintext password (will be hashed)

        Returns:
            True if a record was updated, False if email not found
        """
        await self._ensure_pool()
        password_hash = self.hash_password(new_password)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE customer_passwords "
                "SET password_hash = $1, updated_at = CURRENT_TIMESTAMP "
                "WHERE email = $2",
                password_hash,
                email.lower().strip()
            )
            # asyncpg returns e.g. "UPDATE 1" or "UPDATE 0"
            return result.split()[-1] != '0'
