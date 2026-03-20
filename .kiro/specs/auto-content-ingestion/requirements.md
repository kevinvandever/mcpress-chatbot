# Requirements Document

## Introduction

This feature automates the ingestion of new books and articles published to the MC Press Online PDF repository at `https://prod.mcpressonline.com/images/ngpdfs`. The system will check the source location on a monthly schedule, detect new PDF files that have not been previously loaded, download them, and process them through the existing PDF processing and vector embedding pipeline. This eliminates the need for manual uploads of newly published content.

## Glossary

- **Ingestion_Service**: The backend service responsible for discovering, downloading, and orchestrating the processing of new PDF content from the source location.
- **Source_Location**: The remote URL (`https://prod.mcpressonline.com/images/ngpdfs`) where MC Press publishes new books and articles as PDF files.
- **Ingestion_Run**: A single execution of the monthly content check and processing cycle.
- **Ingestion_Log**: A PostgreSQL table that records each Ingestion_Run, including timestamps, files discovered, files processed, and any errors encountered.
- **Document_Registry**: The existing `books` and `documents` tables in PostgreSQL that track all loaded content and their embeddings.
- **PDF_Processor**: The existing `PDFProcessorFull` class that extracts text, images, and code blocks from PDF files.
- **Vector_Store**: The existing `PostgresVectorStore` class that generates embeddings and stores document chunks with pgvector.

## Requirements

### Requirement 1: Source Content Discovery

**User Story:** As a system administrator, I want the system to list available PDF files at the Source_Location, so that new content can be identified for ingestion.

#### Acceptance Criteria

1. WHEN an Ingestion_Run is triggered, THE Ingestion_Service SHALL fetch the file listing from the Source_Location via HTTP.
2. THE Ingestion_Service SHALL parse the HTTP response to extract all PDF filenames available at the Source_Location.
3. IF the Source_Location is unreachable or returns a non-200 HTTP status, THEN THE Ingestion_Service SHALL log the error in the Ingestion_Log and abort the current Ingestion_Run.
4. IF the Source_Location returns an empty file listing, THEN THE Ingestion_Service SHALL log that zero files were found and complete the Ingestion_Run with no further processing.

### Requirement 2: Deduplication Against Existing Content

**User Story:** As a system administrator, I want the system to skip files that have already been loaded, so that duplicate content is not processed or stored.

#### Acceptance Criteria

1. WHEN the Ingestion_Service has a list of discovered PDF filenames, THE Ingestion_Service SHALL query the Document_Registry to determine which filenames have already been loaded.
2. THE Ingestion_Service SHALL exclude any filename that already exists in the Document_Registry from the current Ingestion_Run processing queue.
3. THE Ingestion_Service SHALL log the count of skipped (already loaded) files and the count of new files identified for each Ingestion_Run.

### Requirement 3: PDF Download

**User Story:** As a system administrator, I want the system to download new PDF files from the Source_Location, so that they can be processed and indexed.

#### Acceptance Criteria

1. WHEN a new PDF file is identified for processing, THE Ingestion_Service SHALL download the file from the Source_Location to a temporary storage location.
2. IF a PDF download fails due to a network error or non-200 HTTP status, THEN THE Ingestion_Service SHALL retry the download up to 3 times with exponential backoff (5s, 15s, 60s delays).
3. IF a PDF download fails after all retry attempts, THEN THE Ingestion_Service SHALL log the failure for that file in the Ingestion_Log and continue processing remaining files.
4. THE Ingestion_Service SHALL validate that each downloaded file has a `.pdf` extension and a file size greater than zero bytes before proceeding to processing.

### Requirement 4: PDF Processing and Embedding

**User Story:** As a system administrator, I want downloaded PDFs to be processed through the existing pipeline, so that their content becomes searchable via the chatbot.

#### Acceptance Criteria

1. WHEN a new PDF file has been downloaded and validated, THE Ingestion_Service SHALL process the file using the PDF_Processor to extract text, images, and code blocks.
2. WHEN extraction is complete, THE Ingestion_Service SHALL store the extracted chunks and their embeddings in the Vector_Store using the existing `add_documents` method.
3. THE Ingestion_Service SHALL assign metadata to each processed document including filename, title (derived from filename), author (extracted or "Unknown"), category (from category mapper or "Uncategorized"), and the ingestion timestamp.
4. IF processing of a single PDF fails, THEN THE Ingestion_Service SHALL log the error for that file in the Ingestion_Log and continue processing remaining files.
5. WHEN a PDF has been processed and stored, THE Ingestion_Service SHALL remove the temporary downloaded file to conserve storage.

### Requirement 5: Monthly Scheduling

**User Story:** As a system administrator, I want the ingestion process to run automatically once per month, so that new content is picked up without manual intervention.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL execute an Ingestion_Run automatically once per calendar month.
2. THE Ingestion_Service SHALL record the timestamp of each completed Ingestion_Run in the Ingestion_Log.
3. WHEN the application starts, THE Ingestion_Service SHALL schedule the next Ingestion_Run based on the last recorded run timestamp in the Ingestion_Log.
4. THE Ingestion_Service SHALL provide an API endpoint to manually trigger an Ingestion_Run on demand (for administrative use).

### Requirement 6: Ingestion Run Logging and Status

**User Story:** As a system administrator, I want to see the history and status of ingestion runs, so that I can verify the system is working and troubleshoot issues.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL record each Ingestion_Run in the Ingestion_Log with: run ID, start timestamp, end timestamp, status (running, completed, failed), total files discovered, files skipped (duplicates), files processed, and files failed.
2. THE Ingestion_Service SHALL provide an API endpoint to retrieve the history of Ingestion_Runs with pagination support.
3. THE Ingestion_Service SHALL provide an API endpoint to retrieve the status of the current or most recent Ingestion_Run.
4. WHEN an Ingestion_Run completes, THE Ingestion_Service SHALL log a summary including the number of new documents added and any errors encountered.

### Requirement 7: Last Check Tracking

**User Story:** As a system administrator, I want the system to track when it last checked the Source_Location, so that it only processes content published since the last check.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL persist the timestamp of the last completed Ingestion_Run in the Ingestion_Log table.
2. WHEN determining which files are new, THE Ingestion_Service SHALL use filename-based deduplication against the Document_Registry rather than relying solely on timestamps, to ensure no content is missed.
3. WHEN no previous Ingestion_Run exists in the Ingestion_Log, THE Ingestion_Service SHALL treat all discovered files as new and process them (initial run behavior).

### Requirement 8: Graceful Error Handling and Resilience

**User Story:** As a system administrator, I want the ingestion process to handle errors gracefully, so that a single failure does not prevent other files from being processed.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL process each PDF file independently, so that a failure in one file does not affect the processing of other files in the same Ingestion_Run.
2. IF the database connection is lost during an Ingestion_Run, THEN THE Ingestion_Service SHALL retry the database operation up to 3 times before marking the file as failed.
3. IF an Ingestion_Run is interrupted (e.g., application restart), THEN THE Ingestion_Service SHALL mark the run as "interrupted" in the Ingestion_Log and allow the next scheduled run to pick up any unprocessed files.
4. THE Ingestion_Service SHALL enforce a timeout of 10 minutes per individual PDF download and 30 minutes per individual PDF processing operation to prevent indefinite hangs.
