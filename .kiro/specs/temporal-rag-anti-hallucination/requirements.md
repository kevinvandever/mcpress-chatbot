# Requirements Document

## Introduction

The MC Press Chatbot has a 30-year library of IBM i and RPG content spanning multiple language eras — from fixed-format RPG III (1990s) through RPG IV and ILE (2000s) to modern fully-free RPG (2010s+). The current vector search retrieves semantically similar content without any temporal or era awareness, causing "era hallucinations" where the system returns 1994 RPG III fixed-format examples when a user asks about modern free-form RPG, or vice versa.

This feature adds temporal awareness in two layers: (1) era-aware few-shot prompting and intent detection in the chat pipeline, and (2) temporal metadata tagging on documents with a re-ranking layer that boosts era-appropriate results.

The MC Press library covers far more than RPG — including CL, DB2/SQL, system administration, security, ILE, web services, PHP on IBM i, and Node.js on IBM i. However, the era hallucination problem is most acute with RPG because it is the language that underwent the most dramatic syntax evolution (fixed-format → free-form → fully-free). Non-RPG content (DB2 books, CL guides, security references, etc.) is tagged with the `general` era label and is unaffected by temporal re-ranking — it continues to rank purely on semantic relevance.

This feature applies equally to both books and articles (approximately 6,200 articles) in the corpus. Articles are often more time-specific than books, making temporal re-ranking particularly valuable for article-heavy queries. Both books and articles are stored in the Books_Table and will receive `publication_year` and `rpg_era` metadata through the same migration and enrichment process.

## Glossary

- **Chat_Handler**: The Python class (`ChatHandler` in `chat_handler.py`) that orchestrates query processing, context building, and OpenAI API calls.
- **Vector_Store**: The PostgreSQL/pgvector-backed store (`PostgresVectorStore` in `vector_store_postgres.py`) that performs embedding-based similarity search.
- **Intent_Detector**: A new component within Chat_Handler that classifies user queries by RPG era intent before retrieval.
- **Re_Ranker**: A new filtering/scoring layer within `_filter_relevant_documents` that adjusts document ranking based on temporal relevance.
- **System_Prompt**: The system message sent to GPT-4o-mini that defines the assistant's behavior and expertise boundaries.
- **RPG_Era**: A categorical label assigned to documents indicating the RPG language era: `fixed-format` (RPG III/RPG-400, pre-2001), `rpg-iv` (RPG IV with mixed format, 2001-2013), `free-form` (free-form RPG IV, 2013-2019), or `fully-free` (fully-free RPG, 2019+).
- **Publication_Year**: The integer year a book or article was published, stored as metadata on the books table.
- **Era_Signal**: A keyword or phrase in a user query that indicates which RPG era the user is asking about (e.g., "free-form", "C-spec", "VS Code", "/free", "fully free", "fixed format").
- **Temporal_Boost**: A numeric adjustment applied to a document's relevance score based on how well its RPG_Era matches the detected query intent.
- **Books_Table**: The PostgreSQL `books` table that stores document-level metadata (title, author, URLs, document_type).
- **Documents_Table**: The PostgreSQL `documents` table that stores individual text chunks with embeddings and JSONB metadata.

## Requirements

### Requirement 1: Era-Aware System Prompt

**User Story:** As a user asking about RPG programming, I want the chatbot to understand the difference between old and new RPG syntax, so that I receive era-appropriate answers instead of outdated code examples.

#### Acceptance Criteria

1. THE System_Prompt SHALL include instructions that distinguish between fixed-format RPG (C-specs, H-specs, D-specs) and modern free-form RPG (fully-free format, `dcl-s`, `dcl-proc`, `dcl-ds`).
2. THE System_Prompt SHALL contain at least two few-shot examples that demonstrate the difference between legacy fixed-format RPG and modern free-form RPG equivalents.
3. WHEN a user asks about RPG without specifying an era, THE System_Prompt SHALL instruct the Chat_Handler to default to modern free-form RPG conventions unless the user explicitly requests legacy syntax.
4. THE System_Prompt SHALL instruct the Chat_Handler to flag when source material uses a different RPG era than what the user requested, by prefacing the answer with a brief era-context note (e.g., "Note: this source uses RPG IV fixed-format; here's the modern equivalent...").

### Requirement 2: Query Intent Detection for RPG Era

**User Story:** As a developer asking about RPG, I want the system to detect whether my question is about modern or legacy RPG, so that the retrieved documents match the era I need.

#### Acceptance Criteria

1. WHEN a user query contains modern Era_Signals (including but not limited to: "free-form", "fully free", "dcl-s", "dcl-proc", "dcl-ds", "dcl-pi", "/free", "**free", "VS Code", "RDi", "SQL embedded", "IBM i 7.3+", "IBM i 7.4", "IBM i 7.5"), THE Intent_Detector SHALL classify the query as `modern`.
2. WHEN a user query contains legacy Era_Signals (including but not limited to: "C-spec", "H-spec", "D-spec", "F-spec", "O-spec", "fixed-format", "RPG III", "RPG/400", "RPG-400", "S/36", "S/38", "AS/400", "RPGLE fixed", "column-based"), THE Intent_Detector SHALL classify the query as `legacy`.
3. WHEN a user query contains no recognizable Era_Signals, THE Intent_Detector SHALL classify the query as `neutral`.
4. THE Intent_Detector SHALL return the detected era classification as a string value: `modern`, `legacy`, or `neutral`.
5. THE Intent_Detector SHALL complete classification within 5 milliseconds for any query up to 500 characters, using keyword matching without LLM calls.

