"""
Usage Gate module for freemium question limiting.

Tracks registered user question counts by email in PostgreSQL and enforces
a configurable free question limit before requiring subscription.
"""

import os
import logging
from typing import Optional

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UsageInfo(BaseModel):
    """Current usage statistics for a free-tier user."""
    questions_used: int
    questions_limit: int
    questions_remaining: int


class UsageResult(BaseModel):
    """Result of a usage gate check — whether the request is allowed."""
    allowed: bool
    usage: UsageInfo
    signup_url: Optional[str] = None


class UsageGate:
    """
    Enforces free question limits for registered free-tier users.

    Reads FREE_QUESTION_LIMIT from environment (default 5).
    Tracks per-email question counts in the free_usage_tracking table.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.free_question_limit = self._read_limit()
        self.pool: Optional[asyncpg.Pool] = None
        logger.info(f"UsageGate initialized with free_question_limit={self.free_question_limit}")

    def _read_limit(self) -> int:
        """Read FREE_QUESTION_LIMIT from env. Default 5. Log warning on bad value."""
        raw = os.getenv("FREE_QUESTION_LIMIT")
        if raw is None:
            return 5
        try:
            return int(raw)
        except (ValueError, TypeError):
            logger.warning(
                f"FREE_QUESTION_LIMIT has non-integer value '{raw}', defaulting to 5"
            )
            return 5

    async def init(self):
        """Create connection pool and ensure free_usage_tracking table exists with user_email column."""
        self.pool = await asyncpg.create_pool(dsn=self.database_url)
        async with self.pool.acquire() as conn:
            # Check if old fingerprint-based table exists and drop it
            has_fingerprint = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'free_usage_tracking'
                    AND column_name = 'fingerprint'
                )
            """)
            if has_fingerprint:
                logger.info("UsageGate: dropping old fingerprint-based free_usage_tracking table")
                await conn.execute("DROP TABLE free_usage_tracking")

            # Create email-based table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS free_usage_tracking (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) UNIQUE NOT NULL,
                    questions_used INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_question_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_free_usage_tracking_email
                ON free_usage_tracking (user_email)
            """)
        logger.info("UsageGate: free_usage_tracking table ready")

    async def check_usage(self, user_email: str) -> UsageResult:
        """
        Check if user_email is under the free question limit.
        Returns UsageResult with allowed/denied status and current counts.
        Does NOT increment — call record_question() after successful stream.
        """
        questions_used = 0
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT questions_used FROM free_usage_tracking WHERE user_email = $1",
                user_email,
            )
            if row is not None:
                questions_used = row["questions_used"]

        limit = self.free_question_limit

        if questions_used >= limit:
            signup_url = os.getenv("SUBSCRIPTION_SIGNUP_URL")
            return UsageResult(
                allowed=False,
                usage=UsageInfo(
                    questions_used=questions_used,
                    questions_limit=limit,
                    questions_remaining=0,
                ),
                signup_url=signup_url,
            )

        return UsageResult(
            allowed=True,
            usage=UsageInfo(
                questions_used=questions_used,
                questions_limit=limit,
                questions_remaining=limit - questions_used,
            ),
        )

    async def record_question(self, user_email: str) -> UsageInfo:
        """
        Increment question count for user_email via UPSERT.
        Called after the chat response stream starts successfully.
        Returns updated UsageInfo for the SSE metadata event.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO free_usage_tracking (user_email, questions_used, last_question_at)
                VALUES ($1, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    questions_used = free_usage_tracking.questions_used + 1,
                    last_question_at = CURRENT_TIMESTAMP
                RETURNING questions_used
                """,
                user_email,
            )
            questions_used = row["questions_used"]

        limit = self.free_question_limit
        return UsageInfo(
            questions_used=questions_used,
            questions_limit=limit,
            questions_remaining=max(0, limit - questions_used),
        )
