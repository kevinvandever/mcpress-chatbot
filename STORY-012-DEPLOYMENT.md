# Story-012: Conversation Export - Deployment Guide

## Status: Ready for Review

Story-012 implements conversation export functionality, allowing users to export conversations to PDF and Markdown formats.

## What's Been Implemented

### Backend (✅ Complete)
- Export service with PDF (HTML fallback) and Markdown generators
- REST API endpoints for single and bulk exports
- Database schema for export tracking
- Code block extraction and formatting
- ZIP archive creation for bulk exports
- Export history tracking

### Frontend (✅ Core Complete)
- Export button in conversation detail view
- Export modal with format selection (PDF/Markdown)
- Custom title and options
- Download functionality
- Loading states and error handling

### Testing (✅ Unit Tests Pass)
- Markdown generation tests
- PDF/HTML generation tests
- Code block extraction tests
- Filename sanitization tests

## Deployment Steps

### 1. Backend Dependencies
The following packages are already installed locally:
- `jinja2` - Template rendering
- `pygments` - Syntax highlighting (ready, not yet used)
- `weasyprint` - PDF generation (optional, HTML fallback active)

For Railway deployment, add to requirements.txt if needed:
```
jinja2>=3.1.0
pygments>=2.0.0
```

Note: WeasyPrint requires system libraries and may not work on Railway. The HTML fallback is production-ready.

### 2. Database Migration
Run the migration to create the export tracking table:
```bash
python backend/export_migration.py
```

Or run manually in Railway console:
```sql
CREATE TABLE IF NOT EXISTS conversation_exports (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    format TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    options JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exports_user
ON conversation_exports(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_exports_conversation
ON conversation_exports(conversation_id);
```

### 3. Backend Deployment
The export service auto-initializes in `main.py` when:
- Conversation service is available (STORY-011)
- Export modules load successfully

No additional configuration needed.

### 4. Frontend Deployment
Changes are in:
- `frontend/services/exportService.ts` (new)
- `frontend/components/ExportModal.tsx` (new)
- `frontend/components/ConversationDetail.tsx` (modified)

Standard Netlify deployment will pick up these changes.

## API Endpoints

```
POST   /api/conversations/{id}/export    # Export single conversation
POST   /api/conversations/bulk-export    # Export multiple conversations
GET    /api/conversations/exports        # List user's exports
DELETE /api/conversations/exports/{id}   # Delete export record
```

## Testing in Production

1. **Export Single Conversation**
   - Navigate to conversation history
   - Open a conversation
   - Click the export button (download icon)
   - Select PDF or Markdown format
   - Download should start automatically

2. **Verify Export Content**
   - PDF: Opens in browser, shows conversation with formatting
   - Markdown: Download .md file, verify YAML front matter and content

3. **Test Options**
   - Custom title
   - Include/exclude timestamps
   - Table of contents (PDF only)

## Known Limitations

1. **PDF Generation**: Uses HTML fallback (not true PDF) due to WeasyPrint system dependencies. HTML files work in all browsers but may not be ideal for printing.

2. **Deferred Features**: 
   - Bulk export UI (backend ready, frontend deferred)
   - Export history page (deferred to future story)
   - Export preview (downloads directly)

3. **Railway PDF**: If WeasyPrint is needed, Railway needs system packages:
   ```
   apt-get install -y libpango-1.0-0 libpangocairo-1.0-0
   ```

## Rollback Plan

If issues occur:
1. Remove export button from ConversationDetail.tsx
2. Comment out export router in main.py (lines 396-429)
3. Redeploy

## Future Enhancements

- True PDF generation with proper system dependencies
- Bulk export UI
- Export history page
- Email delivery option
- Custom branding/themes
- Export to DOCX/HTML

## Files Changed

**Backend (8 files):**
- backend/export_models.py (new)
- backend/export_service.py (new)
- backend/pdf_generator.py (new)
- backend/markdown_generator.py (new)
- backend/export_routes.py (new)
- backend/export_migration.py (new)
- backend/test_export_service.py (new)
- backend/main.py (modified)

**Frontend (3 files):**
- frontend/services/exportService.ts (new)
- frontend/components/ExportModal.tsx (new)
- frontend/components/ConversationDetail.tsx (modified)

---

**Implementation completed by:** Dexter (Dev Agent)
**Date:** 2025-11-11
**Status:** Ready for Review ✅
