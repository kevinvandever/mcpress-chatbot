# Implementation Plan: Article Metadata Quality

## Overview

This plan implements a multi-source metadata resolution system to fix ~290+ articles with poor metadata (numeric titles, unknown authors). The implementation builds up from data-loading services through resolution logic to API endpoints, with each step integrated before moving on. The approach reuses existing `AuthorService` and `DocumentAuthorService` for author management and follows the existing `ingestion_runs` pattern for backfill tracking.

Key files: Excel spreadsheets are at repo root (`MC Press Books - URL-Title-Author.xlsx` and `export_subset_DMU_v2.xlsx`). New backend files must be registered in `backend/main.py`. All testing is API-based against staging.

## Tasks

- [x] 1. Create ExcelLookupService with dual-spreadsheet loading
  - [x] 1.1 Create `backend/excel_lookup_service.py` with `ExcelLookupService` class and `ExcelMetadataEntry` dataclass
    - Load `export_subset_DMU_v2.xlsx` (column A = article ID, column B = title, column J = author, column K = article URL) into an in-memory dict keyed by numeric article ID string
    - Load `MC Press Books - URL-Title-Author.xlsx` (URL, Title, Author columns) as supplementary book data
    - Implement `lookup_by_id(article_id: str) -> Optional[ExcelMetadataEntry]` for O(1) lookup
    - Implement `lookup_by_filename(filename: str) -> Optional[ExcelMetadataEntry]` that extracts numeric ID from filename (e.g., "27814.pdf" → "27814") and delegates to `lookup_by_id`
    - Implement `parse_authors(author_string: str) -> List[str]` reusing the comma/"and" splitting pattern from `ExcelImportService.parse_authors()`
    - Implement `extract_id_from_url(url: str) -> Optional[str]` to extract numeric article ID from URL path segments
    - Implement `extract_id_from_filename(filename: str) -> Optional[str]` to extract numeric ID from filenames like "27814.pdf"
    - Handle missing/unreadable spreadsheet files gracefully: log warning, continue with empty mapping
    - Use openpyxl for reading Excel files (consistent with existing codebase)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 1.2 Write property tests for ExcelLookupService
    - **Property 1: Excel Lookup Round-Trip** — For any entry loaded from the spreadsheet, extracting the numeric article ID and looking it up via `lookup_by_id()` returns the original title
    - **Validates: Requirements 1.2, 7.5**
    - **Property 2: Lookup Miss Returns None** — For any numeric ID string not in the mapping, `lookup_by_id()` returns None
    - **Validates: Requirements 1.3**
    - **Property 3: Filename-to-ID Extraction** — For any string of digits `d`, constructing `"{d}.pdf"` and calling `extract_id_from_filename()` returns `d`
    - **Validates: Requirements 1.4**
    - **Property 4: Author String Parsing Round-Trip** — For any list of author names (no commas or "and"), joining with `", "` then calling `parse_authors()` returns the original list
    - **Validates: Requirements 1.5**
    - Create test file at `test_excel_lookup_properties.py` in repo root
    - Use Hypothesis library with `@settings(max_examples=100)`

  - [ ]* 1.3 Write unit tests for ExcelLookupService
    - Test loading from actual `export_subset_DMU_v2.xlsx` file (verify row count, spot-check known entries)
    - Test loading from actual `MC Press Books - URL-Title-Author.xlsx` file
    - Test graceful handling of missing file path
    - Test `extract_id_from_url` with real MC Press URLs from the spreadsheet
    - Test multi-author parsing edge cases (semicolons, "and", empty strings)
    - Create test file at `test_excel_lookup_unit.py` in repo root
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.4_

