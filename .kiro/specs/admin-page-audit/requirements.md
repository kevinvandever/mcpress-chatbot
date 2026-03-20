# Requirements Document

## Introduction

The admin page for the MC Press Chatbot was built incrementally over multiple feature stories. This audit verifies that the admin page correctly reflects the current database state and can reliably update metadata for books, authors, and links. The Excel file `expert_subset_DMU_v2.xlsm` serves as the source of truth for validating data accuracy. The audit covers three admin subpages (dashboard, documents, upload) and the backend APIs they depend on.

## Glossary

- **Admin_Page**: The admin section of the MC Press Chatbot frontend located at `/admin/*`, comprising the Dashboard, Documents, and Upload subpages
- **Documents_Page**: The admin documents management page at `/admin/documents` that lists, edits, and deletes book/article records
- **Dashboard_Page**: The admin dashboard page at `/admin/dashboard` that displays summary statistics
- **Books_Table**: The PostgreSQL `books` table storing document metadata including title, author, category, mc_press_url, article_url, and document_type
- **Authors_Table**: The PostgreSQL `authors` table storing author records with name and site_url
- **Document_Authors_Table**: The PostgreSQL `document_authors` junction table linking books to authors with ordering via book_id, author_id, and author_order
- **Excel_Source**: The `expert_subset_DMU_v2.xlsm` spreadsheet used as the authoritative source of truth for book titles, authors, mc_press_urls, article_urls, and author site_urls
- **Admin_API**: The backend FastAPI endpoints under `/admin/documents` that serve document listing, updating, and deletion
- **Metadata_API**: The backend FastAPI endpoint at `PUT /documents/{filename}/metadata` used by the Documents_Page to save edits
- **Author_API**: The backend FastAPI endpoints under `/api/authors` for searching, viewing, and updating author records
- **Document_Author_API**: The backend FastAPI endpoints under `/api/documents/{id}/authors` for managing document-author relationships

## Requirements

### Requirement 1: Data Accuracy — Books Match Excel Source

**User Story:** As an admin, I want the books displayed on the Documents_Page to match the Excel_Source, so that I can trust the admin page reflects accurate data.

#### Acceptance Criteria

1. FOR ALL books listed in the Excel_Source, THE Documents_Page SHALL display a corresponding record with a matching title
2. FOR ALL books listed in the Excel_Source, THE Books_Table SHALL contain an author value that matches the author column in the Excel_Source
3. FOR ALL books in the Excel_Source that have a mc_press_url, THE Books_Table SHALL store a mc_press_url value matching the Excel_Source
4. FOR ALL articles in the Excel_Source that have an article_url, THE Books_Table SHALL store an article_url value matching the Excel_Source
5. FOR ALL authors in the Excel_Source that have a site_url, THE Authors_Table SHALL store a site_url value matching the Excel_Source

### Requirement 2: Document Listing Accuracy

**User Story:** As an admin, I want the Documents_Page to accurately reflect the current database state, so that I see real data when managing content.

#### Acceptance Criteria

1. WHEN the Documents_Page loads, THE Admin_API SHALL return all records from the Books_Table with correct title, author, document_type, mc_press_url, and article_url values
2. WHEN multi-author records exist in the Document_Authors_Table, THE Admin_API SHALL return all associated authors in the correct order for each document
3. WHEN a search term is entered on the Documents_Page, THE Admin_API SHALL filter results by title or author name and return only matching records
4. WHEN pagination controls are used, THE Admin_API SHALL return the correct page of results with accurate total count and total_pages values
5. WHEN sort controls are used on the Documents_Page, THE Admin_API SHALL return results ordered by the selected field and direction

### Requirement 3: Document Metadata Editing

**User Story:** As an admin, I want to edit book metadata through the Documents_Page and have changes persist correctly, so that I can fix inaccurate data.

#### Acceptance Criteria

1. WHEN an admin edits a title on the Documents_Page and saves, THE Metadata_API SHALL update the title in the Books_Table and the Documents_Page SHALL display the updated title after refresh
2. WHEN an admin edits an author name on the Documents_Page and saves, THE Metadata_API SHALL update the author in the Books_Table and the Documents_Page SHALL display the updated author after refresh
3. WHEN an admin edits the mc_press_url on the Documents_Page and saves, THE Metadata_API SHALL update the mc_press_url in the Books_Table
4. WHEN an admin edits the article_url on the Documents_Page and saves, THE Metadata_API SHALL update the article_url in the Books_Table
5. WHEN an admin edits the author_site_url on the Documents_Page and saves, THE Author_API SHALL update the site_url in the Authors_Table for the corresponding author
6. IF an admin submits an empty title, THEN THE Metadata_API SHALL reject the update with a 400 status code and a descriptive error message
7. IF an admin submits a URL that does not start with http:// or https://, THEN THE Documents_Page SHALL display a client-side validation error before sending the request


