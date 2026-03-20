# Implementation Plan: Auto Content Ingestion

## Overview

Implement automated ingestion of new PDF content from the MC Press Online repository. The system scrapes an HTML directory listing, deduplicates against the existing `books` table, downloads new PDFs, processes them through the existing `PDFProcessorFull` → `PostgresVectorStore` pipeline, and logs each run. Three API endpoints provide manual triggering, status, and history. APScheduler handles monthly cron scheduling.

All new code lives in three backend modules (`ingestion_service.py`, `ingestion_routes.py`, `ingestion_scheduler.py`) plus a DB migration, with integration wired through `main.py`.

## Tasks

- [x] 1. Database migration for ingestion_runs table
  - [x] 1.1 Create `backend/migrations/005_ingestion_runs.sql` with the `ingestion_runs` table DDL, status/started_at indexes
    - Include `CREATE TABLE IF NOT EXISTS ingestion_runs` with columns: id, run_id, status, started_at, completed_at, source_url, files_discovered, files_skipped, files_processed, files_failed, error_details (JSONB), created_at
    - Include indexes on `status` and `started_at DESC`
    - _Requirements: 6.1, 7.1_
  - [x] 1.2 Add `ensure_table()` method to `IngestionService` that executes the migration SQL via `vector_store.pool`
    - Called during `main.py` startup to auto-create the table on deploy
    - _Requirements: 6.1_

- [x] 2. Core IngestionService — discovery and deduplication
  - [x] 2.1 Create `backend/ingestion_service.py` with `IngestionService.__init__`, `IngestionRunResult` dataclass, and HTML parsing helper
    - `__init__` accepts `vector_store`, `pdf_processor`, `category_mapper`, `source_url`
    - HTML parser uses `html.parser.HTMLParser` (stdlib) to extract `<a href="...">` values ending in `.pdf` (case-insensitive)
    - _Requirements: 1.1, 1.2_
  - [ ]* 2.2 Write property test: HTML Parser Extracts Exactly PDF Links
    - **Property 1: HTML Parser Extracts Exactly PDF Links**
    - **Validates: Requirements 1.2**
  - [x] 2.3 Implement `get_existing_filenames()` querying `books` table and `deduplicate()` computing set difference
    - `get_existing_filenames()` returns `set[str]` from `SELECT filename FROM books`
    - `deduplicate(discovered, existing)` returns list of filenames in discovered but not in existing, no duplicates
    - _Requirements: 2.1, 2.2, 7.2_
  - [ ]* 2.4 Write property test: Deduplication Is Set Difference
    - **Property 2: Deduplication Is Set Difference**
    - **Validates: Requirements 2.2, 7.2**

