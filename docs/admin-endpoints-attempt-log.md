# Admin Endpoints Implementation Attempts - Story 004

**Date**: September 23, 2025
**Issue**: Admin endpoints for metadata management were not working in production

## Summary of Attempts and Issues

### The Problem
- The `/admin/documents` endpoints were needed to display document IDs, page counts, and allow metadata management
- These endpoints needed to query the `books` table (created by migration) instead of `documents` table
- The frontend falls back to `/documents` endpoint when admin endpoints return 404, which doesn't have proper IDs or metadata

## Attempt 1: Using admin_documents.py Module

### What We Tried
Created `admin_documents.py` with full-featured admin endpoints using the vector store's `_get_connection()` method.

### Why It Failed
- The `_get_connection()` method doesn't exist on the production vector store
- The import was failing silently in production
- The router was never being included in the FastAPI app

### Code Location
- File: `backend/admin_documents.py` (still exists)

## Attempt 2: Simplified admin_documents_simple.py

### What We Tried
Created `admin_documents_simple.py` that used direct `asyncpg.connect()` calls instead of relying on vector store methods.

### Why It Failed
- The import was still failing in production (possibly due to module path issues)
- The admin_docs_router was not being included
- Production environment couldn't find the module

### Code Location
- File: `backend/admin_documents_simple.py` (still exists)

## Attempt 3: Embedding Endpoints Directly in main.py

### What We Tried
To guarantee the endpoints would load, we embedded them directly in main.py. This included:

```python
# ADMIN DOCUMENTS ENDPOINTS - EMBEDDED DIRECTLY TO ENSURE THEY LOAD
@app.get("/admin/documents")
async def admin_list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    category: str = Query(""),
    sort_by: str = Query("title"),
    sort_direction: str = Query("asc")
):
    """Admin endpoint to list all documents from books table with proper IDs"""
    import asyncpg
    import asyncio

    try:
        # Add timeout to prevent hanging
        conn = await asyncio.wait_for(
            asyncpg.connect(os.getenv('DATABASE_URL')),
            timeout=5.0
        )

        # Get all books
        rows = await conn.fetch("""
            SELECT id, filename, title, author, category, subcategory,
                   total_pages, file_hash, processed_at
            FROM books
            ORDER BY id DESC
        """)

        documents = []
        for row in rows:
            documents.append({
                'id': row['id'],
                'filename': row['filename'],
                'title': row['title'] or row['filename'].replace('.pdf', ''),
                'author': row['author'],
                'category': row['category'],
                'subcategory': row['subcategory'],
                'total_pages': row['total_pages'] or 0,
                'file_hash': row['file_hash'],
                'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None
            })

        await conn.close()

        # Apply filters
        if search:
            search_lower = search.lower()
            documents = [d for d in documents
                        if search_lower in (d.get('title') or '').lower()
                        or search_lower in (d.get('author') or '').lower()]

        if category:
            documents = [d for d in documents if d.get('category') == category]

        # Sort
        reverse = sort_direction == 'desc'
        documents.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)

        # Paginate
        total = len(documents)
        start = (page - 1) * per_page
        end = start + per_page

        return {
            "documents": documents[start:end],
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }

    except asyncio.TimeoutError:
        print("Admin documents timeout - database connection failed")
        return {"documents": [], "error": "Database connection timeout"}
    except Exception as e:
        print(f"Admin documents error: {e}")
        import traceback
        print(traceback.format_exc())
        return {"documents": [], "error": str(e)}

@app.get("/admin/documents/export")
async def admin_export_csv():
    """Export all documents as CSV"""
    import asyncpg
    import asyncio
    from fastapi.responses import StreamingResponse
    import csv
    import io

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(os.getenv('DATABASE_URL')),
            timeout=5.0
        )

        rows = await conn.fetch("""
            SELECT id, filename, title, author, category, subcategory,
                   year, tags, description, mc_press_url, total_pages, processed_at
            FROM books
            ORDER BY id DESC
        """)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['id', 'filename', 'title', 'author', 'category',
                        'subcategory', 'year', 'tags', 'description',
                        'mc_press_url', 'total_pages', 'processed_at'])

        # Data
        for row in rows:
            writer.writerow([
                row['id'],
                row['filename'],
                row['title'] or '',
                row['author'] or '',
                row['category'] or '',
                row['subcategory'] or '',
                row['year'] or '',
                ','.join(row['tags']) if row['tags'] else '',
                row['description'] or '',
                row['mc_press_url'] or '',
                row['total_pages'] or 0,
                row['processed_at'].isoformat() if row['processed_at'] else ''
            ])

        await conn.close()

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=documents_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )

    except Exception as e:
        return {"error": str(e)}

@app.get("/admin/stats")
async def admin_stats():
    """Get admin dashboard statistics"""
    import asyncpg
    import asyncio

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(os.getenv('DATABASE_URL')),
            timeout=5.0
        )

        doc_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        last_upload = await conn.fetchval("SELECT MAX(processed_at) FROM books")

        await conn.close()

        return {
            "total_documents": doc_count or 0,
            "total_chunks": chunk_count or 0,
            "last_upload": last_upload.isoformat() if last_upload else None
        }

    except Exception as e:
        return {"total_documents": 0, "total_chunks": 0, "error": str(e)}
```