- [x] 2. Create WebsiteMetadataScraper for MC Press website fallback
  - [x] 2.1 Create `backend/website_metadata_scraper.py` with `WebsiteMetadataScraper` class and `ScrapedMetadata` dataclass
    - Implement `scrape_article(article_url: str) -> Optional[ScrapedMetadata]` using aiohttp with 10-second timeout
    - Include `User-Agent: MCPressChatbot/1.0` header in all requests
    - Implement `extract_title_from_html(html: str) -> Optional[str]` — look for `<h1>`, `<h2>` with article title class, or `<title>` tag
    - Implement `extract_author_from_html(html: str) -> Optional[str]` — look for "By Author Name" patterns or author metadata elements
    - Return None on 404, timeout, or parse failure (log appropriately)
    - The scraper uses the article URL from the export spreadsheet (Joomla-style slug URLs), NOT a constructed numeric ID URL
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.2 Write property tests for HTML extraction
    - **Property 5: HTML Metadata Extraction** — For any title and author, constructing HTML with `<h1>{title}</h1>` and "By {author}" pattern, then extracting returns the originals
    - **Validates: Requirements 2.2, 2.3**
    - Create test file at `test_website_scraper_properties.py` in repo root
    - Use Hypothesis with `@settings(max_examples=100)`

  - [ ]* 2.3 Write unit tests for WebsiteMetadataScraper
    - Test HTML extraction with sample MC Press article HTML structures
    - Test handling of 404 responses, timeouts, malformed HTML
    - Test User-Agent header is set correctly
    - Create test file at `test_website_scraper_unit.py` in repo root
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Create MetadataResolver with multi-source priority chain
  - [x] 3.1 Create `backend/metadata_resolver.py` with `MetadataResolver` class and `ResolvedMetadata` dataclass
    - Accept `ExcelLookupService`, `WebsiteMetadataScraper`, and `AuthorExtractor` as constructor dependencies
    - Implement `resolve(filename: str, pdf_path: Optional[str] = None) -> ResolvedMetadata` with resolution order: (a) Excel lookup, (b) website scraping using URL from Excel data, (c) PDF extraction via AuthorExtractor, (d) defaults
    - Short-circuit: if Excel returns both title and author, skip website and PDF steps
    - For website scraping, use the `article_url` from the `ExcelMetadataEntry` (not a constructed URL)
    - Log which source was used for each resolution
    - Return `ResolvedMetadata` with `title`, `authors` (list), `source` ("excel"/"website"/"pdf"/"default"), and optional `article_url`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 3.2 Write unit tests for MetadataResolver
    - Test resolution priority order with mocked dependencies
    - Test short-circuit when Excel match found
    - Test fallback from Excel miss → website → PDF → default
    - Test 404 fallback from website to PDF extraction
    - Test default values when all sources fail
    - Create test file at `test_metadata_resolver_unit.py` in repo root
    - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.7_

- [x] 4. Checkpoint — Review core services
  - Ensure all tests pass, ask the user if questions arise.
  - Verify ExcelLookupService loads both spreadsheets correctly
  - Verify MetadataResolver priority chain works end-to-end with mocked dependencies

- [x] 5. Create MetadataBackfillService and backfill_runs table
  - [x] 5.1 Create `backend/metadata_backfill_service.py` with `MetadataBackfillService` class, `BackfillResult` and `DiagnosticsResult` dataclasses
    - Implement `ensure_table()` to create `backfill_runs` table (following `ingestion_runs` pattern) with columns: id, run_id, status, started_at, completed_at, total_identified, titles_updated, authors_updated, still_poor, error_details (JSONB), details (JSONB)
    - Implement `identify_poor_metadata_articles() -> List[Dict]` — query books table for articles where title is digits-only OR author is "Unknown"/"Unknown Author", with `document_type = 'article'`
    - Implement `run_backfill() -> BackfillResult` that: identifies poor articles, resolves metadata for each via MetadataResolver, updates books table titles, creates/links authors via `AuthorService.get_or_create_author()` and `DocumentAuthorService`, tracks progress in backfill_runs table, handles per-article errors without stopping
    - Implement `get_diagnostics(detailed: bool = False) -> DiagnosticsResult` returning total articles, numeric title count, unknown author count, both-issues count, and sample (up to 20) or full list
    - Use `_running` flag to prevent concurrent backfill execution
    - Operate idempotently — safe to run multiple times without creating duplicate authors (uses `get_or_create_author`)
    - Clear existing document_authors for an article before re-linking (to handle re-runs cleanly)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 6.1, 6.2, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 5.2 Write property test for poor metadata identification
    - **Property 6: Poor Metadata Identification** — For any set of article records, `identify_poor_metadata_articles()` returns exactly those with digits-only titles OR "Unknown"/"Unknown Author" as author, and excludes articles with non-numeric titles and known authors
    - **Validates: Requirements 4.1**
    - This can be tested as a pure function test on the SQL WHERE clause logic
    - Create test in `test_backfill_properties.py` in repo root

  - [ ]* 5.3 Write property test for diagnostics count consistency
    - **Property 8: Diagnostics Count Consistency** — For any set of articles, `both_issues_count <= min(numeric_title_count, unknown_author_count)` and `numeric_title_count + unknown_author_count - both_issues_count <= total_articles`
    - **Validates: Requirements 6.2**
    - Create test in `test_backfill_properties.py` in repo root

  - [ ]* 5.4 Write property test for author deduplication
    - **Property 10: Author Deduplication** — For any set of articles sharing the same author name, after backfill there is exactly one authors table record for that name, and all articles reference the same author_id
    - **Validates: Requirements 8.1, 8.2, 8.6**
    - Create test in `test_backfill_properties.py` in repo root

  - [ ]* 5.5 Write property test for multi-author order preservation
    - **Property 11: Multi-Author Order Preservation** — For any article with multiple comma-separated authors, document_authors entries preserve original order (first author = `author_order=0`, second = `author_order=1`, etc.)
    - **Validates: Requirements 8.5**
    - Create test in `test_backfill_properties.py` in repo root

