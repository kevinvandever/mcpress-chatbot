# Requirements Document

## Introduction

The auto content ingestion pipeline ingests PDF articles from the MC Press FTP server, but approximately 290+ recently ingested articles have poor metadata: titles display as numeric filenames (e.g., "27814") instead of actual article titles, and authors show as "Unknown" or "Unknown Author" instead of the real author names. This feature addresses three needs: (1) improving metadata extraction during ingestion so future articles get correct titles and authors, (2) backfilling the ~290+ articles already ingested with poor metadata, and (3) leveraging the existing Excel spreadsheet "MC Press Books - URL-Title-Author.xlsx" as a metadata lookup source. The FTP server hosts ~6,445 PDFs, most of which were ingested correctly via earlier bulk imports; only the recently auto-ingested articles are affected.

## Glossary

- **Ingestion_Service**: The backend service (`backend/ingestion_service.py`) that discovers, downloads, and processes new PDF content from the MC Press FTP server into the vector store and books table.
- **PDF_Processor**: The backend service (`backend/pdf_processor_full.py`) that extracts text, images, and metadata (including author) from PDF files.
- **Author_Extractor**: The backend module (`backend/author_extractor.py`) that uses regex patterns and PDF metadata to extract author names from PDF content.
- **Excel_Lookup_Service**: A new service that loads title and author mappings from the "MC Press Books - URL-Title-Author.xlsx" spreadsheet and provides lookup by filename or fuzzy title match.
- **Metadata_Backfill_Service**: A new service that identifies articles with poor metadata (numeric titles, unknown authors) and updates them with correct metadata from available sources.
- **Article**: A document in the books table with `document_type = 'article'`, typically originating from a numeric-filename PDF on the FTP server.
- **Numeric_Filename**: A PDF filename consisting only of digits followed by `.pdf` (e.g., `27814.pdf`), indicating an article rather than a book.
- **Poor_Metadata**: An article record where the title is a numeric filename (e.g., "27814") or the author is "Unknown" or "Unknown Author".
- **MC_Press_Website**: The mcpressonline.com website, which publishes articles with structured HTML containing article titles and author names.
- **Excel_Spreadsheet**: The file "MC Press Books - URL-Title-Author.xlsx" in the repository root, containing URL, title, and author mappings for MC Press content.

## Requirements

### Requirement 1: Excel-Based Metadata Lookup

**User Story:** As a system administrator, I want the ingestion pipeline to look up article titles and authors from the Excel spreadsheet, so that articles with numeric filenames get meaningful metadata without relying solely on PDF extraction.

#### Acceptance Criteria

1. WHEN the Excel_Lookup_Service is initialized, THE Excel_Lookup_Service SHALL load all rows from the Excel_Spreadsheet into an in-memory mapping keyed by article identifier.
2. WHEN a Numeric_Filename is provided, THE Excel_Lookup_Service SHALL return the matching title and author from the Excel_Spreadsheet if a match exists.
3. IF no match is found in the Excel_Spreadsheet for a given filename, THEN THE Excel_Lookup_Service SHALL return None for both title and author.
4. THE Excel_Lookup_Service SHALL support lookup by numeric article ID extracted from the filename (e.g., "27814" from "27814.pdf").
5. WHEN the Excel_Spreadsheet contains multiple authors separated by commas or "and", THE Excel_Lookup_Service SHALL parse them into individual author names using the existing `parse_authors` method pattern from the Excel_Import_Service.

### Requirement 2: MC Press Website Metadata Scraping

**User Story:** As a system administrator, I want the system to scrape article metadata from the MC Press website when the Excel spreadsheet has no match, so that articles still get correct titles and authors.

#### Acceptance Criteria

1. WHEN the Excel_Lookup_Service returns no match for an article, THE Ingestion_Service SHALL attempt to fetch metadata from the MC_Press_Website using the article's numeric ID.
2. WHEN the MC_Press_Website returns a valid HTML page for the article ID, THE Ingestion_Service SHALL extract the article title from the page's structured HTML content.
3. WHEN the MC_Press_Website returns a valid HTML page for the article ID, THE Ingestion_Service SHALL extract the author name from the page's structured HTML content.
4. IF the MC_Press_Website returns a 404 or error response for the article ID, THEN THE Ingestion_Service SHALL fall back to PDF-based extraction.
5. THE Ingestion_Service SHALL use a request timeout of 10 seconds when fetching pages from the MC_Press_Website.
6. THE Ingestion_Service SHALL include a User-Agent header identifying the MC Press Chatbot when making requests to the MC_Press_Website.

### Requirement 3: Enhanced Ingestion Pipeline Metadata Resolution

**User Story:** As a system administrator, I want the ingestion pipeline to use a multi-source metadata resolution strategy, so that articles get the best available title and author from any source.

#### Acceptance Criteria

1. WHEN processing a Numeric_Filename PDF, THE Ingestion_Service SHALL attempt metadata resolution in this order: (a) Excel_Spreadsheet lookup, (b) MC_Press_Website scraping, (c) PDF content extraction via Author_Extractor, (d) default values.
2. WHEN the Excel_Lookup_Service returns a title and author, THE Ingestion_Service SHALL use those values and skip subsequent resolution steps for the matched fields.
3. WHEN metadata resolution produces an author name, THE Ingestion_Service SHALL store the author in the books table and create or link the corresponding record in the authors table.
4. WHEN metadata resolution produces a title, THE Ingestion_Service SHALL use that title instead of the numeric filename as the document title in the books table.
5. IF all metadata resolution sources fail to produce a title, THEN THE Ingestion_Service SHALL use the numeric filename as the title and log a warning.
6. IF all metadata resolution sources fail to produce an author, THEN THE Ingestion_Service SHALL use "Unknown Author" and log a warning.
7. THE Ingestion_Service SHALL log which metadata source was used for each article (Excel, website, PDF extraction, or default).

