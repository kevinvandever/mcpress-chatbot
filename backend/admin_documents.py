from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import csv
import io
import json

import os

try:
    from auth import get_current_admin
except ImportError:
    from backend.auth import get_current_admin

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])

# Vector store will be set by main.py after initialization
_vector_store = None

def set_vector_store(store):
    global _vector_store
    _vector_store = store

def get_vector_store():
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Call set_vector_store first.")
    return _vector_store

def get_book_manager():
    try:
        from book_manager import BookManager
        return BookManager()
    except ImportError:
        try:
            from backend.book_manager import BookManager
            return BookManager()
        except:
            return None

class AuthorInfo(BaseModel):
    """Author information for document"""
    id: Optional[int] = None
    name: str
    site_url: Optional[str] = None
    order: int = 0

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[AuthorInfo]] = None  # Multi-author support
    document_type: Optional[str] = None  # 'book' or 'article'
    article_url: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    mc_press_url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    year: Optional[int] = None

class BulkDocumentUpdate(BaseModel):
    ids: List[int]
    action: str  # 'category', 'author', 'delete', etc.
    value: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    ids: List[int]

@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search in title and author"),
    category: str = Query("", description="Filter by category"),
    sort_by: str = Query("title", description="Sort field"),
    sort_direction: str = Query("asc", description="Sort direction (asc/desc)"),
    current_admin = Depends(get_current_admin)
):
    """List all documents with pagination, filtering, and sorting - includes authors array"""
    try:
        # Get connection to books table
        conn = await get_vector_store()._get_connection()
        try:
            # Fetch from books table with document_type
            query = """
                SELECT id, filename, title, category, subcategory,
                       total_pages, file_hash, processed_at, mc_press_url,
                       description, tags, year, document_type, article_url
                FROM books
                ORDER BY id DESC
            """

            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()

                documents = []
                for row in rows:
                    book_id = row[0]
                    
                    # Get authors for this document from document_authors table
                    await cursor.execute("""
                        SELECT a.id, a.name, a.site_url, da.author_order
                        FROM authors a
                        INNER JOIN document_authors da ON a.id = da.author_id
                        WHERE da.book_id = %s
                        ORDER BY da.author_order
                    """, (book_id,))
                    
                    author_rows = await cursor.fetchall()
                    authors = [
                        {
                            'id': author_row[0],
                            'name': author_row[1],
                            'site_url': author_row[2],
                            'order': author_row[3]
                        }
                        for author_row in author_rows
                    ]
                    
                    documents.append({
                        'id': book_id,
                        'filename': row[1],
                        'title': row[2] or row[1].replace('.pdf', ''),
                        'authors': authors,  # Multi-author array
                        'category': row[3],
                        'subcategory': row[4],
                        'total_pages': row[5] or 0,
                        'file_hash': row[6],
                        'processed_at': row[7].isoformat() if row[7] else None,
                        'mc_press_url': row[8],
                        'description': row[9],
                        'tags': row[10] or [],
                        'year': row[11],
                        'document_type': row[12] or 'book',
                        'article_url': row[13]
                    })
        finally:
            await conn.close()

        # Apply search filter
        if search:
            search_lower = search.lower()
            documents = [
                doc for doc in documents
                if ((doc.get('title') or '').lower().find(search_lower) >= 0 or
                    (doc.get('author') or '').lower().find(search_lower) >= 0)
            ]

        # Apply category filter
        if category:
            documents = [doc for doc in documents if doc.get('category') == category]

        # Sort documents
        reverse = (sort_direction == 'desc')
        try:
            documents.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        except:
            # Fallback to title if sort fails
            documents.sort(key=lambda x: x.get('title', ''), reverse=reverse)

        # Calculate pagination
        total = len(documents)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page

        # Apply pagination
        paginated_docs = documents[start:end]

        return {
            "documents": paginated_docs,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{document_id}")
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    current_admin = Depends(get_current_admin)
):
    """Update a single document's metadata - supports multi-author and document_type"""
    try:
        # Import author services
        try:
            from author_service import AuthorService
            from document_author_service import DocumentAuthorService
        except ImportError:
            from backend.author_service import AuthorService
            from backend.document_author_service import DocumentAuthorService
        
        # Get document by ID to verify it exists
        conn = await get_vector_store()._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, title, category, document_type, article_url, mc_press_url
                    FROM books WHERE id = %s
                """, (document_id,))
                
                row = await cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                doc = {
                    'id': row[0],
                    'title': row[1],
                    'category': row[2],
                    'document_type': row[3],
                    'article_url': row[4],
                    'mc_press_url': row[5]
                }

            # Update basic metadata fields
            update_fields = []
            values = []
            history_entries = []

            if update_data.title is not None:
                update_fields.append("title = %s")
                values.append(update_data.title)
                history_entries.append(('title', doc.get('title'), update_data.title))
                
            if update_data.category is not None:
                update_fields.append("category = %s")
                values.append(update_data.category)
                history_entries.append(('category', doc.get('category'), update_data.category))
            
            if update_data.subcategory is not None:
                update_fields.append("subcategory = %s")
                values.append(update_data.subcategory)
                history_entries.append(('subcategory', None, update_data.subcategory))
            
            if update_data.description is not None:
                update_fields.append("description = %s")
                values.append(update_data.description)
                history_entries.append(('description', None, update_data.description))
            
            if update_data.tags is not None:
                update_fields.append("tags = %s")
                values.append(update_data.tags)
                history_entries.append(('tags', None, str(update_data.tags)))
            
            if update_data.year is not None:
                update_fields.append("year = %s")
                values.append(update_data.year)
                history_entries.append(('year', None, str(update_data.year)))
            
            # Validate and update document_type
            if update_data.document_type is not None:
                if update_data.document_type not in ['book', 'article']:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid document_type: {update_data.document_type}. Must be 'book' or 'article'"
                    )
                update_fields.append("document_type = %s")
                values.append(update_data.document_type)
                history_entries.append(('document_type', doc.get('document_type'), update_data.document_type))
            
            # Update type-specific URL fields
            if update_data.article_url is not None:
                update_fields.append("article_url = %s")
                values.append(update_data.article_url)
                history_entries.append(('article_url', doc.get('article_url'), update_data.article_url))
            
            if update_data.mc_press_url is not None:
                update_fields.append("mc_press_url = %s")
                values.append(update_data.mc_press_url)
                history_entries.append(('mc_press_url', doc.get('mc_press_url'), update_data.mc_press_url))

            # Execute basic field updates
            if update_fields:
                values.append(document_id)
                query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = %s"

                async with conn.cursor() as cursor:
                    await cursor.execute(query, values)
                    await conn.commit()

            # Handle authors array update
            if update_data.authors is not None:
                database_url = os.getenv('DATABASE_URL')
                author_service = AuthorService(database_url)
                doc_author_service = DocumentAuthorService(database_url)
                
                await author_service.init_database()
                await doc_author_service.init_database()
                
                try:
                    # Get current authors
                    async with conn.cursor() as cursor:
                        await cursor.execute("""
                            SELECT a.id, a.name
                            FROM authors a
                            INNER JOIN document_authors da ON a.id = da.author_id
                            WHERE da.book_id = %s
                            ORDER BY da.author_order
                        """, (document_id,))
                        
                        current_authors = await cursor.fetchall()
                        old_author_names = [row[1] for row in current_authors]
                    
                    # Remove all current authors (except we need to keep at least one)
                    # So we'll add new ones first, then remove old ones
                    new_author_ids = []
                    
                    for author_info in update_data.authors:
                        # Get or create author
                        author_id = await author_service.get_or_create_author(
                            name=author_info.name,
                            site_url=author_info.site_url
                        )
                        new_author_ids.append(author_id)
                    
                    # Remove old associations
                    for author_row in current_authors:
                        old_author_id = author_row[0]
                        if old_author_id not in new_author_ids:
                            try:
                                await doc_author_service.remove_author_from_document(
                                    book_id=document_id,
                                    author_id=old_author_id
                                )
                            except ValueError:
                                # Can't remove last author - that's ok, we're adding new ones
                                pass
                    
                    # Add new associations
                    for order, author_info in enumerate(update_data.authors):
                        author_id = new_author_ids[order]
                        try:
                            await doc_author_service.add_author_to_document(
                                book_id=document_id,
                                author_id=author_id,
                                order=order
                            )
                        except ValueError as e:
                            # Already exists - just update order
                            if "already associated" in str(e):
                                pass
                            else:
                                raise
                    
                    # Reorder to match the provided order
                    await doc_author_service.reorder_authors(
                        book_id=document_id,
                        author_ids=new_author_ids
                    )
                    
                    # Log author changes to history
                    new_author_names = [a.name for a in update_data.authors]
                    history_entries.append((
                        'authors',
                        '|'.join(old_author_names),
                        '|'.join(new_author_names)
                    ))
                    
                finally:
                    await author_service.close()
                    await doc_author_service.close()

            # Add all changes to metadata history
            if history_entries:
                async with conn.cursor() as cursor:
                    for field_name, old_value, new_value in history_entries:
                        await cursor.execute(
                            """INSERT INTO metadata_history
                               (book_id, field_name, old_value, new_value, changed_by, changed_at)
                               VALUES (%s, %s, %s, %s, %s, NOW())""",
                            (document_id, field_name, str(old_value) if old_value else None, 
                             str(new_value), current_admin["email"])
                        )
                    await conn.commit()

            return {"message": "Document updated successfully", "id": document_id}
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating document: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/bulk")
async def bulk_update_documents(
    bulk_data: BulkDocumentUpdate,
    current_admin = Depends(get_current_admin)
):
    """Bulk update multiple documents"""
    try:
        conn = await get_vector_store()._get_connection()
        try:
            if bulk_data.action == "category":
                query = "UPDATE books SET category = %s WHERE id = ANY(%s)"
                values = (bulk_data.value, bulk_data.ids)
            elif bulk_data.action == "author":
                query = "UPDATE books SET author = %s WHERE id = ANY(%s)"
                values = (bulk_data.value, bulk_data.ids)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {bulk_data.action}")

            async with conn.cursor() as cursor:
                await cursor.execute(query, values)
                affected = cursor.rowcount
                await conn.commit()

                # Log bulk action
                for doc_id in bulk_data.ids:
                    await cursor.execute(
                        """INSERT INTO metadata_history
                           (book_id, field_name, new_value, changed_by, changed_at)
                           VALUES (%s, %s, %s, %s, NOW())""",
                        (doc_id, bulk_data.action, bulk_data.value, current_admin["email"])
                    )
                await conn.commit()

            return {"message": f"Updated {affected} documents", "affected": affected}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error in bulk update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/bulk")
async def bulk_delete_documents(
    delete_request: BulkDeleteRequest,
    current_admin = Depends(get_current_admin)
):
    """Bulk delete multiple documents"""
    try:
        conn = await get_vector_store()._get_connection()
        try:
            # Delete from embeddings first (cascade)
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM embeddings WHERE book_id = ANY(%s)",
                    (delete_request.ids,)
                )

                # Then delete from books
                await cursor.execute(
                    "DELETE FROM books WHERE id = ANY(%s)",
                    (delete_request.ids,)
                )
                affected = cursor.rowcount
                await conn.commit()

            return {"message": f"Deleted {affected} documents", "affected": affected}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error in bulk delete: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_documents_csv(
    current_admin = Depends(get_current_admin)
):
    """Export all documents to CSV"""
    try:
        # Get all documents from books table
        conn = await get_vector_store()._get_connection()
        try:
            query = """
                SELECT id, filename, title, author, category, subcategory,
                       year, tags, description, mc_press_url, total_pages, processed_at
                FROM books
                ORDER BY id DESC
            """

            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()

                documents = []
                for row in rows:
                    documents.append({
                        'id': row[0],
                        'filename': row[1],
                        'title': row[2] or row[1].replace('.pdf', ''),
                        'author': row[3],
                        'category': row[4],
                        'subcategory': row[5],
                        'year': row[6],
                        'tags': row[7] or [],
                        'description': row[8],
                        'mc_press_url': row[9],
                        'total_pages': row[10] or 0,
                        'processed_at': row[11].isoformat() if row[11] else None
                    })
        finally:
            await conn.close()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'id', 'filename', 'title', 'author', 'category', 'subcategory',
            'year', 'tags', 'description', 'mc_press_url', 'total_pages', 'processed_at'
        ])

        # Write data
        for doc in documents:
            writer.writerow([
                doc.get('id', ''),
                doc.get('filename', ''),
                doc.get('title', ''),
                doc.get('author', ''),
                doc.get('category', ''),
                doc.get('subcategory', ''),
                doc.get('year', ''),
                ','.join(doc.get('tags', [])) if isinstance(doc.get('tags'), list) else '',
                doc.get('description', ''),
                doc.get('mc_press_url', ''),
                doc.get('total_pages', 0),
                doc.get('processed_at', '')
            ])

        # Return as downloadable file
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=documents_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    except Exception as e:
        print(f"Error exporting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_documents_csv(
    file: UploadFile = File(...),
    current_admin = Depends(get_current_admin)
):
    """Import document metadata from CSV"""
    try:
        # Read CSV file
        content = await file.read()
        csv_file = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(csv_file)

        conn = await get_vector_store()._get_connection()
        try:
            updated = 0
            errors = []

            for row in reader:
                try:
                    # Find document by filename
                    filename = row.get('filename')
                    if not filename:
                        continue

                    # Update metadata
                    update_fields = []
                    values = []

                    if row.get('title'):
                        update_fields.append("title = %s")
                        values.append(row['title'])
                    if row.get('author'):
                        update_fields.append("author = %s")
                        values.append(row['author'])
                    if row.get('category'):
                        update_fields.append("category = %s")
                        values.append(row['category'])

                    if update_fields:
                        values.append(filename)
                        query = f"UPDATE books SET {', '.join(update_fields)} WHERE filename = %s"

                        async with conn.cursor() as cursor:
                            await cursor.execute(query, values)
                            if cursor.rowcount > 0:
                                updated += 1

                except Exception as row_error:
                    errors.append(f"Row {filename}: {str(row_error)}")

            await conn.commit()

            return {
                "message": f"Import completed. Updated {updated} documents.",
                "updated": updated,
                "errors": errors if errors else None
            }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_admin_stats(
    current_admin = Depends(get_current_admin)
):
    """Get admin dashboard statistics"""
    try:
        conn = await get_vector_store()._get_connection()
        try:
            async with conn.cursor() as cursor:
                # Get document count
                await cursor.execute("SELECT COUNT(*) FROM books")
                doc_count = (await cursor.fetchone())[0]

                # Get total chunks from embeddings table
                await cursor.execute("SELECT COUNT(*) FROM embeddings")
                chunk_count = (await cursor.fetchone())[0]

                # Get last upload date
                await cursor.execute("SELECT MAX(processed_at) FROM books")
                last_upload = await cursor.fetchone()
                last_upload_date = last_upload[0].isoformat() if last_upload and last_upload[0] else None

                return {
                    "total_documents": doc_count,
                    "total_chunks": chunk_count,
                    "last_upload": last_upload_date
                }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        # Return defaults if error
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_upload": None
        }

@router.get("/history/{document_id}")
async def get_document_history(
    document_id: int,
    current_admin = Depends(get_current_admin)
):
    """Get change history for a document"""
    try:
        conn = await get_vector_store()._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT field_name, old_value, new_value, changed_by, changed_at
                       FROM metadata_history
                       WHERE book_id = %s
                       ORDER BY changed_at DESC
                       LIMIT 50""",
                    (document_id,)
                )

                history = []
                async for row in cursor:
                    history.append({
                        "field": row[0],
                        "old_value": row[1],
                        "new_value": row[2],
                        "changed_by": row[3],
                        "changed_at": row[4].isoformat() if row[4] else None
                    })

                return {"document_id": document_id, "history": history}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error getting document history: {str(e)}")
        # Return empty history if table doesn't exist yet
        return {"document_id": document_id, "history": []}

