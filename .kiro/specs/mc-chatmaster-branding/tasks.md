# Implementation Plan: MC ChatMaster Branding Refresh

## Overview

Frontend-only branding refresh across 4 files to establish the "MC ChatMaster" product identity. All changes are text/label updates, two button color changes, a new secondary footer line, and dynamic book/article count computation from the existing `/documents` API response. No backend changes required. TypeScript/Next.js 14 with Jest for testing.

## Tasks

- [x] 1. Update browser tab metadata in `frontend/app/layout.tsx`
  - [x] 1.1 Update HTML title and meta description
    - Change `title` from "MC Press Chatbot - AI-Powered Document Assistant" to "MC ChatMaster | Instant AI-Powered IBM i Expertise"
    - Change `description` from "Ask questions about MC Press technical books and documentation" to "Your 24/7 AI-powered guide to mastering RPG, DB2, System Administration, and IBM i best practices from MC Press technical books and articles"
    - _Requirements: 8.1, 8.2_

- [x] 2. Update page shell branding in `frontend/app/page.tsx`
  - [x] 2.1 Add `bookCount` and `articleCount` state variables and compute them in `checkDocuments`
    - Add `const [bookCount, setBookCount] = useState(0)` and `const [articleCount, setArticleCount] = useState(0)`
    - After extracting the documents array in the `checkDocuments` effect, filter by `document_type === 'book'` and `document_type === 'article'` to set counts
    - _Requirements: 2.2_

  - [x] 2.2 Update section heading, status bar, quick start, and footer text
    - Change heading from "AI Assistant" to "MC ChatMaster Assistant"
    - Change status primary text from "✨ System Ready!" to "✨ MC ChatMaster Ready!"
    - Change status secondary text to use `{bookCount} Books & {articleCount} Articles Loaded • Instant Expertise Active`
    - Change quick start title from "Quick Start - Try these questions:" to "Instant Insights: Try These RPG & IBM i Questions"
    - Change button 1 label to "Master DB2 Config on IBM i" (keep prompt value "How do I configure DB2 on IBM i?" unchanged)
    - Change button 2 label to "Optimize Your RPG Skills" (keep prompt value "RPG programming best practices" unchanged)
    - Change footer primary text to "MC ChatMaster: Instant AI-Powered IBM i Expertise"
    - Add secondary footer line "POWERED BY AI IBM i EXPERTISE" with uppercase, smaller, lighter text styling
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 6.1, 6.2, 6.3_

  - [x] 2.3 Update quick start button colors
    - Change button 1 (DB2) background from `var(--mc-blue)` / `var(--mc-blue-dark)` to `var(--mc-orange)` / `var(--mc-orange-dark)`
    - Change button 2 (RPG) from inline `var(--mc-green)` style to Tailwind `bg-purple-600` / `hover:bg-purple-700` classes, removing the inline style and onMouseEnter/onMouseLeave handlers for that button
    - _Requirements: 3.4, 3.5_

- [ ] 3. Update welcome state and placeholder in `frontend/components/ChatInterface.tsx`
  - [x] 3.1 Update welcome state text and input placeholder
    - Change welcome heading from "Ready to help! ✨" to "MC ChatMaster Ready for Your Query! ✨"
    - Change welcome subtext from "Ask me anything about your MC Press books" to "Your 24/7 Guide to Mastering RPG, DB2, System Administration, and IBM i Best Practices – Fresh Insights Added as MC Press Publishes"
    - Change input placeholder (when docs loaded) from "Ask me about your MC Press books..." to "Ask MC ChatMaster Anything"
    - Keep "Upload documents first to start chatting..." placeholder unchanged when no docs
    - _Requirements: 4.1, 4.2, 5.1, 5.2_

- [x] 4. Update source card labels in `frontend/components/CompactSources.tsx`
  - [x] 4.1 Update section header and button labels
    - Change section header from "References" to "Sources"
    - Change single-author button label from "Author" to "View Author Profile"
    - Change multi-author dropdown button label from "Authors" to "View Author Profiles"
    - Change article link button label from "Read" to "Access Source"
    - Keep "Buy" label on book purchase buttons unchanged
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 5. Checkpoint — Verify all branding changes compile
  - Ensure all files pass TypeScript compilation and there are no build errors
  - Visually confirm the text changes are correct by reviewing the modified files
  - Ask the user if questions arise

- [ ] 6. Write tests for branding changes
  - [ ]* 6.1 Write property test for book/article count derivation logic
    - **Property 1: Book and article counts are correctly derived from document_type**
    - Use `fast-check` to generate random arrays of document objects with `document_type` values from `["book", "article", "other", undefined, null]`
    - Extract the count computation into a pure helper function (e.g., `computeDocumentCounts`) and test it directly
    - Assert `bookCount === docs.filter(d => d.document_type === 'book').length`
    - Assert `articleCount === docs.filter(d => d.document_type === 'article').length`
    - Assert `bookCount + articleCount <= docs.length`
    - Minimum 100 iterations
    - **Validates: Requirement 2.2**

  - [ ]* 6.2 Write unit tests for CompactSources label changes
    - Verify section header renders "Sources"
    - Verify single-author button renders "View Author Profile"
    - Verify multi-author dropdown renders "View Author Profiles"
    - Verify article link button renders "Access Source"
    - Verify book purchase button still renders "Buy"
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 6.3 Write unit tests for ChatInterface welcome state and placeholder
    - Verify welcome heading renders "MC ChatMaster Ready for Your Query! ✨" when hasDocuments=true and no messages
    - Verify welcome subtext matches new branding string
    - Verify input placeholder is "Ask MC ChatMaster Anything" when hasDocuments=true
    - Verify input placeholder is "Upload documents first to start chatting..." when hasDocuments=false
    - _Requirements: 4.1, 4.2, 5.1, 5.2_

- [x] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All changes are frontend-only — no backend deployment needed
- The count computation reuses the existing `/documents` API response; no new API calls
- Button 2 (RPG) switches from inline CSS variable styling to Tailwind classes for purple, matching the pattern used in CompactSources.tsx for author buttons
- Property test validates the only non-trivial logic (count derivation); all other changes are static text replacements best covered by example-based tests
