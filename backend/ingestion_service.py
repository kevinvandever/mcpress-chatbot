"""
Auto Content Ingestion Service

Discovers, downloads, and processes new PDF content from the MC Press Online
repository. Deduplicates against existing books, processes through the existing
PDFProcessorFull → PostgresVectorStore pipeline, and logs each run.
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class IngestionRunResult:
    run_id: str
    status: str  # "completed" | "failed" | "interrupted"
    started_at: datetime
    completed_at: Optional[datetime] = None
    files_discovered: int = 0
    files_skipped: int = 0
    files_processed: int = 0
    files_failed: int = 0
    errors: list = field(default_factory=list)


class PDFLinkParser(HTMLParser):
    """Extracts PDF links from HTML directory listings."""

    def __init__(self):
        super().__init__()
        self.pdf_links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            for attr_name, attr_value in attrs:
                if attr_name.lower() == "href" and attr_value:
                    if attr_value.lower().endswith(".pdf"):
                        # Extract just the filename (no path components)
                        filename = attr_value.rsplit("/", 1)[-1]
                        self.pdf_links.append(filename)


def parse_pdf_links(html: str) -> list[str]:
    """Parse HTML and return list of PDF filenames found in <a> href attributes."""
    parser = PDFLinkParser()
    parser.feed(html)
    return parser.pdf_links


class IngestionService:
    def __init__(
        self,
        vector_store,
        pdf_processor,
        category_mapper,
        source_url: str = "https://prod.mcpressonline.com/images/ngpdfs",
    ):
        self.vector_store = vector_store
        self.pdf_processor = pdf_processor
        self.category_mapper = category_mapper
        self.source_url = source_url.rstrip("/")
        self._running = False

    async def ensure_table(self) -> None:
        """Create ingestion_runs table if it doesn't exist."""
        migration_sql = """
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            id SERIAL PRIMARY KEY,
            run_id VARCHAR(100) UNIQUE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            source_url TEXT NOT NULL,
            files_discovered INTEGER NOT NULL DEFAULT 0,
            files_skipped INTEGER NOT NULL DEFAULT 0,
            files_processed INTEGER NOT NULL DEFAULT 0,
            files_failed INTEGER NOT NULL DEFAULT 0,
            error_details JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status
            ON ingestion_runs (status);
        CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at
            ON ingestion_runs (started_at DESC);
        """
        async with self.vector_store.pool.acquire() as conn:
            await conn.execute(migration_sql)
        logger.info("✅ ingestion_runs table ensured")

    async def mark_interrupted_runs(self) -> None:
        """Mark any 'running' ingestion runs as 'interrupted' (called on startup)."""
        async with self.vector_store.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE ingestion_runs
                SET status = 'interrupted', completed_at = CURRENT_TIMESTAMP
                WHERE status = 'running'
            """)
            count = int(result.split()[-1])
            if count > 0:
                logger.info(f"⚠️ Marked {count} interrupted ingestion run(s)")

    # ------------------------------------------------------------------
    # Discovery & Deduplication
    # ------------------------------------------------------------------

    async def discover_remote_files(self) -> list[str]:
        """Fetch HTML listing from source URL and parse out PDF filenames."""
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.source_url) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Source returned HTTP {resp.status}: {self.source_url}"
                    )
                html = await resp.text()
        return parse_pdf_links(html)

    async def get_existing_filenames(self) -> set[str]:
        """Query books table for all known filenames."""
        async with self.vector_store.pool.acquire() as conn:
            rows = await conn.fetch("SELECT filename FROM books")
        return {row["filename"] for row in rows}

    @staticmethod
    def deduplicate(discovered: list[str], existing: set[str]) -> list[str]:
        """Return filenames in discovered but not in existing, no duplicates."""
        seen: set[str] = set()
        result: list[str] = []
        for name in discovered:
            if name not in existing and name not in seen:
                seen.add(name)
                result.append(name)
        return result


    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @staticmethod
    def validate_pdf_file(filename: str, file_size: int) -> bool:
        """Return True iff filename ends with .pdf (case-insensitive) and size > 0."""
        return filename.lower().endswith(".pdf") and file_size > 0

    async def download_pdf(self, filename: str, dest_dir: str) -> str:
        """Download a single PDF with retry. Returns local file path."""
        url = f"{self.source_url}/{filename}"
        dest_path = os.path.join(dest_dir, filename)
        delays = (5, 15, 60)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=600)  # 10 min
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status == 404:
                            raise FileNotFoundError(f"HTTP 404 for {filename}")
                        if resp.status != 200:
                            raise RuntimeError(f"HTTP {resp.status} downloading {filename}")
                        with open(dest_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)

                file_size = os.path.getsize(dest_path)
                if not self.validate_pdf_file(filename, file_size):
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    raise ValueError(f"Invalid PDF: {filename} (size={file_size})")

                return dest_path

            except FileNotFoundError:
                raise  # Don't retry 404s
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"Download attempt {attempt + 1} failed for {filename}: {e}. "
                    f"Retrying in {delays[attempt]}s..."
                )
                await asyncio.sleep(delays[attempt])

        raise RuntimeError(f"Download failed after {max_retries} attempts: {filename}")

    # ------------------------------------------------------------------
    # Process & Store
    # ------------------------------------------------------------------

    def _build_metadata(self, filename: str, author: str, category: str) -> dict:
        """Build metadata dict for a processed document."""
        title = filename.rsplit(".pdf", 1)[0] if filename.lower().endswith(".pdf") else filename
        return {
            "filename": filename,
            "title": title,
            "author": author or "Unknown",
            "category": category or "Uncategorized",
            "document_type": "book",
        }

    async def process_and_store(self, file_path: str, filename: str) -> dict:
        """Process a PDF and store in vector store + books table. Returns stats."""
        try:
            # 30-minute processing timeout
            result = await asyncio.wait_for(
                self.pdf_processor.process_pdf(file_path), timeout=1800
            )

            chunks = result.get("chunks", [])
            total_pages = result.get("total_pages", 0)
            author = result.get("author") or "Unknown"

            category = self.category_mapper.get_category(filename)
            metadata = self._build_metadata(filename, author, category)

            # Store chunks with embeddings
            if chunks:
                await self.vector_store.add_documents(chunks, metadata={"filename": filename})

            # Upsert into books table
            async with self.vector_store.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO books (filename, title, document_type, category, total_pages, processed_at)
                    VALUES ($1, $2, 'book', $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (filename) DO UPDATE SET
                        title = EXCLUDED.title,
                        category = EXCLUDED.category,
                        total_pages = EXCLUDED.total_pages,
                        processed_at = EXCLUDED.processed_at
                    """,
                    filename,
                    metadata["title"],
                    category,
                    total_pages,
                )

            return {
                "filename": filename,
                "chunks": len(chunks),
                "pages": total_pages,
                "author": author,
                "category": category,
            }
        finally:
            # Always clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)


    # ------------------------------------------------------------------
    # Run Orchestration
    # ------------------------------------------------------------------

    async def run_ingestion(self) -> IngestionRunResult:
        """Execute a full ingestion run."""
        if self._running:
            raise RuntimeError("An ingestion run is already in progress")

        self._running = True
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        run_result = IngestionRunResult(
            run_id=run_id, status="running", started_at=started_at
        )

        # Create run record
        async with self.vector_store.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ingestion_runs (run_id, status, started_at, source_url)
                VALUES ($1, 'running', $2, $3)
                """,
                run_id,
                started_at,
                self.source_url,
            )

        try:
            # 1. Discover
            try:
                discovered = await self.discover_remote_files()
            except Exception as e:
                logger.error(f"Discovery failed: {e}")
                run_result.status = "failed"
                run_result.errors.append({"filename": None, "error_message": str(e), "stage": "discovery"})
                return run_result

            run_result.files_discovered = len(discovered)

            if not discovered:
                logger.info("No files discovered at source. Nothing to do.")
                run_result.status = "completed"
                run_result.completed_at = datetime.utcnow()
                return run_result

            # 2. Deduplicate
            existing = await self.get_existing_filenames()
            new_files = self.deduplicate(discovered, existing)
            run_result.files_skipped = run_result.files_discovered - len(new_files)

            if not new_files:
                logger.info("All discovered files already exist. Nothing to process.")
                run_result.status = "completed"
                run_result.completed_at = datetime.utcnow()
                return run_result

            logger.info(
                f"Ingestion run {run_id}: {len(discovered)} discovered, "
                f"{run_result.files_skipped} skipped, {len(new_files)} new"
            )

            # 3. Download & Process each file independently
            tmp_dir = tempfile.mkdtemp(prefix="ingestion_")
            try:
                for filename in new_files:
                    try:
                        file_path = await self.download_pdf(filename, tmp_dir)
                        await self.process_and_store(file_path, filename)
                        run_result.files_processed += 1
                        logger.info(f"✅ Processed: {filename}")
                    except Exception as e:
                        run_result.files_failed += 1
                        run_result.errors.append({
                            "filename": filename,
                            "error_message": str(e),
                            "stage": "download_or_process",
                        })
                        logger.error(f"❌ Failed: {filename} — {e}")
            finally:
                # Clean up temp directory
                try:
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

            run_result.status = "completed"
            run_result.completed_at = datetime.utcnow()

        except Exception as e:
            run_result.status = "failed"
            run_result.errors.append({"filename": None, "error_message": str(e), "stage": "orchestration"})
            logger.error(f"Ingestion run failed: {e}")

        finally:
            self._running = False
            run_result.completed_at = run_result.completed_at or datetime.utcnow()

            # Update run record in DB
            try:
                async with self.vector_store.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE ingestion_runs
                        SET status = $2,
                            completed_at = $3,
                            files_discovered = $4,
                            files_skipped = $5,
                            files_processed = $6,
                            files_failed = $7,
                            error_details = $8::jsonb
                        WHERE run_id = $1
                        """,
                        run_id,
                        run_result.status,
                        run_result.completed_at,
                        run_result.files_discovered,
                        run_result.files_skipped,
                        run_result.files_processed,
                        run_result.files_failed,
                        json.dumps(run_result.errors),
                    )
            except Exception as db_err:
                logger.error(f"Failed to update ingestion run record: {db_err}")

            logger.info(
                f"Ingestion run {run_id} {run_result.status}: "
                f"discovered={run_result.files_discovered}, "
                f"skipped={run_result.files_skipped}, "
                f"processed={run_result.files_processed}, "
                f"failed={run_result.files_failed}"
            )

        return run_result

    # ------------------------------------------------------------------
    # Status & History
    # ------------------------------------------------------------------

    async def get_current_run(self) -> Optional[dict]:
        """Get the currently running or most recent ingestion run."""
        async with self.vector_store.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT run_id, status, started_at, completed_at, source_url,
                       files_discovered, files_skipped, files_processed, files_failed,
                       error_details
                FROM ingestion_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        if not row:
            return None
        return dict(row)

    async def get_run_history(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get paginated ingestion run history ordered by started_at DESC."""
        async with self.vector_store.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT run_id, status, started_at, completed_at, source_url,
                       files_discovered, files_skipped, files_processed, files_failed,
                       error_details
                FROM ingestion_runs
                ORDER BY started_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [dict(r) for r in rows]