### Requirement 4: Metadata Backfill for Existing Articles

**User Story:** As a system administrator, I want to fix the ~290+ articles that were already ingested with poor metadata, so that all articles in the system have correct titles and authors.

#### Acceptance Criteria

1. THE Metadata_Backfill_Service SHALL identify all articles in the books table where the title matches a Numeric_Filename pattern (digits only) or the author is "Unknown" or "Unknown Author".
2. WHEN the backfill process runs, THE Metadata_Backfill_Service SHALL apply the same multi-source metadata resolution strategy defined in Requirement 3 to each identified article.
3. WHEN the Metadata_Backfill_Service resolves a new title for an article, THE Metadata_Backfill_Service SHALL update the title in the books table.
4. WHEN the Metadata_Backfill_Service resolves a new author for an article, THE Metadata_Backfill_Service SHALL update the author in the books table and create or link the corresponding record in the authors table.
5. THE Metadata_Backfill_Service SHALL produce a summary report containing: total articles identified, articles updated with new titles, articles updated with new authors, articles that remain with poor metadata, and the metadata source used for each update.
6. THE Metadata_Backfill_Service SHALL operate idempotently so that running the backfill multiple times produces the same result without creating duplicate author records.
7. IF the Metadata_Backfill_Service encounters an error updating a single article, THEN THE Metadata_Backfill_Service SHALL log the error and continue processing remaining articles.

### Requirement 5: Backfill API Endpoint

**User Story:** As a system administrator, I want an API endpoint to trigger and monitor the metadata backfill process, so that I can fix existing articles without direct database access.

#### Acceptance Criteria

1. THE Backend SHALL expose a POST endpoint at `/api/articles/backfill-metadata` that triggers the Metadata_Backfill_Service.
2. WHEN the backfill endpoint is called, THE Backend SHALL return an immediate response with a run ID and status "started".
3. WHEN the backfill process completes, THE Backend SHALL make the summary report available via a GET endpoint at `/api/articles/backfill-metadata/{run_id}`.
4. IF a backfill process is already running, THEN THE Backend SHALL return a 409 Conflict response with a message indicating a backfill is in progress.
5. THE Backend SHALL expose a GET endpoint at `/api/articles/poor-metadata` that returns a list of articles currently identified as having Poor_Metadata, with count and details.

### Requirement 6: Metadata Quality Diagnostics

**User Story:** As a system administrator, I want to see which articles have poor metadata before and after running the backfill, so that I can verify the fix worked.

#### Acceptance Criteria

1. THE Backend SHALL expose a GET endpoint at `/api/diagnostics/article-metadata` that returns metadata quality statistics.
2. WHEN the diagnostics endpoint is called, THE Backend SHALL return: total article count, count of articles with numeric-filename titles, count of articles with "Unknown" or "Unknown Author" as author, and count of articles with both issues.
3. THE diagnostics endpoint SHALL return a sample of up to 20 articles with poor metadata, including their current title, author, and filename.
4. WHEN the diagnostics endpoint is called with a `?detailed=true` query parameter, THE Backend SHALL return the full list of all articles with poor metadata.

### Requirement 7: Excel Spreadsheet Parsing

**User Story:** As a developer, I want the system to correctly parse the "MC Press Books - URL-Title-Author.xlsx" spreadsheet, so that the metadata lookup has accurate source data.

#### Acceptance Criteria

1. THE Excel_Lookup_Service SHALL read the Excel_Spreadsheet using the openpyxl or pandas library.
2. WHEN the Excel_Spreadsheet contains columns for URL, Title, and Author, THE Excel_Lookup_Service SHALL map each row to a lookup entry.
3. THE Excel_Lookup_Service SHALL extract the numeric article ID from URLs containing patterns like `mcpressonline.com/.../<numeric_id>` to enable filename-based lookup.
4. IF the Excel_Spreadsheet file is missing or unreadable, THEN THE Excel_Lookup_Service SHALL log a warning and allow the ingestion pipeline to continue without Excel-based lookup.
5. FOR ALL entries loaded from the Excel_Spreadsheet, parsing then looking up by extracted ID then retrieving the title SHALL return the original title from the spreadsheet (round-trip property).

### Requirement 8: Author Record Management During Backfill

**User Story:** As a developer, I want the backfill process to properly manage author records, so that authors are deduplicated and linked correctly in the multi-author system.

#### Acceptance Criteria

1. WHEN the Metadata_Backfill_Service resolves an author name, THE Metadata_Backfill_Service SHALL check the authors table for an existing record with the same name (case-sensitive match).
2. IF an author record already exists, THEN THE Metadata_Backfill_Service SHALL use the existing author ID for the document-author association.
3. IF no author record exists, THEN THE Metadata_Backfill_Service SHALL create a new author record and use the new ID for the document-author association.
4. WHEN creating or linking an author, THE Metadata_Backfill_Service SHALL create a record in the document_authors junction table with the correct book_id and author_id.
5. THE Metadata_Backfill_Service SHALL handle multi-author articles by creating separate author records and document_authors entries for each author, preserving author order.
6. WHEN the same author name appears across multiple articles, THE Metadata_Backfill_Service SHALL reuse the same author record for all articles (deduplication).
