"""
Usage Gate module for freemium question limiting.

Tracks anonymous user question counts in PostgreSQL and enforces
a configurable free question limit before requiring subscription.
"""

import os
import logging
from typing import Optional

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UsageInfo(BaseModel):
    """Current usage statistics for an anonymous user."""
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
    Enforces free question limits for anonymous (non-authenticated) users.

    Reads FREE_QUESTION_LIMIT from environment (default 5).
    Tracks per-fingerprint question counts in the free_usage_tracking table.
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
        """Create connection pool and ensure free_usage_tracking table exists."""
        self.pool = await asyncpg.create_pool(dsn=self.database_url)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS free_usage_tracking (
                    id SERIAL PRIMARY KEY,
                    fingerprint VARCHAR(255) UNIQUE NOT NULL,
                    questions_used INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_question_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_free_usage_tracking_fingerprint
                ON free_usage_tracking (fingerprint)
            """)
        logger.info("UsageGate: free_usage_tracking table ready")

    async def check_and_increment(self, fingerprint: str) -> UsageResult:
        """
        Check if fingerprint is under the free question limit.
        Returns UsageResult with allowed/denied status and current counts.
        Does NOT increment — call record_question() after successful stream.
        """
        questions_used = 0
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT questions_used FROM free_usage_tracking WHERE fingerprint = $1",
                fingerprint,
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

    async def record_question(self, fingerprint: str) -> UsageInfo:
        """
        Increment question count via UPSERT. Called after stream starts successfully.
        Returns updated UsageInfo for the SSE metadata event.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO free_usage_tracking (fingerprint, questions_used, last_question_at)
                VALUES ($1, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (fingerprint)
                DO UPDATE SET
                    questions_used = free_usage_tracking.questions_used + 1,
                    last_question_at = CURRENT_TIMESTAMP
                RETURNING questions_used
                """,
                fingerprint,
            )
            questions_used = row["questions_used"]

        limit = self.free_question_limit
        return UsageInfo(
            questions_used=questions_used,
            questions_limit=limit,
            questions_remaining=max(0, limit - questions_used),
        )
