# Design Document

## Overview

This design addresses a critical bug in the chat handler's source enrichment feature. The chat handler attempts to enrich search results with book and author metadata from the database, but fails due to an incorrect column name in the SQL query. The code references `da.document_id` when the actual column name in the `document_authors` table is `da.book_id`, causing all enrichment attempts to fail with "column da.document_id does not exist" errors.

The fix is straightforward: update the SQL query in the `_enrich_source_metadata()` method to use the correct column name `book_id` instead of `document_id`.

## Architecture

### Current Architecture

The chat handler follows this flow:
1. User submits a query
2. Vector store performs semantic search and returns relevant document chunks
3. Chat handler formats sources by calling `_format_sources()`
4. For each source, `_enrich_source_metadata()` is called to fetch book/author data
5. Enriched metadata is returned to the frontend for display

### Problem Location

The bug exists in `backend/chat_handler.py` in the `_enrich_source_metadata()` method at line ~491:

```python
authors = await conn.fetch("""
    SELECT 
        a.id,
        a.name,
        a.site_url,
        da.author_order
    FROM document_authors da
    JOIN authors a ON da.author_id = a.id
    WHERE da.document_id = $1  # ❌ WRONG: should be da.book_id
    ORDER BY da.author_order
""", book_data['id'])
```

### Database Schema

The correct schema (from migration 003) is:

**books table:**
- `id` (PRIMARY KEY)
- `filename` (used for lookup)
- `title`
- `author` (legacy field)
- `mc_press_url`
- `article_url`
- `document_type`

**authors table:**
- `id` (PRIMARY KEY)
- `name` (UNIQUE)
- `site_url`

**document_authors table:**
- `id` (PRIMARY KEY)
- `book_id` (FK to books.id) ← **This is the correct column name**
- `author_id` (FK to authors.id)
- `author_order`

## Components and Interfaces

### Modified Component

**ChatHandler._enrich_source_metadata()**
- **Input**: `filename: str` - The document filename to enrich
- **Output**: `Dict[str, Any]` - Enriched metadata containing author, URLs, and document type
- **Change**: Update SQL query to use `book_id` instead of `document_id`

### Unchanged Components

- `ChatHandler._format_sources()` - Calls enrichment, no changes needed
- `ChatHandler.stream_response()` - Orchestrates chat flow, no changes needed
- Frontend `CompactSources.tsx` - Already handles enriched metadata correctly

## Data Models

### Enriched Metadata Structure

```python
{
    "author": str,              # Comma-separated author names
    "mc_press_url": str,        # MC Store purchase link (or empty string)
    "article_url": str | None,  # Article link (or None)
    "document_type": str,       # "book" or "article"
    "authors": [                # Array of author objects
        {
            "id": int,
            "name": str,
            "site_url": str | None,
            "order": int
        }
    ]
}
```

### Empty Metadata (Fallback)

When enrichment fails or no data is found:
```python
{}  # Empty dict - caller uses fallback values
```

## Error Handling

### Current Error Handling (Preserved)

The enrichment method already has proper error handling:

1. **Missing DATABASE_URL**: Logs warning, returns empty dict
2. **Database connection failure**: Catches exception, logs error with traceback, returns empty dict
3. **Book not found**: Logs info message, returns empty dict
4. **Query execution error**: Catches exception, logs error with traceback, returns empty dict

### Error Recovery Flow

```
_enrich_source_metadata() fails
    ↓
Returns empty dict {}
    ↓
_format_sources() uses fallback values
    ↓
Source displayed with "Unknown" author
    ↓
Chat response still works
```

This graceful degradation ensures chat functionality is never blocked by enrichment failures.

## Testing Strategy

### Unit Tests

**Test 1: Verify correct column name in query**
- Mock asyncpg connection
- Call `_enrich_source_metadata()` with a test filename
- Verify the SQL query uses `da.book_id` not `da.document_id`
- Assert no UndefinedColumnError is raised

**Test 2: Successful enrichment with authors**
- Mock database to return book with multiple authors
- Verify returned metadata contains all author objects
- Verify authors are ordered by author_order
- Verify all fields are populated correctly

**Test 3: Fallback to legacy author field**
- Mock database to return book with no document_authors records
- Verify returned metadata uses legacy author field
- Verify authors array is empty

**Test 4: Book not found**
- Mock database to return no book record
- Verify empty dict is returned
- Verify appropriate log message

**Test 5: Database connection failure**
- Mock asyncpg.connect() to raise exception
- Verify empty dict is returned
- Verify error is logged with traceback

### Integration Tests

**Test 6: End-to-end chat with enrichment**
- Submit a chat query that returns known documents
- Verify response sources contain enriched metadata
- Verify author names are not "Unknown"
- Verify URLs are populated when available

**Test 7: Frontend display verification**
- Submit chat query
- Verify CompactSources component receives enriched data
- Verify author links are rendered for authors with site_url
- Verify Buy/Read buttons appear based on document_type

