# Implementation Plan: Disqus Feedback Integration

## Overview

Add a collapsible "Community Feedback" panel to the main chat page using Disqus as the commenting platform. This is a frontend-only change — a new `DisqusFeedback` component is created and integrated into `page.tsx` below the chat section. The Disqus embed script is lazy-loaded on first expand to preserve page load performance. Property-based tests use `fast-check`.

## Tasks

- [x] 1. Create the DisqusFeedback component
  - [x] 1.1 Create `frontend/components/DisqusFeedback.tsx` with collapsed/expanded toggle logic
    - Define constants: `DISQUS_SHORTNAME`, `DISQUS_PAGE_IDENTIFIER`, `DISQUS_PAGE_URL`
    - Manage `isExpanded` state (default `false`) and `hasLoadedDisqus` ref (default `false`)
    - Manage `loadError` state for fallback display
    - Render a `<button>` toggle header with "Community Feedback" label and a chevron icon that rotates on expand/collapse
    - Set `aria-expanded` on the toggle button reflecting current state
    - Render `#disqus_thread` container with `aria-label="Community feedback comments"`, hidden when collapsed
    - Use same card styling as chat section: white background, rounded corners, border, shadow, within `max-w-7xl` wrapper
    - Use MC ChatMaster brand color variables for heading text and icon
    - Toggle responds to click, Enter, and Space key events
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 5.3, 5.4_

  - [x] 1.2 Implement lazy Disqus script injection in `DisqusFeedback.tsx`
    - On first expand (`hasLoadedDisqus.current === false`), set `window.disqus_config` with hardcoded `page.identifier` and `page.url`, create `<script>` element pointing to `https://mc-chatmaster-disqus-com.disqus.com/embed.js` with `async: true`, append to `document.body`, set `hasLoadedDisqus.current = true`
    - Attach `onerror` handler to set `loadError = true`
    - Add a timeout fallback (10s) to detect render failures
    - On subsequent expand/collapse, do not inject script again — reuse existing embed
    - When `loadError` is true, display fallback message: "Comments could not be loaded. Please check your connection or ad blocker settings."
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4_

- [x] 2. Integrate DisqusFeedback into the main page
  - Import `DisqusFeedback` in `frontend/app/page.tsx`
  - Place `<DisqusFeedback />` inside the `<main>` element's `space-y-6` container, after the chat section `<div>` and before the closing `</main>` tag
  - No props needed — component is self-contained
  - _Requirements: 1.1, 3.2_

- [x] 3. Checkpoint - Verify component renders and toggles correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Add fast-check and write property-based tests
  - [x] 4.1 Install `fast-check` as a dev dependency in `frontend/`
    - Run `npm install --save-dev fast-check` in the frontend directory
    - _Requirements: (testing infrastructure)_

  - [ ]* 4.2 Write property test for toggle state consistency (Property 1)
    - **Property 1: Toggle state consistency**
    - Generate random arrays of click actions (length 1–50), apply sequentially starting from `isExpanded = false`, verify final state equals `actions.length % 2 === 1` and `aria-expanded` matches at each step
    - **Validates: Requirements 1.4, 1.5, 5.3**

  - [ ]* 4.3 Write property test for Disqus config invariance (Property 2)
    - **Property 2: Disqus config invariance**
    - Generate random URL path and query parameter strings, call the Disqus config function, verify `page.identifier` is always `'mc-chatmaster-main'` and `page.url` is always `'https://mc-chatmaster.netlify.app'`
    - **Validates: Requirements 2.2**

  - [ ]* 4.4 Write property test for script injection idempotence (Property 3)
    - **Property 3: Script injection idempotence**
    - Generate random sequences of expand/collapse actions (length 2–30, first action always expand), count `loadDisqus` invocations, verify it is always exactly 1
    - **Validates: Requirements 4.2, 4.3**

- [ ] 5. Write unit tests for DisqusFeedback component
  - [ ]* 5.1 Write unit tests covering specific examples and edge cases
    - Component renders collapsed by default (Req 1.3)
    - Toggle header displays "Community Feedback" text (Req 1.2)
    - Chevron icon rotates on expand/collapse (Req 1.2)
    - `#disqus_thread` container has correct `aria-label` (Req 2.3, 5.4)
    - No Disqus script in DOM on initial render (Req 4.1)
    - Script element has `async` attribute after first expand (Req 4.4)
    - Fallback message appears when script `onerror` fires (Req 2.4)
    - Toggle is a `<button>` element, focusable via tab (Req 5.1)
    - Enter and Space keys toggle the panel (Req 5.2)
    - Panel uses same card styling classes as chat section (Req 3.1)
    - Panel uses brand color variables for heading (Req 3.4)
    - _Requirements: 1.2, 1.3, 2.3, 2.4, 3.1, 3.4, 4.1, 4.4, 5.1, 5.2, 5.4_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- This is a frontend-only feature — no backend changes required
- Frontend deploys to Netlify; test on staging first per the staging-first workflow
- The `fast-check` library is used for property-based tests with a minimum of 100 iterations per property
