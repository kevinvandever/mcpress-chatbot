# Implementation Plan: Freemium Usage Gate v2 — Progressive Warnings & Conversion Optimization

## Overview

This plan implements the v2 freemium usage gate enhancements: raising the free question limit default to 8, adding a progressive warning system with stage-specific copy, updating the paywall overlay with new pricing and PQL support, adding newsletter capture, and wiring analytics event emission. The backend change is minimal (one default value). The bulk of the work is frontend: new utility functions, new components, and updates to existing components.

All warning stage thresholds are derived from `questions_limit` (never hardcoded to 8). PQL detection and newsletter dismissal are session-scoped in-memory state. Analytics uses a simple `trackEvent()` callback pattern with CustomEvent emission.

## Tasks

- [x] 1. Backend: Update free question limit default
  - [x] 1.1 Change `_read_limit()` default from 5 to 8 in `backend/usage_gate.py`
    - Update the two `return 5` statements to `return 8` (unset env var case and invalid value case)
    - Update the docstring to say "Default 8"
    - Update the warning log message to say "defaulting to 8"
    - _Requirements: 1.1, 1.3_

  - [ ]* 1.2 Write property tests for `_read_limit()` using Hypothesis
    - Create `backend/test_usage_gate_v2.py`
    - **Property 1: Valid integer passthrough** — for any valid integer string, `_read_limit()` returns that integer
    - **Validates: Requirements 1.2**
    - **Property 2: Non-integer default** — for any non-integer string, `_read_limit()` returns 8
    - **Validates: Requirements 1.3**
    - Include example-based tests: env var unset returns 8 (Req 1.1), env var "0" returns 0 (Req 1.4)

- [x] 2. Frontend: Create warning stage utility and analytics utility
  - [x] 2.1 Create `frontend/utils/warningStage.ts`
    - Export `WarningStage` type: `'silent' | 'soft' | 'stronger' | 'upgrade' | 'hardGate'`
    - Export `getWarningStage(questionsUsed: number, questionsLimit: number): WarningStage` pure function
    - Logic: `silent` when `used < limit - 2`, `soft` when `used === limit - 2`, `stronger` when `used === limit - 1`, `upgrade` when `used === limit`, `hardGate` when `used > limit`
    - No hardcoded thresholds — all derived from `questionsLimit`
    - _Requirements: 12.2, 12.3, 12.4_

  - [x] 2.2 Create `frontend/utils/analytics.ts`
    - Export `trackEvent(action: string, data?: Record<string, string | number | boolean>): void`
    - Emit a `CustomEvent('mc_analytics', { detail: { action, ...data, timestamp } })` on `window`
    - Console log in development mode only
    - Wrap in try/catch so analytics failures never break the app
    - _Requirements: 11.1, 11.5_

  - [ ]* 2.3 Write property tests for `getWarningStage()` using fast-check
    - Create `frontend/__tests__/warningStage.property.test.ts`
    - **Property 3: Warning stage computation correctness** — for any `(questionsUsed, questionsLimit)` with `questionsLimit >= 3`, verify the correct stage is returned per the five-stage mapping
    - **Validates: Requirements 2.1, 3.1, 4.1, 5.2, 12.2, 12.3, 12.4**
    - **Property 4: PQL threshold detection** — for any non-negative `sessionQuestionCount`, PQL is true iff `count >= 3`
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 2.4 Write unit tests for `getWarningStage()` and `trackEvent()`
    - Create `frontend/__tests__/warningStage.test.ts` with example-based tests for each stage boundary
    - Create `frontend/__tests__/analytics.test.ts` verifying CustomEvent dispatch and payload structure
    - _Requirements: 11.1, 11.5, 12.2_

