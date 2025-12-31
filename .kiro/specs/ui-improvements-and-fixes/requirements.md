# Requirements Document

## Introduction

This specification addresses comprehensive UI improvements and fixes for the MC Press chatbot system. The focus is on removing demo branding, improving navigation, updating the admin dashboard to display complete metadata, fixing author display issues, ensuring edit functionality works properly, and verifying that upload features use the correct processing pipelines.

## Glossary

- **Chat_Interface**: The main frontend component that displays the chat conversation and search results
- **Admin_Dashboard**: The administrative interface for managing documents and metadata
- **Author_Display**: The system that shows author names and links in both chat results and admin interface
- **Upload_System**: The document processing pipeline that handles PDF uploads and metadata extraction
- **Back_To_Top_Button**: A floating navigation element that scrolls users to the top of the page
- **Demo_Branding**: Text elements that indicate the system is in demo mode
- **Edit_Feature**: The functionality that allows updating author and document metadata
- **Source_Enrichment**: Backend process that fetches complete metadata for display

## Requirements

### Requirement 1: Remove Demo Branding

**User Story:** As a user, I want the chatbot to appear as a production system, so that it feels professional and trustworthy.

#### Acceptance Criteria

1. WHEN users visit the main chat page, THE Chat_Interface SHALL NOT display "Demo Version" text in the header
2. WHEN users navigate through the application, THE Chat_Interface SHALL show production-ready branding
3. THE Chat_Interface SHALL maintain all existing functionality while removing demo indicators
4. WHEN demo text is removed, THE Chat_Interface SHALL preserve header layout and styling
5. THE Chat_Interface SHALL display the MC Press branding without demo qualifiers

### Requirement 2: Page Navigation Enhancement

**User Story:** As a user, I want an easy way to return to the top of long chat conversations, so that I can quickly access the input field and navigation.

#### Acceptance Criteria

1. WHEN users scroll down on the chat page, THE Chat_Interface SHALL display a floating "back to top" button
2. WHEN users click the back to top button, THE Chat_Interface SHALL smoothly scroll to the top of the page
3. THE Back_To_Top_Button SHALL appear only when users have scrolled beyond a reasonable threshold
4. THE Back_To_Top_Button SHALL be positioned to not interfere with chat functionality
5. THE Back_To_Top_Button SHALL be accessible and follow UI design patterns

### Requirement 3: Admin Dashboard Metadata Display

**User Story:** As an administrator, I want to see complete document metadata including author URLs and article links, so that I can verify and manage all document information effectively.

#### Acceptance Criteria

1. WHEN viewing documents in the admin dashboard, THE Admin_Dashboard SHALL display author website URLs alongside author names
2. WHEN viewing articles, THE Admin_Dashboard SHALL show the article URL (link to read the article)
3. WHEN viewing books, THE Admin_Dashboard SHALL show the MC Press purchase URL
4. THE Admin_Dashboard SHALL maintain the existing search functionality
5. WHEN metadata is missing, THE Admin_Dashboard SHALL show appropriate placeholders or "Not Available" indicators

### Requirement 4: Author Display Correction

**User Story:** As a user, I want to see correct author names in both chat results and admin interface, so that I can identify content creators accurately.

#### Acceptance Criteria

1. WHEN documents have authors in the database, THE Author_Display SHALL show the actual author names instead of "Unknown Author"
2. WHEN multiple authors exist for a document, THE Author_Display SHALL show all authors in the correct order
3. THE Author_Display SHALL retrieve author information from the correct database tables (authors and document_authors)
4. WHEN legacy author data exists, THE Author_Display SHALL use multi-author data when available
5. THE Source_Enrichment SHALL properly join author tables to retrieve complete author information

### Requirement 5: Edit Feature Functionality

**User Story:** As an administrator, I want author and metadata edits to persist properly, so that changes are saved and visible after refresh.

#### Acceptance Criteria

1. WHEN administrators modify author information, THE Edit_Feature SHALL save changes to the database
2. WHEN administrators refresh the page after editing, THE Admin_Dashboard SHALL display the updated information
3. THE Edit_Feature SHALL use proper database transactions to ensure data consistency
4. WHEN edit operations fail, THE Edit_Feature SHALL display specific error messages
5. THE Edit_Feature SHALL validate input data before attempting database updates

### Requirement 6: Upload System Verification

**User Story:** As an administrator, I want upload features to use the correct processing programs, so that documents are processed consistently and completely.

#### Acceptance Criteria

1. WHEN using single file upload, THE Upload_System SHALL use the current production PDF processor
2. WHEN using batch upload, THE Upload_System SHALL use the same processing pipeline as single uploads
3. THE Upload_System SHALL extract text, generate embeddings, and populate metadata consistently
4. WHEN uploads complete, THE Upload_System SHALL ensure documents appear in both chat results and admin dashboard
5. THE Upload_System SHALL handle both article and book document types correctly

### Requirement 7: Database Integration Consistency

**User Story:** As a system administrator, I want all UI components to use the same database queries and data sources, so that information is consistent across the application.

#### Acceptance Criteria

1. WHEN displaying author information, THE Author_Display SHALL use the same database queries in chat and admin interfaces
2. WHEN showing document metadata, THE Admin_Dashboard SHALL use the same enrichment process as the chat interface
3. THE Edit_Feature SHALL update the same database tables that the display components read from
4. WHEN database schema changes occur, THE Upload_System SHALL populate all required tables consistently
5. THE Source_Enrichment SHALL provide complete metadata for both chat and admin interfaces

### Requirement 8: User Experience Consistency

**User Story:** As a user, I want consistent behavior and appearance across all parts of the application, so that the interface is predictable and professional.

#### Acceptance Criteria

1. THE Back_To_Top_Button SHALL match the application's design system and color scheme
2. THE Admin_Dashboard SHALL maintain consistent styling when displaying new metadata fields
3. THE Author_Display SHALL use consistent formatting in both chat results and admin interface
4. WHEN errors occur, THE Edit_Feature SHALL show user-friendly error messages consistent with the application style
5. THE Chat_Interface SHALL maintain current chat flow and functionality while adding navigation improvements