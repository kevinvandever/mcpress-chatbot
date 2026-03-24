# Implementation Plan: Freemium Usage Gate (Registration-Required)

## Overview

Rework the freemium usage gate from anonymous fingerprint-based tracking to registration-required email-based tracking. The login flow is modified so users without an Appstle subscription receive a `"free"` session token instead of being denied. The `UsageGate` tracks questions per user email in PostgreSQL. The `/chat` endpoint requires authentication and applies the usage gate only for `"free"` users. All anonymous fingerprint code is removed. Frontend components are updated to use `subscriptionStatus` instead of `isAuthenticated`/`fingerprint`.

## Tasks

- [x] 1. Modify the login flow to allow free-tier users
  - [x] 1.1 Modify `SubscriptionAuthService.login()` in `backend/subscription_auth.py`
    - Change step 4: instead of returning 403 when subscription is not active, determine `subscription_status` as `"active"` or `"free"`
    - Continue to password check (steps 5-7) regardless of subscription status
    - Pass `subscription_status` to `create_token()` in step 8 (instead of hardcoded `"active"`)
    - Update `LoginSuccessResponse` to use the determined `subscription_status`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.2 Modify `SubscriptionAuthService.refresh()` in `backend/subscription_auth.py`
    - On refresh, re-check Appstle subscription status
    - If now active → issue token with `subscription_status="active"`
    - If still not active → issue token with `subscription_status="free"` (instead of returning 403)
    - _Requirements: 2.4, 4.3_

  - [ ]* 1.3 Write property test: login flow subscription status
    - **Property 1: Login issues correct subscription_status based on Appstle response**
    - Active subscription → `subscription_status="active"`, no subscription → `subscription_status="free"`
    - **Validates: Requirements 2.1, 2.3, 2.4**

- [x] 2. Migrate UsageGate from fingerprint to email-based tracking
  - [x] 2.1 Modify `backend/usage_gate.py` table creation
    - Change `init()` to drop the old `free_usage_tracking` table (if it has `fingerprint` column) and recreate with `user_email` column
    - Table: `id` (serial PK), `user_email` (varchar 255, unique, not null), `questions_used` (integer, default 0), `created_at` (timestamp), `last_question_at` (timestamp)
    - Index: `idx_free_usage_tracking_email` on `user_email`
    - _Requirements: 9.1, 9.2_

  - [x] 2.2 Rename `check_and_increment` to `check_usage` and change parameter from `fingerprint` to `user_email`
    - Query: `SELECT questions_used FROM free_usage_tracking WHERE user_email = $1`
    - Logic unchanged: if `questions_used >= limit` → denied, else → allowed
    - _Requirements: 3.1, 3.4_

  - [x] 2.3 Modify `record_question` to accept `user_email` instead of `fingerprint`
    - Upsert: `INSERT INTO free_usage_tracking (user_email, ...) ON CONFLICT (user_email) DO UPDATE ...`
    - _Requirements: 3.2, 3.3, 9.3_

  - [ ]* 2.4 Write property test: usage gate email-based tracking
    - **Property 2: Usage gate correctly allows/denies based on email question count**
    - **Validates: Requirements 3.1, 3.4**

- [x] 3. Modify the `/chat` endpoint for auth-required usage gate
  - [x] 3.1 Remove anonymous path from `chat()` in `backend/main.py`
    - Remove `X-Anonymous-Id` header reading and UUID generation
    - Remove `fingerprint` variable and anonymous user_id assignment
    - Remove `X-Anonymous-Id` from response headers
    - Remove `X-Anonymous-Id` from CORS `expose_headers`
    - _Requirements: 10.1_

  - [x] 3.2 Implement auth-required usage gate in `chat()` endpoint
    - Verify `session_token` cookie → if missing or invalid, return 401
    - Read `subscription_status` from JWT claims (default to `"free"`)
    - If `subscription_status == "active"` → skip usage gate entirely
    - If `subscription_status == "free"` → call `usage_gate.check_usage(email)`, return 402 if denied
    - _Requirements: 3.4, 4.1, 4.2, 5.2_

  - [x] 3.3 Update SSE streaming generator for email-based tracking
    - After first content chunk, call `usage_gate.record_question(email)` for free-tier users only
    - Inject `usage` dict into metadata SSE event for free-tier users
    - Omit `usage` from metadata for subscribed users
    - _Requirements: 3.2, 3.3, 3.5, 8.1, 8.2_

  - [ ]* 3.4 Write property test: authenticated subscribers bypass usage gate
    - **Property 3: Requests with subscription_status="active" never trigger usage gate**
    - **Validates: Requirements 4.1, 4.2, 8.2**