### Why It Failed
- The endpoints did load (they showed up in the OpenAPI spec)
- But the database connections were timing out or causing network errors
- The `asyncpg.connect()` calls were interfering with the main app's database connections
- This broke login, document counting on home page, and caused general network errors
- The entire app became unstable

## Attempt 4: Added Debug Endpoint

### What We Tried
Added a debug endpoint to diagnose the database connection issue:

```python
@app.get("/debug-db")
async def debug_database():
    """Debug endpoint to check database connectivity"""
    import asyncpg
    import asyncio

    db_url = os.getenv('DATABASE_URL', 'Not set')

    # Mask password in URL for security
    if db_url and '@' in db_url:
        parts = db_url.split('@')
        if '://' in parts[0]:
            proto_and_creds = parts[0].split('://')
            if ':' in proto_and_creds[1]:
                user_pass = proto_and_creds[1].split(':')
                masked = f"{proto_and_creds[0]}://{user_pass[0]}:****@{parts[1]}"
            else:
                masked = db_url
        else:
            masked = db_url
    else:
        masked = db_url

    result = {
        "database_url_set": db_url != 'Not set',
        "database_url_masked": masked,
        "connection_test": "pending"
    }

    if db_url != 'Not set':
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(db_url),
                timeout=5.0
            )

            # Test books table
            books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            result["connection_test"] = "success"
            result["books_count"] = books_count

            await conn.close()
        except asyncio.TimeoutError:
            result["connection_test"] = "timeout"
            result["error"] = "Connection timed out after 5 seconds"
        except Exception as e:
            result["connection_test"] = "failed"
            result["error"] = str(e)

    return result
```

### Result
Never got to test it because the app was completely broken by this point.

## Root Causes Identified

1. **Database Connection Conflicts**: Creating new `asyncpg.connect()` connections was conflicting with the existing connection pool
2. **Import Issues**: Production environment has different module paths than local
3. **Async Context Issues**: The way we were handling async connections was causing the entire app to have network errors
4. **No Connection Pool Reuse**: We were creating new connections instead of using the existing pool

## What Actually Needs to Happen

1. **Reuse Existing Database Connection**: The admin endpoints need to use the same connection pool as the main app
2. **Proper Error Handling**: Errors in admin endpoints shouldn't break the entire app
3. **Correct Module Structure**: Admin functionality should be in a module that's guaranteed to load
4. **Test in Production-like Environment**: Need to test with Railway's actual database configuration

## Files Still Present

These files contain the attempted implementations and can be referenced:
- `backend/admin_documents.py` - Full implementation with vector store dependency
- `backend/admin_documents_simple.py` - Simplified version with direct asyncpg
- `backend/migration_endpoint.py` - Migration endpoints that were added

## Lessons Learned

1. Don't create new database connections when there's an existing pool
2. Test database connectivity in production environment before making assumptions
3. Isolated functionality shouldn't break core features
4. Always have a rollback plan when modifying production code
5. The frontend's fallback behavior masks backend issues (it falls back to `/documents` when `/admin/documents` fails)

## Next Steps Recommendation

1. Use the existing vector store's connection pool instead of creating new connections
2. Add the admin endpoints as a proper router module that's imported correctly
3. Test with Railway's actual DATABASE_URL format
4. Implement proper error boundaries so admin features don't break core functionality
5. Consider using the existing `/documents` endpoint and enhancing it rather than creating new endpoints

---

**Note**: The migration was successful - the `books` table exists with all 115 documents and proper page counts. The issue is only with accessing this data through the admin endpoints.