# Implementation Tasks: Appstle Subscription Authentication

## Task 1: Create SubscriptionAuthService backend module

- [x] Create `backend/subscription_auth.py` with the `SubscriptionAuthService` class
- [x] Implement `__init__` reading `APPSTLE_API_URL`, `APPSTLE_API_KEY`, `JWT_SECRET_KEY`, `SUBSCRIPTION_SIGNUP_URL` from environment
- [x] Implement `verify_subscription(email)` — async method that calls the Appstle API at `GET {APPSTLE_API_URL}/api/external/v2/subscription-contract-details/customers?email={email}` with `X-API-Key` header, 10-second timeout, and returns parsed `AppstleSubscriptionResponse`
- [x] Implement `create_token(email, subscription_status, expires_at)` — creates a JWT with claims: `sub`, `subscription_status`, `subscription_expires_at`, `iat`, `exp` (1 hour from `iat`)
- [x] Implement `verify_token(token, allow_grace=False)` — decodes and verifies JWT; when `allow_grace=True`, accepts tokens expired within 5 minutes
- [x] Implement `login(email, client_ip)` — full login flow: check rate limit → call Appstle API → return success with token or denial with status-specific message and redirect URL (email-only, no password)
- [x] Implement `refresh(token)` — verify token with grace window → re-verify subscription with Appstle → issue new token or return 403
- [x] Define Pydantic models: `CustomerLoginRequest`, `AppstleSubscriptionResponse`, `LoginSuccessResponse`, `LoginDeniedResponse`, `RefreshResponse`
- [x] Implement status-specific denial messages: "Your subscription has expired", "Your subscription is paused", "Your subscription has been cancelled", "No subscription found"
- [x] Handle Appstle API errors: non-200 → 503, timeout → 503, malformed response → 500, missing config → 503 with startup warning log
- [x] Instantiate a `RateLimiter` (from existing `backend/auth.py`) for customer login: 5 attempts per IP per 15 minutes, reset on success

**Requirements**: 1, 2, 3, 6, 8, 9
**Design ref**: Components 1 (SubscriptionAuthService), Data Models, Error Handling

## Task 2: Create subscription auth API routes

- [x] Create `backend/subscription_auth_routes.py` with a FastAPI `APIRouter(prefix="/api/auth", tags=["customer-auth"])`
- [x] Implement `POST /api/auth/login` — accepts `CustomerLoginRequest`, extracts client IP from `Request`, calls `SubscriptionAuthService.login()`, sets `session_token` HTTP-only cookie on success (httponly=True, secure=True, samesite=lax, path=/, max_age=3600), returns appropriate JSON response
- [x] Implement `POST /api/auth/logout` — clears the `session_token` cookie by setting max_age=0
- [x] Implement `POST /api/auth/refresh` — reads `session_token` from cookie, calls `SubscriptionAuthService.refresh()`, sets new cookie on success, returns 401 or 403 on failure
- [x] Implement `GET /api/auth/me` — reads `session_token` from cookie, verifies token, returns user email and subscription status

**Requirements**: 1, 3, 5
**Design ref**: Components 2 (SubscriptionAuthRoutes), Cookie Configuration

## Task 3: Register subscription auth routes in main.py

- [x] Add import block in `backend/main.py` for `subscription_auth_routes` (with Railway/local import fallback pattern matching existing code)
- [x] Register the router with `app.include_router(subscription_auth_router)`
- [x] Add startup log message: "✅ Subscription auth endpoints enabled at /api/auth/*"
- [x] Verify existing admin auth router (`/api/admin/*`) is not affected

**Requirements**: 7
**Design ref**: Admin Auth Isolation

## Task 4: Update environment configuration

