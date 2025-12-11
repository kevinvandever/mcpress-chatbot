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
    author: str = Query("", description="Filter by exact author name"),
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
            # Build query with optional author filtering
            base_query = """
                SELECT DISTINCT b.id, b.filename, b.title, b.category, b.subcategory,
                       b.total_pages, b.file_hash, b.processed_at, b.mc_press_url,
                       b.description, b.tags, b.year, b.document_type, b.article_url
                FROM books b
            """
            
            # Add author join if filtering by author or searching
            if author or search:
                base_query += """
                    LEFT JOIN document_authors da ON b.id = da.book_id
                    LEFT JOIN authors a ON da.author_id = a.id
                """
            
            # Add WHERE clause for author filtering
            where_conditions = []
            query_params = []
            
            if author:
                where_conditions.append("a.name = %s")
                query_params.append(author)
            
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            
            base_query += " ORDER BY b.id DESC"

            async with conn.cursor() as cursor:
                await cursor.execute(base_query, query_params)
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

        # Apply search filter (search in title and author names)
        if search:
            search_lower = search.lower()
            filtered_documents = []
            for doc in documents:
                # Search in title
                title_match = (doc.get('title') or '').lower().find(search_lower) >= 0
                
                # Search in author names
                author_match = False
                for author in doc.get('authors', []):
                    if (author.get('name') or '').lower().find(search_lower) >= 0:
                        author_match = True
                        break
                
                if title_match or author_match:
                    filtered_documents.append(doc)
            
            documents = filtered_documents

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
    """Export all documents to CSV with multi-author support"""
    try:
        # Import author services
        try:
            from author_service import AuthorService
        except ImportError:
            from backend.author_service import AuthorService
        
        # Initialize author service
        database_url = os.getenv('DATABASE_URL')
        author_service = AuthorService(database_url)
        await author_service.init_database()
        
        try:
            # Get all documents from books table with new fields
            conn = await get_vector_store()._get_connection()
            try:
                query = """
                    SELECT id, filename, title, category, subcategory,
                           year, tags, description, mc_press_url, total_pages, processed_at,
                           document_type, article_url
                    FROM books
                    ORDER BY id DESC
                """

                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    rows = await cursor.fetchall()

                    documents = []
                    for row in rows:
                        doc_id = row[0]
                        
                        # Get authors for this document
                        authors = await author_service.get_authors_for_document(doc_id)
                        
                        # Format authors and URLs as pipe-delimited strings
                        author_names = [author['name'] for author in authors]
                        author_urls = [author.get('site_url', '') or '' for author in authors]
                        
                        documents.append({
                            'id': doc_id,
                            'filename': row[1],
                            'title': row[2] or row[1].replace('.pdf', ''),
                            'authors': '|'.join(author_names),
                            'author_site_urls': '|'.join(author_urls),
                            'category': row[3],
                            'subcategory': row[4],
                            'year': row[5],
                            'tags': row[6] or [],
                            'description': row[7],
                            'mc_press_url': row[8] or '',
                            'total_pages': row[9] or 0,
                            'processed_at': row[10].isoformat() if row[10] else None,
                            'document_type': row[11] or 'book',
                            'article_url': row[12] or ''
                        })
            finally:
                await conn.close()

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header with new multi-author fields
            writer.writerow([
                'id', 'filename', 'title', 'authors', 'author_site_urls', 'category', 'subcategory',
                'year', 'tags', 'description', 'document_type', 'mc_press_url', 'article_url', 
                'total_pages', 'processed_at'
            ])

            # Write data
            for doc in documents:
                writer.writerow([
                    doc.get('id', ''),
                    doc.get('filename', ''),
                    doc.get('title', ''),
                    doc.get('authors', ''),
                    doc.get('author_site_urls', ''),
                    doc.get('category', ''),
                    doc.get('subcategory', ''),
                    doc.get('year', ''),
                    ','.join(doc.get('tags', [])) if isinstance(doc.get('tags'), list) else '',
                    doc.get('description', ''),
                    doc.get('document_type', 'book'),
                    doc.get('mc_press_url', ''),
                    doc.get('article_url', ''),
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
        finally:
            await author_service.close()
            
    except Exception as e:
        print(f"Error exporting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def export_documents_csv_updated(vector_store=None, author_service=None):
    """
    Export documents to CSV with multi-author support (testable version)
    
    This function is used for testing and can accept services as parameters.
    """
    try:
        # Use provided services or get defaults
        if vector_store is None:
            vector_store = get_vector_store()
        
        if author_service is None:
            # Import and initialize author service
            try:
                from author_service import AuthorService
            except ImportError:
                from backend.author_service import AuthorService
            
            database_url = os.getenv('DATABASE_URL')
            author_service = AuthorService(database_url)
            await author_service.init_database()
        
        # Get all documents from books table with new fields
        conn = await vector_store._get_connection()
        try:
            query = """
                SELECT id, filename, title, category, subcategory,
                       year, tags, description, mc_press_url, total_pages, processed_at,
                       document_type, article_url
                FROM books
                ORDER BY id DESC
            """

            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()

                documents = []
                for row in rows:
                    doc_id = row[0]
                    
                    # Get authors for this document
                    authors = await author_service.get_authors_for_document(doc_id)
                    
                    # Format authors and URLs as pipe-delimited strings
                    author_names = [author['name'] for author in authors]
                    author_urls = [author.get('site_url', '') or '' for author in authors]
                    
                    documents.append({
                        'id': doc_id,
                        'filename': row[1],
                        'title': row[2] or row[1].replace('.pdf', ''),
                        'authors': '|'.join(author_names),
                        'author_site_urls': '|'.join(author_urls),
                        'category': row[3],
                        'subcategory': row[4],
                        'year': row[5],
                        'tags': row[6] or [],
                        'description': row[7],
                        'mc_press_url': row[8] or '',
                        'total_pages': row[9] or 0,
                        'processed_at': row[10].isoformat() if row[10] else None,
                        'document_type': row[11] or 'book',
                        'article_url': row[12] or ''
                    })
        finally:
            await conn.close()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header with new multi-author fields
        writer.writerow([
            'id', 'filename', 'title', 'authors', 'author_site_urls', 'category', 'subcategory',
            'year', 'tags', 'description', 'document_type', 'mc_press_url', 'article_url', 
            'total_pages', 'processed_at'
        ])

        # Write data
        for doc in documents:
            writer.writerow([
                doc.get('id', ''),
                doc.get('filename', ''),
                doc.get('title', ''),
                doc.get('authors', ''),
                doc.get('author_site_urls', ''),
                doc.get('category', ''),
                doc.get('subcategory', ''),
                doc.get('year', ''),
                ','.join(doc.get('tags', [])) if isinstance(doc.get('tags'), list) else '',
                doc.get('description', ''),
                doc.get('document_type', 'book'),
                doc.get('mc_press_url', ''),
                doc.get('article_url', ''),
                doc.get('total_pages', 0),
                doc.get('processed_at', '')
            ])

        # Return as downloadable file
        output.seek(0)
        
        # Create a mock response object for testing
        class MockResponse:
            def __init__(self, content):
                self.body = content.encode('utf-8')
                self.media_type = "text/csv"
                self.headers = {
                    "Content-Disposition": f"attachment; filename=documents_{datetime.now().strftime('%Y%m%d')}.csv"
                }
        
        return MockResponse(output.getvalue())
        
    except Exception as e:
        print(f"Error exporting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_documents_csv(
    file: UploadFile = File(...),
    current_admin = Depends(get_current_admin)
):
    """Import document metadata from CSV with multi-author support"""
    try:
        # Read CSV file
        content = await file.read()
        csv_file = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(csv_file)

        # Initialize author services
        try:
            from author_service import AuthorService
            from document_author_service import DocumentAuthorService
        except ImportError:
            from backend.author_service import AuthorService
            from backend.document_author_service import DocumentAuthorService
        
        database_url = os.getenv('DATABASE_URL')
        author_service = AuthorService(database_url)
        document_author_service = DocumentAuthorService(database_url)
        
        await author_service.init_database()
        await document_author_service.init_database()

        conn = await get_vector_store()._get_connection()
        try:
            updated = 0
            authors_created = 0
            authors_updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header row
                try:
                    # Find document by filename
                    filename = row.get('filename')
                    if not filename:
                        continue

                    # Get document ID
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT id FROM books WHERE filename = %s", (filename,))
                        result = await cursor.fetchone()
                        if not result:
                            errors.append(f"Row {row_num}: Document not found: {filename}")
                            continue
                        
                        doc_id = result[0]

                    # Update basic metadata
                    update_fields = []
                    values = []

                    if row.get('title'):
                        update_fields.append("title = %s")
                        values.append(row['title'])
                    if row.get('category'):
                        update_fields.append("category = %s")
                        values.append(row['category'])
                    if row.get('subcategory'):
                        update_fields.append("subcategory = %s")
                        values.append(row['subcategory'])
                    if row.get('year'):
                        update_fields.append("year = %s")
                        values.append(row['year'])
                    if row.get('description'):
                        update_fields.append("description = %s")
                        values.append(row['description'])
                    
                    # Handle document_type field
                    if row.get('document_type'):
                        document_type = row['document_type'].lower()
                        if document_type in ['book', 'article']:
                            update_fields.append("document_type = %s")
                            values.append(document_type)
                    
                    # Handle URL fields
                    if row.get('mc_press_url'):
                        update_fields.append("mc_press_url = %s")
                        values.append(row['mc_press_url'])
                    
                    if row.get('article_url'):
                        update_fields.append("article_url = %s")
                        values.append(row['article_url'])

                    # Update document metadata if there are changes
                    if update_fields:
                        values.append(doc_id)
                        query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = %s"

                        async with conn.cursor() as cursor:
                            await cursor.execute(query, values)

                    # Handle multi-author data
                    authors_field = row.get('authors', '')
                    author_urls_field = row.get('author_site_urls', '')
                    
                    if authors_field:
                        # Parse pipe-delimited authors
                        author_names = [name.strip() for name in authors_field.split('|') if name.strip()]
                        author_urls = [url.strip() for url in author_urls_field.split('|')] if author_urls_field else []
                        
                        # Pad author_urls list to match author_names length
                        while len(author_urls) < len(author_names):
                            author_urls.append('')
                        
                        # Clear existing authors for this document
                        await document_author_service.clear_document_authors(doc_id)
                        
                        # Create/update authors and associate with document
                        for order, (author_name, author_url) in enumerate(zip(author_names, author_urls)):
                            if not author_name:
                                continue
                                
                            # Clean up URL (empty string if not valid)
                            site_url = author_url if author_url and author_url.startswith(('http://', 'https://')) else None
                            
                            # Get or create author
                            author_id = await author_service.get_or_create_author(author_name, site_url)
                            
                            # Track if this was a new author or update
                            existing_author = await author_service.get_author_by_id(author_id)
                            if existing_author:
                                if existing_author.get('site_url') != site_url and site_url:
                                    await author_service.update_author(author_id, author_name, site_url)
                                    authors_updated += 1
                            else:
                                authors_created += 1
                            
                            # Associate author with document
                            await document_author_service.add_author_to_document(doc_id, author_id, order)
                    
                    updated += 1

                except Exception as row_error:
                    errors.append(f"Row {row_num} ({filename}): {str(row_error)}")

            await conn.commit()

            return {
                "message": f"Import completed. Updated {updated} documents, created {authors_created} authors, updated {authors_updated} authors.",
                "updated": updated,
                "authors_created": authors_created,
                "authors_updated": authors_updated,
                "errors": errors if errors else None
            }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def import_documents_csv_updated(
    csv_content: str,
    vector_store=None,
    author_service=None,
    document_author_service=None
):
    """
    Import document metadata from CSV with multi-author support (testable version)
    
    This function is used for testing and can accept services as parameters.
    
    Args:
        csv_content: CSV content as string
        vector_store: Vector store instance (optional)
        author_service: Author service instance (optional)
        document_author_service: Document author service instance (optional)
    
    Returns:
        Dictionary with import results
    """
    try:
        # Use provided services or get defaults
        if vector_store is None:
            vector_store = get_vector_store()
        
        if author_service is None:
            # Import and initialize author service
            try:
                from author_service import AuthorService
            except ImportError:
                from backend.author_service import AuthorService
            
            database_url = os.getenv('DATABASE_URL')
            author_service = AuthorService(database_url)
            await author_service.init_database()
        
        if document_author_service is None:
            # Import and initialize document author service
            try:
                from document_author_service import DocumentAuthorService
            except ImportError:
                from backend.document_author_service import DocumentAuthorService
            
            database_url = os.getenv('DATABASE_URL')
            document_author_service = DocumentAuthorService(database_url)
            await document_author_service.init_database()

        # Parse CSV content
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        conn = await vector_store._get_connection()
        try:
            updated = 0
            authors_created = 0
            authors_updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header row
                try:
                    # Find document by filename
                    filename = row.get('filename')
                    if not filename:
                        continue

                    # Get document ID
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT id FROM books WHERE filename = %s", (filename,))
                        result = await cursor.fetchone()
                        if not result:
                            errors.append(f"Row {row_num}: Document not found: {filename}")
                            continue
                        
                        doc_id = result[0]

                    # Update basic metadata
                    update_fields = []
                    values = []

                    if row.get('title'):
                        update_fields.append("title = %s")
                        values.append(row['title'])
                    if row.get('category'):
                        update_fields.append("category = %s")
                        values.append(row['category'])
                    if row.get('subcategory'):
                        update_fields.append("subcategory = %s")
                        values.append(row['subcategory'])
                    if row.get('year'):
                        update_fields.append("year = %s")
                        values.append(row['year'])
                    if row.get('description'):
                        update_fields.append("description = %s")
                        values.append(row['description'])
                    
                    # Handle document_type field
                    if row.get('document_type'):
                        document_type = row['document_type'].lower()
                        if document_type in ['book', 'article']:
                            update_fields.append("document_type = %s")
                            values.append(document_type)
                    
                    # Handle URL fields
                    if row.get('mc_press_url'):
                        update_fields.append("mc_press_url = %s")
                        values.append(row['mc_press_url'])
                    
                    if row.get('article_url'):
                        update_fields.append("article_url = %s")
                        values.append(row['article_url'])

                    # Update document metadata if there are changes
                    if update_fields:
                        values.append(doc_id)
                        query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = %s"

                        async with conn.cursor() as cursor:
                            await cursor.execute(query, values)

                    # Handle multi-author data
                    authors_field = row.get('authors', '')
                    author_urls_field = row.get('author_site_urls', '')
                    
                    if authors_field:
                        # Parse pipe-delimited authors
                        author_names = [name.strip() for name in authors_field.split('|') if name.strip()]
                        author_urls = [url.strip() for url in author_urls_field.split('|')] if author_urls_field else []
                        
                        # Pad author_urls list to match author_names length
                        while len(author_urls) < len(author_names):
                            author_urls.append('')
                        
                        # Clear existing authors for this document
                        await document_author_service.clear_document_authors(doc_id)
                        
                        # Create/update authors and associate with document
                        for order, (author_name, author_url) in enumerate(zip(author_names, author_urls)):
                            if not author_name:
                                continue
                                
                            # Clean up URL (empty string if not valid)
                            site_url = author_url if author_url and author_url.startswith(('http://', 'https://')) else None
                            
                            # Get or create author
                            author_id = await author_service.get_or_create_author(author_name, site_url)
                            
                            # Track if this was a new author or update
                            existing_author = await author_service.get_author_by_id(author_id)
                            if existing_author:
                                if existing_author.get('site_url') != site_url and site_url:
                                    await author_service.update_author(author_id, author_name, site_url)
                                    authors_updated += 1
                            else:
                                authors_created += 1
                            
                            # Associate author with document
                            await document_author_service.add_author_to_document(doc_id, author_id, order)
                    
                    updated += 1

                except Exception as row_error:
                    errors.append(f"Row {row_num} ({filename}): {str(row_error)}")

            await conn.commit()

            return {
                "message": f"Import completed. Updated {updated} documents, created {authors_created} authors, updated {authors_updated} authors.",
                "updated": updated,
                "authors_created": authors_created,
                "authors_updated": authors_updated,
                "errors": errors if errors else None
            }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        raise Exception(f"CSV import failed: {str(e)}")

@router.get("/search/by-author")
async def search_documents_by_author(
    author_name: str = Query(..., description="Author name to search for"),
    exact_match: bool = Query(False, description="Use exact name matching"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_admin = Depends(get_current_admin)
):
    """
    Search documents by author name with exact or partial matching
    
    **Validates:** Requirements 8.1, 8.2
    """
    try:
        conn = await get_vector_store()._get_connection()
        try:
            # Build query based on exact match preference
            if exact_match:
                # Exact author name matching
                query = """
                    SELECT DISTINCT b.id, b.filename, b.title, b.category, b.subcategory,
                           b.total_pages, b.file_hash, b.processed_at, b.mc_press_url,
                           b.description, b.tags, b.year, b.document_type, b.article_url
                    FROM books b
                    INNER JOIN document_authors da ON b.id = da.book_id
                    INNER JOIN authors a ON da.author_id = a.id
                    WHERE a.name = %s
                    ORDER BY b.title
                """
                query_params = [author_name]
            else:
                # Partial author name matching (case-insensitive)
                query = """
                    SELECT DISTINCT b.id, b.filename, b.title, b.category, b.subcategory,
                           b.total_pages, b.file_hash, b.processed_at, b.mc_press_url,
                           b.description, b.tags, b.year, b.document_type, b.article_url
                    FROM books b
                    INNER JOIN document_authors da ON b.id = da.book_id
                    INNER JOIN authors a ON da.author_id = a.id
                    WHERE a.name ILIKE %s
                    ORDER BY b.title
                """
                query_params = [f"%{author_name}%"]

            async with conn.cursor() as cursor:
                await cursor.execute(query, query_params)
                rows = await cursor.fetchall()

                documents = []
                for row in rows:
                    book_id = row[0]
                    
                    # Get authors for this document
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
                        'authors': authors,
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

        # Apply pagination
        total = len(documents)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        paginated_docs = documents[start:end]

        return {
            "documents": paginated_docs,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            },
            "search_params": {
                "author_name": author_name,
                "exact_match": exact_match
            }
        }
    except Exception as e:
        print(f"Error searching documents by author: {str(e)}")
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