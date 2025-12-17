# Implementation Plan

- [x] 1. Fix the SQL query column name bug
  - [x] 1.1 Update the SQL query in `_enrich_source_metadata()` to use `da.book_id` instead of `da.document_id`
    - Open `backend/chat_handler.py`
    - Locate the SQL query at approximately line 491
    - Change `WHERE da.document_id = $1` to `WHERE da.book_id = $1`
    - Verify no other references to `document_id` exist in the enrichment code
    - _Requirements: 1.2, 1.3_

  - [ ]* 1.2 Write property test for correct column name usage
    - **Property 1: Correct column name in SQL query**
    - **Validates: Requirements 1.2, 1.3**
    - Create test that mocks database connection
    - Verify SQL query contains "book_id" not "document_id"
    - Verify no UndefinedColumnError is raised
    - _Requirements: 1.2, 1.3_

- [ ] 2. Verify enrichment behavior with test data
  - [-] 2.1 Create unit test for successful enrichment with multiple authors
    - Mock database to return book with 3 authors in specific order
    - Call `_enrich_source_metadata()` with test filename
    - Verify returned metadata contains all author objects
    - Verify all required fields are present (author, mc_press_url, article_url, document_type, authors)
    - _Requirements: 1.4, 2.1, 2.2, 2.3_

  - [ ]* 2.2 Write property test for author ordering
    - **Property 2: Author ordering preservation**
    - **Validates: Requirements 1.5**
    - Generate random number of authors (2-5) with random order values
    - Verify returned authors array is sorted by author_order ascending
    - _Requirements: 1.5_

  - [ ]* 2.3 Write property test for legacy author fallback
    - **Property 3: Legacy author fallback**
    - **Validates: Requirements 1.6**
    - Generate random books with no document_authors records
    - Verify enriched metadata uses legacy author field
    - Verify authors array is empty
    - _Requirements: 1.6_

  - [ ]* 2.4 Write property test for complete metadata structure
    - **Property 4: Complete metadata structure**
    - **Validates: Requirements 2.1, 2.2, 2.3**
    - Generate random valid book data
    - Verify returned metadata contains all required keys
    - Verify data types are correct (author: str, mc_press_url: str, article_url: str|None, document_type: str, authors: list)
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Test error handling and graceful degradation
  - [ ] 3.1 Create unit test for missing DATABASE_URL
    - Mock environment to have no DATABASE_URL
    - Call `_enrich_source_metadata()`
    - Verify empty dict is returned
    - Verify warning is logged
    - _Requirements: 4.1_

  - [ ] 3.2 Create unit test for database connection failure
    - Mock asyncpg.connect() to raise ConnectionError
    - Call `_enrich_source_metadata()`
    - Verify empty dict is returned
    - Verify error is logged with traceback
    - _Requirements: 4.2_

  - [ ] 3.3 Create unit test for book not found
    - Mock database to return no book record
    - Call `_enrich_source_metadata()`
    - Verify empty dict is returned
    - Verify info log message
    - _Requirements: 4.3_

  - [ ]* 3.4 Write property test for graceful degradation
    - **Property 5: Graceful degradation on failure**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
    - Generate various failure scenarios (missing env, connection error, not found)
    - Verify all return empty dict
    - Verify _format_sources() uses fallback values
    - Verify "Unknown" appears as author
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 4. Verify logging behavior
  - [ ]* 4.1 Write property test for error logging
    - **Property 6: Comprehensive error logging**
    - **Validates: Requirements 3.5**
    - Generate random errors during enrichment
    - Verify error message and stack trace appear in logs
    - _Requirements: 3.5_

  - [ ]* 4.2 Write property test for enrichment logging
    - **Property 7: Enrichment attempt logging**
    - **Validates: Requirements 3.1, 3.3, 3.4**
    - Generate random filenames and book data
    - Verify filename is logged at start
    - Verify book title and author are logged when found
    - _Requirements: 3.1, 3.3, 3.4_

- [ ] 5. Deploy and verify fix on Railway
  - [ ] 5.1 Deploy the fix to Railway
    - Commit changes to git
    - Push to main branch to trigger Railway deployment
    - Monitor Railway deployment logs for successful build
    - Wait for deployment to complete (~10-15 minutes)
    - _Requirements: All_

  - [ ] 5.2 Test enrichment in production
    - Submit test chat query: "Tell me about DB2"
    - Monitor Railway logs for enrichment messages
    - Verify no "column da.document_id does not exist" errors
    - Verify logs show "Found book: [title] by [author]"
    - Verify logs show "Using multi-author data: [names]" or "Using legacy author: [name]"
    - Verify logs show "Enrichment result: {..." with populated data
    - _Requirements: All_

  - [ ] 5.3 Verify frontend display
    - Open chat interface in browser
    - Submit query that returns known books
    - Verify sources show actual author names (not "Unknown")
    - Verify "Buy" buttons appear for books with mc_press_url
    - Verify "Read" buttons appear for articles with article_url
    - Verify author names with site_url are clickable links
    - _Requirements: 2.4, 2.5, 5.2, 5.3, 5.4, 5.5_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
