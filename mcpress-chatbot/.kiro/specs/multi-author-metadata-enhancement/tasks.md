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

- [x] 4. Create data migration script
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

- [ ] 9. Implement ExcelImportService for Excel file processing
  - Install required dependencies (pandas, openpyxl, fuzzywuzzy, python-levenshtein)
  - Write validate_excel_file() method for file format and column validation
  - Write preview_excel_data() method for data preview with validation status
  - Write parse_authors() method for comma/"and" delimited author parsing
  - Write fuzzy_match_title() method for book title matching
  - Integrate with existing AuthorService for author management
  - _Requirements: 9.1, 9.2, 9.4, 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 9.1 Write property test for Excel file format validation
  - **Property 30: Excel file format validation**
  - **Validates: Requirements 11.1**

- [ ] 9.2 Write property test for book metadata column validation
  - **Property 31: Book metadata column validation**
  - **Validates: Requirements 11.2**

- [ ] 9.3 Write property test for article metadata sheet validation
  - **Property 32: Article metadata sheet validation**
  - **Validates: Requirements 11.3**

- [ ] 9.4 Write property test for Excel data validation
  - **Property 33: Excel data validation**
  - **Validates: Requirements 11.4**

- [ ] 9.5 Write property test for Excel preview accuracy
  - **Property 34: Excel preview accuracy**
  - **Validates: Requirements 11.5**

- [ ] 10. Implement book metadata import functionality
  - Write import_book_metadata() method to process book-metadata.xlsm
  - Implement fuzzy matching against existing books.title
  - Update matched books with mc_press_url from Excel data
  - Parse and create/update author records for each book
  - Generate detailed import reports with counts and errors
  - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.6_

- [ ] 10.1 Write property test for book title fuzzy matching
  - **Property 37: Book title fuzzy matching**
  - **Validates: Requirements 9.2**

- [ ] 10.2 Write property test for book URL update
  - **Property 38: Book URL update**
  - **Validates: Requirements 9.3**

- [ ] 10.3 Write property test for book author parsing
  - **Property 39: Book author parsing**
  - **Validates: Requirements 9.4**

- [ ] 10.4 Write property test for book author service integration
  - **Property 40: Book author service integration**
  - **Validates: Requirements 9.5**

- [ ] 10.5 Write property test for book import reporting
  - **Property 41: Book import reporting**
  - **Validates: Requirements 9.6**

- [ ] 11. Implement article metadata import functionality
  - Write import_article_metadata() method to process article-links.xlsm
  - Read only export_subset sheet and filter by feature article = "yes"
  - Match article IDs against PDF filenames (with/without .pdf extension)
  - Create/update author records with author URLs from column L
  - Store article URLs and set document_type to "article"
  - Generate detailed import reports with counts and errors
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 11.1 Write property test for article sheet filtering
  - **Property 42: Article sheet filtering**
  - **Validates: Requirements 10.1**

- [ ] 11.2 Write property test for article feature filtering
  - **Property 43: Article feature filtering**
  - **Validates: Requirements 10.2**

- [ ] 11.3 Write property test for article ID matching
  - **Property 44: Article ID matching**
  - **Validates: Requirements 10.3**

- [ ] 11.4 Write property test for article author processing
  - **Property 45: Article author processing**
  - **Validates: Requirements 10.4**

- [ ] 11.5 Write property test for article URL storage
  - **Property 46: Article URL storage**
  - **Validates: Requirements 10.5, 10.6**

- [ ] 11.6 Write property test for article import reporting
  - **Property 47: Article import reporting**
  - **Validates: Requirements 10.7**

- [ ] 12. Implement Excel import API endpoints
  - Create POST /api/excel/validate endpoint for file validation and preview
  - Create POST /api/excel/import/books endpoint for book metadata import
  - Create POST /api/excel/import/articles endpoint for article metadata import
  - Add file upload handling with multipart/form-data support
  - Implement comprehensive error handling and validation
  - Add detailed logging for all Excel import operations
  - _Requirements: 11.1, 11.6, 11.7_

- [ ] 12.1 Write property test for Excel error reporting
  - **Property 35: Excel error reporting**
  - **Validates: Requirements 11.6**

- [ ] 12.2 Write property test for Excel workflow control
  - **Property 36: Excel workflow control**
  - **Validates: Requirements 11.7**

- [ ] 13. Create data migration script to populate authors table
  - Extract unique authors from existing books.author column
  - Create author records using AuthorService.get_or_create_author()
  - Create document_authors associations for all existing books
  - Verify all documents have at least one author after migration
  - Log migration progress and any errors
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 14. Update batch upload to support multi-author parsing
  - Parse multiple authors from PDF metadata (separated by semicolon, comma, or "and")
  - Call AuthorService.get_or_create_author() for each parsed author
  - Create document_authors associations in correct order
  - Set document_type based on file metadata or default to 'book'
  - Handle missing author metadata with default or prompt
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 14.1 Write property test for batch upload author creation
  - **Property 17: Batch upload creates authors**
  - **Validates: Requirements 6.1**

- [ ] 14.2 Write property test for multi-author parsing
  - **Property 18: Parse multiple authors**
  - **Validates: Requirements 6.2**

- [ ] 14.3 Write property test for batch deduplication
  - **Property 19: Batch upload deduplicates authors**
  - **Validates: Requirements 6.5**

