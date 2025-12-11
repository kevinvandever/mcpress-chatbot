# Requirements Document

## Introduction

This feature enhances the document management system to support multiple authors per document, distinguish between books and articles, and add additional metadata fields for external links. The current system has a one-to-one relationship between documents and authors stored in a single `books` table. This enhancement will normalize the database schema to support many-to-many author relationships and add fields for author websites, article URLs, and book purchase links.

## Glossary

- **Document**: A book or article stored in the system (currently in the `books` table)
- **Book**: A published book document with associated purchase information
- **Article**: A published article document with associated article URL
- **Author**: A person who has written one or more documents
- **Author Site URL**: A link to an author's personal or professional website
- **Article URL**: A direct link to an online article
- **MC Press URL**: An existing field in the books table containing a link to purchase a book from MC Press
- **Books Table**: The current database table storing document metadata
- **Authors Table**: A new table to store unique author information
- **Document Authors Junction Table**: A new table linking documents to authors in a many-to-many relationship
- **Document Type**: An enumeration distinguishing between books and articles
- **Batch Upload**: The existing functionality to upload multiple documents simultaneously
- **Database Migration**: The process of transforming the existing schema to the new schema while preserving data
- **Excel Import**: The process of reading author and document metadata from Excel (.xlsm) files and updating the database
- **Book Metadata Excel**: The book-metadata.xlsm file containing book purchase URLs and author information
- **Article Metadata Excel**: The article-links.xlsm file containing article metadata and author information
- **Fuzzy Matching**: Approximate string matching to handle minor variations in book titles
- **Feature Article Filter**: Processing only articles where the "feature article" column equals "yes"

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to store multiple authors for each document, so that I can accurately represent documents with co-authors or multiple contributors.

#### Acceptance Criteria

1. WHEN the system stores document metadata THEN the system SHALL support associating zero or more authors with each document
2. WHEN an author is associated with multiple documents THEN the system SHALL store the author information once and reference it from multiple documents
3. WHEN retrieving a document THEN the system SHALL return all associated authors in a consistent order
4. WHEN adding an author to a document THEN the system SHALL prevent duplicate author associations for the same document
5. WHEN deleting a document THEN the system SHALL remove author associations while preserving author records that are referenced by other documents

### Requirement 2

**User Story:** As a system administrator, I want to distinguish between books and articles, so that I can display appropriate metadata and links for each document type.

#### Acceptance Criteria

1. WHEN creating a document record THEN the system SHALL require a document type of either "book" or "article"
2. WHEN the document type is "book" THEN the system SHALL continue to support the existing mc_press_url field
3. WHEN the document type is "article" THEN the system SHALL allow storing an article URL
4. WHEN retrieving documents THEN the system SHALL include the document type in the response
5. WHEN filtering documents THEN the system SHALL support filtering by document type

### Requirement 3

**User Story:** As a system administrator, I want to store author website URLs, so that users can learn more about the authors of documents they are reading.

#### Acceptance Criteria

1. WHEN creating or updating an author record THEN the system SHALL allow storing an optional author site URL
2. WHEN an author site URL is provided THEN the system SHALL validate that it is a properly formatted URL
3. WHEN retrieving author information THEN the system SHALL include the author site URL if available
4. WHEN multiple documents share an author THEN the system SHALL return the same author site URL for all documents by that author

### Requirement 4

**User Story:** As a system administrator, I want to migrate existing document data to the new schema, so that no data is lost during the database restructuring.

#### Acceptance Criteria

1. WHEN the migration executes THEN the system SHALL create the new authors table and document_authors junction table
2. WHEN the migration executes THEN the system SHALL extract unique authors from existing document records and create author records
3. WHEN the migration executes THEN the system SHALL create document-author associations for all existing documents
4. WHEN the migration executes THEN the system SHALL preserve all existing document metadata including titles, categories, and URLs
5. WHEN the migration completes THEN the system SHALL verify that all documents have at least one author association
6. WHEN the migration encounters errors THEN the system SHALL log detailed error information and continue processing remaining records

### Requirement 5

**User Story:** As a system administrator, I want to add, update, and remove authors for documents through the existing admin document interface, so that I can maintain accurate author information without switching between multiple interfaces.

#### Acceptance Criteria

1. WHEN updating a document in the admin interface THEN the system SHALL display all associated authors with the ability to add or remove authors
2. WHEN adding an author to a document THEN the system SHALL provide autocomplete suggestions from existing authors
3. WHEN adding an author that does not exist THEN the system SHALL create a new author record
4. WHEN adding an author that already exists THEN the system SHALL reuse the existing author record
5. WHEN viewing an author in the document interface THEN the system SHALL allow inline editing of author details including name and site URL
6. WHEN updating author information THEN the system SHALL update the author record for all documents by that author
7. WHEN removing the last author from a document THEN the system SHALL prevent the removal and require at least one author

