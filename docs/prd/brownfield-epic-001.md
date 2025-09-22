# Brownfield Epic: Technical Foundation & Admin Tools

**Epic ID**: EPIC-001  
**Type**: Brownfield Technical Debt Resolution  
**Priority**: P0 (Critical)  
**Timeline**: Month 0 (4 weeks)  

## Context

This epic addresses critical technical debt in the existing MC Press Chatbot system and establishes foundational admin capabilities required for sustainable growth. As a brownfield project, we're working with existing infrastructure constraints and must ensure zero downtime during transitions.

## Current State Analysis

### Existing Issues
1. **Broken Search**: Non-functional search feature confusing users
2. **No Admin Interface**: David cannot manage content without developer intervention
3. **Missing Metadata**: 110+ documents lack proper metadata
4. **Storage Constraints**: Approaching Railway free tier limits (500MB)

### Technical Stack
- **Frontend**: Next.js on Netlify
- **Backend**: Python/FastAPI on Railway
- **Database**: Supabase PostgreSQL
- **Vector Store**: Supabase pgvector

## Epic Objectives

1. Remove broken functionality to improve user experience
2. Enable autonomous content management for business owner
3. Establish scalable foundation for feature development
4. Maintain production stability throughout changes

## Migration Strategy

### Phase 1: Remove Search (Week 1)
- Feature flag to disable search UI
- Redirect search routes to chat
- Monitor for any dependency breaks
- Clean up unused search code

### Phase 2: Admin Dashboard (Weeks 2-3)
- Deploy admin interface as separate route
- Implement authentication without affecting main app
- Test with subset of documents first
- Gradual rollout to avoid overload

### Phase 3: Data Cleanup (Week 4)
- Batch process existing documents
- Add missing metadata
- Verify vector embeddings
- Optimize storage usage

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| User disruption during search removal | Medium | Feature flag, gradual rollout |
| Storage limits exceeded | High | Monitor usage, upgrade tier if needed |
| Authentication conflicts | Medium | Separate admin auth flow |
| Data loss during migration | High | Backup all data before changes |

## Success Criteria

- [ ] Zero production incidents during migration
- [ ] Search feature cleanly removed without errors
- [ ] Admin can upload and manage documents independently
- [ ] All 110+ documents have complete metadata
- [ ] Storage usage optimized and under control

## Dependencies

- Railway platform stability
- Supabase availability
- David's availability for UAT
- Backup storage solution ready

## Brownfield Considerations

### Code Preservation
- Keep all working chat functionality intact
- Maintain existing API contracts
- Preserve user conversation history

### Incremental Changes
- Each story independently deployable
- Rollback plan for each change
- Feature flags for risky modifications

### Testing Strategy
- Regression testing for chat functionality
- Load testing for batch uploads
- Security testing for admin access
- End-to-end testing before each deployment

## Post-Epic State

After successful completion:
- Clean, maintainable codebase without broken features
- Self-service admin capabilities
- Optimized storage and performance
- Ready for Phase 1 feature development

---

## Linked Stories

1. [STORY-001: Remove Search Feature](./stories/story-001-remove-search.md)
2. [STORY-002: Admin Authentication](./stories/story-002-admin-auth.md)
3. [STORY-003: PDF Upload Interface](./stories/story-003-pdf-upload.md)
4. [STORY-004: Metadata Management](./stories/story-004-metadata-mgmt.md)
5. [STORY-005: Document Processing Pipeline](./stories/story-005-doc-processing.md)