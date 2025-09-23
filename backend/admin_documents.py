from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import csv
import io
import json

try:
    from auth import get_current_admin
    from vector_store_postgres import VectorStorePostgres
    from book_manager import BookManager
except ImportError:
    from backend.auth import get_current_admin
    from backend.vector_store_postgres import VectorStorePostgres
    from backend.book_manager import BookManager

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])

# Initialize services
vector_store = VectorStorePostgres()
book_manager = BookManager()

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
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
    """List all documents with pagination, filtering, and sorting"""
    try:
        # Get all documents from vector store
        all_docs = await vector_store.list_documents()
        documents = all_docs.get('documents', [])

        # Apply search filter
        if search:
            search_lower = search.lower()
            documents = [
                doc for doc in documents
                if (doc.get('title', '').lower().find(search_lower) >= 0 or
                    doc.get('author', '').lower().find(search_lower) >= 0)
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
    """Update a single document's metadata"""
    try:
        # Get document by ID
        all_docs = await vector_store.list_documents()
        documents = all_docs.get('documents', [])

        doc = None
        for d in documents:
            if d.get('id') == document_id:
                doc = d
                break

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update metadata in database
        conn = await vector_store._get_connection()
        try:
            update_fields = []
            values = []

            if update_data.title is not None:
                update_fields.append("title = %s")
                values.append(update_data.title)
            if update_data.author is not None:
                update_fields.append("author = %s")
                values.append(update_data.author)
            if update_data.category is not None:
                update_fields.append("category = %s")
                values.append(update_data.category)

            if update_fields:
                values.append(document_id)
                query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = %s"

                async with conn.cursor() as cursor:
                    await cursor.execute(query, values)
                    await conn.commit()

                # Add to metadata history
                async with conn.cursor() as cursor:
                    for field, value in zip(update_fields, values[:-1]):
                        field_name = field.split(' = ')[0]
                        await cursor.execute(
                            """INSERT INTO metadata_history
                               (book_id, field_name, old_value, new_value, changed_by, changed_at)
                               VALUES (%s, %s, %s, %s, %s, NOW())""",
                            (document_id, field_name, doc.get(field_name), value, current_admin["email"])
                        )
                    await conn.commit()

            return {"message": "Document updated successfully", "id": document_id}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error updating document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/bulk")
async def bulk_update_documents(
    bulk_data: BulkDocumentUpdate,
    current_admin = Depends(get_current_admin)
):
    """Bulk update multiple documents"""
    try:
        conn = await vector_store._get_connection()
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
        conn = await vector_store._get_connection()
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
        # Get all documents
        all_docs = await vector_store.list_documents()
        documents = all_docs.get('documents', [])

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
                ','.join(doc.get('tags', [])) if doc.get('tags') else '',
                doc.get('description', ''),
                doc.get('mc_press_url', ''),
                doc.get('total_pages', ''),
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

        conn = await vector_store._get_connection()
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

@router.get("/history/{document_id}")
async def get_document_history(
    document_id: int,
    current_admin = Depends(get_current_admin)
):
    """Get change history for a document"""
    try:
        conn = await vector_store._get_connection()
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
        conn = await vector_store._get_connection()
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