# Story: Conversation History

**Story ID**: STORY-011
**Epic**: EPIC-002 (Core Productivity Suite)
**Type**: New Feature
**Priority**: P1 (High)
**Points**: 5
**Sprint**: 9-10
**Status**: Ready for Testing
**Agent Model Used**: claude-sonnet-4-5-20250929

## User Story

**As a** user
**I want** to access my complete chat history
**So that** I can reference previous solutions and track my learning progress

## Context

Conversation history transforms the chatbot from a stateless Q&A tool into a persistent knowledge companion. Users can return to previous solutions, track their learning journey, and build on past conversations. This feature is essential for professional users who need to reference technical solutions weeks or months later.

## Current State

### Existing System
- **Chat Interface**: Currently stateless (no history persistence)
- **Messages**: Only stored in browser session storage
- **Database**: No conversation storage tables
- **User System**: Authentication and user management exist
- **Chat Handler**: Processes messages but doesn't persist them

### Gap Analysis
- Conversations lost when browser session ends
- No way to access previous solutions
- Cannot search past conversations
- No organization by topic or date
- Cannot share or reference old conversations
- No conversation metadata (title, tags, summary)

## Acceptance Criteria

### Core History Features
- [ ] Persistent conversation storage across sessions
- [ ] List view of all conversations with metadata
- [ ] Conversation details view (full message history)
- [ ] Automatic conversation titling (AI-generated)
- [ ] Search within conversation history
- [ ] Filter by date range
- [ ] Filter by topic/category
- [ ] Pagination for large history (20 conversations per page)

### Conversation Management
- [ ] Rename conversation title
- [ ] Add tags to conversations
- [ ] Star/favorite important conversations
- [ ] Archive old conversations
- [ ] Delete conversations (with confirmation)
- [ ] Bulk actions (archive, delete, tag)
- [ ] Conversation statistics (message count, date created/updated)

### Search & Discovery
- [ ] Full-text search across all messages
- [ ] Search by keywords, code snippets, topics
- [ ] Filter by tags
- [ ] Sort by date, relevance, message count
- [ ] Recent conversations quick access
- [ ] Most referenced conversations

### User Experience
- [ ] Seamless continuation of archived conversations
- [ ] Keyboard shortcuts for navigation
- [ ] Mobile-responsive history view
- [ ] Infinite scroll or pagination
- [ ] Loading states and skeletons
- [ ] Empty state for new users

## Technical Design

### Data Models

```python
class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    summary: Optional[str] = None  # AI-generated summary
    tags: List[str] = []
    is_favorite: bool = False
    is_archived: bool = False
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Dict[str, Any] = {}  # Code snippets, book references, etc.
    tokens_used: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationMetadata(BaseModel):
    """Extracted metadata about conversation"""
    topics: List[str]  # AI-detected topics
    mentioned_books: List[str]  # Referenced books
    code_languages: List[str]  # Languages discussed
    difficulty_level: str  # 'beginner', 'intermediate', 'advanced'
    primary_category: str  # RPG, SQL, CL, etc.
```

### Conversation Service