@router.post("/run-migration")
async def run_migration(
    current_admin = Depends(get_current_admin)
):
    """Run database migration for metadata management"""
    try:
        conn = await get_vector_store()._get_connection()
        try:
            async with conn.cursor() as cursor:
                # Create metadata history table
                await cursor.execute("""
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

                # Create indexes
                await cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
                    ON metadata_history(book_id)
                """)

                await cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
                    ON metadata_history(changed_at)
                """)

                # Add missing columns to books table
                columns_to_add = [
                    ('subcategory', 'TEXT'),
                    ('description', 'TEXT'),
                    ('tags', 'TEXT[]'),
                    ('mc_press_url', 'TEXT'),
                    ('year', 'INTEGER')
                ]

                results = []
                for column_name, column_type in columns_to_add:
                    try:
                        await cursor.execute(f"""
                            ALTER TABLE books
                            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                        """)
                        results.append(f"✅ Added column {column_name}")
                    except Exception as col_error:
                        if "already exists" in str(col_error).lower():
                            results.append(f"ℹ️ Column {column_name} already exists")
                        else:
                            results.append(f"⚠️ Could not add column {column_name}: {str(col_error)}")

                await conn.commit()

                return {
                    "status": "success",
                    "message": "Migration completed successfully",
                    "details": results
                }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error running migration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")