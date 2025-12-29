# Implementation Plan: Final UI Fixes

## Overview

This implementation plan addresses the final UI and data consistency issues in the MC Press chatbot. The tasks focus on fixing the source enrichment process, correcting URL formatting in the import pipeline, and resolving frontend component behavior issues.

## Tasks

- [x] 1. Fix Source Enrichment Title Display
  - Debug why chat interface shows ID numbers instead of titles from books.title
  - Verify enrichment query returns correct title data
  - Ensure enrichment response format matches frontend expectations
  - Add logging to trace data flow from database to frontend
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 1.1 Write property test for title display consistency
  - **Property 1: Title Display Consistency**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [ ] 2. Fix URL Format in Import Service
  - Add URL normalization to convert "ww.mcpressonline.com" to "www.mcpressonline.com"
  - Update `backend/excel_import_service.py` import_article_metadata method
  - Add URL validation and correction during Excel processing
  - Ensure corrected URLs are saved to database
  - _Requirements: 3.1, 3.2, 3.3_

- [ ]* 2.1 Write property test for URL normalization
  - **Property 3: URL Format Normalization**
  - **Validates: Requirements 3.1, 3.2**

- [ ] 3. Fix Document Type Classification
  - Ensure articles get `document_type='article'` during import
  - Verify source enrichment correctly retrieves document_type
  - Test that frontend shows correct button types (Read vs Buy)
  - Debug any transaction issues preventing document_type updates
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ]* 3.1 Write property test for document type button mapping
  - **Property 2: Document Type Button Mapping**
  - **Validates: Requirements 2.1, 2.2**

- [ ] 4. Fix Author Button Dropdown
  - Update `frontend/components/CompactSources.tsx` to fix hover dropdown
  - Remove direct hyperlinks from author names
  - Ensure Author button only shows when authors have websites
  - Fix dropdown positioning and styling issues
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 4.1 Write property test for author button behavior
  - **Property 4: Author Button Dropdown Behavior**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ] 5. Fix Author Name Display
  - Debug why articles show "Unknown Author" instead of real names
  - Verify author data is being imported from Excel Column J
  - Check document_authors relationship table population
  - Ensure source enrichment retrieves multi-author data correctly
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 5.1 Write property test for author name resolution
  - **Property 6: Author Name Resolution**
  - **Validates: Requirements 5.1, 5.2**

- [ ] 6. Fix Import Transaction Reliability
  - Debug why import API reports success but database isn't updated
  - Add proper transaction handling and error reporting
  - Ensure database changes are committed after successful operations
  - Add detailed logging for debugging import issues
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 6.1 Write property test for import transaction consistency
  - **Property 5: Import Transaction Consistency**
  - **Validates: Requirements 6.1, 6.2**

- [ ] 7. Checkpoint - Test Individual Fixes
  - Run article metadata import and verify database updates
  - Test chat interface with sample queries
  - Verify URL corrections are working
  - Check author button functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Integration Testing and Validation
  - Test complete flow: Excel import → Database → Chat Interface
  - Verify articles show proper titles instead of ID numbers
  - Verify "Read" buttons work with corrected URLs
  - Verify Author buttons show dropdown with working links
  - Verify books still show "Buy" buttons correctly
  - _Requirements: All requirements_

- [ ]* 8.1 Write integration tests for complete flow
  - Test end-to-end: Import → Database → Chat → Display
  - Test URL fix service with real data
  - Test frontend component with various data states
  - _Requirements: All requirements_

- [ ] 9. Final Checkpoint - Complete System Validation
  - Run comprehensive test suite
  - Verify all UI issues are resolved
  - Test with real user queries
  - Ensure system performance is maintained
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Integration tests validate end-to-end functionality
- Focus on debugging existing issues rather than adding new features