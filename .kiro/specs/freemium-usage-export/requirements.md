# Requirements Document

## Introduction

MC ChatMaster tracks free-tier user engagement in the `free_usage_tracking` PostgreSQL table (columns: `user_email`, `questions_used`, `created_at`, `last_question_at`). The business partner wants a simple way to see who started with free questions and how far they got — a report of free-tier user engagement and conversion funnel data.

This feature adds three capabilities:

1. **Backend API endpoint** to export free-tier usage data as CSV, callable via a local Python script (following the project's established API-based script pattern). The endpoint is admin-authenticated so only authorized users can pull the data.
2. **Wire existing frontend analytics events to Google Analytics** — the freemium system already emits DOM `CustomEvent`s (`warning_stage_change`, `upgrade_click`, `pql_qualified`, `newsletter_dismissed`, `newsletter_signup`) via `trackEvent()` in `frontend/utils/analytics.ts`, but these are not forwarded to the Google Analytics gtag (measurement ID: `G-EMLGMF3E5K`). This feature bridges that gap.
3. **Basic funnel statistics** included in the export — total free users, counts per warning stage reached, and conversion indicators.

**Out of scope:** Admin dashboard UI for viewing this data (partner prefers CSV export), real-time analytics dashboards, changes to the `free_usage_tracking` table schema, changes to the freemium gate logic itself.

## Glossary

- **Export_Endpoint**: The backend API endpoint (`/api/admin/freemium-export`) that queries the `free_usage_tracking` table and returns usage data in CSV or JSON format.
- **Free_Usage_Tracking_Table**: The existing PostgreSQL table with columns `id`, `user_email`, `questions_used`, `created_at`, `last_question_at` that stores per-email question counts for free-tier users.
- **Export_Script**: A local Python script that calls the Export_Endpoint via HTTP and saves the response to a file, following the project's API-based script pattern.
- **Analytics_Bridge**: The modification to `frontend/utils/analytics.ts` that forwards `CustomEvent` data to the Google Analytics gtag function in addition to emitting DOM events.
- **GA_Measurement_ID**: The Google Analytics 4 measurement ID `G-EMLGMF3E5K`, already configured in `frontend/app/layout.tsx`.
- **Freemium_Events**: The set of custom analytics events emitted by the freemium system: `warning_stage_change`, `upgrade_click`, `pql_qualified`, `newsletter_dismissed`, `newsletter_signup`.
- **Funnel_Summary**: An aggregated statistics section in the export that shows total free users, distribution by questions_used count, and counts of users who reached each warning stage threshold.
- **Admin_Auth**: The existing admin authentication system (`backend/auth_routes.py`) using JWT tokens, reused to protect the Export_Endpoint.
- **CSV_Format**: Comma-separated values format with a header row, used as the primary export format for partner sharing.

## Requirements

### Requirement 1: Freemium Usage Data Export Endpoint

**User Story:** As a product owner, I want a backend API endpoint that returns free-tier usage data from the database, so that I can share engagement reports with my business partner.

#### Acceptance Criteria

1. THE Export_Endpoint SHALL be accessible at `GET /api/admin/freemium-export`.
2. THE Export_Endpoint SHALL require Admin_Auth (existing admin JWT authentication) and return HTTP 401 for unauthenticated requests.
3. WHEN a valid authenticated request is made with `format=csv` (or no format parameter), THE Export_Endpoint SHALL return a CSV response with `Content-Type: text/csv` and a `Content-Disposition` header suggesting filename `freemium-usage-export-{YYYY-MM-DD}.csv`.
4. WHEN a valid authenticated request is made with `format=json`, THE Export_Endpoint SHALL return a JSON response with `Content-Type: application/json`.
5. THE CSV output SHALL include a header row with columns: `email`, `questions_used`, `first_seen`, `last_active`.
6. THE Export_Endpoint SHALL return one row per user from the Free_Usage_Tracking_Table, ordered by `questions_used` descending then `last_question_at` descending.
7. THE `first_seen` column SHALL map to the `created_at` column and the `last_active` column SHALL map to the `last_question_at` column from the Free_Usage_Tracking_Table, formatted as ISO 8601 timestamps.

### Requirement 2: Funnel Summary Statistics

**User Story:** As a product owner, I want the export to include summary statistics about the free-tier conversion funnel, so that my partner can quickly understand user engagement patterns without manual analysis.

#### Acceptance Criteria

1. WHEN the export format is JSON, THE Export_Endpoint SHALL include a `summary` object alongside the `users` array.
2. THE `summary` object SHALL include `total_free_users` (count of all rows in Free_Usage_Tracking_Table).
3. THE `summary` object SHALL include `reached_soft_warning` (count of users with `questions_used >= questions_limit - 2`), `reached_strong_warning` (count of users with `questions_used >= questions_limit - 1`), and `reached_limit` (count of users with `questions_used >= questions_limit`).
4. THE `summary` object SHALL include `average_questions_used` (mean of `questions_used` across all free-tier users, rounded to one decimal place).
5. WHEN the export format is CSV, THE Export_Endpoint SHALL append the summary as additional rows below the user data, separated by a blank row, with the format `# Summary`, `# total_free_users, {value}`, etc.
6. THE Export_Endpoint SHALL read the current `FREE_QUESTION_LIMIT` environment variable to compute warning stage thresholds for the summary.

### Requirement 3: Date Range Filtering

**User Story:** As a product owner, I want to filter the export by date range, so that I can pull reports for specific time periods.

#### Acceptance Criteria

1. THE Export_Endpoint SHALL accept optional `start_date` and `end_date` query parameters in ISO 8601 date format (`YYYY-MM-DD`).
2. WHEN `start_date` is provided, THE Export_Endpoint SHALL include only users whose `created_at` is on or after the start date.
3. WHEN `end_date` is provided, THE Export_Endpoint SHALL include only users whose `created_at` is on or before the end of that date (23:59:59).
4. WHEN both `start_date` and `end_date` are provided, THE Export_Endpoint SHALL include only users whose `created_at` falls within the inclusive range.
5. WHEN neither date parameter is provided, THE Export_Endpoint SHALL return all users.
6. IF `start_date` or `end_date` contains an invalid date format, THEN THE Export_Endpoint SHALL return HTTP 400 with a descriptive error message.

### Requirement 4: Local Export Script

**User Story:** As a developer, I want a local Python script that calls the export endpoint and saves the result to a file, so that I can quickly pull reports without using curl or a browser.

#### Acceptance Criteria

1. THE Export_Script SHALL be a standalone Python file at the project root named `export_freemium_usage.py`.
2. THE Export_Script SHALL authenticate against the backend using the admin login endpoint (`/api/admin/login`) with credentials from environment variables `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
3. THE Export_Script SHALL call the Export_Endpoint with the obtained JWT token in the Authorization header.
4. THE Export_Script SHALL accept optional command-line arguments for `--format` (csv or json, default csv), `--start-date`, `--end-date`, and `--output` (output file path).
5. WHEN no `--output` argument is provided, THE Export_Script SHALL save the file to the current directory with the name `freemium-usage-export-{YYYY-MM-DD}.{format}`.
6. THE Export_Script SHALL print a summary line to stdout indicating the number of users exported and the output file path.
7. IF authentication fails, THEN THE Export_Script SHALL print a descriptive error message and exit with a non-zero status code.

### Requirement 5: Wire Freemium Analytics Events to Google Analytics

**User Story:** As a product owner, I want the existing freemium custom events forwarded to Google Analytics, so that I can track conversion funnel metrics in GA4 without code changes to the components that emit events.

#### Acceptance Criteria

1. WHEN `trackEvent()` in `frontend/utils/analytics.ts` is called, THE Analytics_Bridge SHALL call `gtag('event', action, params)` with the event action and data parameters in addition to emitting the DOM `CustomEvent`.
2. THE Analytics_Bridge SHALL check that the `gtag` function exists on `window` before calling it, to avoid errors in environments where GA is not loaded.
3. THE Analytics_Bridge SHALL forward the following Freemium_Events to Google Analytics: `warning_stage_change`, `upgrade_click`, `pql_qualified`, `newsletter_dismissed`, `newsletter_signup`.
4. THE Analytics_Bridge SHALL pass the event data object as GA4 event parameters (e.g., `stage`, `questionsUsed`, `isPQL`, `sessionQuestionCount`).
5. THE Analytics_Bridge SHALL not block or delay the DOM `CustomEvent` emission if the `gtag` call fails.
6. IF the `gtag` function is not available on `window`, THEN THE Analytics_Bridge SHALL silently skip the GA call without logging errors in production.

### Requirement 6: GA Event Parameter Mapping

**User Story:** As a product owner, I want the GA events to include structured parameters, so that I can build meaningful reports and funnels in GA4.

#### Acceptance Criteria

1. WHEN a `warning_stage_change` event is forwarded to GA, THE Analytics_Bridge SHALL include parameters: `stage` (string), `questions_used` (number).
2. WHEN an `upgrade_click` event is forwarded to GA, THE Analytics_Bridge SHALL include parameters: `stage` (string), `is_pql` (boolean).
3. WHEN a `pql_qualified` event is forwarded to GA, THE Analytics_Bridge SHALL include parameter: `session_question_count` (number).
4. WHEN a `newsletter_dismissed` event is forwarded to GA, THE Analytics_Bridge SHALL include parameter: `questions_used` (number).
5. WHEN a `newsletter_signup` event is forwarded to GA, THE Analytics_Bridge SHALL include parameter: `questions_used` (number).
6. THE Analytics_Bridge SHALL convert parameter names from camelCase to snake_case for GA4 compatibility (e.g., `questionsUsed` becomes `questions_used`, `isPQL` becomes `is_pql`).

### Requirement 7: TypeScript Type Safety for gtag

**User Story:** As a developer, I want the gtag integration to be type-safe, so that the build does not produce type errors and the code is maintainable.

#### Acceptance Criteria

1. THE Analytics_Bridge SHALL declare the `gtag` function type on the `window` object using a TypeScript declaration (either inline or in a `.d.ts` file).
2. THE type declaration SHALL define `gtag` as an optional function accepting `(command: string, action: string, params?: Record<string, string | number | boolean>)`.
3. THE Analytics_Bridge SHALL not require any new npm dependencies for the gtag integration.
