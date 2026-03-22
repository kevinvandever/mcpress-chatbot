# Implementation Plan: Document Removal

## Overview

Replace the existing unauthenticated, incomplete delete endpoints with authenticated, cascading document removal. Add bulk selection UI, enhanced confirmation dialogs, chunk count column, and vector index rebuild capability. Backend is Python/FastAPI, frontend is Next.js/TypeScript.

## Tasks

- [x] 1. Define Pydantic request/response models and add auth import to admin_documents_fixed.py
  - Create `BulkDeleteRequest`, `DocumentDeletionDetail`, `SingleRemovalSummary`, and `BulkRemovalSummary` Pydantic models in `backend/admin_documents_fixed.py`
  - Add import for `get_current_user` from `auth_routes` (following the try/except Railway vs local pattern used in `ingestion_routes.py`)
  - Add `from pydantic import BaseModel` import
  - _Requirements: 1.1, 3.1, 3.3_

- [x] 2. Implement authenticated single document delete with cascading cleanup
  - [x] 2.1 Replace the existing `DELETE /admin/documents/{doc_id}` endpoint with an authenticated version
    - Add `Depends(get_current_user)` to the endpoint signature
    - Inside a `conn.transaction()` block, delete from `document_authors`, `metadata_history`, `documents` (chunks by filename), and `books` in that order
    - Count rows deleted from each table for the `SingleRemovalSummary` response
    - Return 404 if `doc_id` not found in `books`, 401 if unauthenticated, 500 on DB error with transaction rollback
    - Call `invalidate_cache()` after successful deletion
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 Write property test: Unauthenticated requests are rejected (Property 1)
    - **Property 1: Unauthenticated requests are rejected**
    - Generate requests without JWT or with invalid tokens, verify 401 on both delete endpoints
    - **Validates: Requirements 1.1**

  - [ ]* 2.3 Write property test: Non-existent document returns 404 (Property 2)
    - **Property 2: Non-existent document returns 404**
    - Generate random large integer IDs, verify 404 response from single delete endpoint
    - **Validates: Requirements 1.4**

  - [ ]* 2.4 Write property test: Single document cascading delete completeness (Property 3)
    - **Property 3: Single document cascading delete completeness**
    - Create a test document with chunks, author associations, and metadata history, then delete it and verify zero rows remain in all four tables
    - **Validates: Requirements 1.2, 1.3, 2.1, 2.2, 8.1, 8.2, 8.3**

  - [ ]* 2.5 Write property test: Orphaned author retention (Property 4)
    - **Property 4: Orphaned author retention**
    - Create a document with a unique author (no other documents), delete the document, verify the author record still exists in `authors` table
    - **Validates: Requirements 2.3**

  - [ ]* 2.6 Write property test: Cache invalidation after deletion (Property 5)
    - **Property 5: Cache invalidation after deletion**
    - Delete a document, then call the listing endpoint, verify the deleted document is absent from results
    - **Validates: Requirements 2.4**

- [x] 3. Implement authenticated bulk document delete
  - [x] 3.1 Replace the existing `DELETE /admin/documents/bulk` endpoint with an authenticated version
    - Add `Depends(get_current_user)` and accept `BulkDeleteRequest` body
    - Return 400 if `ids` list is empty
    - Query `books` for all provided IDs, partition into found vs not_found
    - For each found document, perform cascading delete inside a transaction (same order as single delete)
    - Return `BulkRemovalSummary` with `deleted_count`, `not_found_ids`, `deleted_documents`, totals
    - Call `invalidate_cache()` after successful deletion
    - _Requirements: 1.1, 3.1, 3.2, 3.3, 3.4_

  - [ ]* 3.2 Write property test: Bulk delete cascading completeness (Property 6)
    - **Property 6: Bulk delete cascading completeness**
    - Create multiple test documents with related data, bulk delete them, verify all tables are clean for each
    - **Validates: Requirements 3.1**

  - [ ]* 3.3 Write property test: Bulk delete mixed ID partitioning and summary accuracy (Property 7)
    - **Property 7: Bulk delete mixed ID partitioning and summary accuracy**
    - Mix real and fake IDs in bulk delete, verify `not_found_ids` contains exactly the invalid IDs, `deleted_count` matches valid count, and `total_chunks_deleted` is accurate
    - **Validates: Requirements 3.2, 3.3**

