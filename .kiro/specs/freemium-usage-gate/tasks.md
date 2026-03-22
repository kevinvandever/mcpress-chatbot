# Implementation Plan: Freemium Usage Gate

## Overview

Transform MC ChatMaster from a login-required application into a freemium product. Backend changes add a `UsageGate` class in Python/FastAPI that tracks anonymous question counts in PostgreSQL and enforces a configurable limit. Frontend changes (Next.js/TypeScript) remove the login redirect, add anonymous fingerprint handling, display remaining question counts, and show a paywall overlay when the limit is reached. The existing `/chat` endpoint is modified to detect auth via `session_token` cookie and route to either the authenticated (unlimited) or anonymous (gated) path.

## Tasks

- [x] 1. Create the `UsageGate` backend module with Pydantic models and env config
  - [x] 1.1 Create `backend/usage_gate.py` with `UsageInfo` and `UsageResult` Pydantic models
    - `UsageInfo`: `questions_used` (int), `questions_limit` (int), `questions_remaining` (int)
    - `UsageResult`: `allowed` (bool), `usage` (UsageInfo), `signup_url` (Optional[str])
    - _Requirements: 7.1_

  - [x] 1.2 Implement `UsageGate.__init__` and `_read_limit` method
    - Read `FREE_QUESTION_LIMIT` from `os.getenv`, default to 5
    - Log warning and default to 5 if value is non-integer
    - Support `FREE_QUESTION_LIMIT=0` to require subscription for all anonymous requests
    - Store `database_url` and initialize `pool = None`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.3 Implement `UsageGate.init` method for DB setup
    - Create `asyncpg` connection pool from `database_url`
    - Execute `CREATE TABLE IF NOT EXISTS free_usage_tracking` with columns: `id` (serial PK), `fingerprint` (varchar 255, unique, not null), `questions_used` (integer, default 0), `created_at` (timestamp, default now), `last_question_at` (timestamp, default now)
    - Execute `CREATE INDEX IF NOT EXISTS idx_free_usage_tracking_fingerprint ON free_usage_tracking (fingerprint)`
    - _Requirements: 8.1, 8.2_

  - [x] 1.4 Implement `UsageGate.check_and_increment` method
    - Accept `fingerprint: str`, query `SELECT questions_used FROM free_usage_tracking WHERE fingerprint = $1`
    - If no row found, treat as 0 questions used
    - If `questions_used >= free_question_limit`, return `UsageResult(allowed=False, ...)` with `signup_url` from `SUBSCRIPTION_SIGNUP_URL` env var
    - If under limit, return `UsageResult(allowed=True, ...)` with current counts
    - _Requirements: 3.1, 3.4, 2.3_

  - [x] 1.5 Implement `UsageGate.record_question` method
    - Accept `fingerprint: str`, execute upsert: `INSERT INTO free_usage_tracking (fingerprint, questions_used, last_question_at) VALUES ($1, 1, CURRENT_TIMESTAMP) ON CONFLICT (fingerprint) DO UPDATE SET questions_used = free_usage_tracking.questions_used + 1, last_question_at = CURRENT_TIMESTAMP RETURNING questions_used`
    - Return `UsageInfo` with updated counts
    - _Requirements: 3.2, 3.3, 8.3_

  - [ ]* 1.6 Write property test: env variable parsing
    - **Property 1: FREE_QUESTION_LIMIT parsing**
    - Generate random integer strings, non-integer strings, empty strings, and "0" — verify `_read_limit` returns correct integer or default 5
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [ ]* 1.7 Write property test: check_and_increment correctness
    - **Property 2: Usage gate allows requests under limit and denies at/above limit**
    - For a given limit N and questions_used M, verify `allowed=True` when M < N and `allowed=False` when M >= N
    - **Validates: Requirements 3.1, 3.4**


