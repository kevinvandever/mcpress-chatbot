# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Book Authors Missing site_url During Import
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate book authors never receive site_url values during import
  - **Scoped PBT Approach**: Scope the property to the concrete failing case: call `import_book_metadata()` for a book whose author name exists in the article Excel mapping, then verify the author's `site_url` is non-NULL
  - **Bug Condition**: `isBugCondition(author) = author.name IN article_excel_mapping AND author was created/updated via import_book_metadata()`
  - **Expected Behavior**: `expectedBehavior(author) = author.site_url == article_excel_mapping[author.name]` (non-NULL, matching the article data)
  - Create a test script `tests/test_author_url_bug_condition.py` that:
    - Calls `POST /api/excel/import/books` with the book Excel file (no author_url_file) against staging
    - Then queries `GET /api/authors/search?q={author_name}` for a known matching author (one of the 37 matches)
    - Asserts the author's `site_url` is non-NULL and matches the expected URL from article data
  - Run test on UNFIXED code - expect FAILURE (author.site_url will be NULL, confirming the bug)
  - Document counterexample: e.g., "Author 'Jim Buck' has site_url=NULL despite having URL in article Excel"
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Import Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - **Observe on UNFIXED code**:
    - `POST /api/excel/import/articles` with article Excel still passes author_url to `_get_or_create_author_in_transaction()` (article authors get site_url)
    - `POST /api/excel/import/books` still creates correct author-document associations
    - `POST /api/excel/import/books` still performs fuzzy title matching and mc_press_url updates
    - Authors with no matching URL in article data remain with NULL site_url
  - Create a test script `tests/test_author_url_preservation.py` that:
    - Calls `GET /api/authors/search?q={name}` for several article-imported authors and verifies their site_url is already non-NULL (article import path works)
    - Calls `GET /api/authors/{id}/documents` for a known book author and verifies document associations exist
    - Calls `GET /api/authors/search?q={name}` for an author known to have NO article URL and verifies site_url is NULL
    - Verifies the book import endpoint still returns expected stats (books_processed, books_matched counts)
  - Write property-based tests: for all authors imported via article path, site_url should be non-NULL; for all book-only authors with no article match, site_url should be NULL
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Implement the fix for missing author site_url during book import

  - [x] 3.1 Add `build_author_url_mapping()` method to `ExcelImportService`
    - Add new method in `backend/excel_import_service.py`
    - Read article Excel file (`export_subset_DMU_v2.xlsx`) with `openpyxl` using `data_only=True` (cells contain formulas)
    - Iterate the `export_subset` sheet, extracting column J (index 9, author name) and column L (index 11, "Arthor URL")
    - Build `Dict[str, str]` mapping `author_name → author_url`
    - Normalize URLs via existing `_normalize_url()`, validate via `_is_valid_url()`
    - Skip rows with empty/invalid author names or URLs
    - Return the mapping (expect ~959 unique entries)
    - _Bug_Condition: isBugCondition(author) = author.name IN mapping AND author created via import_book_metadata() without site_url_
    - _Expected_Behavior: build_author_url_mapping() returns Dict where every value is valid http/https URL_
    - _Preservation: Article import path unchanged - this is a new additive method_
    - _Requirements: 2.1, 2.3_

  - [x] 3.2 Modify `import_book_metadata()` to accept and use author URL mapping
    - Change signature to `async def import_book_metadata(self, file_path: str, author_url_mapping: Optional[Dict[str, str]] = None) -> ImportResult:`
    - In the author processing loop, look up: `site_url = author_url_mapping.get(author_name) if author_url_mapping else None`
    - Pass site_url to `_get_or_create_author_in_transaction(conn, author_name, site_url)`
    - Track `authors_updated` count when a URL is applied
    - Default `None` preserves backward compatibility (existing callers unaffected)
    - _Bug_Condition: import_book_metadata() calls _get_or_create_author_in_transaction(conn, author_name) without site_url_
    - _Expected_Behavior: import_book_metadata() now passes site_url from mapping when available_
    - _Preservation: When author_url_mapping is None, behavior identical to current code_
    - _Requirements: 2.1, 2.2, 3.1, 3.4_

  - [x] 3.3 Add `POST /api/excel/backfill-author-urls` endpoint
    - Add new endpoint in `backend/excel_import_routes.py`
    - Accept article Excel file via `UploadFile`
    - Save to temp file, call `build_author_url_mapping()` to extract author URLs
    - Iterate mapping entries, call `_get_or_create_author_in_transaction()` for each author with their URL
    - The `ON CONFLICT` upsert with `COALESCE(EXCLUDED.site_url, authors.site_url)` handles updates correctly
    - Return stats: `{ mapping_size, authors_checked, authors_updated, authors_not_found }`
    - Clean up temp file in finally block
    - _Bug_Condition: No mechanism existed to backfill author URLs for existing authors_
    - _Expected_Behavior: Endpoint updates matched authors' site_url from article data_
    - _Preservation: Does not modify unmatched authors or any document associations_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.3_

  - [x] 3.4 Modify existing `POST /api/excel/import/books` endpoint to accept optional author URL file
    - Update endpoint signature to accept optional `author_url_file: Optional[UploadFile] = File(None)`
    - If `author_url_file` provided, save to temp, call `build_author_url_mapping()`, pass to `import_book_metadata()`
    - If not provided, call `import_book_metadata()` without mapping (backward compatible)
    - Clean up both temp files in finally block
    - _Bug_Condition: Endpoint had no way to supply author URL data during book import_
    - _Expected_Behavior: Endpoint optionally accepts article Excel and passes mapping through_
    - _Preservation: Without author_url_file, behavior identical to current endpoint_
    - _Requirements: 2.3, 3.4_

  - [x] 3.5 Register backfill endpoint in `backend/main.py` (if needed)
    - The backfill endpoint is on the existing `excel_import_routes.router` so it should auto-register
    - Verify the new endpoint appears in the deployed API
    - _Requirements: 2.3_

  - [x] 3.6 Create `backfill_author_urls.py` root-level script
    - API-based script following project patterns (uses `requests`, runs locally)
    - Uploads `export_subset_DMU_v2.xlsx` to `POST /api/excel/backfill-author-urls` on staging
    - Prints response stats (mapping_size, authors_updated, etc.)
    - Use staging URL by default: `https://mcpress-chatbot-staging.up.railway.app`
    - _Requirements: 2.1, 2.2, 2.3_

  - [-] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Book Authors Get site_url From Article Data
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - After deploying the fix to staging and running the backfill script:
    - Re-run `tests/test_author_url_bug_condition.py` against staging
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms matched authors now have non-NULL site_url
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [-] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Import Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Re-run `tests/test_author_url_preservation.py` against staging
    - Verify article-imported authors still have site_url
    - Verify book-only authors with no match still have NULL site_url
    - Verify document associations unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Deploy all changes to staging via `feature/* → staging` merge
  - Wait for Railway staging deployment (~10-15 min)
  - Run `backfill_author_urls.py` against staging to populate author URLs
  - Run `tests/test_author_url_bug_condition.py` - should PASS
  - Run `tests/test_author_url_preservation.py` - should PASS
  - Verify via `GET /api/authors/search?q={name}` that matched authors have site_url
  - Verify via `GET /api/authors/search?q={name}` that unmatched authors still have NULL site_url
  - Ensure all tests pass, ask the user if questions arise