### Manual Testing on Railway

**Test 8: Production database query**
- Deploy fix to Railway
- Submit test query: "Tell me about DB2"
- Check Railway logs for successful enrichment messages
- Verify no "column da.document_id does not exist" errors
- Verify frontend displays correct author information

## Implementation Notes

### The Fix

Change line ~491 in `backend/chat_handler.py`:

```python
# BEFORE (incorrect)
WHERE da.document_id = $1

# AFTER (correct)
WHERE da.book_id = $1
```

### Verification

After the fix, Railway logs should show:
```
INFO:backend.chat_handler:Found book: [title] by [author]
INFO:backend.chat_handler:Using multi-author data: [author names]
INFO:backend.chat_handler:Enrichment result: {'author': '...', 'mc_press_url': '...', ...}
```

Instead of:
```
ERROR:backend.chat_handler:Error enriching source metadata: column da.document_id does not exist
INFO:backend.chat_handler:Enrichment result: {}
```

### Deployment

1. Update `backend/chat_handler.py` with the fix
2. Commit and push to trigger Railway deployment
3. Monitor Railway logs during next chat query
4. Verify enrichment succeeds
5. Test frontend display of enriched metadata

## Performance Considerations

### Database Queries

The enrichment performs two queries per unique filename:
1. SELECT from books table (indexed on filename)
2. SELECT from document_authors + authors (indexed on book_id and author_id)

These queries are fast (<10ms each) and only execute once per unique filename in the result set.

### Caching Opportunities (Future)

Currently, enrichment happens on every chat request. Future optimization could:
- Cache enriched metadata in memory (TTL: 1 hour)
- Pre-compute enrichment during document upload
- Store enriched metadata in vector store metadata field

However, the current approach is acceptable given:
- Typical result sets have 5-12 sources
- Most sources are from the same 2-3 books
- Query time is negligible compared to LLM response time

## Rollback Plan

If the fix causes unexpected issues:

1. **Immediate**: Revert commit in Git
2. **Railway**: Trigger redeployment of previous version
3. **Verification**: Confirm chat still works (with "Unknown" authors)
4. **Investigation**: Review logs to identify new issue
5. **Fix**: Address root cause and redeploy

The fix is low-risk because:
- It only changes a column name in a SQL query
- Error handling ensures chat works even if enrichment fails
- No schema changes or data migrations required
- Easy to verify success/failure in logs


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Correct column name in SQL query

*For any* book record found in the books table, the SQL query to retrieve authors SHALL use `da.book_id` (not `da.document_id`) to join the document_authors table

**Validates: Requirements 1.2, 1.3**

**Rationale**: This is the core bug fix. The query must use the correct column name that exists in the database schema. Using the wrong column name causes `UndefinedColumnError` and prevents all enrichment from working.

### Property 2: Author ordering preservation

*For any* document with multiple authors, the returned authors array SHALL be ordered by the author_order field in ascending order

**Validates: Requirements 1.5**

**Rationale**: Author order matters for proper attribution. The first author (order=0) should appear first in the list, maintaining the authorship hierarchy defined in the database.

### Property 3: Legacy author fallback

*For any* book that has no records in the document_authors table, the enriched metadata SHALL use the value from the books.author field and return an empty authors array

**Validates: Requirements 1.6**

**Rationale**: Ensures backward compatibility with books that haven't been migrated to the multi-author system. The legacy author field provides a fallback so enrichment never returns completely empty data when a book exists.

### Property 4: Complete metadata structure

*For any* successful enrichment, the returned metadata SHALL contain all required fields: author (string), mc_press_url (string), article_url (string or None), document_type (string), and authors (array)

**Validates: Requirements 2.1, 2.2, 2.3**

**Rationale**: The frontend expects a consistent metadata structure. Missing fields would cause rendering errors or incorrect display. All fields must be present even if some values are empty/null.

### Property 5: Graceful degradation on failure

*For any* enrichment failure (missing DATABASE_URL, connection error, book not found, or query error), the function SHALL return an empty dict and the caller SHALL use fallback values resulting in "Unknown" author

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

**Rationale**: Enrichment failures must never break chat functionality. By returning an empty dict, the system gracefully degrades to showing "Unknown" author while still delivering the chat response to the user.

### Property 6: Comprehensive error logging

*For any* error during enrichment, the system SHALL log the error message and full stack trace to aid debugging

**Validates: Requirements 3.5**

**Rationale**: When enrichment fails in production, developers need detailed error information to diagnose the issue. Stack traces are essential for identifying the root cause, especially for database-related errors.

### Property 7: Enrichment attempt logging

*For any* enrichment attempt, the system SHALL log the filename being enriched and, if successful, the book title and author information found

**Validates: Requirements 3.1, 3.3, 3.4**

**Rationale**: Logging enrichment attempts and results provides visibility into whether the feature is working correctly in production. This helps verify the fix is deployed and functioning as expected.
