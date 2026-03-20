# Implementation Plan: UI Enhancements Round Two

## Overview

Incremental implementation of branding refinements, dynamic content, responsive improvements, and visual polish across the MC ChatMaster frontend. Changes span `page.tsx`, `ChatInterface.tsx`, `layout.tsx`, `globals.css`, and static assets in `public/`.

## Tasks

- [x] 1. Add CSS foundations: background ovals, pulse animation, and tooltip styles
  - [x] 1.1 Add background ovals CSS classes, pulse-gentle keyframes, and tooltip styles to `frontend/app/globals.css`
    - Add `header-bg-ovals` and `footer-bg-ovals` classes using `::before`/`::after` pseudo-elements with `border-radius: 50%`, low opacity light blue fills, and absolute positioning
    - Add `main-bg-ovals` class for background ovals in the main content area
    - Add `@keyframes pulse-gentle` animation and `.animate-pulse-gentle` utility class
    - Add `prefers-reduced-motion: reduce` rule for `animate-pulse-gentle` to disable animation
    - Add `.status-bar-tooltip` CSS-only tooltip using `::after` pseudo-element on hover
    - _Requirements: 1.2, 5.4, 3.4, 7.4, 10.2_

- [x] 2. Refactor header with branded wordmark, tagline, sub-line, powered note, and background ovals
  - [x] 2.1 Replace the `<img>` logo in `frontend/app/page.tsx` header with a styled text wordmark
    - Render "MC |" in black with an orange/red vertical bar (`#EF9537`), "CHAT" in bold red (`#990000`), "MASTER" in black
    - Add tagline "Instant AI-Powered IBM i Expertise" next to logo on desktop, stacked on mobile (`< 640px`)
    - Add sub-line "Your 24/7 Knowledge Assistant" below the tagline
    - Add powered note "Powered by MC Press Knowledge" as link to `https://mc-store.com/products/mc-chatmaster`
    - Apply `header-bg-ovals` CSS class to the header for background ovals
    - Ensure tagline shortens or stacks on viewports < 640px to prevent truncation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 3. Enhance assistant title and status bar
  - [x] 3.1 Update the assistant title in `frontend/app/page.tsx`
    - Change text to "MC ChatMaster – Your IBM i Expertise Companion"
    - Increase font size to `text-2xl` and weight to `font-bold`
    - Add orange/red accent underline via `border-bottom` or `::after` pseudo-element with gradient from `#EF9537` to `#990000`
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 3.2 Update the status bar in `frontend/app/page.tsx`
    - Change ready status text to: "MC ChatMaster Primed & Continuously Updating! {bookCount} Books & {articleCount}+ Articles Loaded – Fresh Insights Added as MC Press Publishes"
    - Ensure `bookCount` and `articleCount` remain dynamically fetched, never hardcoded
    - Add consistent emoji and spacing in the status message
    - Add `status-bar-tooltip` CSS class so hovering shows: "Knowledge base auto-updates with every new MC Press publication"
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 10.4_
  - [ ]* 3.3 Write property test: Dynamic status bar reflects actual counts (Property 1)
    - **Property 1: Dynamic status bar reflects actual counts**
    - Use `fast-check` to generate random non-negative integer pairs for bookCount/articleCount
    - Extract status bar text rendering logic into a testable helper or test rendered output
    - Assert output string contains both numbers as substrings and never displays hardcoded values
    - **Validates: Requirements 3.1, 3.2, 10.4**


- [x] 4. Refine quick start section with 6+ branded buttons
  - [x] 4.1 Update the quick start section in `frontend/app/page.tsx`
    - Change section title to "Instant Mastery Insights: Try These Expert IBM i & RPG Questions"
    - Add at least 6 buttons with MC Press palette colors:
      - Orange/red (`#EF9537`/`#990000`): "Modernize Legacy RPG to Free-Format", "Master DB2 Config on IBM i"
      - Purple: "Optimize Your RPG Skills", "High Availability with PowerHA Essentials"
      - Green (`#A1A88B`): "Ace IBM i System Admin", "Secure Your IBM i Environment"
    - Refine button labels to reference MC Press source tie-ins where applicable
    - Ensure buttons stack vertically (`flex-col`) on viewports < 640px
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.1_

