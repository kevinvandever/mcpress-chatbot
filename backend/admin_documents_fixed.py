"""
Admin document management endpoints that properly use the existing database connection pool
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
import csv
import io
import logging
import time

# Re-use the existing admin auth dependency
try:
    from auth_routes import get_current_user
except ImportError:
    from backend.auth_routes import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Pydantic request/response models for document removal ---

class BulkDeleteRequest(BaseModel):
    ids: List[int]

class DocumentDeletionDetail(BaseModel):
    id: int
    filename: str
    chunks_deleted: int

class SingleRemovalSummary(BaseModel):
    deleted: bool
    document_id: int
    filename: str
    title: str
    chunks_deleted: int
    author_associations_deleted: int
    metadata_history_deleted: int

class BulkRemovalSummary(BaseModel):
    deleted_count: int
    not_found_ids: List[int]
    deleted_documents: List[DocumentDeletionDetail]
    total_chunks_deleted: int
    total_author_associations_deleted: int
    total_metadata_history_deleted: int

# --- Reindex state ---
_reindex_in_progress = False
_last_reindex_completed_at: Optional[str] = None
_last_reindex_duration: Optional[float] = None

# Global reference to vector store (will be set by main.py)
_vector_store = None

# Global cache invalidation function (will be set by main.py)
_global_cache_invalidator = None

def set_global_cache_invalidator(invalidator_func):
    """Set the global cache invalidation function"""
    global _global_cache_invalidator
    _global_cache_invalidator = invalidator_func
    logger.info("✅ Global cache invalidator set for admin documents")

# Cache invalidation tracking
_cache_invalidation_timestamp = 0

def invalidate_cache():
    """Mark cache as invalid by updating timestamp"""
    global _cache_invalidation_timestamp, _global_cache_invalidator
    _cache_invalidation_timestamp = time.time()
    logger.info(f"📤 Cache invalidated at {_cache_invalidation_timestamp}")
    
    # Also invalidate global cache if available
    if _global_cache_invalidator:
        try:
            _global_cache_invalidator()
        except Exception as e:
            logger.warning(f"Failed to invalidate global cache: {e}")

def should_refresh_cache(refresh: bool = False) -> bool:
    """Determine if cache should be refreshed based on refresh parameter or invalidation"""
    global _cache_invalidation_timestamp
    
    if refresh:
        logger.info("🔄 Explicit cache refresh requested")
        return True
    
    # For now, we'll always refresh since we don't have a persistent cache
    # In the future, this could check against a cache timestamp
    return True

# Global reference to vector store (will be set by main.py)
_vector_store = None

def set_vector_store(vector_store):
    """Set the vector store instance to use for database operations"""
    global _vector_store
    _vector_store = vector_store
    logger.info("✅ Admin documents router initialized with vector store")

async def get_db_connection():
    """Get a database connection from the existing pool"""
    if not _vector_store:
        raise HTTPException(status_code=500, detail="Database not initialized")

    if not _vector_store.pool:
        await _vector_store.init_database()

    return _vector_store.pool

@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    category: str = Query(""),
    sort_by: str = Query("title"),
    sort_direction: str = Query("asc"),
    refresh: bool = Query(False, description="Force refresh cache and bypass any caching mechanisms")
):
    """List all documents from books table with proper IDs and metadata"""
    try:
        # Check if we should refresh cache
        force_refresh = should_refresh_cache(refresh)
        if force_refresh:
            logger.info("🔄 Cache refresh requested - bypassing any caching mechanisms")
        
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # First check if books table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'books'
                )
            """)

            if not table_exists:
                logger.info("Books table doesn't exist, creating it now...")
                # Create books table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id SERIAL PRIMARY KEY,
                        filename TEXT UNIQUE NOT NULL,
                        title TEXT,
                        author TEXT,
                        category TEXT,
                        subcategory TEXT,
                        description TEXT,
                        tags TEXT[],
                        mc_press_url TEXT,
                        article_url TEXT,
                        document_type TEXT DEFAULT 'book',
                        year INTEGER,
                        total_pages INTEGER,
                        file_hash TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Migrate data from documents table with better author extraction
                logger.info("Migrating data from documents to books table...")
                await conn.execute("""
                    INSERT INTO books (filename, title, author, category, total_pages, processed_at)
                    SELECT DISTINCT ON (filename)
                        filename,
                        COALESCE((metadata->>'title')::text, REPLACE(filename, '.pdf', '')),
                        CASE 
                            WHEN (metadata->>'author')::text IS NOT NULL 
                                 AND (metadata->>'author')::text != '' 
                                 AND (metadata->>'author')::text != 'Unknown'
                            THEN (metadata->>'author')::text
                            ELSE 'Unknown Author'
                        END,
                        COALESCE((metadata->>'category')::text, 'General'),
                        MAX(page_number) OVER (PARTITION BY filename),
                        MIN(created_at) OVER (PARTITION BY filename)
                    FROM documents
                    WHERE filename IS NOT NULL
                    ON CONFLICT (filename) DO UPDATE SET
                        author = CASE 
                            WHEN (EXCLUDED.author != 'Unknown Author' AND EXCLUDED.author IS NOT NULL)
                            THEN EXCLUDED.author
                            ELSE books.author
                        END,
                        title = CASE 
                            WHEN (EXCLUDED.title IS NOT NULL AND EXCLUDED.title != '')
                            THEN EXCLUDED.title
                            ELSE books.title
                        END
                """)

                logger.info("Migration complete")
                
                # Update existing books with better author data if they currently have "Unknown Author"
                logger.info("Updating existing books with better author data...")
                updated_count = await conn.fetchval("""
                    UPDATE books 
                    SET author = subq.real_author
                    FROM (
                        SELECT DISTINCT ON (filename)
                            filename,
                            CASE 
                                WHEN (metadata->>'author')::text IS NOT NULL 
                                     AND (metadata->>'author')::text != '' 
                                     AND (metadata->>'author')::text != 'Unknown'
                                THEN (metadata->>'author')::text
                                ELSE NULL
                            END as real_author
                        FROM documents
                        WHERE filename IS NOT NULL
                        AND (metadata->>'author')::text IS NOT NULL 
                        AND (metadata->>'author')::text != '' 
                        AND (metadata->>'author')::text != 'Unknown'
                    ) subq
                    WHERE books.filename = subq.filename
                    AND (books.author = 'Unknown Author' OR books.author IS NULL)
                    AND subq.real_author IS NOT NULL
                    RETURNING books.id
                """)
                
                if updated_count:
                    logger.info(f"Updated {len(updated_count) if isinstance(updated_count, list) else 'some'} books with real author data")

            # FIXED: Use proper multi-author query structure like chat system
            # Check if multi-author tables exist and have correct structure
            authors_table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'authors'
                )
            """)
            
            document_authors_table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'document_authors'
                )
            """)

            # Check if document_authors has the correct column structure
            has_correct_structure = False
            if document_authors_table_exists:
                try:
                    # Test if the expected columns exist
                    await conn.fetchval("""
                        SELECT book_id, author_id, author_order 
                        FROM document_authors 
                        LIMIT 1
                    """)
                    has_correct_structure = True
                    logger.info("✅ Multi-author tables have correct structure")
                except Exception as e:
                    logger.info(f"❌ Multi-author tables exist but have wrong structure: {e}")
                    has_correct_structure = False

            # Use multi-author query if tables exist and have correct structure
            if authors_table_exists and document_authors_table_exists and has_correct_structure:
                # Multi-author query with correct column names (book_id, not document_id)
                logger.info("Using multi-author query with correct column structure")
                query = """
                    SELECT DISTINCT b.id, b.filename, b.title, b.category, 
                           COALESCE(b.document_type, 'book') as document_type, 
                           b.mc_press_url, 
                           COALESCE(b.article_url, '') as article_url,
                           b.created_at,
                           COALESCE(a.name, b.author, 'Unknown Author') as author_name,
                           a.site_url as author_site_url,
                           da.author_order,
                           (SELECT COUNT(*) FROM documents d WHERE d.filename = b.filename) AS chunk_count
                    FROM books b
                    LEFT JOIN document_authors da ON b.id = da.book_id
                    LEFT JOIN authors a ON da.author_id = a.id
                    WHERE 1=1
                """
                
                count_query = """
                    SELECT COUNT(DISTINCT b.id) FROM books b
                    LEFT JOIN document_authors da ON b.id = da.book_id
                    LEFT JOIN authors a ON da.author_id = a.id
                    WHERE 1=1
                """
                
                sort_field_map = {
                    'id': 'b.id',
                    'title': 'b.title', 
                    'author': 'COALESCE(a.name, b.author)',
                    'author_name': 'COALESCE(a.name, b.author)',
                    'document_type': 'b.document_type'
                }
                
                use_multi_author = True
            else:
                # Simple query without JOINs (current state)
                logger.info("Using simple query without multi-author JOINs")
                query = """
                    SELECT b.id, b.filename, b.title, b.category, 
                           COALESCE(b.document_type, 'book') as document_type, 
                           b.mc_press_url, 
                           COALESCE(b.article_url, '') as article_url,
                           b.created_at,
                           COALESCE(b.author, 'Unknown Author') as author_name,
                           (SELECT COUNT(*) FROM documents d WHERE d.filename = b.filename) AS chunk_count
                    FROM books b
                    WHERE 1=1
                """
                
                count_query = """
                    SELECT COUNT(*) FROM books b
                    WHERE 1=1
                """
                
                sort_field_map = {
                    'id': 'b.id',
                    'title': 'b.title', 
                    'author': 'b.author',
                    'author_name': 'b.author',
                    'document_type': 'b.document_type'
                }
                
                use_multi_author = False

            params = []
            param_count = 0

            # Add search filter
            if search:
                param_count += 1
                if use_multi_author:
                    query += f" AND (LOWER(b.title) LIKE LOWER(${param_count}) OR LOWER(COALESCE(a.name, b.author)) LIKE LOWER(${param_count}))"
                    count_query += f" AND (LOWER(b.title) LIKE LOWER('%{search}%') OR LOWER(COALESCE(a.name, b.author)) LIKE LOWER('%{search}%'))"
                else:
                    query += f" AND (LOWER(b.title) LIKE LOWER(${param_count}) OR LOWER(b.author) LIKE LOWER(${param_count}))"
                    count_query += f" AND (LOWER(b.title) LIKE LOWER('%{search}%') OR LOWER(b.author) LIKE LOWER('%{search}%'))"
                params.append(f"%{search}%")

            # Add category filter
            if category:
                param_count += 1
                query += f" AND b.category = ${param_count}"
                count_query += f" AND b.category = '{category}'"
                params.append(category)

            # Add sorting
            valid_sort_fields = ['id', 'title', 'author_name', 'document_type']
            if sort_by not in valid_sort_fields:
                sort_by = 'title'
            
            db_sort_field = sort_field_map.get(sort_by, 'b.title')
            sort_dir = 'DESC' if sort_direction == 'desc' else 'ASC'
            
            if use_multi_author:
                query += f" ORDER BY {db_sort_field} {sort_dir}, da.author_order ASC"
            else:
                query += f" ORDER BY {db_sort_field} {sort_dir}"

            # Get total count before pagination
            total = await conn.fetchval(count_query)

            # Add pagination
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(per_page)

            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append((page - 1) * per_page)

            # Execute query
            rows = await conn.fetch(query, *params)

            # Process results
            if use_multi_author:
                # Group authors by document since we have one row per document-author pair
                documents_dict = {}
                for row in rows:
                    doc_id = row['id']
                    if doc_id not in documents_dict:
                        documents_dict[doc_id] = {
                            'id': doc_id,
                            'filename': row['filename'],
                            'title': row['title'] or row['filename'].replace('.pdf', ''),
                            'category': row['category'],
                            'document_type': row['document_type'] or 'book',
                            'mc_press_url': row['mc_press_url'],
                            'article_url': row['article_url'],
                            'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                            'chunk_count': row['chunk_count'] or 0,
                            'authors': []
                        }
                    
                    # Add author info if available
                    if row['author_name']:
                        author_info = {
                            'name': row['author_name'],
                            'site_url': row.get('author_site_url'),
                            'order': row.get('author_order', 0) or 0
                        }
                        documents_dict[doc_id]['authors'].append(author_info)
                
                # Convert to list and sort authors by order
                documents = []
                for doc in documents_dict.values():
                    # Sort authors by order
                    doc['authors'].sort(key=lambda x: x['order'])
                    
                    # Set primary author for backward compatibility
                    if doc['authors']:
                        doc['author'] = doc['authors'][0]['name']
                    else:
                        doc['author'] = 'Unknown Author'
                    
                    documents.append(doc)
            else:
                # Simple processing without multi-author support
                documents = []
                for row in rows:
                    doc = {
                        'id': row['id'],
                        'filename': row['filename'],
                        'title': row['title'] or row['filename'].replace('.pdf', ''),
                        'category': row['category'],
                        'document_type': row['document_type'] or 'book',
                        'mc_press_url': row['mc_press_url'],
                        'article_url': row['article_url'],
                        'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                        'chunk_count': row['chunk_count'] or 0,
                        'author': row['author_name'],
                        'authors': [{'name': row['author_name'], 'site_url': None, 'order': 0}] if row['author_name'] else []
                    }
                    documents.append(doc)

            return {
                "documents": documents,
                "total": total or 0,
                "page": page,
                "per_page": per_page,
                "total_pages": ((total or 0) + per_page - 1) // per_page
            }

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Return empty result instead of error to prevent frontend breaking
        return {
            "documents": [],
            "total": 0,
            "page": 1,
            "per_page": per_page,
            "total_pages": 0,
            "error": str(e)
        }