- [x] Add `APPSTLE_API_URL`, `APPSTLE_API_KEY`, `SUBSCRIPTION_SIGNUP_URL` to `.env.example` with placeholder values and comments
- [x] Add `JWT_SECRET_KEY` to `.env.example` if not already present (it's used by existing admin auth too)
- [x] Add the same variables to `.env.railway` template if it exists

**Requirements**: 8
**Design ref**: Environment Variables table

## Task 5: Update frontend login page with email-only form

- [x] Rewrite `frontend/app/login/page.tsx` to accept email only (no password — Appstle checks subscription by email)
- [x] On submit, POST to `/api/auth/login` with `{email}`
- [x] On 200 success: redirect to `/` with `router.push('/')` and `router.refresh()`
- [x] On 401: display "Invalid email or password" error
- [x] On 403 (subscription issue): display status-specific message from response (`error` field) and show "Subscribe Now" button linking to `redirect_url` from response (opens in new tab)
- [x] On 429: display "Too many login attempts. Please try again later."
- [x] On 503: display "Subscription service temporarily unavailable. Please try again later."
- [x] Show loading spinner while API call is in progress
- [x] If user already has a valid `session_token` cookie (check via `/api/auth/me`), redirect to `/` immediately

**Requirements**: 1, 4, 10
**Design ref**: Components 4 (Login Page), Error Handling tables

## Task 6: Create frontend Next.js API proxy routes

- [x] Rewrite `frontend/app/api/auth/login/route.ts` to proxy POST requests to Railway backend `{VITE_API_URL}/api/auth/login`, forward the response body, and copy the `Set-Cookie` header from the backend response (or set the cookie from the response JSON)
- [x] Create `frontend/app/api/auth/logout/route.ts` — clears the `session_token` cookie (set max_age=0) and returns success
- [x] Create `frontend/app/api/auth/refresh/route.ts` — proxies POST to Railway backend `{VITE_API_URL}/api/auth/refresh`, forwards the `session_token` cookie, copies the new `Set-Cookie` header back
- [x] Create `frontend/app/api/auth/me/route.ts` — proxies GET to Railway backend `{VITE_API_URL}/api/auth/me`, forwards the `session_token` cookie

**Requirements**: 3, 4
**Design ref**: Components 5 (Next.js API Routes)

## Task 7: Update Next.js middleware for cookie-based auth

- [x] Update `frontend/middleware.ts` to check for `session_token` cookie on protected routes
- [x] Protected routes: everything except `/login`, `/admin/*`, `/api/*`, and static assets
- [x] If `session_token` cookie is missing on a protected route → redirect to `/login`
- [x] If `session_token` cookie exists on `/login` → redirect to `/` (authenticated user bypass)
- [x] Admin routes (`/admin/*`) remain unchanged — they continue using the existing `adminToken` localStorage check on the client side
- [x] Keep the existing matcher config for static asset exclusion

**Requirements**: 4, 7
**Design ref**: Components 3 (Next.js Middleware)

## Task 8: Update chat page to use cookie-based auth and add logout

- [x] Update `frontend/app/page.tsx` to remove the `adminToken` localStorage check for customer auth
- [x] The middleware now handles redirecting unauthenticated users, so the client-side redirect to `/admin/login` should be removed
- [x] Update the logout button handler to call `POST /api/auth/logout` (which clears the cookie), then redirect to `/login`
- [x] Optionally fetch user info from `/api/auth/me` to display the user's email in the header

**Requirements**: 4, 5
**Design ref**: Architecture (High-Level Flow)

## Task 9: Implement silent token refresh on the frontend

- [x] Create a `useAuthRefresh` hook (or add logic to the main page layout) that:
  - On mount, calls `GET /api/auth/me` to get token expiry info
  - Sets a timer to call `POST /api/auth/refresh` ~5 minutes before token expiry (i.e., at ~55 minutes)
  - On successful refresh: resets the timer for the new token
  - On 403 (subscription no longer active): clears cookie, redirects to `/login` with a message
  - On 401 (token too expired): redirects to `/login`
- [x] Integrate the hook into the root layout or the chat page so it runs for all authenticated pages

**Requirements**: 3 (criteria 8-11), 4
**Design ref**: Token Refresh Flow, Error Recovery Strategy

## Task 10: Backend unit and property-based tests

- [x] Create `backend/test_subscription_auth.py` with pytest + Hypothesis tests
- [x] Implement Property 1 test: Token structure completeness — for any email and expiration date, `create_token` produces a JWT containing all required claims (`sub`, `subscription_status`, `subscription_expires_at`, `iat`, `exp`)
- [x] Implement Property 2 test: Token expiration window — for any issued JWT, `exp` is exactly 3600 seconds after `iat`
- [x] Implement Property 3 test: Token verification round-trip — tokens created by `create_token` are accepted by `verify_token`; tokens with tampered signatures or expired beyond grace window are rejected
- [x] Implement Property 4 test: Cookie security attributes — mock a successful login request and verify the response sets cookie with `httponly=True`, `secure=True`, `samesite=lax`, `path=/`
- [x] Implement Property 5 test: Non-active subscription denial — for any status in `["cancelled", "expired", "paused", "not_found", "unknown", ""]`, login returns denial with redirect URL
- [x] Implement Property 6 test: Active subscription grants access — mock Appstle returning active status, verify login returns success with valid JWT
- [x] Implement Property 7 test: Grace window acceptance — tokens expired within 5 minutes are accepted by `verify_token(allow_grace=True)`; tokens expired beyond 5 minutes are rejected
- [x] Implement Property 8 test: Refresh with active subscription — mock Appstle active, verify refresh issues new token with fresh 1-hour expiry
- [x] Implement Property 9 test: Refresh with inactive subscription — mock Appstle inactive, verify refresh returns 403 with redirect URL
- [x] Implement Property 12 test: Rate limiting enforcement — simulate 5 failed attempts, verify 6th returns 429
- [x] Implement Property 13 test: Rate limiting reset — after failed attempts, a successful login resets the counter
- [x] Implement Property 14 test: Disabled configuration — when `APPSTLE_API_URL` or `APPSTLE_API_KEY` is missing, login returns 503
- [x] Implement Property 15 test: Appstle API errors — mock non-200 responses and timeouts, verify 503 returned
- [x] Implement Property 16 test: Status-specific denial messages — verify each status maps to its correct user-facing message
- [x] Add admin auth isolation test: verify `POST /api/admin/login` still works independently of customer auth
- [x] Use `@settings(max_examples=100)` for all Hypothesis property tests
- [x] Tag each test with comment: `# Feature: appstle-subscription-auth, Property {N}: {description}`

**Requirements**: All (validation)
**Design ref**: Testing Strategy, Correctness Properties 1-16

## Task 11: Frontend tests

- [x] Create `frontend/components/__tests__/LoginPage.test.tsx` (or equivalent test file)
- [x] Test login page renders email and password input fields
- [x] Test login page shows "Invalid email or password" on 401 response
- [x] Test login page shows subscription-required message with "Subscribe Now" button on 403 response
- [x] Test login page shows correct status-specific messages (expired, paused, cancelled, not found)
- [x] Test "Subscribe Now" button links to the `redirect_url` from the response and opens in new tab
- [x] Test login page shows rate limit message on 429 response
- [x] Test login page shows service unavailable message on 503 response
- [x] Test login page shows loading spinner during API call
- [x] Test login page redirects to `/` when user already has valid session (via `/api/auth/me` returning 200)
- [x] Test middleware redirects unauthenticated users (no `session_token` cookie) to `/login`
- [x] Test middleware allows authenticated users (with `session_token` cookie) through to protected routes
- [x] Test middleware redirects authenticated users away from `/login` to `/`
- [x] Test logout clears cookie and redirects to `/login`

**Requirements**: 4, 5, 10 (validation)
**Design ref**: Testing Strategy — Frontend Tests

## Task 12: Deploy and verify on Railway

- [x] Commit all backend changes and push to `main` to trigger Railway deployment
- [ ] Wait for deployment to complete (~10-15 minutes)
- [ ] Set `APPSTLE_API_URL`, `APPSTLE_API_KEY`, `SUBSCRIPTION_SIGNUP_URL`, and `JWT_SECRET_KEY` environment variables in Railway dashboard
- [ ] Verify `GET /health` still works
- [ ] Test `POST /api/auth/login` with valid Appstle credentials via curl
- [ ] Test `POST /api/auth/login` with invalid credentials (expect 401)
- [ ] Test `POST /api/auth/refresh` with a valid session cookie
- [ ] Test `POST /api/auth/logout`
- [ ] Test `GET /api/auth/me` with a valid session cookie
- [ ] Verify `POST /api/admin/login` still works unchanged (admin auth isolation)
- [ ] Commit frontend changes and push to trigger Netlify deployment
- [ ] Verify login page renders with email + password fields
- [ ] Verify full login → chat → logout flow in browser
- [ ] Verify middleware redirects unauthenticated users to `/login`
- [ ] Verify silent refresh fires before token expiry

**Requirements**: All
**Design ref**: Testing Strategy