- [x] 5. Checkpoint - Verify header, status bar, and quick start changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Enhance welcome message, input field, and send button in ChatInterface
  - [x] 6.1 Update the welcome message in `frontend/components/ChatInterface.tsx`
    - Increase chat bubble icon size from `w-20 h-20` to `w-24 h-24` or `w-28 h-28`
    - Apply `animate-pulse-gentle` class to the chat bubble icon container
    - Render "24/7" and "Mastering" in orange/red color (`#EF9537` or `#990000`) using `<span>` elements
    - Add the line "Get Precise, Sourced Answers – Every Response Links to Original MC Press Articles/Books"
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [x] 6.2 Redesign the input field and send button in `frontend/components/ChatInterface.tsx`
    - Change input placeholder to "Ask MC ChatMaster Anything About IBM i, RPG, DB2..."
    - Change send button background from blue (`bg-mc-blue`) to orange/red (`#EF9537` or `#990000`)
    - Change send button label from "Send" to "Ask Expert" when not streaming
    - Keep "Thinking..." label with spinner when streaming (already partially implemented)
    - Add hint text below the input area: "Unlimited Queries • 24/7 • Sources Always Linked" in small muted text
    - Ensure input field is full-width on viewports < 640px with appropriate padding
    - Ensure send button is full-width or min 44x44px touch target on mobile
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.2, 8.3_
  - [ ]* 6.3 Write property test: Send button label reflects streaming state (Property 2)
    - **Property 2: Send button label reflects streaming state**
    - Use `fast-check` to generate random boolean for isStreaming
    - Render the send button or call the label logic
    - Assert label is "Ask Expert" when `isStreaming` is false, "Thinking..." when true
    - **Validates: Requirements 6.3, 6.4**

- [x] 7. Append source CTA to chat responses
  - [x] 7.1 Add source link CTA to assistant messages in `frontend/components/ChatInterface.tsx`
    - After rendering assistant message content and before `CompactSources`, check if `message.sources` has at least one source with a truthy `mc_press_url`
    - If yes, append "Need more details? Dive into the full source:" followed by a clickable link to the first available `mc_press_url`
    - If no sources have `mc_press_url`, do not render the CTA
    - _Requirements: 10.3_
  - [ ]* 7.2 Write property test: Source CTA appended to responses with available links (Property 4)
    - **Property 4: Source CTA appended to responses with available links**
    - Use `fast-check` to generate random arrays of Source objects, some with `mc_press_url` and some without
    - Call the response rendering logic or a helper function that determines CTA visibility
    - Assert CTA text appears if and only if at least one source has a truthy `mc_press_url`
    - **Validates: Requirements 10.3**

- [x] 8. Enhance footer with links, privacy note, and background ovals
  - [x] 8.1 Update the footer in `frontend/app/page.tsx`
    - Change footer text to "MC ChatMaster: Instant AI-Powered IBM i Expertise – Powered by MC Press Online"
    - Add link to `mcpressonline.com` and link to `mc-store.com`
    - Add privacy note: "Private • Secure • Continuously Updated Knowledge Base"
    - Apply `footer-bg-ovals` CSS class for background ovals
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 9. Checkpoint - Verify ChatInterface changes and footer
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Add favicon files and update layout metadata
  - [x] 10.1 Place favicon files in `frontend/public/`
    - Add `favicon.ico` (multi-size: 16x16, 32x32), `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png` (180x180) generated from existing `mc-chatmaster-logo.png`
    - _Requirements: 9.1, 9.2_
  - [x] 10.2 Update `frontend/app/layout.tsx` metadata to include favicon icons configuration
    - Add `icons` property to the `metadata` export referencing `favicon.ico`, `favicon-16x16.png`, `favicon-32x32.png`, and `apple-touch-icon.png`
    - _Requirements: 9.1, 9.2_

- [x] 11. Responsive design and brand consistency pass
  - [x] 11.1 Add responsive adaptations across `frontend/app/page.tsx` and `frontend/components/ChatInterface.tsx`
    - Ensure all text readable without horizontal scrolling on viewports as narrow as 320px
    - Ensure chat message area and answer display are fully scrollable on mobile
    - Adjust layout spacing and font sizes for tablet viewports (640px–1024px)
    - _Requirements: 8.4, 8.5, 8.6_
  - [x] 11.2 Audit all visible text for brand name casing consistency
    - Ensure every occurrence uses "MC ChatMaster" (capital C, capital M) across all affected files
    - Add background ovals to the main content area via `main-bg-ovals` class
    - _Requirements: 10.1, 10.2_
  - [ ]* 11.3 Write property test: Brand name casing consistency (Property 3)
    - **Property 3: Brand name casing consistency**
    - Use `fast-check` to scan `.tsx` and `.ts` source files for strings matching `/mc\s*chat\s*master/i`
    - Assert every match uses the exact casing "MC ChatMaster"
    - Static analysis property test — verify across the source set
    - **Validates: Requirements 10.1**

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use `fast-check` for TypeScript property-based testing
- Responsive behavior (Requirements 8.x) should be validated via manual testing or E2E viewport simulation
- All `bookCount`/`articleCount` values are already dynamically fetched — never introduce hardcoded fallbacks
- Favicon files need to be generated from existing `mc-chatmaster-logo.png` in `frontend/public/`