### Requirement 6

**User Story:** As a system administrator, I want the batch upload functionality to continue working with the new schema, so that I can efficiently upload multiple documents.

#### Acceptance Criteria

1. WHEN batch uploading documents THEN the system SHALL create or associate authors for each document
2. WHEN batch uploading documents with author metadata THEN the system SHALL parse multiple authors from the provided metadata
3. WHEN batch uploading documents without author metadata THEN the system SHALL prompt for author information or assign a default author
4. WHEN batch uploading completes THEN the system SHALL report the number of documents processed and any errors encountered
5. WHEN batch uploading encounters duplicate authors THEN the system SHALL reuse existing author records

### Requirement 7

**User Story:** As a system administrator, I want to export document and author data, so that I can analyze or backup the information.

#### Acceptance Criteria

1. WHEN exporting documents to CSV THEN the system SHALL include all authors for each document in a single field
2. WHEN exporting documents to CSV THEN the system SHALL include document type, author site URLs, article URLs, and mc_press_url
3. WHEN exporting documents to CSV THEN the system SHALL format multiple authors as a delimited list
4. WHEN importing documents from CSV THEN the system SHALL parse multiple authors from the delimited format
5. WHEN importing documents from CSV THEN the system SHALL create or update author records as needed

### Requirement 8

**User Story:** As a system administrator, I want to search and filter by author, so that I can find all documents by a specific author.

#### Acceptance Criteria

1. WHEN searching documents by author name THEN the system SHALL return all documents associated with authors matching the search term
2. WHEN filtering by author THEN the system SHALL support exact author name matching
3. WHEN retrieving author information THEN the system SHALL include the count of documents by that author
4. WHEN listing authors THEN the system SHALL support pagination and sorting by name or document count
5. WHEN an author has no associated documents THEN the system SHALL optionally exclude that author from search results

### Requirement 9

**User Story:** As a system administrator, I want to import book metadata from Excel files, so that I can efficiently update existing book records with purchase URLs and author information from MC Press data.

#### Acceptance Criteria

1. WHEN importing book metadata THEN the system SHALL read book-metadata.xlsm file with columns URL, Title, and Author
2. WHEN processing book metadata THEN the system SHALL match Title column against existing books.title using fuzzy matching to handle minor variations
3. WHEN a book title matches THEN the system SHALL update the book record with the URL as mc_press_url
4. WHEN processing book authors THEN the system SHALL parse multiple authors separated by comma or "and" and trim whitespace
5. WHEN importing book data THEN the system SHALL create or update author records for each parsed author using the existing AuthorService
6. WHEN importing book data THEN the system SHALL report the number of books matched, updated, and any errors encountered

### Requirement 10

**User Story:** As a system administrator, I want to import article metadata from Excel files, so that I can efficiently link article IDs to metadata for PDF upload processing and author management.

#### Acceptance Criteria

1. WHEN importing article metadata THEN the system SHALL read only the export_subset sheet from article-links.xlsm
2. WHEN processing article records THEN the system SHALL only process rows where column H (feature article) equals "yes"
3. WHEN processing article metadata THEN the system SHALL use column A (id) to match against PDF filenames during upload (with or without .pdf extension)
4. WHEN processing article authors THEN the system SHALL create or update author records using column J (Author) and store column L (Author URL) as the author's site_url
5. WHEN processing articles THEN the system SHALL store column K (Article URL) as article_url for future document linking
6. WHEN processing articles THEN the system SHALL set document_type to "article" for documents that match the article ID
7. WHEN importing article data THEN the system SHALL report the number of articles processed, authors created/updated, and any validation errors

### Requirement 11

**User Story:** As a system administrator, I want to validate and preview Excel data before importing, so that I can identify and correct data issues before they affect the production database.

#### Acceptance Criteria

1. WHEN uploading an Excel file for import THEN the system SHALL validate the file format (.xlsm) and required columns before processing
2. WHEN validating book metadata THEN the system SHALL check for required columns (URL, Title, Author) and report any missing fields
3. WHEN validating article metadata THEN the system SHALL check for the export_subset sheet and required columns (A, H, J, K, L)
4. WHEN validating Excel data THEN the system SHALL identify invalid URLs, missing required data, and format issues
5. WHEN validating Excel data THEN the system SHALL provide a preview of the first 10 rows with validation status for each row
6. WHEN validation errors are found THEN the system SHALL provide detailed error messages indicating the specific row and column with issues
7. WHEN validation passes THEN the system SHALL allow the administrator to proceed with the import or cancel the operation