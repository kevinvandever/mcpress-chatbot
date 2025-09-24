"""
Admin document management endpoints that properly use the existing database connection pool
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import csv
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

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
    sort_direction: str = Query("asc")
):
    """List all documents from books table with proper IDs and metadata"""
    try:
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
                        year INTEGER,
                        total_pages INTEGER,
                        file_hash TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Migrate data from documents table
                logger.info("Migrating data from documents to books table...")
                await conn.execute("""
                    INSERT INTO books (filename, title, author, category, total_pages, processed_at)
                    SELECT DISTINCT ON (filename)
                        filename,
                        COALESCE((metadata->>'title')::text, REPLACE(filename, '.pdf', '')),
                        COALESCE((metadata->>'author')::text, 'Unknown'),
                        COALESCE((metadata->>'category')::text, 'General'),
                        MAX(page_number) OVER (PARTITION BY filename),
                        MIN(created_at) OVER (PARTITION BY filename)
                    FROM documents
                    WHERE filename IS NOT NULL
                    ON CONFLICT (filename) DO NOTHING
                """)

                logger.info("Migration complete")

            # Build query with filters
            query = """
                SELECT id, filename, title, author, category, subcategory,
                       total_pages, file_hash, processed_at, mc_press_url,
                       description, tags, year
                FROM books
                WHERE 1=1
            """
            params = []
            param_count = 0

            if search:
                param_count += 1
                query += f" AND (LOWER(title) LIKE LOWER($${param_count}) OR LOWER(author) LIKE LOWER($${param_count}))"
                params.append(f"%{search}%")

            if category:
                param_count += 1
                query += f" AND category = $${param_count}"
                params.append(category)

            # Add sorting
            valid_sort_fields = ['id', 'title', 'author', 'category', 'total_pages', 'processed_at']
            if sort_by not in valid_sort_fields:
                sort_by = 'title'

            sort_dir = 'DESC' if sort_direction == 'desc' else 'ASC'
            query += f" ORDER BY {sort_by} {sort_dir}"

            # Get total count before pagination
            count_query = """
                SELECT COUNT(*) FROM books WHERE 1=1
            """
            if search:
                count_query += f" AND (LOWER(title) LIKE LOWER('%{search}%') OR LOWER(author) LIKE LOWER('%{search}%'))"
            if category:
                count_query += f" AND category = '{category}'"

            total = await conn.fetchval(count_query)

            # Add pagination
            param_count += 1
            query += f" LIMIT $${param_count}"
            params.append(per_page)

            param_count += 1
            query += f" OFFSET $${param_count}"
            params.append((page - 1) * per_page)

            # Execute query
            rows = await conn.fetch(query, *params)

            documents = []
            for row in rows:
                documents.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'] or row['filename'].replace('.pdf', ''),
                    'author': row['author'] or 'Unknown',
                    'category': row['category'] or 'General',
                    'subcategory': row['subcategory'],
                    'total_pages': row['total_pages'] or 0,
                    'file_hash': row['file_hash'],
                    'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None,
                    'mc_press_url': row['mc_press_url'],
                    'description': row['description'],
                    'tags': row['tags'] or [],
                    'year': row['year']
                })

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

            return {
                "updated": updated_count,
                "ids": [row['id'] for row in result]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document and all its embeddings"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Get filename before deletion
            filename = await conn.fetchval(
                "SELECT filename FROM books WHERE id = $1",
                doc_id
            )

            if not filename:
                raise HTTPException(status_code=404, detail="Document not found")

            # Delete from books table (cascade will handle metadata_history)
            await conn.execute("DELETE FROM books WHERE id = $1", doc_id)

            # Delete all chunks from documents table
            result = await conn.execute(
                "DELETE FROM documents WHERE filename = $1",
                filename
            )

            chunks_deleted = int(result.split()[-1])

            return {
                "deleted": True,
                "filename": filename,
                "chunks_deleted": chunks_deleted
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/bulk")
async def bulk_delete_documents(ids: List[int]):
    """Delete multiple documents"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Get filenames
            rows = await conn.fetch(
                "SELECT id, filename FROM books WHERE id = ANY($1)",
                ids
            )

            if not rows:
                raise HTTPException(status_code=404, detail="No documents found")

            filenames = [row['filename'] for row in rows]

            # Delete from books
            await conn.execute("DELETE FROM books WHERE id = ANY($1)", ids)

            # Delete chunks from documents
            result = await conn.execute(
                "DELETE FROM documents WHERE filename = ANY($1)",
                filenames
            )

            chunks_deleted = int(result.split()[-1])

            return {
                "deleted": len(rows),
                "filenames": filenames,
                "chunks_deleted": chunks_deleted
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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