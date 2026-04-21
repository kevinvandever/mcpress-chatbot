"""
Metadata Backfill Service for Article Metadata Quality
Feature: article-metadata-quality

Identifies articles with poor metadata (numeric titles, unknown authors)
and backfills them using the multi-source MetadataResolver. Tracks each
backfill run in a dedicated backfill_runs table following the ingestion_runs
pattern.

Also provides diagnostics for metadata quality assessment.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

import asyncpg

try:
    from metadata_resolver import MetadataResolver
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
    from excel_lookup_service import ExcelLookupService
except ImportError:
    from backend.metadata_resolver import MetadataResolver
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService
    from backend.excel_lookup_service import ExcelLookupService

logger = logging.getLogger(__name__)


@dataclass
class BackfillResult:
    """Result of a backfill run."""
    run_id: str
    status: str  # "completed", "failed"
    total_identified: int = 0
    titles_updated: int = 0
    authors_updated: int = 0
    still_poor: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DiagnosticsResult:
    """Result of a metadata quality diagnostics check."""
    total_articles: int = 0
    numeric_title_count: int = 0
    unknown_author_count: int = 0
    both_issues_count: int = 0
    sample_articles: List[Dict[str, Any]] = field(default_factory=list)


class MetadataBackfillService:
    """
    Identifies and backfills articles with poor metadata.

    Uses MetadataResolver for multi-source resolution and existing
    AuthorService / DocumentAuthorService for author management.
    Tracks runs in the backfill_runs table (following ingestion_runs pattern).
    """

    def __init__(
        self,
        database_url: str,
        metadata_resolver: MetadataResolver,
        author_service: AuthorService,
        document_author_service: DocumentAuthorService,
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.metadata_resolver = metadata_resolver
        self.author_service = author_service
        self.document_author_service = document_author_service
        self.pool: Optional[asyncpg.Pool] = None
        self._running = False

    async def _ensure_pool(self):
        """Ensure connection pool is initialized (lazy initialization)."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                statement_cache_size=0,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    async def ensure_table(self) -> None:
        """Create backfill_runs table if it doesn't exist."""
        await self._ensure_pool()
        migration_sql = """
        CREATE TABLE IF NOT EXISTS backfill_runs (
            id SERIAL PRIMARY KEY,
            run_id VARCHAR(100) UNIQUE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_identified INTEGER DEFAULT 0,
            titles_updated INTEGER DEFAULT 0,
            authors_updated INTEGER DEFAULT 0,
            still_poor INTEGER DEFAULT 0,
            error_details JSONB DEFAULT '[]'::jsonb,
            details JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_backfill_runs_status
            ON backfill_runs(status);
        CREATE INDEX IF NOT EXISTS idx_backfill_runs_started
            ON backfill_runs(started_at DESC);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(migration_sql)
        logger.info("✅ backfill_runs table ensured")

    # ------------------------------------------------------------------
    # Poor metadata identification
    # ------------------------------------------------------------------

    async def identify_poor_metadata_articles(self) -> List[Dict[str, Any]]:
        """
        Query books table for articles with numeric titles or unknown authors.

        Matches:
        - title consisting only of digits (numeric filename)
        - author = 'Unknown' or 'Unknown Author'
        - document_type = 'article'

        Returns list of dicts with id, filename, title, author.
        """
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, filename, title, author
                FROM books
                WHERE document_type = 'article'
                  AND (
                      title ~ '^[0-9]+$'
                      OR author IN ('Unknown', 'Unknown Author')
                      OR author IS NULL
                  )
                ORDER BY id
            """)
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Backfill execution
    # ------------------------------------------------------------------

    async def run_backfill(self, run_id: str = None) -> BackfillResult:
        """
        Execute full backfill process:
        1. Identify articles with poor metadata
        2. Resolve metadata for each article via MetadataResolver
        3. Update books table with resolved titles
        4. Create/link author records via AuthorService
        5. Create document_authors entries via DocumentAuthorService
        6. Track progress in backfill_runs table

        Operates idempotently — safe to run multiple times without
        creating duplicate authors (uses get_or_create_author).
        Handles per-article errors without stopping.
        """
        if self._running:
            raise RuntimeError("A backfill is already in progress")

        self._running = True
        await self._ensure_pool()

        run_id = run_id or str(uuid.uuid4())
        started_at = datetime.utcnow()
        result = BackfillResult(run_id=run_id, status="running")

        # Create run record
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO backfill_runs (run_id, status, started_at)
                VALUES ($1, 'running', $2)
                """,
                run_id,
                started_at,
            )

        try:
            # 1. Identify poor metadata articles
            poor_articles = await self.identify_poor_metadata_articles()
            result.total_identified = len(poor_articles)

            if not poor_articles:
                logger.info("No articles with poor metadata found. Nothing to backfill.")
                result.status = "completed"
                return result

            logger.info(
                "Backfill run %s: identified %d articles with poor metadata",
                run_id,
                len(poor_articles),
            )

            # 2. Process each article
            titles_updated = 0
            authors_updated = 0

            for article in poor_articles:
                article_id = article["id"]
                filename = article["filename"]
                old_title = article["title"]
                old_author = article["author"]

                article_detail: Dict[str, Any] = {
                    "book_id": article_id,
                    "filename": filename,
                    "old_title": old_title,
                    "old_author": old_author,
                    "new_title": None,
                    "new_authors": None,
                    "source": None,
                    "error": None,
                }

                try:
                    # Resolve metadata
                    resolved = await self.metadata_resolver.resolve(filename)

                    new_title = resolved.title
                    new_authors = resolved.authors
                    source = resolved.source

                    article_detail["new_title"] = new_title
                    article_detail["new_authors"] = new_authors
                    article_detail["source"] = source

                    title_changed = (
                        new_title != old_title
                        and new_title != filename.rsplit(".pdf", 1)[0]
                    )
                    author_changed = (
                        new_authors
                        and new_authors != ["Unknown Author"]
                        and (old_author in ("Unknown", "Unknown Author", None) or old_author is None)
                    )

                    # Update books table
                    article_url = resolved.article_url
                    async with self.pool.acquire() as conn:
                        if title_changed and author_changed:
                            await conn.execute(
                                """
                                UPDATE books
                                SET title = $1, author = $2,
                                    article_url = COALESCE(NULLIF($4, ''), article_url)
                                WHERE id = $3
                                """,
                                new_title,
                                ", ".join(new_authors),
                                article_id,
                                article_url or '',
                            )
                            titles_updated += 1
                            authors_updated += 1
                        elif title_changed:
                            await conn.execute(
                                """
                                UPDATE books
                                SET title = $1,
                                    article_url = COALESCE(NULLIF($3, ''), article_url)
                                WHERE id = $2
                                """,
                                new_title,
                                article_id,
                                article_url or '',
                            )
                            titles_updated += 1
                        elif author_changed:
                            await conn.execute(
                                """
                                UPDATE books
                                SET author = $1,
                                    article_url = COALESCE(NULLIF($3, ''), article_url)
                                WHERE id = $2
                                """,
                                ", ".join(new_authors),
                                article_id,
                                article_url or '',
                            )
                            authors_updated += 1
                        elif article_url:
                            # Even if title/author didn't change, update URL if we have one
                            await conn.execute(
                                """
                                UPDATE books
                                SET article_url = COALESCE(NULLIF($2, ''), article_url)
                                WHERE id = $1
                                """,
                                article_id,
                                article_url,
                            )

                    # Create / link authors in the multi-author system
                    if author_changed and new_authors:
                        # Clear existing document_authors for idempotent re-runs
                        await self.document_author_service.clear_document_authors(
                            article_id
                        )

                        for order, author_name in enumerate(new_authors):
                            author_name = author_name.strip()
                            if not author_name:
                                continue
                            try:
                                author_id = (
                                    await self.author_service.get_or_create_author(
                                        author_name
                                    )
                                )
                                await self.document_author_service.add_author_to_document(
                                    book_id=article_id,
                                    author_id=author_id,
                                    order=order,
                                )
                            except Exception as author_err:
                                logger.warning(
                                    "Could not link author '%s' to article %d: %s",
                                    author_name,
                                    article_id,
                                    author_err,
                                )

                    article_detail["title_updated"] = title_changed
                    article_detail["author_updated"] = author_changed

                except Exception as e:
                    logger.error(
                        "Error processing article %d (%s): %s",
                        article_id,
                        filename,
                        e,
                    )
                    article_detail["error"] = str(e)
                    result.errors.append(
                        {
                            "book_id": str(article_id),
                            "filename": filename,
                            "error_message": str(e),
                        }
                    )

                result.details.append(article_detail)

            result.titles_updated = titles_updated
            result.authors_updated = authors_updated

            # Calculate still_poor: re-query to get current count
            remaining = await self.identify_poor_metadata_articles()
            result.still_poor = len(remaining)

            result.status = "completed"

        except Exception as e:
            result.status = "failed"
            result.errors.append(
                {"book_id": None, "filename": None, "error_message": str(e)}
            )
            logger.error("Backfill run %s failed: %s", run_id, e)

        finally:
            self._running = False
            completed_at = datetime.utcnow()

            # Update run record
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE backfill_runs
                        SET status = $2,
                            completed_at = $3,
                            total_identified = $4,
                            titles_updated = $5,
                            authors_updated = $6,
                            still_poor = $7,
                            error_details = $8::jsonb,
                            details = $9::jsonb
                        WHERE run_id = $1
                        """,
                        run_id,
                        result.status,
                        completed_at,
                        result.total_identified,
                        result.titles_updated,
                        result.authors_updated,
                        result.still_poor,
                        json.dumps(result.errors),
                        json.dumps(result.details, default=str),
                    )
            except Exception as db_err:
                logger.error("Failed to update backfill run record: %s", db_err)

            logger.info(
                "Backfill run %s %s: identified=%d, titles_updated=%d, "
                "authors_updated=%d, still_poor=%d, errors=%d",
                run_id,
                result.status,
                result.total_identified,
                result.titles_updated,
                result.authors_updated,
                result.still_poor,
                len(result.errors),
            )

        return result

    # ------------------------------------------------------------------
    # Run history
    # ------------------------------------------------------------------

    async def get_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a backfill run record by run_id."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT run_id, status, started_at, completed_at,
                       total_identified, titles_updated, authors_updated,
                       still_poor, error_details, details
                FROM backfill_runs
                WHERE run_id = $1
                """,
                run_id,
            )
        if not row:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    async def get_diagnostics(self, detailed: bool = False) -> DiagnosticsResult:
        """
        Return metadata quality statistics.

        Args:
            detailed: If True, return full list of poor-metadata articles
                      instead of a sample of up to 20.

        Returns:
            DiagnosticsResult with counts and article samples/list.
        """
        await self._ensure_pool()

        async with self.pool.acquire() as conn:
            # Total articles
            total_articles = await conn.fetchval(
                "SELECT COUNT(*) FROM books WHERE document_type = 'article'"
            )

            # Numeric title count
            numeric_title_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM books
                WHERE document_type = 'article'
                  AND title ~ '^[0-9]+$'
                """
            )

            # Unknown author count
            unknown_author_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM books
                WHERE document_type = 'article'
                  AND (author IN ('Unknown', 'Unknown Author') OR author IS NULL)
                """
            )

            # Both issues count
            both_issues_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM books
                WHERE document_type = 'article'
                  AND title ~ '^[0-9]+$'
                  AND (author IN ('Unknown', 'Unknown Author') OR author IS NULL)
                """
            )

            # Sample or full list of poor-metadata articles
            limit_clause = "" if detailed else "LIMIT 20"
            rows = await conn.fetch(f"""
                SELECT id, filename, title, author
                FROM books
                WHERE document_type = 'article'
                  AND (
                      title ~ '^[0-9]+$'
                      OR author IN ('Unknown', 'Unknown Author')
                      OR author IS NULL
                  )
                ORDER BY id
                {limit_clause}
            """)

        sample_articles = [dict(row) for row in rows]

        return DiagnosticsResult(
            total_articles=total_articles,
            numeric_title_count=numeric_title_count,
            unknown_author_count=unknown_author_count,
            both_issues_count=both_issues_count,
            sample_articles=sample_articles,
        )

    @property
    def is_running(self) -> bool:
        """Whether a backfill is currently in progress."""
        return self._running