- [x] 2. Modify the `/chat` endpoint in `main.py` for auth detection and usage gate integration
  - [x] 2.1 Add usage gate initialization to `main.py` startup
    - Import `UsageGate` from `usage_gate` (with try/except Railway vs local import pattern)
    - Create module-level `usage_gate = None` variable
    - In `startup_event`, if `DATABASE_URL` is set, instantiate `UsageGate(database_url)` and call `await usage_gate.init()`
    - _Requirements: 8.2_

  - [x] 2.2 Add `uuid` import and modify the `chat()` endpoint signature
    - Add `import uuid` at top of `main.py`
    - Add `request: Request` parameter to the `chat()` function to access cookies and headers
    - Import `JSONResponse` from `fastapi.responses` if not already imported
    - _Requirements: 2.1, 2.2_

  - [x] 2.3 Implement auth detection and anonymous path in `chat()` endpoint
    - Check `request.cookies.get("session_token")` — if present, verify via `subscription_auth_service.verify_token(session_token, allow_grace=False)` (wrap in try/except)
    - If valid token → `is_authenticated = True`, extract `user_id` from claims
    - If no valid token → read `X-Anonymous-Id` header, or generate `str(uuid.uuid4())` if missing
    - Call `usage_gate.check_and_increment(fingerprint)` — if denied, return `JSONResponse(status_code=402, content={...}, headers={"X-Anonymous-Id": fingerprint})`
    - If allowed, set `user_id = f"anon:{fingerprint}"`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.4, 4.1, 4.2, 4.3_

  - [x] 2.4 Modify the SSE streaming generator for usage tracking
    - After first successful `content` chunk, call `await usage_gate.record_question(fingerprint)` (only for anonymous users, only once)
    - Inject `usage` dict into the `metadata` SSE event for anonymous users (from `UsageInfo.model_dump()`)
    - Omit `usage` from metadata for authenticated users
    - Add `X-Anonymous-Id` response header when fingerprint is present
    - _Requirements: 3.2, 3.3, 3.5, 7.1, 7.2, 7.3_

  - [ ]* 2.5 Write property test: authenticated users bypass usage gate
    - **Property 3: Authenticated requests skip usage gate entirely**
    - Verify that requests with a valid `session_token` cookie never trigger `check_and_increment` or `record_question`, and no `usage` object appears in metadata
    - **Validates: Requirements 4.1, 4.2, 7.2**

  - [ ]* 2.6 Write property test: 402 response structure
    - **Property 4: HTTP 402 response contains required fields**
    - When limit is reached, verify response has `error`, `signup_url`, and `usage` object with correct counts
    - **Validates: Requirements 3.4, 7.1**

- [x] 3. Checkpoint - Ensure backend usage gate works
  - Ensure all tests pass, ask the user if questions arise.


- [x] 4. Create the fingerprint utility and update frontend for anonymous access
  - [x] 4.1 Create `frontend/utils/anonymousId.ts`
    - Export `getOrCreateAnonymousId(): string` — reads `anonymousUserId` from localStorage, generates `crypto.randomUUID()` if missing, persists and returns it
    - Handle SSR (`typeof window === 'undefined'`) by returning empty string
    - _Requirements: 2.5, 5.2_

  - [x] 4.2 Modify `frontend/app/page.tsx` to allow anonymous access
    - Remove the `router.replace('/login')` redirect on 401 from `/api/auth/me`
    - Add `isAuthenticated` state (boolean, default false) — set true on 200, false on 401
    - When not authenticated: hide History button, Logout button, and `userEmail` display
    - When not authenticated: show a "Sign In" link in the header that navigates to `/login`
    - Call `getOrCreateAnonymousId()` and store in state as `fingerprint`
    - Pass `isAuthenticated` and `fingerprint` as props to `ChatInterface`
    - _Requirements: 5.1, 9.1, 9.2, 9.3, 9.4_

  - [x] 4.3 Update `ChatInterfaceProps` interface in `ChatInterface.tsx`
    - Add `isAuthenticated?: boolean` and `fingerprint?: string | null` props
    - Add component state: `remainingQuestions` (number | null), `questionsLimit` (number | null), `showPaywall` (boolean), `signupUrl` (string)
    - _Requirements: 5.3, 5.4, 6.1_

  - [x] 4.4 Modify `sendMessage()` in `ChatInterface.tsx` for anonymous flow
    - If not authenticated, add `X-Anonymous-Id` header to the fetch request using the `fingerprint` prop
    - Handle HTTP 402 response: parse JSON body, set `showPaywall = true`, store `signupUrl` from response
    - Parse `usage` from the `metadata` SSE event — update `remainingQuestions` and `questionsLimit` state
    - When `showPaywall` is true, disable the input field and send button
    - _Requirements: 2.2, 5.3, 6.1, 6.5_

  - [ ]* 4.5 Write unit test: fingerprint generation and persistence
    - Verify `getOrCreateAnonymousId()` returns a UUID string, persists to localStorage, and returns the same value on subsequent calls
    - **Validates: Requirements 2.5, 2.6**