- [ ] 15. Update CSV export to include multi-author data
  - Add authors column with pipe-delimited author names
  - Add author_site_urls column with pipe-delimited URLs
  - Add document_type column
  - Add article_url column
  - Keep mc_press_url column as-is (already exists)
  - Format multiple authors as "Author1|Author2|Author3"
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 15.1 Write property test for CSV multi-author export
  - **Property 20: CSV export includes all authors**
  - **Validates: Requirements 7.1**

- [ ] 15.2 Write property test for CSV field inclusion
  - **Property 21: CSV export includes all URL fields**
  - **Validates: Requirements 7.2**

- [ ] 15.3 Write property test for CSV formatting
  - **Property 22: CSV multi-author formatting**
  - **Validates: Requirements 7.3**

- [ ] 16. Update CSV import to parse multi-author data
  - Parse pipe-delimited authors from CSV
  - Parse pipe-delimited author_site_urls from CSV
  - Call AuthorService.get_or_create_author() for each author
  - Create document_authors associations
  - Handle document_type field
  - Handle article_url and mc_press_url fields
  - _Requirements: 7.4, 7.5_

- [ ]* 16.1 Write property test for CSV round-trip
  - **Property 23: CSV import round-trip**
  - **Validates: Requirements 7.4**

- [ ]* 16.2 Write property test for CSV import author creation
  - **Property 24: CSV import creates authors**
  - **Validates: Requirements 7.5**

- [ ] 17. Implement author search and filtering in existing endpoints
  - Update document search to query document_authors join
  - Implement exact author name matching filter
  - Add author document count to author responses (already in AuthorService)
  - Implement pagination for author lists (already in author_routes)
  - Implement sorting by name or document count
  - Add filter to exclude authors with zero documents
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 17.1 Write property test for author search
  - **Property 25: Search by author returns all documents**
  - **Validates: Requirements 8.1**

- [ ]* 17.2 Write property test for exact matching
  - **Property 26: Exact author name matching**
  - **Validates: Requirements 8.2**

- [ ]* 17.3 Write property test for document count
  - **Property 27: Author document count**
  - **Validates: Requirements 8.3**

- [ ]* 17.4 Write property test for pagination and sorting
  - **Property 28: Author pagination and sorting**
  - **Validates: Requirements 8.4**

- [ ]* 17.5 Write property test for filtering empty authors
  - **Property 29: Filter authors without documents**
  - **Validates: Requirements 8.5**

- [ ] 18. Create ExcelImportDialog React component
  - Build file upload interface with drag-and-drop support
  - Add file type selection (book/article) with radio buttons
  - Implement validation preview with error highlighting
  - Add progress tracking during import with loading states
  - Display detailed results with success/error counts
  - Show error reporting with row/column specific details
  - Style using MC Press design tokens
  - _Requirements: 11.1, 11.4, 11.5, 11.6, 11.7_

- [ ] 19. Create MultiAuthorInput React component
  - Build input field with autocomplete for author names
  - Implement author search API integration using /api/authors/search
  - Add ability to add new authors inline
  - Implement drag-and-drop for author reordering
  - Add inline editing for author site URLs
  - Add remove button for each author (with last-author validation)
  - Style using MC Press design tokens (--mc-blue, --mc-orange, etc.)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7_

- [ ] 20. Create DocumentTypeSelector React component
  - Build radio buttons for book/article selection
  - Show mc_press_url field when type is 'book' (existing field)
  - Show article_url field when type is 'article'
  - Implement URL validation on frontend
  - Style using MC Press design tokens
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 21. Update DocumentList component for multi-author display
  - Fetch authors from GET /api/documents/{document_id} endpoint
  - Display all authors for each document (comma-separated)
  - Show document type badge (book/article)
  - Update edit dialog to use MultiAuthorInput component
  - Update edit dialog to use DocumentTypeSelector component
  - Handle author site URL display and linking
  - Add Excel import button and integrate ExcelImportDialog
  - _Requirements: 1.3, 2.4, 3.3, 3.4_

- [ ] 22. Update MetadataEditDialog for multi-author editing
  - Replace single author input with MultiAuthorInput component
  - Add DocumentTypeSelector component
  - Add conditional URL fields based on document type
  - Update save handler to call POST /api/documents/{document_id}/authors
  - Handle author reordering using PUT /api/documents/{document_id}/authors/order
  - _Requirements: 5.1, 5.5, 5.6, 5.7_

- [ ] 23. Update BatchUpload component for multi-author support
  - Update progress display to show parsed authors
  - Handle author prompt for documents without metadata
  - Display author count in upload summary
  - Show document type in file status
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 24. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 25. Test Excel import functionality with actual data files
  - Test book-metadata.xlsm import with your actual MC Press book data
  - Test article-links.xlsm import with your actual article data
  - Verify fuzzy matching works correctly with real book titles
  - Verify author parsing handles all author name formats in your data
  - Test validation and error handling with various file formats
  - _Requirements: 9.1-9.6, 10.1-10.7, 11.1-11.7_

- [ ] 26. Run database migration on production environment
  - Create database backup
  - Execute migration script (backend/run_migration_003.py)
  - Run data migration script to populate authors table
  - Run verification queries
  - Check for any data integrity issues
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 27. Update API documentation
  - Document new Excel import endpoints
  - Document author management endpoints
  - Document updated document endpoints with authors array
  - Document CSV format changes
  - Document migration procedure
  - Add examples for multi-author and Excel import operations
  - _Requirements: All_

- [ ] 28. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.