- [x] 4. Checkpoint - Ensure backend delete endpoints work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement vector index rebuild endpoints
  - [x] 5.1 Add `POST /admin/documents/reindex` endpoint
    - Add module-level `_reindex_in_progress` flag, `_last_reindex_completed_at`, and `_last_reindex_duration` variables
    - On POST, check flag — return 409 if already in progress
    - Use `asyncio.create_task` to run `REINDEX INDEX documents_embedding_idx` in background
    - Set flag before starting, clear on completion or failure, record duration
    - Return `{ "status": "started", "message": "Vector index rebuild initiated" }`
    - _Requirements: 7.3, 7.7_

  - [x] 5.2 Add `GET /admin/documents/reindex/status` endpoint
    - Return `{ "in_progress": bool, "last_completed_at": str|null, "last_duration_seconds": float|null }`
    - _Requirements: 7.4, 7.5, 7.6_

- [x] 6. Add chunk count to document listing response
  - Modify the `list_documents` query in `admin_documents_fixed.py` to include a subquery or join that counts rows in `documents` table per filename
  - Return `chunk_count` field in each document object in the listing response
  - _Requirements: 6.1, 6.3_

  - [ ]* 6.1 Write property test: Chunk count present in listing response (Property 8)
    - **Property 8: Chunk count present in listing response**
    - For documents in listing response, verify `chunk_count` field exists and matches actual DB count for that filename
    - **Validates: Requirements 6.3**

- [x] 7. Remove old unauthenticated delete endpoint from main.py
  - Remove the `DELETE /documents/{filename}` route from `backend/main.py`
  - This endpoint is unauthenticated and only deletes chunks — it's replaced by the new authenticated endpoints
  - _Requirements: 1.1_

- [x] 8. Checkpoint - Ensure all backend changes work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Frontend: Add chunk count column to document table
  - In `frontend/app/admin/documents/page.tsx`, add a "Chunks" column to the table header and body
  - Display `doc.chunk_count` for each row (show "N/A" if undefined)
  - The data is already returned by the backend listing endpoint
  - _Requirements: 6.1, 6.2_

- [x] 10. Frontend: Enhance single delete confirmation dialog
  - Update the existing `showDeleteDialog` modal to display:
    - Document title
    - Document type badge (book/article)
    - Chunk count that will be deleted
  - Update `handleDelete` to call `DELETE /admin/documents/{doc_id}` (the new authenticated endpoint via `apiClient`) and display the `SingleRemovalSummary` on success
  - Show API error messages on failure
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 11. Frontend: Add checkbox selection for bulk operations
  - Add `selectedIds` state (`Set<number>`)
  - Add a checkbox column to the table: header checkbox for "select all on page", row checkboxes for individual selection
  - Clear selections on page change, search, or after bulk delete
  - _Requirements: 5.1, 5.5_

- [x] 12. Frontend: Add bulk delete button and confirmation dialog
  - Show a "Delete N selected" button above the table when `selectedIds.size > 0`
  - On click, open a bulk delete confirmation dialog showing:
    - List of selected document titles (scrollable)
    - Total chunk count across all selected
    - Warning about irreversibility
  - On confirm, call `DELETE /admin/documents/bulk` with `{ ids: [...selectedIds] }` and display `BulkRemovalSummary`
  - On cancel, close dialog without action
  - Deselect all and refresh document list after successful bulk delete
  - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 13. Frontend: Add rebuild vector index button
  - Add a "Rebuild Vector Index" button in the page header area
  - On click, show confirmation dialog explaining the operation may take a few minutes
  - On confirm, call `POST /admin/documents/reindex`
  - While in progress, poll `GET /admin/documents/reindex/status` and show a spinner, disable the button
  - On completion, show success message with elapsed time
  - On failure, show error message
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All backend testing must be done on Railway after deployment (no local testing)
- Frontend deploys to Netlify; backend deploys to Railway
- The `get_current_user` auth dependency follows the existing try/except import pattern used throughout the codebase
