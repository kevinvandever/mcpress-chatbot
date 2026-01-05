"""
Minimal admin documents endpoints that work with actual production database schema
Only uses columns that definitely exist: id, filename, title, author, category, document_type, mc_press_url, article_url
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
import logging
import asyncpg
import os

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
    """List all documents from books table - minimal version with only existing columns"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Ultra-safe query with only guaranteed columns
            query = """
                SELECT id, filename, title, author, category, document_type, mc_press_url, article_url
                FROM books
                WHERE 1=1
            """
            params = []
            param_count = 0

            # Add search filter
            if search:
                param_count += 1
                query += f" AND (LOWER(title) LIKE LOWER(${param_count}) OR LOWER(author) LIKE LOWER(${param_count}))"
                params.append(f"%{search}%")

            # Add category filter
            if category:
                param_count += 1
                query += f" AND category = ${param_count}"
                params.append(category)

            # Add sorting
            valid_sort_fields = ['id', 'title', 'author', 'category', 'document_type']
            if sort_by not in valid_sort_fields:
                sort_by = 'title'

            sort_dir = 'DESC' if sort_direction == 'desc' else 'ASC'
            query += f" ORDER BY {sort_by} {sort_dir}"

            # Get total count
            count_query = "SELECT COUNT(*) FROM books WHERE 1=1"
            count_params = []
            
            if search:
                count_query += " AND (LOWER(title) LIKE LOWER($1) OR LOWER(author) LIKE LOWER($1))"
                count_params.append(f"%{search}%")
            
            if category:
                if search:
                    count_query += " AND category = $2"
                    count_params.append(category)
                else:
                    count_query += " AND category = $1"
                    count_params.append(category)

            total = await conn.fetchval(count_query, *count_params)

            # Add pagination
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(per_page)

            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append((page - 1) * per_page)

            # Execute query
            rows = await conn.fetch(query, *params)

            # Format results - ultra-safe version
            documents = []
            for row in rows:
                # Use only legacy author field for now - no multi-author queries
                authors = []
                if row['author']:
                    authors = [{'id': None, 'name': row['author'], 'site_url': None, 'order': 0}]

                documents.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'] or row['filename'].replace('.pdf', ''),
                    'author': row['author'],  # Legacy field
                    'authors': authors,  # Simple single-author array
                    'category': row['category'],
                    'document_type': row['document_type'] or 'book',
                    'mc_press_url': row['mc_press_url'],
                    'article_url': row['article_url'],
                    'total_pages': 0,  # Not available in current schema
                    'chunk_count': 0,  # Not available in current schema
                })

            # Calculate pagination
            total_pages = (total + per_page - 1) // per_page

            return {
                "documents": documents,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "error": None
            }

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return {
            "documents": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0,
            "error": str(e)
        }

@router.get("/stats")
async def get_admin_stats():
    """Get basic admin statistics"""
    try:
        pool = await get_db_connection()

        async with pool.acquire() as conn:
            # Get document count
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM books")

            # Get chunk count from documents table
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM documents")

            return {
                "total_documents": doc_count or 0,
                "total_chunks": chunk_count or 0,
                "last_upload": None  # Not available in current schema
            }

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_upload": None
        }