- [x] 3. Frontend: Create ProgressiveWarningBanner component
  - [x] 3.1 Create `frontend/components/ProgressiveWarningBanner.tsx`
    - Props: `questionsUsed`, `questionsLimit`, `isPQL`, `signupUrl`, `onUpgradeClick`
    - Use `getWarningStage()` to determine which stage to render
    - `silent` → return `null`
    - `soft` → blue/neutral info banner with copy: "You've used {used} of your {limit} free MC ChatMaster questions. You still have {remaining} left to explore the MC Press knowledge base."
    - `stronger` → amber/warm warning banner with copy: "You have 1 free question remaining. Upgrade anytime for unlimited source-backed IBM i answers." (no price)
    - `upgrade` → full upgrade prompt card with pricing. Standard copy: "You've reached your {limit} free questions. Continue with unlimited access to MC ChatMaster for $19.95/month. Get instant, source-linked answers from 113+ MC Press books and 6,300+ technical articles." PQL copy: "Looks like you're working through a real IBM i issue. Unlock unlimited access and keep going without interruption." + standard pricing/CTA
    - CTA button: "Start Unlimited Access — $19.95/month" opening `signupUrl` in new tab
    - "Cancel anytime." text near pricing
    - Call `onUpgradeClick` and `trackEvent('upgrade_click', ...)` on CTA click
    - Banner appears below chat messages, above input field
    - _Requirements: 2.1, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.2, 5.3, 5.4, 5.6, 7.1, 7.3, 7.4, 7.5, 9.3, 9.5_

  - [ ]* 3.2 Write unit tests for ProgressiveWarningBanner
    - Test silent stage renders nothing (Req 2.1)
    - Test soft stage renders blue banner with correct copy (Req 3.1, 3.2)
    - Test stronger stage renders amber banner, mentions "Upgrade" but not "$19.95" (Req 4.1, 4.2, 7.3)
    - Test upgrade stage renders pricing "$19.95/month" and "Cancel anytime." (Req 7.1, 7.4, 7.5)
    - Test PQL variant copy when `isPQL=true` (Req 9.3)
    - Test standard copy when `isPQL=false` (Req 9.5)
    - Test CTA button text is "Start Unlimited Access — $19.95/month" (Req 7.4)
    - _Requirements: 2.1, 3.1, 3.2, 4.1, 4.2, 7.1, 7.3, 7.4, 7.5, 9.3, 9.5_

- [x] 4. Checkpoint — Verify utilities and ProgressiveWarningBanner
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Frontend: Create NewsletterCapturePrompt component
  - [x] 5.1 Create `frontend/components/NewsletterCapturePrompt.tsx`
    - Props: `userEmail`, `onDismiss`, `onSignup`
    - Pre-fill email input with `userEmail` (fall back to empty if not available)
    - "Join the MC Press Newsletter" heading with brief value prop
    - Submit button and dismiss (X) button
    - Non-blocking — user can dismiss and continue chatting
    - On dismiss: call `onDismiss()`, emit `trackEvent('newsletter_dismissed', { questionsUsed })`
    - On submit: call `onSignup(email)`, emit `trackEvent('newsletter_signup', { questionsUsed })`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.3, 11.4_

  - [ ]* 5.2 Write unit tests for NewsletterCapturePrompt
    - Test email pre-fill from props (Req 10.3)
    - Test dismiss callback fires and emits analytics event (Req 10.4, 11.3)
    - Test signup callback fires and emits analytics event (Req 11.4)
    - _Requirements: 10.3, 10.4, 11.3, 11.4_

- [x] 6. Frontend: Update PaywallOverlay with new copy and PQL support
  - [x] 6.1 Update `frontend/components/PaywallOverlay.tsx`
    - Add `isPQL?: boolean` prop to interface
    - Standard copy: "You've reached your free questions. Continue with unlimited access to MC ChatMaster for $19.95/month. Get instant, source-linked answers from 113+ MC Press books and 6,300+ technical articles."
    - PQL copy: "Looks like you're working through a real IBM i issue. Unlock unlimited access and keep going without interruption." + standard pricing/CTA
    - CTA button text: "Start Unlimited Access — $19.95/month"
    - Add "Cancel anytime." text near pricing
    - Keep "Already subscribed? Sign In" link
    - Emit `trackEvent('upgrade_click', { stage: 'hardGate', isPQL })` on CTA click
    - _Requirements: 6.3, 7.2, 7.4, 7.5, 9.4, 11.2_

  - [ ]* 6.2 Write unit tests for updated PaywallOverlay
    - Test "$19.95/month" and "Cancel anytime." are displayed (Req 7.2, 7.5)
    - Test PQL copy when `isPQL=true` (Req 9.4)
    - Test CTA button text is "Start Unlimited Access — $19.95/month" (Req 7.4)
    - Test analytics event emitted on CTA click (Req 11.2)
    - _Requirements: 7.2, 7.4, 7.5, 9.4, 11.2_

