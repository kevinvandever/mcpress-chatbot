# Requirements Document

## Introduction

This feature adds the capability for administrators to remove books and/or articles from the MC Press Chatbot system (MC Chatmaster). When a content owner or publisher requests removal of their material, an admin needs to fully purge the document and all associated data — including vector embeddings (chunks), book metadata, author associations, and metadata history — through both an API endpoint and the existing admin UI.

The system currently has partial delete functionality scattered across multiple endpoints (`DELETE /documents/{filename}`, `DELETE /admin/documents/{doc_id}`, `DELETE /admin/documents/bulk`), but these lack admin authentication, confirmation safeguards, and consistent cleanup of all related data (e.g., `document_authors`, `metadata_history`, orphaned authors). This feature consolidates and hardens document removal into a reliable, admin-only operation.

## Glossary

- **Admin**: An authenticated administrator user with a valid JWT access token
- **Document**: A book or article stored in the system, represented by a row in the `books` table and associated chunk rows in the `documents` table
- **Chunk**: A single text segment from a document stored in the `documents` table with its vector embedding
- **Book**: A document of type "book", typically a full-length PDF with many pages and chunks
- **Article**: A document of type "article", typically shorter content with fewer chunks
- **Author_Association**: A row in the `document_authors` table linking a document to an author
- **Metadata_History**: A row in the `metadata_history` table tracking changes to a document's metadata
- **Removal_API**: The backend FastAPI endpoint(s) responsible for deleting documents and all related data
- **Admin_UI**: The Next.js admin document management page at `/admin/documents`
- **Orphaned_Author**: An author record in the `authors` table that is no longer associated with any document
- **Removal_Summary**: A response object describing what was deleted (filenames, chunk counts, author associations removed)
- **Vector_Index_Rebuild**: The process of executing `REINDEX INDEX documents_embedding_idx` to rebalance the IVFFlat vector index after document deletions

## Requirements

### Requirement 1: Admin-Authenticated Document Removal API

**User Story:** As an admin, I want to remove a document through an authenticated API endpoint, so that only authorized users can delete content from the system.

#### Acceptance Criteria

1. WHEN an unauthenticated request is made to the Removal_API, THE Removal_API SHALL return a 401 Unauthorized response
2. WHEN an authenticated Admin sends a DELETE request with a valid document ID, THE Removal_API SHALL delete the document record from the `books` table
3. WHEN an authenticated Admin sends a DELETE request with a valid document ID, THE Removal_API SHALL delete all Chunk rows from the `documents` table matching the document's filename
4. WHEN an authenticated Admin sends a DELETE request with a non-existent document ID, THE Removal_API SHALL return a 404 Not Found response
5. IF a database error occurs during deletion, THEN THE Removal_API SHALL return a 500 error response with a descriptive message and leave the data in a consistent state

### Requirement 2: Cascading Cleanup of Related Data

**User Story:** As an admin, I want all related data to be cleaned up when I remove a document, so that no orphaned records remain in the database.

#### Acceptance Criteria

1. WHEN a document is deleted, THE Removal_API SHALL delete all Author_Association rows from the `document_authors` table for that document
2. WHEN a document is deleted, THE Removal_API SHALL delete all Metadata_History rows from the `metadata_history` table for that document
3. WHEN a document deletion results in an Orphaned_Author (an author with zero remaining document associations), THE Removal_API SHALL retain the Orphaned_Author record in the `authors` table
4. WHEN a document is deleted, THE Removal_API SHALL invalidate the documents cache so subsequent queries reflect the removal

### Requirement 3: Bulk Document Removal

**User Story:** As an admin, I want to remove multiple documents at once, so that I can efficiently handle batch removal requests.

#### Acceptance Criteria