- [x] 6. Create API routes and register in main.py
  - [x] 6.1 Create `backend/article_metadata_routes.py` with FastAPI router
    - `POST /api/articles/backfill-metadata` — triggers backfill as background task, returns `{run_id, status: "started"}`, returns 409 if already running
    - `GET /api/articles/backfill-metadata/{run_id}` — returns backfill run result by run_id from backfill_runs table
    - `GET /api/articles/poor-metadata` — returns list of articles with poor metadata (delegates to `identify_poor_metadata_articles`)
    - `GET /api/diagnostics/article-metadata` — returns metadata quality statistics, supports `?detailed=true` query param
    - Use `set_backfill_service()` pattern for dependency injection (consistent with ingestion_routes.py)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

  - [x] 6.2 Register all new services and routes in `backend/main.py`
    - Import `ExcelLookupService`, `WebsiteMetadataScraper`, `MetadataResolver`, `MetadataBackfillService`, and `article_metadata_routes` using the try/except Railway/local import pattern
    - Initialize `ExcelLookupService` with paths to both Excel files during startup
    - Initialize `WebsiteMetadataScraper`
    - Initialize `MetadataResolver` with Excel lookup, website scraper, and existing `AuthorExtractor`
    - Initialize `MetadataBackfillService` with database_url, metadata_resolver, author_service, and document_author_service
    - Call `await backfill_service.ensure_table()` during startup to create backfill_runs table
    - Register the article_metadata_routes router
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Integrate MetadataResolver into IngestionService
  - [x] 7.1 Modify `backend/ingestion_service.py` to accept optional `MetadataResolver` in constructor
    - Add `metadata_resolver` parameter to `__init__`
    - In `process_and_store()`, after `_build_metadata()`, check if `document_type == "article"` and `metadata_resolver` is available
    - If so, call `await self.metadata_resolver.resolve(filename, file_path)` and override title/author with resolved values
    - Update author in books table and create author records via AuthorService (pass author_service as optional dependency)
    - Log which metadata source was used
    - Update the `IngestionService` initialization in `main.py` to pass the `MetadataResolver` instance
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 8. Checkpoint — Full integration review
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all new routes are registered and accessible
  - Verify backfill_runs table migration runs on startup

- [x] 9. Create API-based test scripts for staging validation
  - [x] 9.1 Create `test_article_metadata_api.py` in repo root for staging API testing
    - Test `GET /api/diagnostics/article-metadata` returns valid statistics structure
    - Test `GET /api/diagnostics/article-metadata?detailed=true` returns full article list
    - Test `GET /api/articles/poor-metadata` returns articles with poor metadata
    - Test `POST /api/articles/backfill-metadata` triggers backfill and returns run_id
    - Test `GET /api/articles/backfill-metadata/{run_id}` returns backfill results
    - Test 409 conflict when triggering concurrent backfill
    - Use `requests` library against staging URL (`https://mcpress-chatbot-staging.up.railway.app`)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

  - [ ]* 9.2 Write property test for backfill idempotence (API-based)
    - **Property 7: Backfill Idempotence** — Running backfill twice produces the same database state (same titles, authors, document_authors) and no duplicate author records
    - **Validates: Requirements 4.6**
    - This is an integration-level property test that calls the backfill API twice and compares diagnostics results
    - Create test in `test_backfill_idempotence_api.py` in repo root

- [x] 10. Final checkpoint — End-to-end validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify diagnostics endpoint shows correct counts before and after backfill
  - Verify backfill updates article titles and authors correctly
  - Verify ingestion pipeline uses metadata resolver for new numeric-filename articles

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The `export_subset_DMU_v2.xlsx` file is from late last year and won't contain the ~290 recently uploaded articles — the website scraping fallback handles those
- All testing is API-based against staging (no local test environment)
- New backend files must be registered in `backend/main.py` using the try/except import pattern
- Author management reuses existing `AuthorService.get_or_create_author()` and `DocumentAuthorService` — no new author tables needed
- Property 9 (URL Numeric ID Extraction) is covered by Property 1 and the unit tests in task 1.3