- [x] 4. Checkpoint — verify backend changes work
  - Deploy to staging, test login with non-subscriber email, verify "free" token is issued, verify usage gate tracks by email

- [x] 5. Remove anonymous access and fingerprint code from frontend
  - [x] 5.1 Restore login-required middleware in `frontend/middleware.ts`
    - Remove the `pathname === '/'` bypass that allows unauthenticated access to root
    - Root path `/` should redirect to `/login` when no `session_token` cookie is present
    - _Requirements: 5.1, 5.2, 10.3_

  - [x] 5.2 Delete `frontend/utils/anonymousId.ts`
    - Remove the fingerprint generation utility entirely
    - _Requirements: 10.2_

  - [x] 5.3 Update `frontend/app/page.tsx`
    - Remove `fingerprint` state and `getOrCreateAnonymousId()` call
    - Remove `isAuthenticated` state — user is always authenticated if they reach this page
    - Read `subscription_status` from `/api/auth/me` response and store in state
    - Pass `subscriptionStatus` prop to `ChatInterface` (instead of `isAuthenticated` and `fingerprint`)
    - Restore redirect to `/login` on 401 from `/api/auth/me`
    - _Requirements: 5.1, 6.4, 10.2, 10.3_

  - [x] 5.4 Update `frontend/components/ChatInterface.tsx`
    - Replace `isAuthenticated` and `fingerprint` props with `subscriptionStatus?: string`
    - Remove `X-Anonymous-Id` header from `sendMessage()` fetch request
    - Parse `usage` from metadata SSE event when `subscriptionStatus === "free"`
    - Handle 402 response → set `showPaywall = true`
    - Show `RemainingQuestionsBanner` when `subscriptionStatus === "free"` and usage data available
    - Hide banner when `subscriptionStatus === "active"`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.5, 10.1, 10.2_

- [x] 6. Update PaywallOverlay with kind messaging
  - [x] 6.1 Modify `frontend/components/PaywallOverlay.tsx`
    - Update message to: "We hope you've enjoyed exploring MC ChatMaster! To continue asking questions, subscribe to get unlimited access."
    - "Subscribe Now" button opens `signupUrl` in new tab
    - "Already subscribed? Sign in" link navigates to `/login`
    - Ensure overlay sits above input area, not over message list
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 7. Update RemainingQuestionsBanner integration
  - [x] 7.1 Modify `RemainingQuestionsBanner` integration in `ChatInterface.tsx`
    - Show when `subscriptionStatus === "free"` and `remainingQuestions` is not null (instead of `isAuthenticated === false`)
    - Hide when `subscriptionStatus === "active"`
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 8. Update login page for free-tier handling
  - [x] 8.1 Modify `frontend/app/login/page.tsx` (or equivalent)
    - On successful login (200 response), redirect to `/` regardless of `subscription_status`
    - Remove or update error handling for 403 "No subscription found" — this case no longer occurs for normal login
    - Handle `subscription_status: "free"` in the success response gracefully
    - _Requirements: 5.3, 5.4_

- [x] 9. Checkpoint — verify frontend changes work end-to-end
  - Deploy to staging, test full flow: login without subscription → chat with free questions → hit limit → paywall → subscribe link

- [x] 10. Final integration checkpoint
  - Verify subscribed users still have unlimited access
  - Verify free-tier users see banner and hit paywall at limit
  - Verify login page works for both new and existing users
  - Verify environment variables (`FREE_QUESTION_LIMIT`, `SUBSCRIPTION_SIGNUP_URL`) are respected

## Notes

- Tasks marked with `*` are optional property tests
- The existing `UsageGate`, `RemainingQuestionsBanner`, and `PaywallOverlay` are being MODIFIED, not created from scratch
- All backend testing must be done on Railway after deployment (no local testing)
- Frontend deploys to Netlify; backend deploys to Railway
- The `free_usage_tracking` table migration drops old fingerprint data — this is acceptable since the feature was only on staging
- The subscription_auth.py `login()` change is the most critical backend modification