### Requirement 3: Temporal Metadata on Books and Articles

**User Story:** As a system administrator, I want each book and article (including the ~6,200 articles in the corpus) to have publication year and RPG era metadata, so that the search pipeline can use temporal information for ranking.

#### Acceptance Criteria

1. THE Books_Table SHALL include a `publication_year` column of type INTEGER that stores the year the document was published.
2. THE Books_Table SHALL include an `rpg_era` column of type VARCHAR(20) that stores one of the following values: `fixed-format`, `rpg-iv`, `free-form`, `fully-free`, or `general`.
3. WHEN a new book is added to the Books_Table without a `publication_year` value, THE Vector_Store SHALL store NULL for the `publication_year` column.
4. WHEN a new book is added to the Books_Table without an `rpg_era` value, THE Vector_Store SHALL store `general` as the default value for the `rpg_era` column.
5. THE Books_Table SHALL allow updating `publication_year` and `rpg_era` through the existing metadata update endpoint.

### Requirement 4: Temporal Re-Ranking of Search Results

**User Story:** As a user asking about modern RPG, I want search results from modern-era documents to be prioritized over legacy-era documents, so that I get the most relevant and current information.

#### Acceptance Criteria

1. WHEN the Intent_Detector classifies a query as `modern`, THE Re_Ranker SHALL apply a Temporal_Boost that reduces the distance score of documents tagged with `rpg_era` values of `free-form` or `fully-free` by a configurable factor (default: 0.10 distance reduction).
2. WHEN the Intent_Detector classifies a query as `legacy`, THE Re_Ranker SHALL apply a Temporal_Boost that reduces the distance score of documents tagged with `rpg_era` values of `fixed-format` or `rpg-iv` by the same configurable factor.
3. WHEN the Intent_Detector classifies a query as `neutral`, THE Re_Ranker SHALL apply no Temporal_Boost and preserve the original distance-based ranking.
4. THE Re_Ranker SHALL apply the Temporal_Boost after the initial vector similarity search and before the relevance threshold filter in `_filter_relevant_documents`.
5. WHEN a document has no `rpg_era` metadata (NULL or `general`), THE Re_Ranker SHALL apply no Temporal_Boost to that document regardless of query intent.
6. THE Re_Ranker SHALL log the original distance, the Temporal_Boost applied, and the adjusted distance for each document to aid debugging.

### Requirement 5: Era Context in Built Context

**User Story:** As a user, I want the context provided to the LLM to include era information about each source, so that the model can reason about temporal relevance when composing answers.

#### Acceptance Criteria

1. WHEN building context from retrieved documents, THE Chat_Handler SHALL include the `rpg_era` label and `publication_year` (if available) in the source annotation for each document chunk.
2. WHEN a document has no `rpg_era` or `publication_year` metadata, THE Chat_Handler SHALL omit those fields from the source annotation rather than displaying "Unknown" or placeholder values.
3. THE Chat_Handler SHALL format the era annotation as part of the existing source info bracket, for example: `[Source: filename.pdf, Page 42, Era: fully-free, Year: 2021]`.

### Requirement 6: Database Migration for Temporal Columns

**User Story:** As a developer, I want the temporal metadata columns added via a safe database migration, so that existing data is preserved and the migration is repeatable.

#### Acceptance Criteria

1. THE migration script SHALL add `publication_year` (INTEGER, nullable) and `rpg_era` (VARCHAR(20), default `general`) columns to the Books_Table using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` syntax.
2. THE migration script SHALL be idempotent, producing no errors when executed multiple times against the same database.
3. THE migration script SHALL preserve all existing data in the Books_Table during execution.
4. THE migration script SHALL create an index on the `rpg_era` column for efficient filtering.
5. THE migration script SHALL be exposed as an API endpoint following the project's established pattern for database migrations.

### Requirement 7: Bulk Metadata Enrichment for Existing Books and Articles

**User Story:** As a system administrator, I want to populate `publication_year` and `rpg_era` for all existing books and articles based on known heuristics, so that the temporal re-ranking works immediately for the entire corpus (books and ~6,200 articles).

#### Acceptance Criteria

1. THE enrichment process SHALL assign `rpg_era` values to existing books based on `publication_year` using the following rules: year <= 2000 maps to `fixed-format`, 2001-2013 maps to `rpg-iv`, 2014-2019 maps to `free-form`, 2020+ maps to `fully-free`.
2. WHEN a book has no `publication_year`, THE enrichment process SHALL assign `general` as the `rpg_era` value.
3. THE enrichment process SHALL be exposed as an API endpoint that can be triggered manually.
4. THE enrichment process SHALL return a summary report indicating how many books were updated per `rpg_era` category.
5. THE enrichment process SHALL not overwrite `rpg_era` values that have already been manually set to a non-`general` value.