1. WHEN an authenticated Admin sends a bulk DELETE request with a list of valid document IDs, THE Removal_API SHALL delete all specified documents and their related data
2. WHEN a bulk DELETE request contains a mix of valid and invalid document IDs, THE Removal_API SHALL process all valid IDs and report which IDs were not found
3. THE Removal_API SHALL return a Removal_Summary containing the count of deleted documents, list of filenames removed, and total chunks deleted
4. WHEN a bulk DELETE request contains an empty list of IDs, THE Removal_API SHALL return a 400 Bad Request response

### Requirement 4: Removal Confirmation in Admin UI

**User Story:** As an admin, I want a confirmation step before deleting a document, so that I do not accidentally remove content.

#### Acceptance Criteria

1. WHEN an Admin clicks the delete button for a single document, THE Admin_UI SHALL display a confirmation dialog showing the document title, document type (book or article), and the number of chunks that will be deleted
2. WHEN an Admin confirms the deletion in the dialog, THE Admin_UI SHALL call the Removal_API and display a success message with the Removal_Summary
3. WHEN an Admin cancels the deletion in the dialog, THE Admin_UI SHALL close the dialog and take no action
4. IF the Removal_API returns an error, THEN THE Admin_UI SHALL display the error message to the Admin

### Requirement 5: Bulk Removal in Admin UI

**User Story:** As an admin, I want to select multiple documents and remove them in one action, so that I can handle batch takedown requests efficiently.

#### Acceptance Criteria

1. THE Admin_UI SHALL provide checkboxes for selecting multiple documents in the document list
2. WHEN one or more documents are selected, THE Admin_UI SHALL display a bulk delete button with the count of selected documents
3. WHEN the Admin clicks the bulk delete button, THE Admin_UI SHALL display a confirmation dialog listing all selected document titles and the total chunk count
4. WHEN the Admin confirms the bulk deletion, THE Admin_UI SHALL call the bulk Removal_API and display the Removal_Summary
5. WHEN the bulk deletion completes, THE Admin_UI SHALL deselect all documents and refresh the document list

### Requirement 6: Document Chunk Count Display

**User Story:** As an admin, I want to see how many chunks each document has before deleting it, so that I understand the impact of the removal.

#### Acceptance Criteria

1. THE Admin_UI SHALL display the chunk count for each document in the document list or detail panel
2. WHEN the chunk count is not yet loaded, THE Admin_UI SHALL display a loading indicator or "N/A" placeholder
3. THE Removal_API SHALL include the chunk count in the document listing response for each document

### Requirement 7: Vector Index Rebuild

**User Story:** As an admin, I want the option to rebuild the vector search index after removing documents, so that search quality remains optimal after large deletions.

#### Acceptance Criteria

1. THE Admin_UI SHALL display a "Rebuild Vector Index" button on the admin documents page
2. WHEN an Admin clicks the rebuild button, THE Admin_UI SHALL display a confirmation dialog explaining that the operation may take a few minutes and will not affect search availability
3. WHEN an Admin confirms the rebuild, THE Removal_API SHALL execute a `REINDEX INDEX documents_embedding_idx` operation on the vector index
4. WHILE the rebuild is in progress, THE Admin_UI SHALL display a progress indicator and disable the rebuild button
5. WHEN the rebuild completes successfully, THE Admin_UI SHALL display a success message with the elapsed time
6. IF the rebuild fails, THE Removal_API SHALL return an error response and THE Admin_UI SHALL display the error message to the Admin
7. THE Removal_API SHALL allow search queries to continue during the rebuild operation (non-blocking)

### Requirement 8: Post-Removal Verification

**User Story:** As an admin, I want confirmation that a removed document is no longer searchable, so that I can verify the removal was complete.

#### Acceptance Criteria

1. WHEN a document has been deleted, THE Removal_API SHALL ensure zero chunks remain in the `documents` table for that filename
2. WHEN a document has been deleted, THE Removal_API SHALL ensure zero rows remain in the `books` table for that document ID
3. WHEN a document has been deleted, THE Removal_API SHALL ensure zero Author_Association rows remain in the `document_authors` table for that document ID
