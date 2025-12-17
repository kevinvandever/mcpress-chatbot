# Requirements Document

## Introduction

The MC Press Chatbot chat handler currently fails to enrich chat response sources with book and author metadata from the database. Despite having complete book and author data in the `books`, `authors`, and `document_authors` tables, the chat interface displays "Unknown" for authors and empty arrays for author details. This bug prevents users from seeing proper attribution, author website links, and purchase/article links in chat responses.

## Glossary

- **Chat Handler**: The backend service (`backend/chat_handler.py`) that processes user queries, retrieves relevant documents, and streams responses from the OpenAI API
- **Source Enrichment**: The process of augmenting search results with metadata from the `books` and `authors` tables before returning them to the frontend
- **Vector Store**: The PostgreSQL database with pgvector extension that stores document embeddings and performs semantic similarity search
- **Books Table**: Database table containing book/article metadata including title, category, URLs, and document type
- **Authors Table**: Database table containing author information including name and website URL
- **Document Authors Table**: Junction table linking books to authors with ordering information
- **Metadata**: Additional information about documents including author names, URLs, document type, and purchase links

## Requirements

### Requirement 1

**User Story:** As a user asking questions in the chat interface, I want to see accurate author information for source documents, so that I can identify who wrote the content and access their websites.

#### Acceptance Criteria

1. WHEN the chat handler retrieves relevant documents from the vector store THEN the system SHALL query the books table using the document filename
2. WHEN a book record is found in the books table THEN the system SHALL query the document_authors table using the book_id field (not document_id)
3. WHEN querying the document_authors table THEN the system SHALL use the correct foreign key column name book_id to join with the books table
4. WHEN author records are found in the document_authors table THEN the system SHALL join with the authors table to retrieve author names and website URLs
5. WHEN multiple authors exist for a document THEN the system SHALL order them by the author_order field
6. WHEN no authors are found in the document_authors table THEN the system SHALL fall back to the legacy author field in the books table

### Requirement 2

**User Story:** As a user viewing chat sources, I want to see purchase links for books and article links for articles, so that I can access the full content.

#### Acceptance Criteria

1. WHEN a source document has a document_type of "book" and an mc_press_url THEN the system SHALL include the mc_press_url in the enriched metadata
2. WHEN a source document has a document_type of "article" and an article_url THEN the system SHALL include the article_url in the enriched metadata
3. WHEN enriched metadata is returned to the frontend THEN the system SHALL include the document_type field
4. WHEN the frontend receives enriched metadata with mc_press_url THEN the system SHALL display a "Buy" button linking to the MC Store
5. WHEN the frontend receives enriched metadata with article_url THEN the system SHALL display a "Read" button linking to the article

### Requirement 3

**User Story:** As a developer debugging the chat enrichment feature, I want detailed logging of the enrichment process, so that I can identify where failures occur.

#### Acceptance Criteria

1. WHEN the enrichment process begins for a filename THEN the system SHALL log the filename being enriched
2. WHEN a database query is executed THEN the system SHALL log the query parameters
3. WHEN a book record is found THEN the system SHALL log the book title and legacy author
4. WHEN author records are retrieved THEN the system SHALL log the count and names of authors found
5. WHEN an error occurs during enrichment THEN the system SHALL log the full exception with stack trace

### Requirement 4

**User Story:** As a system administrator, I want the chat handler to gracefully handle missing or incomplete metadata, so that chat responses are always returned even when enrichment fails.

#### Acceptance Criteria

1. WHEN the DATABASE_URL environment variable is not set THEN the system SHALL log a warning and return empty enrichment metadata
2. WHEN a database connection fails THEN the system SHALL catch the exception and return empty enrichment metadata
3. WHEN a filename is not found in the books table THEN the system SHALL return empty enrichment metadata
4. WHEN enrichment returns empty metadata THEN the system SHALL use fallback values from the document metadata
5. WHEN all enrichment attempts fail THEN the system SHALL still return chat responses with "Unknown" author and empty URLs

### Requirement 5

**User Story:** As a user, I want the chat interface to display author website links as clickable elements, so that I can easily visit author websites.

#### Acceptance Criteria

1. WHEN an author has a site_url in the authors table THEN the system SHALL include it in the enriched metadata
2. WHEN the frontend receives author objects with site_url THEN the system SHALL render author names as clickable links
3. WHEN an author does not have a site_url THEN the system SHALL display the author name as plain text
4. WHEN multiple authors exist with different site_url values THEN the system SHALL display each author with their respective link or plain text
5. WHEN a user clicks an author website link THEN the system SHALL open the link in a new browser tab
