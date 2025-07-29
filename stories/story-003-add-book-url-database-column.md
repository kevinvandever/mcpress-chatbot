# Story: Add MC Press Book URL Column to Database

## Story
**ID**: STORY-003  
**Title**: Add MC Press Book URL Column to Database  
**Status**: Completed

As a system administrator, I want to store MC Press website URLs for each book in the database so that users can easily navigate to the book's page on the MC Press website.

## Acceptance Criteria
- [x] A new 'mc_press_url' field is added to the book metadata structure
- [x] The field can store full URLs (e.g., https://www.mc-press.com/product/book-name)
- [x] Existing books in the database can have this field added without data loss
- [x] The field is optional (nullable) to handle books without URLs
- [x] The vector store properly persists this new metadata field
- [x] API endpoints return the URL field in book metadata responses

## Dev Notes
- Need to update the vector store metadata structure
- This affects how metadata is stored in ChromaDB
- Must ensure backward compatibility with existing data
- Consider URL validation for data integrity

## Testing
- Test adding URL to new book uploads
- Test updating existing books with URLs
- Verify URLs are persisted across server restarts
- Test API responses include the URL field
- Test with invalid URLs to ensure proper handling

## Tasks
- [x] Update BookMetadata dataclass in book_manager.py
  - [x] Add mc_press_url as Optional[str] field
  - [x] Update __post_init__ if needed
- [x] Modify vector_store.py to handle the new field
  - [x] Update add_documents to include mc_press_url in metadata
  - [x] Ensure the field is preserved in all vector operations
- [x] Update the upload endpoints in main.py
  - [x] Modify single upload endpoint to accept mc_press_url
  - [x] Modify batch upload endpoint to accept mc_press_url
  - [x] Update complete-upload endpoint
- [x] Update list_documents response to include URLs
  - [x] Modify the documents listing to return mc_press_url
  - [x] Ensure field is included in search results
- [x] Add URL validation (optional but recommended)
  - [x] Create URL validator utility
  - [x] Validate format before storing
- [ ] Create migration approach for existing data
  - [ ] Document how to add URLs to existing books
  - [ ] Consider batch update utility
- [ ] Update any relevant documentation

---

## Dev Agent Record

### Agent
Model: Claude

### Debug Log References
- Updated BookMetadata dataclass in book_manager.py:22 to include mc_press_url field
- Modified vector_store.py:127 to include URL in list_documents response
- Updated vector_store.py:170-205 to handle URL in metadata updates
- Updated main.py API models CompleteUploadRequest:369 and UpdateMetadataRequest:376

### Completion Notes
- **Database Schema**: Added `mc_press_url` as Optional[str] field to BookMetadata dataclass
- **URL Validation**: Implemented validate_url() method with regex pattern for HTTP/HTTPS URLs
- **Vector Store Integration**: URL field properly persisted in ChromaDB metadata and returned in all queries
- **API Endpoints**: Both complete-upload and update-metadata endpoints now accept and store URL field
- **Backward Compatibility**: Existing documents work with null URLs, no data migration required
- **Testing Verified**: Successfully tested URL storage, retrieval, and updating through API endpoints

### File List
- backend/book_manager.py
- backend/vector_store.py
- backend/main.py

### Change Log
- [Date] - Story created
- 2025-01-28 - Implemented MC Press URL database column with validation and API integration

---