- [x] 3. Checkpoint — Ensure discovery and dedup logic is correct
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Core IngestionService — download, process, and run orchestration
  - [x] 4.1 Implement `download_pdf()` with retry logic and file validation
    - Uses `aiohttp` with 10-minute timeout per file
    - Retry up to 3 times with exponential backoff (5s, 15s, 60s)
    - Validates `.pdf` extension and file size > 0
    - Saves to temp directory, returns local path
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 8.4_
  - [ ]* 4.2 Write property test: File Validation Accepts Only Valid PDFs
    - **Property 3: File Validation Accepts Only Valid PDFs**
    - **Validates: Requirements 3.4**
  - [x] 4.3 Implement `process_and_store()` — process PDF and store in vector store + books table
    - Calls `pdf_processor.process_pdf()`, `category_mapper.get_category()`, `vector_store.add_documents()`
    - Inserts into `books` table with `ON CONFLICT (filename) DO UPDATE`
    - Assigns metadata: filename, title (from filename), author (from extraction or "Unknown"), category, document_type, ingestion timestamp
    - Deletes temp file in `finally` block
    - Enforces 30-minute processing timeout via `asyncio.wait_for()`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 8.1, 8.4_
  - [ ]* 4.4 Write property test: Metadata Contains All Required Fields
    - **Property 4: Metadata Contains All Required Fields**
    - **Validates: Requirements 4.3**
  - [x] 4.5 Implement `run_ingestion()` — full orchestration method
    - Creates ingestion_runs record with status "running"
    - Calls discover → dedup → download → process for each new file
    - Processes files independently (one failure doesn't stop others)
    - Updates ingestion_runs record with final counts and status
    - Logs summary on completion
    - On startup, marks any "running" runs as "interrupted"
    - _Requirements: 1.1, 1.3, 1.4, 2.3, 5.2, 6.1, 6.4, 7.1, 7.3, 8.1, 8.2, 8.3_
  - [ ]* 4.6 Write property test: Run Record Accounting Invariant
    - **Property 5: Run Record Accounting Invariant**
    - **Validates: Requirements 6.1, 2.3**
  - [ ]* 4.7 Write property test: Completed Runs Have Timestamps
    - **Property 6: Completed Runs Have Timestamps**
    - **Validates: Requirements 5.2, 7.1**
  - [ ]* 4.8 Write property test: Independent File Processing
    - **Property 7: Independent File Processing**
    - **Validates: Requirements 8.1, 4.4, 3.3**

- [x] 5. Checkpoint — Ensure core service logic and all property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. API routes and status/history queries
  - [x] 6.1 Implement `get_current_run()` and `get_run_history()` on `IngestionService`
    - `get_current_run()` returns the most recent or currently running ingestion run
    - `get_run_history(limit, offset)` returns paginated run history ordered by `started_at DESC`
    - _Requirements: 6.2, 6.3_
  - [x] 6.2 Create `backend/ingestion_routes.py` with FastAPI router and 3 endpoints
    - `POST /api/ingestion/trigger` — starts ingestion run as background task, returns 409 if one is already running
    - `GET /api/ingestion/status` — returns current/most recent run status
    - `GET /api/ingestion/history?limit=20&offset=0` — returns paginated run history
    - All endpoints require admin auth (follow existing auth pattern)
    - _Requirements: 5.4, 6.2, 6.3_

- [x] 7. Scheduler setup
  - [x] 7.1 Create `backend/ingestion_scheduler.py` with APScheduler monthly cron
    - `setup_ingestion_scheduler(ingestion_service)` creates `AsyncIOScheduler` with `CronTrigger(day=1, hour=3, minute=0)`
    - `start_scheduler(scheduler)` starts the scheduler, checks last completed run to avoid double-running
    - `stop_scheduler(scheduler)` graceful shutdown
    - _Requirements: 5.1, 5.3_

- [x] 8. Wire everything into main.py
  - [x] 8.1 Add imports and initialization for `IngestionService`, `ingestion_routes`, and `ingestion_scheduler` in `backend/main.py`
    - Follow existing try/except import pattern for Railway vs local imports
    - Initialize `IngestionService` in `startup_event()` with existing `vector_store`, `pdf_processor`, `category_mapper`
    - Call `ensure_table()` during startup
    - Mark interrupted runs on startup
    - Register ingestion routes on the FastAPI app
    - Start scheduler on startup, stop on shutdown
    - _Requirements: 5.1, 5.3, 5.4, 8.3_
  - [x] 8.2 Add `apscheduler` to `requirements.txt`
    - Add `APScheduler>=3.10.0` to the project dependencies
    - _Requirements: 5.1_

- [x] 9. Checkpoint — Ensure full integration compiles and deploys cleanly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Integration test script for Railway API testing
  - [x] 10.1 Create `test_ingestion_api.py` at project root — API-based integration test script
    - Uses `requests` library to call staging Railway endpoints (no local imports)
    - Tests: trigger ingestion (expect 200 or 409), get status (expect 200 with `status` field), get history (expect 200 with `runs` list), trigger duplicate (expect 409)
    - Follows project pattern of API-based test scripts (not Railway shell)
    - _Requirements: 5.4, 6.2, 6.3_

- [x] 11. Final checkpoint — Ensure all tests pass and feature is ready for staging deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using `hypothesis`
- Integration tests run locally against Railway staging API (no local DB needed)
- All new backend files follow the existing Railway/local dual-import pattern
- The `apscheduler` dependency is the only new pip package required
