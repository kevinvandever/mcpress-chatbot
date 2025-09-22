# Story: Remove Non-Functional Search Feature

**Story ID**: STORY-001  
**Epic**: EPIC-001 (Technical Foundation)  
**Type**: Brownfield Cleanup  
**Priority**: P0 (Critical)  
**Points**: 3  
**Sprint**: 1  

## User Story

**As a** user  
**I want** the broken search feature removed  
**So that** I don't encounter errors and confusion  

## Current State

### Problem
- Search bar visible but returns errors
- Backend search endpoints failing
- Users confused about search vs chat functionality
- Error logs cluttered with search failures

### Code Locations
- Frontend: `frontend/src/components/SearchBar.tsx`
- Backend: `backend/api/search.py`
- Routes: `frontend/src/app/search/*`

## Implementation Plan

### 1. Frontend Changes
```typescript
// Remove from frontend/src/components/Layout.tsx
- import SearchBar from './SearchBar';
- <SearchBar />

// Delete files:
- frontend/src/components/SearchBar.tsx
- frontend/src/app/search/page.tsx
```

### 2. Backend Changes
```python
# Remove from backend/main.py
- from api import search
- app.include_router(search.router)

# Delete files:
- backend/api/search.py
```

### 3. Database Cleanup
```sql
-- Remove unused search indexes if any
DROP INDEX IF EXISTS idx_document_search;
```

### 4. Navigation Updates
- Remove search from navigation menu
- Update help documentation
- Redirect /search routes to /chat

## Acceptance Criteria

- [ ] Search bar not visible on any page
- [ ] Search menu item removed from navigation
- [ ] `/search` routes redirect to `/chat` (301)
- [ ] Search API endpoints return 410 Gone
- [ ] No console errors related to search
- [ ] No search-related error logs
- [ ] Help docs updated to remove search references
- [ ] Tests updated to remove search coverage

## Testing Checklist

### Manual Testing
- [ ] Navigate all pages - no search UI visible
- [ ] Try accessing /search - redirects to /chat
- [ ] Check browser console - no errors
- [ ] Test on mobile - no search remnants

### Automated Testing
- [ ] Remove search component tests
- [ ] Update E2E tests to exclude search
- [ ] Verify chat functionality unaffected
- [ ] Load testing still passes

## Rollback Plan

1. Revert git commit
2. Redeploy previous version
3. Clear CDN cache
4. Monitor error logs

## Definition of Done

- [ ] Code changes completed
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] UAT approved by David
- [ ] Deployed to production
- [ ] Monitoring confirms no errors
- [ ] Documentation updated

## Notes

- This is a cleanup task, not a feature removal
- Search was never fully functional
- Focus should remain on chat interface
- Consider adding search within chat history in future

## Dependencies

None - this can be done independently

## Risks

- **Risk**: Users expecting search functionality
- **Mitigation**: Clear messaging about chat capabilities

## Post-Implementation

- Monitor user feedback for search requests
- Track any increase in chat usage
- Consider adding FAQ about finding content via chat