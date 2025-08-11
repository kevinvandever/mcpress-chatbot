# Story #4: Fix Silent Chat Request Failure

**Status:** In Progress
**Priority:** CRITICAL
**Points:** 3

## Story
Chat requests are submitted but receive no response, and no error messages appear in the UI or console.

## Acceptance Criteria
- [ ] All chat requests receive a response (success or error)
- [ ] Loading indicator shows while processing
- [ ] Timeout errors display if request takes too long
- [ ] Chat responds within 30 seconds or shows timeout message

## Dev Notes
- Frontend trying to reach `/api` in local development
- Backend runs on `http://localhost:8000`
- Production uses `/api` proxy through Netlify to Railway
- Need environment-specific configuration

## Tasks
- [ ] Fix API URL configuration for local development
- [ ] Ensure proper error handling for failed requests
- [ ] Add timeout handling
- [ ] Test local and verify production not affected

## Dev Agent Record

### Debug Log
- Issue identified: `/api` endpoint not proxied correctly in development
- next.config.js has rewrite rule but not environment-specific

### Completion Notes
- [ ] Local testing confirmed working
- [ ] Production deployment verified

### File List
- frontend/next.config.js
- frontend/config/api.ts

### Change Log
- [Pending] Make next.config.js rewrites development-only

## Testing
```bash
# Local test
cd frontend && npm run dev
# Try chat functionality
# Should connect to localhost:8000
```