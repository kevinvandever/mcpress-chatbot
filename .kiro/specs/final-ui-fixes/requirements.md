# Requirements Document

## Introduction

This specification addresses the final UI and data consistency issues in the MC Press chatbot after the article migration and metadata import. The system currently has correct data in the database but the chat interface is not displaying it properly, and there are URL formatting issues that need to be resolved.

## Glossary

- **Chat_Interface**: The frontend component that displays search results and source references
- **Article**: A document with `document_type='article'` that should show green "Read" buttons
- **Book**: A document with `document_type='book'` that should show blue "Buy" buttons  
- **Source_Enrichment**: Backend process that fetches metadata from database to display in chat
- **Author_Button**: Purple dropdown button that shows author website links
- **URL_Typo**: The "ww.mcpressonline.com" vs "www.mcpressonline.com" formatting issue

## Requirements

### Requirement 1: Chat Interface Title Display

**User Story:** As a user, I want to see proper article and book titles in chat results, so that I can identify relevant content by name instead of ID numbers.

#### Acceptance Criteria

1. WHEN the chat interface displays search results, THE Chat_Interface SHALL show the title from books.title column instead of filename
2. WHEN an article appears in search results, THE Chat_Interface SHALL display the article title from Excel Column B (not "4247" or "5765")
3. WHEN a book appears in search results, THE Chat_Interface SHALL display the book title from the books table
4. THE Source_Enrichment SHALL correctly map filename to title for all document types
5. WHEN enrichment fails to find a title, THE Chat_Interface SHALL fall back to filename without extension

### Requirement 2: Document Type Classification

**User Story:** As a user, I want articles to show "Read" buttons and books to show "Buy" buttons, so that I can access the appropriate content links.

#### Acceptance Criteria

1. WHEN a document has `document_type='article'`, THE Chat_Interface SHALL display a green "Read" button
2. WHEN a document has `document_type='book'`, THE Chat_Interface SHALL display a blue "Buy" button
3. THE Source_Enrichment SHALL correctly retrieve document_type from the books table
4. WHEN document_type is missing or null, THE Chat_Interface SHALL default to 'book' type
5. THE Chat_Interface SHALL use article_url for "Read" buttons and mc_press_url for "Buy" buttons

### Requirement 3: URL Format Consistency

**User Story:** As a user, I want article "Read" buttons to work correctly, so that I can access the full articles on MC Press Online.

#### Acceptance Criteria

1. WHEN article URLs are imported from Excel, THE Import_Service SHALL ensure URLs use "www.mcpressonline.com" format
2. WHEN article URLs contain "ww.mcpressonline.com", THE Import_Service SHALL automatically correct them to "www.mcpressonline.com"
3. WHEN users click "Read" buttons, THE Chat_Interface SHALL navigate to valid MC Press Online URLs
4. THE URL_Fix_Service SHALL be idempotent and safe to run multiple times
5. WHEN URLs are already correct, THE Import_Service SHALL leave them unchanged

### Requirement 4: Author Button Functionality

**User Story:** As a user, I want to access author websites through a dropdown button, so that I can learn more about the content creators.

#### Acceptance Criteria

1. WHEN authors have website URLs, THE Chat_Interface SHALL display a purple "Author" button
2. WHEN users hover over the Author button, THE Chat_Interface SHALL show a dropdown with author names and website links
3. WHEN users click an author link in the dropdown, THE Chat_Interface SHALL open the author's website in a new tab
4. THE Chat_Interface SHALL NOT make author names directly clickable as hyperlinks
5. WHEN no authors have websites, THE Chat_Interface SHALL NOT display the Author button

### Requirement 5: Author Name Display

**User Story:** As a user, I want to see real author names instead of "Unknown Author", so that I can identify content creators.

#### Acceptance Criteria

1. WHEN articles are imported, THE Import_Service SHALL populate author names from Excel Column J ("vlookup created-by")
2. WHEN multiple authors exist, THE Chat_Interface SHALL display all author names separated by commas
3. WHEN author data is missing, THE Chat_Interface SHALL display "Unknown Author" as fallback
4. THE Source_Enrichment SHALL retrieve author information from the document_authors relationship table
5. WHEN legacy author data exists, THE Source_Enrichment SHALL use it if multi-author data is unavailable

### Requirement 6: Data Import Reliability

**User Story:** As a system administrator, I want article metadata imports to actually update the database, so that changes are reflected in the chat interface.

#### Acceptance Criteria

1. WHEN the import API reports success, THE Import_Service SHALL commit all database changes
2. WHEN database updates fail, THE Import_Service SHALL report the actual error instead of false success
3. THE Import_Service SHALL use proper database transaction handling to ensure consistency
4. WHEN import operations are retried, THE Import_Service SHALL handle duplicate data gracefully
5. THE Import_Service SHALL provide detailed logging of all database operations for debugging

### Requirement 7: Frontend Component Consistency

**User Story:** As a user, I want consistent button behavior and styling across all source references, so that the interface is predictable and professional.

#### Acceptance Criteria

1. THE Chat_Interface SHALL use hover-based dropdowns for Author buttons (not click-based)
2. THE Chat_Interface SHALL maintain consistent button sizing and spacing across all reference types
3. WHEN buttons are disabled, THE Chat_Interface SHALL show appropriate visual feedback
4. THE Chat_Interface SHALL handle edge cases like missing URLs or empty author lists gracefully
5. THE Chat_Interface SHALL maintain accessibility standards for all interactive elements