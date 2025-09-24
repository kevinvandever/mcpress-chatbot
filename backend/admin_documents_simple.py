"""
Simplified admin documents endpoints that work with production database
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncpg
import os
import csv
import io
from datetime import datetime

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])

async def get_db_connection():
    """Get direct database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return await asyncpg.connect(database_url)

@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search in title and author"),
    category: str = Query("", description="Filter by category"),
    sort_by: str = Query("title", description="Sort field"),
    sort_direction: str = Query("asc", description="Sort direction (asc/desc)")
):
    """List all documents with pagination, filtering, and sorting"""
    try:
        conn = await get_db_connection()
        try:
            # Fetch all books
            rows = await conn.fetch("""
                SELECT id, filename, title, author, category, subcategory,
                       total_pages, file_hash, processed_at, mc_press_url,
                       description, tags, year
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
                    'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None,
                    'mc_press_url': row['mc_press_url'],
                    'description': row['description'],
                    'tags': row['tags'] or [],
                    'year': row['year']
                })

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
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_documents_csv():
    """Export all documents to CSV"""
    try:
        conn = await get_db_connection()
        try:
            rows = await conn.fetch("""
                SELECT id, filename, title, author, category, subcategory,
                       year, tags, description, mc_press_url, total_pages, processed_at
                FROM books
                ORDER BY id DESC
            """)

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'id', 'filename', 'title', 'author', 'category', 'subcategory',
                'year', 'tags', 'description', 'mc_press_url', 'total_pages', 'processed_at'
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
            await conn.close()
    except Exception as e:
        print(f"Error exporting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        conn = await get_db_connection()
        try:
            # Get document count
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM books")

            # Get total chunks from embeddings or estimate
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
            if chunk_count == 0:
                # Estimate from documents table
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM documents")

            # Get last upload date
            last_upload = await conn.fetchval("SELECT MAX(processed_at) FROM books")

            return {
                "total_documents": doc_count or 0,
                "total_chunks": chunk_count or 0,
                "last_upload": last_upload.isoformat() if last_upload else None
            }
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_upload": None
        }