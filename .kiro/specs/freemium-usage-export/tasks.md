# Implementation Plan: Freemium Usage Export

## Overview

This plan implements three capabilities: a backend CSV/JSON export endpoint for free-tier usage data, a Google Analytics bridge in the frontend `trackEvent()` function, and a local export script. The backend endpoint lives in a new `backend/freemium_export_routes.py` module registered in `main.py` via the standard try/except pattern. The frontend change extends `analytics.ts` with a `gtag` bridge and camelCase-to-snake_case conversion. The export script is a standalone `requests`-based Python script at the project root.

The design specifies Python (backend) and TypeScript (frontend) — no pseudocode. Hypothesis is used for backend property tests; fast-check for frontend property tests. Both are already in project dependencies.

## Tasks

- [x] 1. Backend: Create freemium export route module
  - [x] 1.1 Create `backend/freemium_export_routes.py` with the export endpoint
    - Create `APIRouter(prefix="/api/admin", tags=["admin"])`
    - Add module-level `_database_url` variable and `set_database_url(url)` setter function (lazy pool pattern)
    - Add `_read_limit()` helper that reads `FREE_QUESTION_LIMIT` from env, defaults to 8 on missing/invalid (same pattern as `UsageGate._read_limit()`)
    - Add helper to parse and validate ISO 8601 date strings (`YYYY-MM-DD`), returning HTTP 400 on invalid format
    - Add validation that `start_date` is not after `end_date`, returning HTTP 400
    - Implement `GET /freemium-export` endpoint with `Depends(get_current_user)` from `auth_routes.py`
    - Accept query params: `format` (csv or json, default csv), `start_date` (optional), `end_date` (optional)
    - Query `free_usage_tracking` table: `SELECT user_email, questions_used, created_at, last_question_at` with optional date filters, ordered by `questions_used DESC, last_question_at DESC`
    - Compute summary aggregates: `total_free_users`, `reached_soft_warning` (>= limit-2), `reached_strong_warning` (>= limit-1), `reached_limit` (>= limit), `average_questions_used` (rounded to 1 decimal), `questions_limit`
    - For CSV: return `text/csv` with `Content-Disposition: attachment; filename=freemium-usage-export-{YYYY-MM-DD}.csv`, header row `email,questions_used,first_seen,last_active`, user rows, blank row, then `#`-prefixed summary rows
    - For JSON: return `application/json` with `{"users": [...], "summary": {...}}` structure
    - Format timestamps as ISO 8601 strings
    - Wrap database operations in try/except, return HTTP 500 with descriptive message on failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 1.2 Register freemium export routes in `backend/main.py`
    - Add standard try/except import block for `freemium_export_routes` (both Railway and local import paths)
    - Set `FREEMIUM_EXPORT_AVAILABLE` flag
    - In `startup_event`, after `DATABASE_URL` is confirmed: call `set_database_url(database_url)`, then `app.include_router(freemium_export_router)`
    - Print status messages following existing pattern (`✅` on success, `⚠️` on failure)
    - _Requirements: 1.1_

- [x] 2. Checkpoint — Verify backend export endpoint compiles
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Backend: Property and unit tests for export logic
  - [ ]* 3.1 Write property test: Export ordering correctness (Property 1)
    - Create `backend/test_freemium_export.py`
    - Use Hypothesis to generate lists of user records with varying `questions_used` and `last_question_at` values
    - Extract the sorting/ordering logic into a testable pure function in `freemium_export_routes.py`
    - Verify output is sorted by `questions_used` DESC then `last_question_at` DESC
    - **Property 1: Export ordering is correct**
    - **Validates: Requirements 1.6**

  - [ ]* 3.2 Write property test: ISO 8601 timestamp round-trip (Property 2)
    - Use Hypothesis to generate `datetime` values
    - Format as ISO 8601 string and parse back, verify equivalence
    - **Property 2: ISO 8601 timestamp round-trip**
    - **Validates: Requirements 1.7**

  - [ ]* 3.3 Write property test: Summary threshold counts consistency (Property 3)
    - Use Hypothesis to generate lists of user records and positive integer `questions_limit`
    - Compute summary fields and verify: `total_free_users` equals count, threshold counts match filter criteria, invariant `reached_limit <= reached_strong_warning <= reached_soft_warning <= total_free_users` holds
    - **Property 3: Summary threshold counts are consistent with user data**
    - **Validates: Requirements 2.2, 2.3, 2.6**

  - [ ]* 3.4 Write property test: Summary average computation (Property 4)
    - Use Hypothesis to generate non-empty and empty lists of user records
    - Verify `average_questions_used` equals `round(sum/count, 1)` for non-empty, `0` for empty
    - **Property 4: Summary average computation**
    - **Validates: Requirements 2.4**

  - [ ]* 3.5 Write property test: Date range filtering correctness (Property 5)
    - Use Hypothesis to generate user records with varying `created_at` and date ranges
    - Verify all returned records fall within range, and all records in range are returned
    - Verify no date range returns all records
    - **Property 5: Date range filtering correctness**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

  - [ ]* 3.6 Write unit tests for export endpoint
    - Test 401 response without auth token (Req 1.2)
    - Test CSV Content-Type and Content-Disposition headers (Req 1.3)
    - Test JSON Content-Type header (Req 1.4)
    - Test CSV header row matches `email,questions_used,first_seen,last_active` (Req 1.5)
    - Test JSON response contains `users` array and `summary` object (Req 2.1)
    - Test CSV summary rows appear after blank row with `#` prefix (Req 2.5)
    - Test valid date params succeed (Req 3.1)
    - Test no date params returns all users (Req 3.5)
    - Test invalid date format returns 400 (Req 3.6)
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.5, 3.1, 3.5, 3.6_

