# Implementation Plan: Admin Page Audit

## Overview

Build an API-based test suite that audits the MC Press Chatbot admin page against the Railway-deployed backend. Tests use Python `requests` for HTTP calls and `hypothesis` for property-based testing. The Excel file `expert_subset_DMU_v2.xlsm` is the source of truth. All tests run locally via `python3 -m pytest tests/` — no local database or server needed.

## Tasks

- [x] 1. Set up test infrastructure and shared fixtures
  - [x] 1.1 Create `tests/conftest.py` with shared fixtures
    - Define `API_URL` fixture reading from environment variable (default to Railway staging URL)
    - Create `api_session` fixture returning a `requests.Session` with base URL and timeout defaults
    - Create `excel_data` fixture that loads `expert_subset_DMU_v2.xlsm` via `openpyxl` or `pandas` and returns a list of `ExcelBookRecord` dicts with title, author, mc_press_url, article_url, author_site_url, document_type
    - Create `all_documents` fixture that fetches all documents from `GET /admin/documents` (paginating through all pages) and returns the full list
    - Create helper functions: `fetch_document_by_title(session, api_url, title)`, `update_metadata(session, api_url, filename, payload)`, `delete_document(session, api_url, filename)`
    - Create a `test_document` fixture that creates or identifies a dedicated test document for write tests, with teardown that restores original values
    - _Requirements: All (shared infrastructure)_

- [x] 2. Implement Excel-to-database accuracy tests
  - [x] 2.1 Create `tests/test_data_accuracy.py` with Property 1 tests
    - Load Excel data via `excel_data` fixture and all documents via `all_documents` fixture
    - For each Excel row, find the matching database record by title
    - Assert author, mc_press_url (if present), article_url (if present), and author site_url (if present) match between Excel and database
    - Report mismatches with field name, Excel value, and database value
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.2, 7.3_

  - [ ]* 2.2 Write property test for Excel-to-database field accuracy
    - **Property 1: Excel-to-database field accuracy**
    - Use `hypothesis` `@given` with `sampled_from(excel_rows)` to pick random Excel rows
    - For each sampled row, verify all fields match the database record
    - Configure `@settings(max_examples=100)`
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

- [x] 3. Implement document listing tests
  - [x] 3.1 Create `tests/test_document_listing.py` with listing verification tests
    - Test that `GET /admin/documents` returns documents with non-null id, filename, title, author/authors, and document_type fields
    - Test that multi-author documents return all authors sorted by author_order
    - Test search filtering: for a given search term, every returned document contains the term in title or author name
    - Test pagination: verify `total_pages == ceil(total / per_page)` and correct document count per page
    - Test sort: verify documents are ordered by the requested field and direction
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2_

  - [ ]* 3.2 Write property test for listing completeness (Property 2)
    - **Property 2: Listing returns complete document fields**
    - Sample random pages from the listing endpoint
    - Assert every document has non-null id, filename, title, author/authors, document_type
    - **Validates: Requirements 2.1**

  - [ ]* 3.3 Write property test for multi-author ordering (Property 3)
    - **Property 3: Multi-author documents return all authors in order**
    - Filter documents with multiple authors from listing
    - Assert authors array is sorted by author_order ascending
    - Assert author names come from authors table (not legacy books.author)
    - **Validates: Requirements 2.2, 5.1, 5.2**

  - [ ]* 3.4 Write property test for search correctness (Property 4)
    - **Property 4: Search returns only matching results**
    - Use `hypothesis` to generate random substrings from known titles/authors
    - Call `GET /admin/documents?search=X` and verify every result contains X in title or author name (case-insensitive)
    - **Validates: Requirements 2.3**

  - [ ]* 3.5 Write property test for pagination arithmetic (Property 5)
    - **Property 5: Pagination arithmetic is correct**
    - Use `hypothesis` to generate random page/per_page combinations
    - Assert `total_pages == ceil(total / per_page)`, returned count == `min(per_page, total - (page-1)*per_page)`, and page matches request
    - **Validates: Requirements 2.4**

  - [ ]* 3.6 Write property test for sort order (Property 6)
    - **Property 6: Sort order is correct**
    - Use `hypothesis` to sample from valid sort_by fields and directions
    - Fetch two consecutive pages and verify ordering is correct across the response
    - **Validates: Requirements 2.5**