- [x] 5. Create the `RemainingQuestionsBanner` component
  - [x] 5.1 Create `frontend/components/RemainingQuestionsBanner.tsx`
    - Accept props: `questionsUsed: number`, `questionsLimit: number`
    - Normal state: display "X of Y free questions remaining" in a subtle info-styled banner
    - Warning state (1 remaining): display "Last free question!" in a warning-styled banner (amber/yellow)
    - Use Tailwind CSS classes consistent with existing MC Press design
    - _Requirements: 5.4, 5.5_

  - [x] 5.2 Integrate `RemainingQuestionsBanner` into `ChatInterface.tsx`
    - Render above the input area when `isAuthenticated` is false and `remainingQuestions` is not null
    - Hide when `isAuthenticated` is true
    - _Requirements: 5.4, 5.5_


- [x] 6. Create the `PaywallOverlay` component
  - [x] 6.1 Create `frontend/components/PaywallOverlay.tsx`
    - Accept props: `signupUrl: string`, `onSignIn: () => void`
    - Display message: "You've used all your free questions. Subscribe to continue chatting."
    - "Subscribe Now" button that opens `signupUrl` in a new tab (`window.open(signupUrl, '_blank')`)
    - "Sign In" link that calls `onSignIn` (navigates to `/login`)
    - Position overlay above the input area, not over the message list (previous messages remain visible)
    - Use Tailwind CSS consistent with MC Press brand colors
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_

  - [x] 6.2 Integrate `PaywallOverlay` into `ChatInterface.tsx`
    - Render when `showPaywall` is true
    - Pass `signupUrl` from state and `onSignIn` handler that uses `router.push('/login')`
    - Ensure chat input and send button are disabled while paywall is shown
    - _Requirements: 6.1, 6.5, 6.6_

- [x] 7. Checkpoint - Ensure frontend anonymous flow works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Wire everything together and add environment variable documentation
  - [x] 8.1 Add `FREE_QUESTION_LIMIT` and `SUBSCRIPTION_SIGNUP_URL` to `.env.example` and `backend/.env.example`
    - Add comments explaining defaults and purpose
    - _Requirements: 1.1, 1.2_

  - [x] 8.2 Verify `X-Anonymous-Id` header is exposed through CORS
    - In `main.py` CORS middleware config, ensure `expose_headers` includes `X-Anonymous-Id` so the frontend can read it from the response
    - _Requirements: 7.3_

  - [ ]* 8.3 Write property test: question counter increment only on success
    - **Property 5: Counter increments only after successful stream start**
    - Verify that if the SSE stream fails before the first content chunk, the question counter is not incremented
    - **Validates: Requirements 3.3**

  - [ ]* 8.4 Write property test: upsert handles concurrent requests safely
    - **Property 6: Concurrent upserts for same fingerprint produce correct count**
    - Simulate concurrent `record_question` calls for the same fingerprint, verify final `questions_used` equals the number of calls
    - **Validates: Requirements 8.3**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All backend testing must be done on Railway after deployment (no local testing)
- Frontend deploys to Netlify; backend deploys to Railway
- The subscription auth cookie verification follows the existing pattern in `subscription_auth_routes.py`
- The `UsageGate` uses `asyncpg` connection pooling consistent with the rest of the backend