@router.patch("/documents/{doc_id}")
async def update_document(doc_id: int, updates: Dict[str, Any]):
    """Update a single document's metadata"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Build update query dynamically
            allowed_fields = ['title', 'author', 'category', 'subcategory',
                            'description', 'tags', 'mc_press_url', 'year']

            set_clauses = []
            params = []
            param_count = 0

            for field, value in updates.items():
                if field in allowed_fields:
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")
                    if field == 'tags' and isinstance(value, list):
                        params.append(value)
                    else:
                        params.append(value)

            if not set_clauses:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            param_count += 1
            query = f"""
                UPDATE books
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING *
            """
            params.append(doc_id)

            row = await conn.fetchrow(query, *params)

            if not row:
                raise HTTPException(status_code=404, detail="Document not found")

            # Log the change to metadata_history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_history (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Track each field change
            for field, new_value in updates.items():
                if field in allowed_fields:
                    await conn.execute("""
                        INSERT INTO metadata_history (book_id, field_name, new_value, changed_by)
                        VALUES ($1, $2, $3, 'admin')
                    """, doc_id, field, str(new_value))

            # Invalidate cache after successful update
            invalidate_cache()
            logger.info(f"📝 Document {doc_id} updated, cache invalidated")

            return {
                'id': row['id'],
                'filename': row['filename'],
                'title': row['title'],
                'author': row['author'],
                'category': row['category'],
                'subcategory': row['subcategory'],
                'total_pages': row['total_pages'],
                'mc_press_url': row['mc_press_url'],
                'description': row['description'],
                'tags': row['tags'],
                'year': row['year']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/documents/bulk")
async def bulk_update_documents(ids: List[int], updates: Dict[str, Any]):
    """Update multiple documents at once"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Build update query
            allowed_fields = ['category', 'author', 'subcategory', 'tags']

            set_clauses = []
            params = []
            param_count = 0

            for field, value in updates.items():
                if field in allowed_fields:
                    param_count += 1
                    if field == 'tags' and updates.get('tags_operation') == 'append':
                        set_clauses.append(f"tags = array_cat(COALESCE(tags, ARRAY[]::text[]), ${param_count})")
                        params.append(value if isinstance(value, list) else [value])
                    elif field == 'tags' and updates.get('tags_operation') == 'remove':
                        # Remove specific tags
                        set_clauses.append(f"tags = array_remove(tags, ${param_count})")
                        params.append(value)
                    else:
                        set_clauses.append(f"{field} = ${param_count}")
                        params.append(value)

            if not set_clauses:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            param_count += 1
            query = f"""
                UPDATE books
                SET {', '.join(set_clauses)}
                WHERE id = ANY(${param_count})
                RETURNING id
            """
            params.append(ids)

            result = await conn.fetch(query, *params)
            updated_count = len(result)

            # Log bulk changes
            for field, value in updates.items():
                if field in allowed_fields:
                    for doc_id in ids:
                        await conn.execute("""
                            INSERT INTO metadata_history (book_id, field_name, new_value, changed_by)
                            VALUES ($1, $2, $3, 'admin')
                        """, doc_id, field, str(value))

            # Invalidate cache after successful bulk update
            invalidate_cache()
            logger.info(f"📝 Bulk update of {updated_count} documents completed, cache invalidated")

            return {
                "updated": updated_count,
                "ids": [row['id'] for row in result]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _do_reindex():
    """Background task to reindex the vector index."""
    global _reindex_in_progress, _last_reindex_completed_at, _last_reindex_duration
    start = time.time()
    try:
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            await conn.execute("REINDEX INDEX documents_embedding_idx")
        elapsed = time.time() - start
        _last_reindex_completed_at = datetime.utcnow().isoformat()
        _last_reindex_duration = round(elapsed, 2)
        logger.info(f"✅ Vector index rebuild completed in {_last_reindex_duration}s")
    except Exception as e:
        logger.error(f"❌ Vector index rebuild failed: {e}")
    finally:
        _reindex_in_progress = False


@router.post("/documents/reindex")
async def reindex_documents(current_user=Depends(get_current_user)):
    """Trigger a background vector index rebuild."""
    global _reindex_in_progress
    if _reindex_in_progress:
        raise HTTPException(status_code=409, detail="Rebuild already in progress")

    _reindex_in_progress = True
    asyncio.create_task(_do_reindex())

    return {"status": "started", "message": "Vector index rebuild initiated"}


@router.get("/documents/reindex/status")
async def reindex_status(current_user=Depends(get_current_user)):
    """Return the current status of the vector index rebuild."""
    return {
        "in_progress": _reindex_in_progress,
        "last_completed_at": _last_reindex_completed_at,
        "last_duration_seconds": _last_reindex_duration,
    }


@router.delete("/documents/{doc_id}", response_model=SingleRemovalSummary)
async def delete_document(doc_id: int, current_user=Depends(get_current_user)):
    """Delete a document and all related data with cascading cleanup"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Fetch the book record to get filename and title
            book = await conn.fetchrow(
                "SELECT id, filename, title FROM books WHERE id = $1",
                doc_id
            )

            if not book:
                raise HTTPException(status_code=404, detail="Document not found")

            filename = book["filename"]
            title = book["title"] or filename

            # Check which optional tables exist before starting transaction
            has_document_authors = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'document_authors' AND column_name = 'book_id'
                )
            """)
            has_metadata_history = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'metadata_history' AND column_name = 'book_id'
                )
            """)

            async with conn.transaction():
                # 1. Delete author associations (if table/column exists)
                author_associations_deleted = 0
                if has_document_authors:
                    da_result = await conn.execute(
                        "DELETE FROM document_authors WHERE book_id = $1",
                        doc_id
                    )
                    author_associations_deleted = int(da_result.split()[-1])

                # 2. Delete metadata history (if table/column exists)
                metadata_history_deleted = 0
                if has_metadata_history:
                    mh_result = await conn.execute(
                        "DELETE FROM metadata_history WHERE book_id = $1",
                        doc_id
                    )
                    metadata_history_deleted = int(mh_result.split()[-1])

                # 3. Delete chunks from documents table by filename
                chunks_result = await conn.execute(
                    "DELETE FROM documents WHERE filename = $1",
                    filename
                )
                chunks_deleted = int(chunks_result.split()[-1])

                # 4. Delete the book record itself
                await conn.execute(
                    "DELETE FROM books WHERE id = $1",
                    doc_id
                )

            # Invalidate cache after successful deletion
            invalidate_cache()
            logger.info(
                f"🗑️ Document {doc_id} ({filename}) deleted: "
                f"{chunks_deleted} chunks, {author_associations_deleted} author assocs, "
                f"{metadata_history_deleted} history rows"
            )

            return SingleRemovalSummary(
                deleted=True,
                document_id=doc_id,
                filename=filename,
                title=title,
                chunks_deleted=chunks_deleted,
                author_associations_deleted=author_associations_deleted,
                metadata_history_deleted=metadata_history_deleted,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/documents/bulk-delete", response_model=BulkRemovalSummary)
async def bulk_delete_documents(request: BulkDeleteRequest, current_user=Depends(get_current_user)):
    """Delete multiple documents with cascading cleanup"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Query books for all provided IDs to partition into found vs not_found
            rows = await conn.fetch(
                "SELECT id, filename, title FROM books WHERE id = ANY($1)",
                request.ids
            )

            found_ids = {row["id"] for row in rows}
            not_found_ids = [id for id in request.ids if id not in found_ids]

            deleted_documents: List[DocumentDeletionDetail] = []
            total_chunks_deleted = 0
            total_author_associations_deleted = 0
            total_metadata_history_deleted = 0

            # Check which optional tables exist before starting deletes
            has_document_authors = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'document_authors' AND column_name = 'book_id'
                )
            """)
            has_metadata_history = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'metadata_history' AND column_name = 'book_id'
                )
            """)

            # For each found document, perform cascading delete inside a transaction
            for row in rows:
                doc_id = row["id"]
                filename = row["filename"]

                async with conn.transaction():
                    # 1. Delete author associations (if table/column exists)
                    author_associations_deleted = 0
                    if has_document_authors:
                        da_result = await conn.execute(
                            "DELETE FROM document_authors WHERE book_id = $1",
                            doc_id
                        )
                        author_associations_deleted = int(da_result.split()[-1])

                    # 2. Delete metadata history (if table/column exists)
                    metadata_history_deleted = 0
                    if has_metadata_history:
                        mh_result = await conn.execute(
                            "DELETE FROM metadata_history WHERE book_id = $1",
                            doc_id
                        )
                        metadata_history_deleted = int(mh_result.split()[-1])

                    # 3. Delete chunks from documents table by filename
                    chunks_result = await conn.execute(
                        "DELETE FROM documents WHERE filename = $1",
                        filename
                    )
                    chunks_deleted = int(chunks_result.split()[-1])

                    # 4. Delete the book record itself
                    await conn.execute(
                        "DELETE FROM books WHERE id = $1",
                        doc_id
                    )

                # Accumulate totals
                total_chunks_deleted += chunks_deleted
                total_author_associations_deleted += author_associations_deleted
                total_metadata_history_deleted += metadata_history_deleted

                deleted_documents.append(DocumentDeletionDetail(
                    id=doc_id,
                    filename=filename,
                    chunks_deleted=chunks_deleted,
                ))

            # Invalidate cache after successful deletion
            invalidate_cache()
            logger.info(
                f"🗑️ Bulk delete of {len(deleted_documents)} documents completed: "
                f"{total_chunks_deleted} chunks, {total_author_associations_deleted} author assocs, "
                f"{total_metadata_history_deleted} history rows"
            )

            return BulkRemovalSummary(
                deleted_count=len(deleted_documents),
                not_found_ids=not_found_ids,
                deleted_documents=deleted_documents,
                total_chunks_deleted=total_chunks_deleted,
                total_author_associations_deleted=total_author_associations_deleted,
                total_metadata_history_deleted=total_metadata_history_deleted,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/documents/export")
async def export_documents_csv():
    """Export all documents to CSV"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, filename, title, author, category, subcategory,
                       year, tags, description, mc_press_url, total_pages, processed_at
                FROM books
                ORDER BY id
            """)

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'id', 'filename', 'title', 'author', 'category',
                'subcategory', 'year', 'tags', 'description',
                'mc_press_url', 'total_pages', 'processed_at'
            ])

            # Write data
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

            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )

    except Exception as e:
        logger.error(f"Error exporting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/import")
