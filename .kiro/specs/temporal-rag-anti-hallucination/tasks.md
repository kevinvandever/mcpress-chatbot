# Implementation Plan: Temporal RAG Anti-Hallucination

## Overview

Add temporal awareness to the MC Press Chatbot's RAG pipeline to eliminate era hallucinations in RPG content. Implementation follows four layers: config setup, intent detection, database migration + enrichment, temporal re-ranking, era-aware context building, and system prompt updates. All new code is Python (FastAPI backend), tested with `hypothesis` property-based tests.

## Tasks

- [x] 1. Add temporal configuration to `backend/config.py`
  - Add `TEMPORAL_CONFIG` dict with `era_boost_amount` (default 0.10) from env var `ERA_BOOST_AMOUNT`
  - _Requirements: 4.1, 4.2_

- [ ] 2. Implement IntentDetector and temporal re-ranking logic
  - [x] 2.1 Create `IntentDetector` class in `backend/chat_handler.py`
    - Define `MODERN_SIGNALS` and `LEGACY_SIGNALS` keyword sets per design document
    - Implement `detect_era(query: str) -> str` returning `"modern"`, `"legacy"`, or `"neutral"`
    - Case-insensitive keyword matching; return `"neutral"` for empty/None input or ambiguous (both signal types present)
    - Must complete in <5ms for queries up to 500 chars (pure keyword matching, no LLM)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.2 Write property test: Modern signals produce modern classification
    - **Property 1: Modern signals produce modern classification**
    - Generate random query strings containing at least one MODERN_SIGNALS keyword and no LEGACY_SIGNALS keywords; assert `detect_era` returns `"modern"`
    - **Validates: Requirements 2.1**

  - [ ]* 2.3 Write property test: Legacy signals produce legacy classification
    - **Property 2: Legacy signals produce legacy classification**
    - Generate random query strings containing at least one LEGACY_SIGNALS keyword and no MODERN_SIGNALS keywords; assert `detect_era` returns `"legacy"`
    - **Validates: Requirements 2.2**

  - [ ]* 2.4 Write property test: Absence of signals produces neutral classification
    - **Property 3: Absence of signals produces neutral classification**
    - Generate random query strings with no keywords from either signal set; assert `detect_era` returns `"neutral"`
    - **Validates: Requirements 2.3**

  - [x] 2.5 Implement `apply_temporal_boost` function in `backend/chat_handler.py`
    - Accept documents list, era_intent string, and boost_amount (from `TEMPORAL_CONFIG`)
    - For `modern` intent: reduce distance for docs with `rpg_era` in `{"free-form", "fully-free"}` by `boost_amount`
    - For `legacy` intent: reduce distance for docs with `rpg_era` in `{"fixed-format", "rpg-iv"}` by `boost_amount`
    - For `neutral` intent or docs with `rpg_era` in `{None, "general"}`: no adjustment
    - Clamp adjusted distance to `max(0, adjusted_distance)`
    - Log original distance, boost applied, and adjusted distance per document
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 2.6 Write property test: Era-matching documents receive distance reduction
    - **Property 4: Era-matching documents receive distance reduction**
    - Generate random document lists with random `rpg_era` values and distances; apply boost with `modern` and `legacy` intents; verify era-matching docs get `distance - boost_amount` (clamped ≥ 0) and non-matching docs are unchanged
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 2.7 Write property test: Neutral intent or general era means no distance change
    - **Property 5: Neutral intent or general era means no distance change**
    - Generate random document lists; apply boost with `neutral` intent; verify all distances unchanged. Also verify docs with `rpg_era` in `{None, "general"}` are unchanged regardless of intent
    - **Validates: Requirements 4.3, 4.5**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Database migration for temporal metadata columns
  - [x] 4.1 Create `backend/migrations/006_temporal_metadata.sql`
    - `ALTER TABLE books ADD COLUMN IF NOT EXISTS publication_year INTEGER`
    - `ALTER TABLE books ADD COLUMN IF NOT EXISTS rpg_era VARCHAR(20) DEFAULT 'general'`
    - `CREATE INDEX IF NOT EXISTS idx_books_rpg_era ON books (rpg_era)`
    - Must be idempotent (safe to run multiple times)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 4.2 Create `backend/run_migration_006.py` with `POST /run-migration-006` endpoint
    - Follow the established pattern from `run_migration_004.py`
    - Read and execute the SQL migration file
    - Return structured JSON with status, affected columns, and any errors
    - _Requirements: 6.2, 6.5_

  - [x] 4.3 Register migration endpoint in `backend/main.py`
    - Import and include `migration_006_router` following the existing migration-004 pattern
    - _Requirements: 6.5_