- [x] 4. Checkpoint - Ensure all read-only tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement metadata editing tests
  - [x] 5.1 Create `tests/test_metadata_editing.py` with edit and validation tests
    - Test round-trip: edit title via `PUT /documents/{filename}/metadata`, then read back via `GET /admin/documents?search={title}&refresh=true` and assert values match
    - Test round-trip for author, mc_press_url, article_url fields
    - Test author_site_url round-trip: edit via `PATCH /api/authors/{id}`, read back via `GET /api/authors/{id}`
    - Test empty title rejection: submit empty/whitespace title, assert HTTP 400 and title unchanged
    - Restore original values in `finally` blocks after each write test
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 5.4_

  - [ ]* 5.2 Write property test for metadata edit round-trip (Property 7)
    - **Property 7: Metadata edit round-trip**
    - Use `hypothesis` to generate random valid titles (non-empty text), URLs (http:// prefixed strings)
    - Save via PUT, read back via GET with refresh=true, assert exact match
    - Restore original values in finally block
    - Configure `@settings(max_examples=100)`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3**

  - [ ]* 5.3 Write property test for empty title rejection (Property 8)
    - **Property 8: Empty and whitespace titles are rejected**
    - Use `hypothesis` to generate whitespace-only strings (spaces, tabs, newlines, empty)
    - Submit as title via PUT, assert HTTP 400
    - Verify document title remains unchanged
    - **Validates: Requirements 3.6**

- [x] 6. Implement author consistency tests
  - [x] 6.1 Create `tests/test_author_consistency.py` with author propagation tests
    - Test that updating an author name via `PATCH /api/authors/{id}` causes all associated documents to show the new name in `GET /admin/documents` with refresh
    - Restore original author name in `finally` block
    - _Requirements: 5.3_

  - [ ]* 6.2 Write property test for author name propagation (Property 9)
    - **Property 9: Author name update propagates to all documents**
    - Use `hypothesis` to generate random valid author names
    - Update author via PATCH, fetch all associated documents, verify new name appears
    - Restore original name in finally block
    - Configure `@settings(max_examples=100)`
    - **Validates: Requirements 5.3**

- [x] 7. Implement dashboard, Excel verification, and endpoint alignment tests
  - [x] 7.1 Create `tests/test_dashboard_stats.py` with dashboard accuracy tests
    - Test that dashboard document count (from `GET /documents`) matches admin listing total (from `GET /admin/documents`)
    - Test that last upload date is a real parseable date from document data, not hardcoded
    - _Requirements: 6.1, 6.2_

  - [x] 7.2 Create `tests/test_excel_verification.py` with Excel comparison tests
    - Test that `POST /api/excel/validate` accepts the source file without errors
    - Test that comparison results identify missing books and field mismatches
    - Test that each mismatch includes field_name, excel_value, and database_value
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 7.3 Create `tests/test_endpoint_alignment.py` with contract verification tests
    - Test `PUT /documents/{filename}/metadata` accepts correct payload structure (filename, title, author, category, mc_press_url, article_url)
    - Test `PATCH /api/authors/{author_id}` accepts site_url field
    - Test `DELETE /documents/{filename}` with correct filename encoding
    - Test `GET /admin/documents` accepts page, per_page, search, sort_by, sort_direction, refresh query parameters
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 8. Implement delete operation tests
  - [x] 8.1 Create `tests/test_delete_operations.py` with delete and cascade tests
    - Test that deleting a document via `DELETE /documents/{filename}` removes it from `GET /admin/documents` results
    - Test that document_authors entries are also removed (verify via `GET /api/documents/{id}` returning 404)
    - Test that deleting a non-existent document returns 404
    - Use a dedicated test document (upload or create one for the test, or use a known expendable record)
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 8.2 Write property test for delete cascade (Property 10)
    - **Property 10: Delete removes document and cascades to associations**
    - Create a test document, delete it, verify it no longer appears in listing
    - Verify document_authors entries removed (GET /api/documents/{id} returns 404)
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All write tests must restore original state in `finally` blocks to avoid polluting the shared database
- Tests run via `API_URL=https://mcpress-chatbot-staging.up.railway.app python3 -m pytest tests/ -v`
