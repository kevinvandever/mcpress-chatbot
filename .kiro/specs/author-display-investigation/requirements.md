# Requirements Document: Author Display Investigation and Fix

## Introduction

This specification addresses systematic investigation and resolution of author display issues in the MC Press Chatbot. Users report that books are showing incorrect authors, missing authors, or displaying placeholder names like "Admin" or "Annegrubb" instead of actual author names. This affects both the chat interface source attribution and the admin document management interface.

## Glossary

- **System**: The MC Press Chatbot application (backend + frontend)
- **Author_Record**: A row in the `authors` table containing author metadata
- **Document_Author_Association**: A row in the `document_authors` junction table linking books to authors
- **Book_Record**: A row in the `books` table containing book metadata
- **Chat_Source**: Source attribution displayed in chat responses showing book title and author
- **Admin_Interface**: The admin document management UI at `/admin/documents`
- **Excel_Import**: The CSV/Excel import process that creates book and author records
- **Vector_Store**: The PostgreSQL database with pgvector extension storing document chunks
- **Enrichment_Service**: The chat_handler.py service that adds metadata to chat sources

## Requirements

### Requirement 1: Author Data Integrity

**User Story:** As a system administrator, I want to ensure all books have correct author associations, so that users see accurate attribution in chat responses.

#### Acceptance Criteria

1. WHEN querying the books table, THE System SHALL return all books with at least one valid author association
2. WHEN an author name is "Admin", "admin", "Unknown", "Annegrubb", or similar placeholder, THE System SHALL flag it as suspicious
3. WHEN a book has multiple authors, THE System SHALL return them in the correct order specified by author_order
4. WHEN checking author associations, THE System SHALL verify that author_id references exist in the authors table
5. WHEN a book is displayed, THE System SHALL show all associated authors from the document_authors table

### Requirement 2: Author Display in Chat Interface

**User Story:** As a user, I want to see correct author names and clickable author links in chat responses, so that I can identify and learn more about the content creators.

#### Acceptance Criteria

1. WHEN a chat response includes sources, THE System SHALL display the correct author name(s) for each source
2. WHEN an author has a site_url, THE System SHALL render the author name as a clickable link
3. WHEN a book has multiple authors, THE System SHALL display all authors separated by appropriate delimiters
4. WHEN enriching chat sources, THE System SHALL query the books table with proper author joins
5. WHEN no author is found, THE System SHALL display "Unknown Author" rather than placeholder names

### Requirement 3: Excel Import Author Parsing

**User Story:** As a system administrator, I want the Excel import process to correctly parse and associate authors, so that new books have accurate metadata from the start.

#### Acceptance Criteria

1. WHEN importing a CSV with an "authors" column, THE System SHALL parse pipe-delimited author names correctly
2. WHEN creating author records during import, THE System SHALL use get_or_create_author to prevent duplicates
3. WHEN an author name contains special characters or formatting, THE System SHALL normalize it before lookup
4. WHEN multiple authors are specified, THE System SHALL create document_author associations with correct ordering
5. WHEN author_site_urls are provided, THE System SHALL associate them with the correct author by position

### Requirement 4: Author Association Verification

**User Story:** As a developer, I want diagnostic tools to identify author association problems, so that I can quickly find and fix data integrity issues.

#### Acceptance Criteria

1. WHEN running diagnostics, THE System SHALL identify books with missing author associations
2. WHEN checking data quality, THE System SHALL find books associated with placeholder author names
3. WHEN analyzing the database, THE System SHALL detect orphaned author records with zero document associations
4. WHEN verifying imports, THE System SHALL compare Excel data against database records to find mismatches
5. WHEN generating reports, THE System SHALL list all books with suspicious or incorrect author data

### Requirement 5: Author Correction Workflow

**User Story:** As a system administrator, I want tools to bulk-correct author associations, so that I can efficiently fix multiple books with incorrect authors.

#### Acceptance Criteria

1. WHEN correcting an author association, THE System SHALL update the document_authors table to reference the correct author_id
2. WHEN replacing a placeholder author, THE System SHALL preserve the author_order for multi-author books
3. WHEN applying bulk corrections, THE System SHALL validate that target author_ids exist before updating
4. WHEN fixing author data, THE System SHALL log all changes for audit purposes
5. WHEN corrections are complete, THE System SHALL verify that no books remain with placeholder authors

### Requirement 6: Frontend Author Display

**User Story:** As a user, I want to see author information prominently displayed in the UI, so that I can easily identify content creators and visit their websites.

#### Acceptance Criteria

1. WHEN viewing chat sources, THE System SHALL display author names with visual distinction from book titles
2. WHEN an author has a website, THE System SHALL show a clickable link or button to visit it
3. WHEN multiple authors exist, THE System SHALL display them in a readable format with proper separators
4. WHEN hovering over author links, THE System SHALL provide visual feedback indicating clickability
5. WHEN no author website exists, THE System SHALL display the author name without a link

### Requirement 7: Database Query Optimization

**User Story:** As a developer, I want efficient database queries for author data, so that chat responses and admin pages load quickly.

#### Acceptance Criteria

1. WHEN fetching books with authors, THE System SHALL use JOIN operations rather than N+1 queries
2. WHEN enriching multiple sources, THE System SHALL batch author lookups into a single query
3. WHEN querying the books table, THE System SHALL use ARRAY_AGG to collect authors efficiently
4. WHEN filtering by author, THE System SHALL use indexed columns for fast lookups
5. WHEN paginating results, THE System SHALL maintain consistent author data across pages

### Requirement 8: Author Data Migration

**User Story:** As a system administrator, I want to migrate existing incorrect author data to correct associations, so that historical books display accurate information.

#### Acceptance Criteria

1. WHEN identifying books with incorrect authors, THE System SHALL generate SQL correction scripts
2. WHEN migrating author data, THE System SHALL preserve existing correct associations
3. WHEN updating associations, THE System SHALL handle multi-author books without data loss
4. WHEN corrections are applied, THE System SHALL verify the changes were successful
5. WHEN migration is complete, THE System SHALL generate a summary report of all changes

### Requirement 9: Author Search and Lookup

**User Story:** As a system administrator, I want to search for authors and see their associated books, so that I can verify and correct author data.

#### Acceptance Criteria

1. WHEN searching for an author by name, THE System SHALL return matching authors with document counts
2. WHEN viewing an author's details, THE System SHALL list all books associated with that author
3. WHEN comparing authors, THE System SHALL identify potential duplicates based on name similarity
4. WHEN looking up an author by ID, THE System SHALL return complete metadata including site_url
5. WHEN filtering books by author, THE System SHALL support partial name matching

### Requirement 10: Error Handling and Validation

**User Story:** As a developer, I want robust error handling for author operations, so that data integrity is maintained even when errors occur.

#### Acceptance Criteria

1. WHEN an author lookup fails, THE System SHALL log the error and return a default "Unknown Author" value
2. WHEN creating author associations, THE System SHALL validate that both book_id and author_id exist
3. WHEN parsing author names, THE System SHALL handle null, empty, and malformed values gracefully
4. WHEN enriching sources, THE System SHALL continue processing even if one author lookup fails
5. WHEN database queries timeout, THE System SHALL return partial results rather than failing completely