- [x] 4. Frontend: Add Google Analytics bridge to trackEvent
  - [x] 4.1 Update `frontend/utils/analytics.ts` with gtag bridge
    - Add `declare global { interface Window { gtag?: ... } }` TypeScript type declaration for `gtag` on `window`
    - Add `toSnakeCase(str: string): string` helper function (convert camelCase to snake_case)
    - Add `convertKeysToSnakeCase(data)` helper function
    - Extend `trackEvent()` with a second try/catch block that checks `typeof window.gtag === 'function'` and calls `window.gtag('event', action, convertKeysToSnakeCase(data))`
    - Keep existing DOM `CustomEvent` emission in its own try/catch (unaffected by gtag failures)
    - Export `toSnakeCase` and `convertKeysToSnakeCase` for testing
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3_

- [ ] 5. Frontend: Property and unit tests for analytics bridge
  - [ ]* 5.1 Write property test: camelCase to snake_case conversion (Property 6)
    - Create `frontend/__tests__/analytics.property.test.ts`
    - Use fast-check to generate camelCase strings
    - Verify output contains no uppercase letters, uppercase letters are preceded by underscore
    - Verify idempotence: `toSnakeCase` on already-snake_case input returns same string
    - **Property 6: camelCase to snake_case conversion**
    - **Validates: Requirements 6.6**

  - [ ]* 5.2 Write unit tests for analytics bridge
    - Create `frontend/__tests__/analytics.test.ts`
    - Test `trackEvent` emits DOM `CustomEvent` with correct payload (Req 5.1)
    - Test `trackEvent` calls `window.gtag` when available (Req 5.1)
    - Test `trackEvent` does not throw when `gtag` is undefined (Req 5.2, 5.6)
    - Test `trackEvent` emits DOM event even when `gtag` throws (Req 5.5)
    - Test GA params for `warning_stage_change` include `stage`, `questions_used` (Req 6.1)
    - Test GA params for `upgrade_click` include `stage`, `is_pql` (Req 6.2)
    - Test GA params for `pql_qualified` include `session_question_count` (Req 6.3)
    - _Requirements: 5.1, 5.2, 5.5, 5.6, 6.1, 6.2, 6.3_

- [ ] 6. Checkpoint — Verify frontend analytics changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create local export script
  - [x] 7.1 Create `export_freemium_usage.py` at project root
    - Standalone Python script using `requests` and `argparse` (no backend imports)
    - Read `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `API_URL` (default: production Railway URL) from environment variables
    - Authenticate via `POST {API_URL}/api/admin/login` with `{"email": ..., "password": ...}`
    - Extract `access_token` from response; on failure, print error and `sys.exit(1)`
    - Accept CLI args: `--format` (csv/json, default csv), `--start-date`, `--end-date`, `--output` (default: `freemium-usage-export-{today}.{format}`)
    - Call `GET {API_URL}/api/admin/freemium-export` with Bearer token and query params
    - Save response body to output file
    - Print summary line: `"Exported to {filepath}"` with user count parsed from response
    - Handle network errors, auth failures, and non-200 responses with descriptive messages and `sys.exit(1)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Properties 1–6 from design)
- Unit tests validate specific examples, edge cases, and HTTP behavior
- Backend uses Hypothesis for property tests; frontend uses fast-check — both already in project dependencies
- All integration testing on Railway/Netlify staging after deployment — no local test environment
- The export script follows the project's established API-based script pattern (uses `requests`, no backend imports)
- No database migrations required — the `free_usage_tracking` table schema is unchanged
- The `gtag` function is already loaded in `layout.tsx` via Google Tag Manager script