async def import_documents_csv(file_content: str):
    """Import document metadata from CSV"""
    try:
        pool = await get_db_connection()

        # Parse CSV
        reader = csv.DictReader(io.StringIO(file_content))
        updates = []

        for row in reader:
            if 'filename' in row and row['filename']:
                update = {
                    'filename': row['filename'],
                    'updates': {}
                }

                # Map CSV fields to database fields
                field_mapping = {
                    'title': 'title',
                    'author': 'author',
                    'category': 'category',
                    'subcategory': 'subcategory',
                    'year': 'year',
                    'description': 'description',
                    'mc_press_url': 'mc_press_url'
                }

                for csv_field, db_field in field_mapping.items():
                    if csv_field in row and row[csv_field]:
                        if db_field == 'year' and row[csv_field]:
                            try:
                                update['updates'][db_field] = int(row[csv_field])
                            except ValueError:
                                pass
                        else:
                            update['updates'][db_field] = row[csv_field]

                # Handle tags specially
                if 'tags' in row and row['tags']:
                    update['updates']['tags'] = row['tags'].split(',')

                if update['updates']:
                    updates.append(update)

        # Apply updates
        updated_count = 0
        async with pool.acquire() as conn:
            for update in updates:
                # Build update query
                set_clauses = []
                params = []
                param_count = 0

                for field, value in update['updates'].items():
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")
                    params.append(value)

                if set_clauses:
                    param_count += 1
                    query = f"""
                        UPDATE books
                        SET {', '.join(set_clauses)}
                        WHERE filename = ${param_count}
                    """
                    params.append(update['filename'])

                    result = await conn.execute(query, *params)
                    if '1' in result:
                        updated_count += 1

        # Invalidate cache after successful import
        if updated_count > 0:
            invalidate_cache()
            logger.info(f"📥 CSV import completed, {updated_count} documents updated, cache invalidated")

        return {
            "imported": len(updates),
            "updated": updated_count,
            "message": f"Successfully updated {updated_count} documents"
        }

    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/history/{doc_id}")