```python
class ConversationService:
    """Manage conversation history"""

    async def create_conversation(
        self,
        user_id: str,
        initial_message: str
    ) -> Conversation:
        """Create new conversation"""

        # Generate conversation title from first message
        title = await self._generate_title(initial_message)

        conversation = Conversation(
            user_id=user_id,
            title=title,
            message_count=1
        )

        await self._save_conversation(conversation)

        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = {}
    ) -> Message:
        """Add message to conversation"""

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata
        )

        await self._save_message(message)

        # Update conversation
        await self._update_conversation_stats(conversation_id)

        # Update metadata periodically
        conversation = await self._get_conversation(conversation_id)
        if conversation.message_count % 10 == 0:
            await self._update_conversation_metadata(conversation_id)

        return message

    async def list_conversations(
        self,
        user_id: str,
        filters: Dict[str, Any] = {},
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Conversation], int]:
        """List user's conversations with filtering"""

        query_conditions = [f"user_id = '{user_id}'"]

        # Apply filters
        if filters.get('is_archived') is not None:
            query_conditions.append(
                f"is_archived = {filters['is_archived']}"
            )

        if filters.get('is_favorite'):
            query_conditions.append("is_favorite = true")

        if filters.get('tags'):
            tags_condition = " OR ".join([
                f"'{tag}' = ANY(tags)" for tag in filters['tags']
            ])
            query_conditions.append(f"({tags_condition})")

        if filters.get('date_from'):
            query_conditions.append(
                f"created_at >= '{filters['date_from']}'"
            )

        if filters.get('date_to'):
            query_conditions.append(
                f"created_at <= '{filters['date_to']}'"
            )

        # Build query
        where_clause = " AND ".join(query_conditions)
        offset = (page - 1) * per_page

        # Get conversations
        conversations = await self._query_conversations(
            where_clause,
            limit=per_page,
            offset=offset,
            order_by="last_message_at DESC"
        )

        # Get total count
        total = await self._count_conversations(where_clause)

        return conversations, total

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Conversation], int]:
        """Full-text search across conversations"""

        # Search in conversation titles and message content
        search_query = f"""
            SELECT DISTINCT c.* FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = '{user_id}'
            AND (
                c.title ILIKE '%{query}%'
                OR c.summary ILIKE '%{query}%'
                OR m.content ILIKE '%{query}%'
                OR '{query}' = ANY(c.tags)
            )
            ORDER BY c.last_message_at DESC
            LIMIT {per_page} OFFSET {(page - 1) * per_page}
        """

        conversations = await self._execute_search(search_query)
        total = await self._count_search_results(user_id, query)

        return conversations, total

    async def get_conversation_with_messages(
        self,
        conversation_id: str,
        user_id: str
    ) -> Tuple[Conversation, List[Message]]:
        """Get conversation with all messages"""

        conversation = await self._get_conversation(conversation_id)

        # Verify ownership
        if conversation.user_id != user_id:
            raise PermissionError("Access denied")

        messages = await self._get_messages(conversation_id)

        return conversation, messages

    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Conversation:
        """Update conversation metadata"""

        conversation = await self._get_conversation(conversation_id)

        # Verify ownership
        if conversation.user_id != user_id:
            raise PermissionError("Access denied")

        # Apply updates
        for key, value in updates.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)

        conversation.updated_at = datetime.utcnow()

        await self._save_conversation(conversation)

        return conversation

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> None:
        """Delete conversation and all messages"""

        conversation = await self._get_conversation(conversation_id)

        # Verify ownership
        if conversation.user_id != user_id:
            raise PermissionError("Access denied")

        # Delete messages
        await self._delete_messages(conversation_id)

        # Delete conversation
        await self._delete_conversation(conversation_id)

    async def _generate_title(self, first_message: str) -> str:
        """Generate conversation title using Claude"""

        prompt = f"""Generate a concise title (max 60 characters) for a conversation that starts with:

"{first_message[:200]}"

Title should be descriptive but brief. Respond with ONLY the title, no explanation."""

        response = await self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        title = response.content[0].text.strip()

        # Fallback if too long
        if len(title) > 60:
            title = first_message[:57] + "..."

        return title

    async def _update_conversation_metadata(
        self,
        conversation_id: str
    ) -> None:
        """Update AI-generated metadata"""

        conversation, messages = await self._get_conversation_with_messages(
            conversation_id
        )

        # Build conversation context
        context = "\n".join([
            f"{msg.role}: {msg.content[:500]}"
            for msg in messages[-10:]  # Last 10 messages
        ])

        # Extract metadata using Claude
        prompt = f"""Analyze this conversation and extract metadata:

{context}

Provide:
1. Topics discussed (max 5)
2. Mentioned books (if any)
3. Programming languages discussed
4. Difficulty level (beginner/intermediate/advanced)
5. Primary category (RPG, SQL, CL, General, etc.)
6. Brief summary (2-3 sentences)

Respond in JSON format."""

        response = await self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse metadata
        metadata = json.loads(response.content[0].text)

        # Update conversation
        conversation.tags = metadata.get('topics', [])
        conversation.summary = metadata.get('summary', '')

        await self._save_conversation(conversation)
```

### Database Schema

```sql
-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    tags TEXT[] DEFAULT '{}',
    is_favorite BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Conversation metadata (for analytics)
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id SERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    topics TEXT[],
    mentioned_books TEXT[],
    code_languages TEXT[],
    difficulty_level TEXT,
    primary_category TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    UNIQUE(conversation_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user
ON conversations(user_id, last_message_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_tags
ON conversations USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_conversations_search
ON conversations USING GIN(to_tsvector('english', title || ' ' || COALESCE(summary, '')));

CREATE INDEX IF NOT EXISTS idx_messages_conversation
ON messages(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_messages_search
ON messages USING GIN(to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_conversations_favorite
ON conversations(user_id, is_favorite) WHERE is_favorite = true;

CREATE INDEX IF NOT EXISTS idx_conversations_archived
ON conversations(user_id, is_archived);
```

### API Endpoints

