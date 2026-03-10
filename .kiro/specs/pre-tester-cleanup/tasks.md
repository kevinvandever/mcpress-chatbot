# Implementation Plan: Pre-Tester Cleanup

## Overview

Comprehensive cleanup of the MC Press Chatbot codebase before sharing with first testers. The work follows a strict execution order: endpoint removal first (to decouple routers from dead files), then file deletions across backend/root/frontend, then additive changes (.gitignore, post-login flash fix), and finally trivial cleanup (empty spec dir). All backend changes require Railway deployment; all testing must be done via API-based scripts against the deployed Railway URL.

## Tasks

- [x] 1. Remove dangerous, debug, and migration endpoints from `backend/main.py`
  - [x] 1.1 Remove dangerous data-destructive endpoints (inline functions and imports)
  - [x] 1.2 Remove debug endpoints (inline functions and router registrations)
  - [x] 1.3 Remove deprecated migration endpoints (inline functions and router registrations)
  - [x] 1.4 Remove one-off admin/diagnostic router registrations
  - [x] 1.5 Remove dead fallback import blocks for vector store variants

- [x] 2. Checkpoint — Verify endpoint removal
  - Deferred to final checkpoint (Task 10) since all changes are being made together before deployment.

- [x] 3. Delete dead backend files (variants and one-off scripts)
  - [x] 3.1 Delete backend file variants (main_*, admin_documents*, pdf_processor*, vector_store*)
  - [x] 3.2 Delete backend one-off test scripts, diagnostic scripts, debug scripts, and removed endpoint files
  - [x] 3.3 Delete backend completed migration scripts and standalone docs

- [x] 4. Delete root-level ad-hoc scripts and data files
  - [x] 4.1 Delete root-level Python scripts (~257 files)
  - [x] 4.2 Delete root-level data files and orphaned docs (~97 markdown files, json, csv, sql, txt, pages, numbers, xlsm, sh, html)

- [x] 5. Delete frontend dead files
  - [x] 5.1 Delete frontend dead files and root-level orphans (page_original.tsx, test artifacts, example components, vercel.json, root-level .tsx orphans)

- [x] 6. Checkpoint — Verify file deletions
  - Deferred to final checkpoint (Task 10) since all changes are being made together before deployment.

- [x] 7. Update `.gitignore` with data file patterns
  - [x] 7.1 Add gitignore patterns for data files and tool artifacts (/*.json, /*.csv, /*.sql, /*.txt with negations, *.numbers, *.pages, *.xlsm, .hypothesis/)

- [x] 8. Fix post-login page flash in `frontend/app/page.tsx`
  - [x] 8.1 Add `isInitializing` loading gate with branded spinner, resolved in `finally` block of checkDocuments

- [x] 9. Remove empty spec directory
  - [x] Deleted `.kiro/specs/shopify-subscription-auth/` directory

- [x] 10. Final checkpoint — Deploy and verify all changes
  - Deploy to Railway (git push to main), wait for deployment
  - Verify `GET /health` returns 200
  - Verify all removed endpoints return 404
  - Verify frontend builds and deploys successfully on Netlify
  - Verify post-login redirect shows loading spinner (no flash)

## Notes

- Tasks marked with `*` (property tests) were skipped for faster MVP — can be added later if needed
- All backend changes require Railway deployment before testing
- The execution order is critical: endpoint removal before file deletion prevents import errors during deployment