### Requirement 4: Document Metadata Edit Round-Trip Integrity

**User Story:** As an admin, I want edits made on the Documents_Page to be fully persisted and retrievable, so that no data is lost during the save cycle.

#### Acceptance Criteria

1. FOR ALL editable fields (title, author, mc_press_url, article_url, author_site_url), saving a value on the Documents_Page then reloading the page SHALL display the saved value unchanged
2. WHEN a document is updated via the Metadata_API, THE Admin_API listing endpoint SHALL return the updated values on the next request with refresh=true
3. WHEN a document is updated via the Metadata_API, THE cache invalidation mechanism SHALL ensure stale data is not served on subsequent requests

### Requirement 5: Author Management Consistency

**User Story:** As an admin, I want author data to be consistent between the Documents_Page and the Author_API, so that author information is reliable across the system.

#### Acceptance Criteria

1. FOR ALL documents with entries in the Document_Authors_Table, THE Documents_Page SHALL display the author name from the Authors_Table rather than the legacy books.author column
2. WHEN a document has multiple authors in the Document_Authors_Table, THE Documents_Page SHALL display all authors with a "Multi-author:" prefix and comma-separated names
3. WHEN an author's name is updated via the Author_API, THE Documents_Page SHALL reflect the updated name for all documents associated with that author after refresh
4. WHEN an author's site_url is updated via the Documents_Page edit panel, THE Author_API SHALL persist the change to the Authors_Table for the correct author record

### Requirement 6: Dashboard Statistics Accuracy

**User Story:** As an admin, I want the Dashboard_Page to show accurate statistics, so that I have a reliable overview of the system.

#### Acceptance Criteria

1. WHEN the Dashboard_Page loads, THE Dashboard_Page SHALL display a total document count that matches the number of records in the Books_Table
2. WHEN the Dashboard_Page loads, THE Dashboard_Page SHALL display a last upload date derived from actual document data rather than a hardcoded or estimated value

### Requirement 7: Excel Data Verification Capability

**User Story:** As an admin, I want to compare database records against the Excel_Source, so that I can identify and fix discrepancies.

#### Acceptance Criteria

1. WHEN the Excel_Source is uploaded via the Excel import API, THE Excel import service SHALL validate the file structure and report any formatting errors before processing
2. WHEN the Excel_Source is compared against the Books_Table, THE comparison SHALL identify books present in the Excel_Source but missing from the database
3. WHEN the Excel_Source is compared against the Books_Table, THE comparison SHALL identify mismatches in title, author, mc_press_url, article_url, or author site_url between the Excel_Source and the database
4. WHEN discrepancies are identified, THE comparison result SHALL include the specific field name, the Excel_Source value, and the database value for each mismatch

### Requirement 8: Delete Operations

**User Story:** As an admin, I want to delete documents through the Documents_Page and have the deletion fully applied, so that removed content no longer appears.

#### Acceptance Criteria

1. WHEN an admin confirms deletion of a document on the Documents_Page, THE Admin_API SHALL remove the record from the Books_Table and all associated chunks from the documents table
2. WHEN a document is deleted, THE Admin_API SHALL remove associated entries from the Document_Authors_Table
3. WHEN a document is deleted, THE Documents_Page SHALL no longer display the deleted document after refresh
4. IF a delete request references a non-existent document ID, THEN THE Admin_API SHALL return a 404 status code

### Requirement 9: API-Frontend Endpoint Alignment

**User Story:** As an admin, I want the Documents_Page to use the correct backend endpoints, so that edits and actions work without errors.

#### Acceptance Criteria

1. WHEN the Documents_Page saves metadata changes, THE Documents_Page SHALL send the request to `PUT /documents/{filename}/metadata` with the correct payload structure including filename, title, author, category, mc_press_url, and article_url
2. WHEN the Documents_Page updates an author site_url, THE Documents_Page SHALL send the request to `PATCH /api/authors/{author_id}` with the site_url field
3. WHEN the Documents_Page deletes a document, THE Documents_Page SHALL send the request to `DELETE /documents/{filename}` using the correct filename encoding
4. WHEN the Documents_Page lists documents, THE Documents_Page SHALL send the request to `GET /admin/documents` with page, per_page, search, sort_by, sort_direction, and refresh query parameters