async def get_document_history(doc_id: int):
    """Get change history for a document"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Check if metadata_history table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'metadata_history'
                )
            """)

            if not table_exists:
                return {"history": []}

            rows = await conn.fetch("""
                SELECT field_name, old_value, new_value, changed_by, changed_at
                FROM metadata_history
                WHERE book_id = $1
                ORDER BY changed_at DESC
                LIMIT 50
            """, doc_id)

            history = []
            for row in rows:
                history.append({
                    'field': row['field_name'],
                    'old_value': row['old_value'],
                    'new_value': row['new_value'],
                    'changed_by': row['changed_by'],
                    'changed_at': row['changed_at'].isoformat() if row['changed_at'] else None
                })

            return {"history": history}

    except Exception as e:
        logger.error(f"Error getting history for document {doc_id}: {e}")
        return {"history": [], "error": str(e)}

@router.get("/stats")
async def get_admin_stats():
    """Get statistics for admin dashboard"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Check if books table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'books'
                )
            """)

            if table_exists:
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM books")
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                last_upload = await conn.fetchval("SELECT MAX(processed_at) FROM books")

                # Get category breakdown
                categories = await conn.fetch("""
                    SELECT category, COUNT(*) as count
                    FROM books
                    GROUP BY category
                    ORDER BY count DESC
                """)

                category_breakdown = {row['category'] or 'Uncategorized': row['count']
                                    for row in categories}
            else:
                doc_count = 0
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                last_upload = await conn.fetchval("SELECT MAX(created_at) FROM documents")
                category_breakdown = {}

            return {
                "total_documents": doc_count or 0,
                "total_chunks": chunk_count or 0,
                "last_upload": last_upload.isoformat() if last_upload else None,
                "category_breakdown": category_breakdown
            }

    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_upload": None,
            "category_breakdown": {},
            "error": str(e)
        }