- [ ] 5. Bulk temporal metadata enrichment
  - [x] 5.1 Create `backend/temporal_enrichment.py` with enrichment service
    - Implement year-to-era mapping function: ≤2000 → `fixed-format`, 2001-2013 → `rpg-iv`, 2014-2019 → `free-form`, 2020+ → `fully-free`, None → `general`
    - Implement `POST /api/temporal/enrich` endpoint that reads all books, applies year→era mapping, skips books where `rpg_era` is already non-`general`, returns summary of updates per era category
    - Wrap in transaction for atomicity
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 5.2 Write property test: Year-to-era mapping follows defined rules
    - **Property 7: Year-to-era mapping follows defined rules**
    - Generate random integers for years; verify mapping returns correct era per defined ranges. Test None → `"general"`
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 5.3 Write property test: Enrichment preserves manually-set eras
    - **Property 8: Enrichment preserves manually-set eras**
    - Generate random book records with pre-set non-general `rpg_era` values; run enrichment logic; verify era values unchanged
    - **Validates: Requirements 7.5**

  - [x] 5.4 Register enrichment endpoint in `backend/main.py`
    - Import and include the temporal enrichment router
    - _Requirements: 7.3_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Integrate temporal re-ranking into search pipeline
  - [x] 7.1 Modify `_filter_relevant_documents` in `backend/chat_handler.py`
    - Call `IntentDetector.detect_era(query)` to get era intent
    - Look up `rpg_era` metadata for each document from the `books` table (via filename join)
    - Call `apply_temporal_boost(documents, era_intent, boost_amount)` after vector search results arrive and before the relevance threshold filter
    - Re-sort documents by adjusted distance before applying threshold and MAX_SOURCES limit
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 7.2 Add `rpg_era` lookup helper to `ChatHandler`
    - Query `books` table for `rpg_era` by filename to attach era metadata to search results before re-ranking
    - Cache the lookup within a single request to avoid repeated DB queries
    - Handle missing books gracefully (default to `"general"`)
    - _Requirements: 4.5_

- [ ] 8. Era-aware context building and system prompt
  - [x] 8.1 Modify `_build_context` in `backend/chat_handler.py`
    - Include `Era: {rpg_era}` in source annotation when `rpg_era` is not None and not `"general"`
    - Include `Year: {publication_year}` in source annotation when `publication_year` is not None
    - Omit era/year fields when metadata is missing rather than showing placeholders
    - Format: `[Source: filename.pdf, Page 42, Era: fully-free, Year: 2021]`
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 8.2 Write property test: Era annotation reflects metadata availability
    - **Property 6: Era annotation reflects metadata availability**
    - Generate random document metadata dicts with optional `rpg_era` and `publication_year`; verify context string contains/omits `Era:` and `Year:` annotations correctly
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 8.3 Update system prompt in `stream_response` in `backend/chat_handler.py`
    - Add section distinguishing fixed-format RPG (C-specs, H-specs, D-specs) from modern free-form RPG (`dcl-s`, `dcl-proc`, `dcl-ds`)
    - Add at least two few-shot examples showing the same operation in fixed-format vs. free-form
    - Add instruction to default to modern free-form RPG when user doesn't specify an era
    - Add instruction to flag era mismatches with a brief note (e.g., "Note: this source uses RPG IV fixed-format; here's the modern equivalent...")
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 8.4 Write unit tests for system prompt content
    - Verify prompt contains RPG era distinctions, at least two few-shot examples, default-to-modern instruction, and era-mismatch flagging instruction
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Wire everything together and create test file
  - [x] 10.1 Create `backend/test_temporal_rag.py` with all property-based and unit tests
    - Consolidate all property tests (Properties 1-8) and unit tests into single test file
    - Use `hypothesis` library with `@settings(max_examples=100)` for property tests
    - Tag each property test with comment referencing design property number
    - Include unit tests for edge cases: empty query, None query, ambiguous signals, empty doc list, zero boost_amount, distance already at 0
    - Include unit test verifying `TEMPORAL_CONFIG["era_boost_amount"]` defaults to 0.10
    - _Requirements: 2.1-2.5, 4.1-4.6, 5.1-5.3, 7.1-7.5_

  - [x] 10.2 Verify `_enrich_source_metadata` in `ChatHandler` includes `rpg_era` and `publication_year`
    - Extend the existing `_enrich_source_metadata` query to SELECT `publication_year` and `rpg_era` from the `books` table
    - Pass these fields through to `_build_context` and `_format_sources`
    - _Requirements: 5.1, 5.3_

  - [x] 10.3 Ensure metadata update endpoint supports `publication_year` and `rpg_era`
    - Verify `update_document_metadata` in `vector_store_postgres.py` handles the new columns when updating book metadata
    - _Requirements: 3.3, 3.4, 3.5_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All testing runs on Railway after deployment — no local testing
- The `hypothesis` library is already available in the project
- Migration and enrichment endpoints follow the established API-based pattern (see `run_migration_004.py`)
