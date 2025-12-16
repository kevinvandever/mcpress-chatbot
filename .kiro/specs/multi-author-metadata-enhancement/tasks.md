# Implementation Plan

- [x] 1. Create database schema for multi-author support
  - Create authors table with id, name, site_url, timestamps
  - Create document_authors junction table with book_id, author_id, author_order
  - Add document_type and article_url columns to books table (mc_press_url already exists)
  - Create indexes on authors.name, document_authors foreign keys
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1_

- [x] 1.1 Write property test for author table constraints
  - **Property 2: Author deduplication**
  - **Validates: Requirements 1.2**

- [x] 2. Implement AuthorService for author management
  - Write get_or_create_author() method with name deduplication
  - Write update_author() method for updating author details
  - Write get_author_by_id() method for retrieval
  - Write search_authors() method for autocomplete
  - Write get_authors_for_document() method to fetch ordered authors
  - _Requirements: 1.2, 3.1, 3.2, 5.2, 5.3, 5.4_

- [x] 2.1 Write property test for author deduplication
  - **Property 2: Author deduplication**
  - **Validates: Requirements 1.2**

- [x] 2.2 Write property test for get or create behavior
  - **Property 14: Create or reuse author on add**
  - **Validates: Requirements 5.3, 5.4**

- [x] 3. Implement DocumentAuthorService for relationship management
  - Write add_author_to_document() method with duplicate prevention
  - Write remove_author_from_document() method with last-author validation
  - Write reorder_authors() method for changing author order
  - Write get_documents_by_author() method for author filtering
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 5.7, 8.1_

- [x] 3.1 Write property test for duplicate prevention
  - **Property 3: No duplicate author associations**
  - **Validates: Requirements 1.4**

- [x] 3.2 Write property test for last author validation
  - **Property 16: Require at least one author**
  - **Validates: Requirements 5.7**

- [x] 3.3 Write property test for cascade deletion
  - **Property 4: Cascade deletion preserves shared authors**
  - **Validates: Requirements 1.5**

- [x] 4. Create database migration script
  - Write migration to create new tables (authors, document_authors)
  - Extract unique authors from books.author column
  - Create author records with deduplication
  - Create document_authors associations for all books
  - Add new columns to books table (document_type, article_url) - mc_press_url already exists
  - Set default document_type='book' for existing records
  - Verify all documents have at least one author after migration
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4.1 Write property test for migration data preservation
  - **Property 13: Migration preserves metadata**
  - **Validates: Requirements 4.4**

- [x] 5. Implement author management API endpoints
  - Create GET /api/authors/search endpoint for autocomplete
  - Create GET /api/authors/{author_id} endpoint for author details
  - Create PATCH /api/authors/{author_id} endpoint for updates
  - Create GET /api/authors/{author_id}/documents endpoint
  - Add URL validation for author site URLs
  - _Requirements: 3.1, 3.2, 3.3, 5.2, 5.6, 8.1, 8.3_

- [x] 5.1 Write property test for URL validation
  - **Property 10: URL validation**
  - **Validates: Requirements 3.2**

- [x] 5.2 Write property test for author updates propagating
  - **Property 15: Author updates propagate**
  - **Validates: Requirements 5.6**

- [x] 6. Implement document-author relationship API endpoints
  - Create POST /api/documents/{document_id}/authors endpoint
  - Create DELETE /api/documents/{document_id}/authors/{author_id} endpoint
  - Create PUT /api/documents/{document_id}/authors/order endpoint
  - Update GET /api/documents/{document_id} to include authors array
  - Add document_type to document responses
  - _Requirements: 1.1, 1.3, 2.4, 5.1, 5.7_

- [x] 6.1 Write property test for multiple author association
  - **Property 1: Multiple author association**
  - **Validates: Requirements 1.1, 1.3**

- [x] 6.2 Write property test for document type in responses
  - **Property 7: Document type in responses**
  - **Validates: Requirements 2.4**

- [x] 7. Integrate author services into main.py
  - Initialize AuthorService and DocumentAuthorService in main.py
  - Register author_router and document_author_router
  - Set service instances for route handlers
  - _Requirements: All backend endpoints_

- [x] 8. Update admin documents endpoints for multi-author support
  - Modify list_documents endpoint to include authors array from document_authors table
  - Modify update_document endpoint to handle authors array
  - Update document model to include document_type field
  - Add validation for document_type (book/article)
  - Update metadata_history to track author changes
  - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.5, 5.6_

- [x] 8.1 Write property test for document type validation
  - **Property 5: Document type validation**
  - **Validates: Requirements 2.1**

- [x] 8.2 Write property test for type-specific URL fields
  - **Property 6: Type-specific URL fields**
  - **Validates: Requirements 2.2, 2.3**

- [x] 9. Create data migration script to populate authors table
  - Extract unique authors from existing books.author column
  - Create author records using AuthorService.get_or_create_author()
  - Create document_authors associations for all existing books
  - Verify all documents have at least one author after migration
  - Log migration progress and any errors
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 10. Update CSV export to include multi-author data
  - Add authors column with pipe-delimited author names
  - Add author_site_urls column with pipe-delimited URLs
  - Add document_type column
  - Add article_url column
  - Keep mc_press_url column as-is (already exists)
  - Format multiple authors as "Author1|Author2|Author3"
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 10.1 Write property test for CSV multi-author export
  - **Property 20: CSV export includes all authors**
  - **Validates: Requirements 7.1**

- [x] 10.2 Write property test for CSV field inclusion
  - **Property 21: CSV export includes all URL fields**
  - **Validates: Requirements 7.2**