```python
# Conversation management
GET    /api/conversations              # List conversations
POST   /api/conversations              # Create conversation
GET    /api/conversations/{id}         # Get conversation with messages
PUT    /api/conversations/{id}         # Update conversation
DELETE /api/conversations/{id}         # Delete conversation
POST   /api/conversations/{id}/archive # Archive conversation
POST   /api/conversations/{id}/favorite # Toggle favorite

# Messages
POST   /api/conversations/{id}/messages # Add message
GET    /api/conversations/{id}/messages # Get messages

# Search
GET    /api/conversations/search       # Search conversations

# Bulk operations
POST   /api/conversations/bulk/archive # Archive multiple
POST   /api/conversations/bulk/delete  # Delete multiple
POST   /api/conversations/bulk/tag     # Tag multiple

# Analytics
GET    /api/conversations/stats        # User conversation statistics
```

## Implementation Tasks

### Backend Tasks
- [ ] Create conversation service
- [ ] Implement message persistence
- [ ] Build search functionality
- [ ] Add AI title generation
- [ ] Create metadata extraction
- [ ] Implement filtering logic
- [ ] Add pagination
- [ ] Create bulk operations
- [ ] Build conversation API endpoints
- [ ] Add conversation analytics

### Frontend Tasks
- [x] Create `/history` page
- [x] Build conversation list component
- [x] Implement conversation detail view
- [x] Add search interface
- [x] Create filter controls
- [x] Build tag management UI
- [x] Implement bulk actions
- [ ] Add keyboard shortcuts
- [x] Create mobile-responsive layout
- [x] Build empty states

### Database Tasks
- [ ] Create conversations table
- [ ] Create messages table
- [ ] Create conversation_analytics table
- [ ] Add full-text search indexes
- [ ] Create migration script
- [ ] Optimize query performance

### Integration Tasks
- [ ] Integrate with existing chat interface
- [ ] Wire conversation persistence to chat
- [ ] Connect search to frontend
- [ ] Test pagination
- [ ] Validate bulk operations

## Testing Requirements

### Unit Tests
- [ ] Conversation CRUD operations
- [ ] Message persistence
- [ ] Search functionality
- [ ] Filtering logic
- [ ] Title generation

### Integration Tests
- [ ] Complete conversation flow
- [ ] Search across conversations
- [ ] Bulk operations
- [ ] Pagination
- [ ] Metadata updates

### E2E Tests
- [ ] Start conversation → save → retrieve
- [ ] Search for specific message
- [ ] Filter by date/tags
- [ ] Archive conversations
- [ ] Delete conversations
- [ ] Continue archived conversation

## Success Metrics

- **Retention**: 40% of users return to view history
- **Search Usage**: 20% of users search history
- **Conversation Duration**: Increased by 30% (users continue conversations)
- **Average Conversations**: 10+ per active user
- **Favorite Rate**: 15% of conversations favorited
- **Archive Rate**: 30% of old conversations archived

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Performance tested with 1000+ conversations
- [ ] Search performance optimized
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring confirms stable operation

## Dependencies

- Existing chat interface
- User authentication system
- PostgreSQL database
- Claude API for title/summary generation

## Risks

- **Risk**: Database performance with large conversation histories
  - **Mitigation**: Proper indexing, pagination, query optimization

- **Risk**: AI title generation costs
  - **Mitigation**: Cache titles, only regenerate on request

- **Risk**: User confusion with too many conversations
  - **Mitigation**: Good search, smart defaults, archiving

## Future Enhancements

- Conversation folders/projects
- Share conversations publicly
- Conversation templates
- Smart suggestions based on history
- Conversation insights/analytics
- Auto-tagging with ML
- Conversation threading

---

## Notes

This feature significantly increases user retention and platform stickiness. Focus on performant search and intuitive organization.

---

## Dev Agent Record

### Implementation Summary

**Date**: 2025-11-11
**Developer**: Dexter (Dev Agent)
**Backend Status**: Previously completed (70%) - see STORY-011-STATUS.md
**Frontend Status**: 100% complete

### Frontend Implementation Details

#### Files Created (6 new files)
```
frontend/services/conversationService.ts          (380 lines) - API client with full TypeScript types
frontend/app/history/page.tsx                     (220 lines) - Main history page with split-view layout
frontend/components/ConversationList.tsx          (180 lines) - Conversation list with pagination
frontend/components/ConversationCard.tsx          (90 lines)  - Individual conversation card component
frontend/components/ConversationDetail.tsx        (300 lines) - Full conversation detail view with actions
frontend/components/ConversationSearch.tsx        (200 lines) - Search and filter component
```

#### Files Modified (1)
```
frontend/app/page.tsx - Added "History" button to main chat header
```

**Total Frontend Code**: ~1,370 lines of production code

### Feature Implementation Status