- [x] 7. Checkpoint — Verify all new components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Frontend: Update ChatInterface with progressive warning integration
  - [x] 8.1 Add new state variables and PQL detection to `frontend/components/ChatInterface.tsx`
    - Add `userEmail` to `ChatInterfaceProps` interface
    - Add state: `sessionQuestionCount` (number, starts 0), `isPQL` (boolean), `newsletterDismissed` (boolean), `newsletterSignedUp` (boolean), `previousWarningStage` (WarningStage)
    - On successful SSE metadata received: increment `sessionQuestionCount`, compute `warningStage` via `getWarningStage()`, emit `trackEvent('warning_stage_change', ...)` on stage transitions, set `isPQL = true` when `sessionQuestionCount >= 3` and emit `trackEvent('pql_qualified', ...)`
    - _Requirements: 9.1, 9.2, 11.1, 12.1_

  - [x] 8.2 Replace RemainingQuestionsBanner with ProgressiveWarningBanner in ChatInterface
    - Remove `RemainingQuestionsBanner` import and rendering
    - Import and render `ProgressiveWarningBanner` when `subscriptionStatus === 'free'` and usage data is available
    - Pass `questionsUsed`, `questionsLimit`, `isPQL`, `signupUrl`, `onUpgradeClick` props
    - _Requirements: 2.1, 3.1, 4.1, 5.2_

  - [x] 8.3 Integrate NewsletterCapturePrompt into ChatInterface
    - Import and render `NewsletterCapturePrompt` when warning stage is `soft` and `!isPQL` and `!newsletterDismissed` and `!newsletterSignedUp`
    - Pass `userEmail` from props, wire `onDismiss` to set `newsletterDismissed = true`, wire `onSignup` to set `newsletterSignedUp = true`
    - _Requirements: 10.1, 10.2, 10.4, 10.5_

  - [x] 8.4 Disable chat input at upgrade and hardGate stages
    - Disable textarea and send button when warning stage is `upgrade` or `hardGate` (in addition to existing `showPaywall` check)
    - _Requirements: 5.5, 6.4_

  - [x] 8.5 Update footer text for free-tier users
    - Change the footer line "Unlimited Queries • 24/7 • Sources Always Linked" to conditionally hide "Unlimited Queries" when `subscriptionStatus === 'free'`
    - Free-tier footer: "24/7 • Sources Always Linked"
    - Subscribed footer: "Unlimited Queries • 24/7 • Sources Always Linked" (unchanged)
    - _Requirements: 2.2_

  - [x] 8.6 Pass `isPQL` to PaywallOverlay
    - Update the `PaywallOverlay` rendering to pass `isPQL` prop
    - _Requirements: 9.4_

- [x] 9. Frontend: Update page.tsx to pass userEmail to ChatInterface
  - [x] 9.1 Update `frontend/app/page.tsx` to pass `userEmail` prop to ChatInterface
    - Add `userEmail={userEmail}` to the `<ChatInterface>` JSX
    - _Requirements: 10.3_

- [x] 10. Checkpoint — Verify full integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Final wiring and cleanup
  - [x] 11.1 Verify subscribed user bypass is unaffected
    - Confirm `ProgressiveWarningBanner` does not render when `subscriptionStatus !== 'free'`
    - Confirm `NewsletterCapturePrompt` does not render for subscribed users
    - Confirm no question counter increments for subscribed users (existing backend behavior, no change needed)
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 11.2 Remove or deprecate `frontend/components/RemainingQuestionsBanner.tsx`
    - Remove the file or add a deprecation comment, since it is fully replaced by `ProgressiveWarningBanner`
    - Remove any remaining imports of `RemainingQuestionsBanner` across the codebase
    - _Requirements: 2.1, 3.1_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Properties 1–4 from design)
- Unit tests validate specific examples, edge cases, and component rendering
- All testing on Railway/Netlify staging after deployment — no local test environment for integration tests
- Backend uses Hypothesis for property tests; frontend uses fast-check (both already in project dependencies)
- The `RemainingQuestionsBanner` is fully replaced — not modified — by `ProgressiveWarningBanner`