- [x] 10.3 Write property test for CSV formatting
  - **Property 22: CSV multi-author formatting**
  - **Validates: Requirements 7.3**

- [x] 11. Update CSV import to parse multi-author data
  - Parse pipe-delimited authors from CSV
  - Parse pipe-delimited author_site_urls from CSV
  - Call AuthorService.get_or_create_author() for each author
  - Create document_authors associations
  - Handle document_type field
  - Handle article_url and mc_press_url fields
  - _Requirements: 7.4, 7.5_

- [x]* 11.1 Write property test for CSV round-trip
  - **Property 23: CSV import round-trip**
  - **Validates: Requirements 7.4**

- [x]* 11.2 Write property test for CSV import author creation
  - **Property 24: CSV import creates authors**
  - **Validates: Requirements 7.5**

- [x] 12. Create MultiAuthorInput React component
  - Build input field with autocomplete for author names
  - Implement author search API integration using /api/authors/search
  - Add ability to add new authors inline
  - Implement drag-and-drop for author reordering
  - Add inline editing for author site URLs
  - Add remove button for each author (with last-author validation)
  - Style using MC Press design tokens (--mc-blue, --mc-orange, etc.)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7_

- [x] 13. Create DocumentTypeSelector React component
  - Build radio buttons for book/article selection
  - Show mc_press_url field when type is 'book' (existing field)
  - Show article_url field when type is 'article'
  - Implement URL validation on frontend
  - Style using MC Press design tokens
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 14. Update DocumentList component for multi-author display
  - Fetch authors from GET /api/documents/{document_id} endpoint
  - Display all authors for each document (comma-separated)
  - Show document type badge (book/article)
  - Update edit dialog to use MultiAuthorInput component
  - Update edit dialog to use DocumentTypeSelector component
  - Handle author site URL display and linking
  - _Requirements: 1.3, 2.4, 3.3, 3.4_

- [x] 15. Update MetadataEditDialog for multi-author editing
  - Replace single author input with MultiAuthorInput component
  - Add DocumentTypeSelector component
  - Add conditional URL fields based on document type
  - Update save handler to call POST /api/documents/{document_id}/authors
  - Handle author reordering using PUT /api/documents/{document_id}/authors/order
  - _Requirements: 5.1, 5.5, 5.6, 5.7_

- [x] 16. Implement author search and filtering in existing endpoints
  - Update document search to query document_authors join
  - Implement exact author name matching filter
  - Add author document count to author responses (already in AuthorService)
  - Implement pagination for author lists (already in author_routes)
  - Implement sorting by name or document count
  - Add filter to exclude authors with zero documents
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x]* 16.1 Write property test for author search
  - **Property 25: Search by author returns all documents**
  - **Validates: Requirements 8.1**

- [x]* 16.2 Write property test for exact matching
  - **Property 26: Exact author name matching**
  - **Validates: Requirements 8.2**

- [x]* 16.3 Write property test for document count
  - **Property 27: Author document count**
  - **Validates: Requirements 8.3**

- [x]* 16.4 Write property test for pagination and sorting
  - **Property 28: Author pagination and sorting**
  - **Validates: Requirements 8.4**

- [x]* 16.5 Write property test for filtering empty authors
  - **Property 29: Filter authors without documents**
  - **Validates: Requirements 8.5**

- [x] 17. Update BatchUpload component for multi-author support
  - Update progress display to show parsed authors
  - Handle author prompt for documents without metadata
  - Display author count in upload summary
  - Show document type in file status
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 18. Add spreadsheet import functionality for author metadata
  - Create Excel import endpoint for author metadata spreadsheets
  - Parse author names, site URLs, and additional metadata from files
  - Create new author records and update existing ones
  - Validate URLs before storing in database
  - Report creation/update statistics and validation errors
  - Support CSV format with configurable column mappings
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 19. Add spreadsheet import functionality for article metadata
  - Create Excel import endpoint for article metadata spreadsheets
  - Parse document IDs, article URLs, titles, and category information
  - Update existing document records with article metadata
  - Set document_type to "article" for documents with article URLs
  - Validate URLs and preserve existing document data
  - Report update statistics and handle missing document IDs
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 20. Add spreadsheet validation and preview functionality
  - Validate file format and column headers before processing
  - Check for required columns and report missing fields
  - Identify invalid URLs, duplicate entries, and data format issues
  - Provide preview of first 10 rows with validation status
  - Show detailed error messages for specific rows and columns
  - Allow administrators to proceed or cancel after validation
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [x] 21. Update batch upload to support multi-author parsing
  - Parse multiple authors from PDF metadata (separated by semicolon, comma, or "and")
  - Call AuthorService.get_or_create_author() for each parsed author
  - Create document_authors associations in correct order
  - Set document_type based on file metadata or default to 'book'
  - Handle missing author metadata with default or prompt
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x]* 21.1 Write property test for batch upload author creation
  - **Property 17: Batch upload creates authors**
  - **Validates: Requirements 6.1**

- [x]* 21.2 Write property test for multi-author parsing
  - **Property 18: Parse multiple authors**
  - **Validates: Requirements 6.2**

- [x]* 21.3 Write property test for batch deduplication
  - **Property 19: Batch upload deduplicates authors**
  - **Validates: Requirements 6.5**

- [x] 22. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 23. Run database migration on production environment
  - Create database backup
  - Execute migration script (backend/run_migration_003.py)
  - Run data migration script to populate authors table
  - Run verification queries
  - Check for any data integrity issues
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 24. Update API documentation
  - Document new author management endpoints
  - Document updated document endpoints with authors array
  - Document CSV format changes
  - Document migration procedure
  - Add examples for multi-author operations
  - _Requirements: All_

- [x] 25. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

