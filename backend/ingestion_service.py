"""
Auto Content Ingestion Service

Discovers, downloads, and processes new PDF content from the MC Press Online
FTP server. Deduplicates against existing books, processes through the existing
PDFProcessorFull → PostgresVectorStore pipeline, and logs each run.

FTP credentials are read from environment variables:
  FTP_HOST     – FTP server IP/hostname (default: 209.142.66.171)
  FTP_PORT     – FTP port (default: 21)
  FTP_USER     – FTP username
  FTP_PASSWORD  – FTP password
  FTP_REMOTE_DIR – Remote directory containing PDFs (default: /)
"""

import asyncio
import ftplib
import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

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


class IngestionService:
    def __init__(
        self,
        vector_store,
        pdf_processor,
        category_mapper,
        metadata_resolver=None,
        author_service=None,
    ):
        self.vector_store = vector_store
        self.pdf_processor = pdf_processor
        self.category_mapper = category_mapper
        self.metadata_resolver = metadata_resolver
        self.author_service = author_service

        # FTP configuration from environment variables
        self.ftp_host = os.getenv("FTP_HOST", "209.142.66.171")
        self.ftp_port = int(os.getenv("FTP_PORT", "21"))
        self.ftp_user = os.getenv("FTP_USER", "")
        self.ftp_password = os.getenv("FTP_PASSWORD", "")
        self.ftp_remote_dir = os.getenv("FTP_REMOTE_DIR", "/")

        # Used for logging in ingestion_runs table
        self.source_url = f"ftp://{self.ftp_host}:{self.ftp_port}{self.ftp_remote_dir}"
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

    def _connect_ftp(self) -> ftplib.FTP:
        """Create and return an authenticated FTP connection."""
        if not self.ftp_user or not self.ftp_password:
            raise RuntimeError(
                "FTP credentials not configured. Set FTP_USER and FTP_PASSWORD environment variables."
            )
        ftp = ftplib.FTP()
        ftp.connect(self.ftp_host, self.ftp_port, timeout=60)
        ftp.login(self.ftp_user, self.ftp_password)
        if self.ftp_remote_dir and self.ftp_remote_dir != "/":
            ftp.cwd(self.ftp_remote_dir)
        logger.info(f"✅ Connected to FTP {self.ftp_host}:{self.ftp_port}")
        return ftp

    async def discover_remote_files(self) -> list[str]:
        """List PDF files on the FTP server."""
        def _list_files():
            ftp = self._connect_ftp()
            try:
                all_files = ftp.nlst()
                return [f for f in all_files if f.lower().endswith(".pdf")]
            finally:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()

        return await asyncio.get_event_loop().run_in_executor(None, _list_files)

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
        """Download a single PDF from FTP with retry. Returns local file path."""
        dest_path = os.path.join(dest_dir, filename)
        delays = (5, 15, 60)
        max_retries = 3

        def _download():
            ftp = self._connect_ftp()
            try:
                with open(dest_path, "wb") as f:
                    ftp.retrbinary(f"RETR {filename}", f.write)
            finally:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()

        for attempt in range(max_retries):
            try:
                await asyncio.get_event_loop().run_in_executor(None, _download)

                file_size = os.path.getsize(dest_path)
                if not self.validate_pdf_file(filename, file_size):
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    raise ValueError(f"Invalid PDF: {filename} (size={file_size})")

                return dest_path

            except ftplib.error_perm as e:
                # Permanent FTP errors (e.g., file not found) — don't retry
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise FileNotFoundError(f"FTP error for {filename}: {e}")
            except Exception as e:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
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
        # Detect document type: numeric filenames are articles, descriptive names are books
        name_without_ext = filename.rsplit(".pdf", 1)[0] if filename.lower().endswith(".pdf") else filename
        doc_type = "article" if name_without_ext.isdigit() else "book"
        return {
            "filename": filename,
            "title": title,
            "author": author or "Unknown",
            "category": category or "Uncategorized",
            "document_type": doc_type,
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

            # Enhanced metadata resolution for numeric-filename articles
            metadata_source = "default"
            resolved_authors = []
            if metadata["document_type"] == "article" and self.metadata_resolver:
                try:
                    resolved = await self.metadata_resolver.resolve(filename, file_path)
                    metadata_source = resolved.source

                    # Override title if resolver found a better one
                    name_without_ext = filename.rsplit(".pdf", 1)[0] if filename.lower().endswith(".pdf") else filename
                    if resolved.title != name_without_ext:
                        metadata["title"] = resolved.title

                    # Override author if resolver found a known author
                    if resolved.authors and resolved.authors[0] != "Unknown Author":
                        metadata["author"] = resolved.authors[0]
                        author = resolved.authors[0]
                        resolved_authors = resolved.authors

                    logger.info(
                        "Metadata resolved for '%s' via %s: title='%s', author='%s'",
                        filename,
                        metadata_source,
                        metadata["title"],
                        metadata["author"],
                    )
                except Exception as e:
                    logger.warning(
                        "Metadata resolution failed for '%s', using defaults: %s",
                        filename,
                        e,
                    )

            # Store chunks with embeddings
            if chunks:
                await self.vector_store.add_documents(chunks, metadata={"filename": filename})

            # Upsert into books table
            async with self.vector_store.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO books (filename, title, author, document_type, category, total_pages, processed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    ON CONFLICT (filename) DO UPDATE SET
                        title = EXCLUDED.title,
                        author = EXCLUDED.author,
                        document_type = EXCLUDED.document_type,
                        category = EXCLUDED.category,
                        total_pages = EXCLUDED.total_pages,
                        processed_at = EXCLUDED.processed_at
                    """,
                    filename,
                    metadata["title"],
                    metadata["author"],
                    metadata["document_type"],
                    category,
                    total_pages,
                )

                # Create author records and link via document_authors if resolver found authors
                if resolved_authors and self.author_service:
                    try:
                        book_id = await conn.fetchval(
                            "SELECT id FROM books WHERE filename = $1", filename
                        )
                        if book_id:
                            for order, author_name in enumerate(resolved_authors):
                                author_name = author_name.strip()
                                if not author_name or author_name == "Unknown Author":
                                    continue
                                author_id = await self.author_service.get_or_create_author(author_name)
                                # Insert into document_authors, skip if already linked
                                await conn.execute(
                                    """
                                    INSERT INTO document_authors (book_id, author_id, author_order)
                                    VALUES ($1, $2, $3)
                                    ON CONFLICT (book_id, author_id) DO NOTHING
                                    """,
                                    book_id,
                                    author_id,
                                    order,
                                )
                            logger.info(
                                "Linked %d author(s) for '%s' via %s",
                                len(resolved_authors),
                                filename,
                                metadata_source,
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to create author records for '%s': %s",
                            filename,
                            e,
                        )

            return {
                "filename": filename,
                "chunks": len(chunks),
                "pages": total_pages,
                "author": author,
                "category": category,
                "metadata_source": metadata_source,
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