#### ✅ Completed Features
1. **API Service Layer**
   - Full TypeScript types matching backend models
   - All CRUD operations for conversations
   - Search with debouncing
   - Filter by date range, favorites, archived status
   - Pagination support (20 conversations per page)
   - Bulk operations (archive, delete, tag)
   - Auth token handling from localStorage
   - User ID extraction from JWT

2. **History Page (`/history`)**
   - Split-view layout (conversation list + detail view)
   - Fully responsive (mobile and desktop)
   - Stats summary in header (total conversations, messages, favorites)
   - URL-based conversation selection
   - Loading states throughout
   - Error handling with user-friendly messages

3. **Conversation List Component**
   - Displays conversation cards with metadata
   - Full pagination with page numbers and ellipsis
   - Loading skeleton states
   - Empty state for new users
   - "Showing X to Y of Z" counter
   - Mobile-first responsive design

4. **Conversation Card Component**
   - Shows title, summary, message count
   - Relative timestamps ("2h ago", "3d ago", "Nov 10")
   - Tag display (first 3 tags + overflow count)
   - Favorite/archive status icons
   - Selected state styling
   - Hover effects

5. **Conversation Detail Component**
   - Full message history display with scrolling
   - User vs assistant message styling
   - Inline title editing (click to edit)
   - Toggle favorite button
   - Toggle archive button
   - Delete with confirmation modal
   - Mobile back button for navigation
   - Auto-scroll to bottom on load
   - Formatted timestamps

6. **Search and Filter Component**
   - Debounced search input (500ms delay)
   - Collapsible filter panel
   - Status filters (favorites only, hide archived, archived only)
   - Date range picker (from/to dates)
   - Quick date filters (Today, Last 7 days, Last 30 days)
   - Active filter counter badge
   - Clear all filters button

7. **Main Chat Integration**
   - Added "History" button to header
   - Clock icon for easy identification
   - Responsive (hides text on mobile)
   - Smooth navigation to /history page

#### ⏳ Pending/Not Implemented
1. **Keyboard Shortcuts** - Not implemented (low priority)
2. **Backend Testing** - Needs validation
3. **End-to-End Testing** - Pending deployment

### Testing Status

#### 🔴 Not Yet Tested
- Backend API endpoints (conversation service may not be fully working per status notes)
- Frontend-backend integration
- Search functionality
- Filter operations
- Pagination
- Conversation actions (favorite, archive, delete)
- Bulk operations

#### Testing Recommendations
1. **Backend Verification First**
   - Test `/api/conversations` endpoint
   - Verify conversation creation during chat
   - Check database tables exist and are populated
   - Confirm JWT auth is working

2. **Frontend Testing**
   - Deploy to Netlify
   - Navigate to /history page
   - Verify empty state shows if no conversations
   - Test search and filters
   - Test conversation selection
   - Test conversation actions
   - Verify mobile responsiveness

3. **Integration Testing**
   - Start a chat conversation
   - Verify it appears in /history
   - Check conversation title generation
   - Test favorite/archive/delete operations
   - Validate pagination with multiple conversations

### Known Limitations

1. **Backend Integration**: Backend conversation service may not be fully operational (per STORY-011-STATUS.md)
2. **AI Title Generation**: May be using fallback (truncated first message) if anthropic package not installed
3. **Keyboard Shortcuts**: Not implemented - would require additional library or custom key event handling
4. **Real-time Updates**: No WebSocket integration for live updates across tabs/devices

### File List (Modified/Created)
- ✅ `frontend/services/conversationService.ts` (NEW)
- ✅ `frontend/app/history/page.tsx` (NEW)
- ✅ `frontend/components/ConversationList.tsx` (NEW)
- ✅ `frontend/components/ConversationCard.tsx` (NEW)
- ✅ `frontend/components/ConversationDetail.tsx` (NEW)
- ✅ `frontend/components/ConversationSearch.tsx` (NEW)
- ✅ `frontend/app/page.tsx` (MODIFIED - added History button)
- ✅ `docs/prd/stories/story-011-conversation-history.md` (MODIFIED - completion notes)

### Completion Notes

**Frontend Development**: 100% complete for core functionality
**Backend Development**: Previously completed (~70%) but requires testing
**Overall Story Progress**: ~90% complete (pending testing and backend validation)

**Next Steps**:
1. Deploy frontend to Netlify (push to GitHub)
2. Test backend API endpoints manually
3. Perform end-to-end testing of full conversation flow
4. Address any bugs or issues discovered
5. Update status to "Complete" after successful testing

### Debug Log References
- Backend implementation: See `/docs/prd/stories/STORY-011-STATUS.md`
- Frontend build logs: TBD after deployment
- Integration test results: TBD

---

**Implementation Date**: 2025-11-11
**Developer**: Dexter
**Status**: ✅ Frontend Complete | ⏳ Awaiting Backend Testing
