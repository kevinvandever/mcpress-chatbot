"""
Books API v2 - Multi-Author Support
Provides enhanced book endpoints with proper multi-author metadata
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import asyncpg
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/books", tags=["books-v2"])

# Global database pool
_pool = None

async def get_db_pool():
    """Get or create database connection pool"""
    global _pool
    if _pool is None:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        _pool = await asyncpg.create_pool(database_url)
    return _pool

@router.get("/")
async def list_books_v2(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    document_type: Optional[str] = Query(None, description="Filter by document type (book/article)")
):
    """
    List books with multi-author support and filtering
    
    Returns books from the books table with proper author relationships,
    replacing the old documents-based aggregation.
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Check if books table exists
            books_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'books'
                )
            """)
            
            if not books_exists:
                raise HTTPException(
                    status_code=503, 
                    detail="Books table not available. Migration may be required."
                )
            
            # Build WHERE clause for filtering
            where_conditions = []
            params = []
            param_count = 0
            
            if author:
                param_count += 1
                where_conditions.append(f"a.name ILIKE ${param_count}")
                params.append(f"%{author}%")
            
            if category:
                param_count += 1
                where_conditions.append(f"b.category ILIKE ${param_count}")
                params.append(f"%{category}%")
                
            if document_type:
                param_count += 1
                where_conditions.append(f"b.document_type = ${param_count}")
                params.append(document_type)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Calculate offset
            offset = (page - 1) * limit
            param_count += 1
            limit_param = param_count
            param_count += 1
            offset_param = param_count
            params.extend([limit, offset])
            
            # Main query with multi-author support
            query = f"""
                WITH book_authors AS (
                    SELECT 
                        b.id,
                        b.filename,
                        b.title,
                        b.category,
                        b.subcategory,
                        b.document_type,
                        b.mc_press_url,
                        b.article_url,
                        b.total_pages,
                        b.processed_at,
                        ARRAY_AGG(
                            json_build_object(
                                'id', a.id,
                                'name', a.name,
                                'site_url', a.site_url,
                                'order', da.author_order
                            ) ORDER BY da.author_order
                        ) FILTER (WHERE a.id IS NOT NULL) as authors_json,
                        STRING_AGG(a.name, '; ' ORDER BY da.author_order) as authors_string,
                        COUNT(d.id) as chunk_count
                    FROM books b
                    LEFT JOIN document_authors da ON b.id = da.book_id
                    LEFT JOIN authors a ON da.author_id = a.id
                    LEFT JOIN documents d ON b.filename = d.filename
                    {where_clause}
                    GROUP BY b.id, b.filename, b.title, b.category, b.subcategory, 
                             b.document_type, b.mc_press_url, b.article_url, 
                             b.total_pages, b.processed_at
                    ORDER BY b.processed_at DESC
                    LIMIT ${limit_param} OFFSET ${offset_param}
                )
                SELECT * FROM book_authors
            """
            
            rows = await conn.fetch(query, *params)
            
            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(DISTINCT b.id)
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                LEFT JOIN authors a ON da.author_id = a.id
                {where_clause}
            """
            
            total_count = await conn.fetchval(count_query, *params[:-2])  # Exclude limit/offset params
            
            books = []
            for row in rows:
                # Handle authors
                authors = row['authors_json'] or []
                authors_string = row['authors_string'] or 'Unknown'
                
                books.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'] or row['filename'].replace('.pdf', ''),
                    'authors': authors,  # Full author objects with metadata
                    'author': authors_string,  # Legacy string format for compatibility
                    'category': row['category'] or 'Uncategorized',
                    'subcategory': row['subcategory'],
                    'document_type': row['document_type'] or 'book',
                    'mc_press_url': row['mc_press_url'],
                    'article_url': row['article_url'],
                    'total_pages': row['total_pages'],
                    'chunk_count': row['chunk_count'] or 0,
                    'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None
                })
            
            return {
                'books': books,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'pages': (total_count + limit - 1) // limit
                },
                'filters': {
                    'author': author,
                    'category': category,
                    'document_type': document_type
                }
            }
            
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{book_id}")
async def get_book_v2(book_id: int):
    """
    Get a single book with full multi-author details
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get book with authors
            row = await conn.fetchrow("""
                SELECT 
                    b.id,
                    b.filename,
                    b.title,
                    b.category,
                    b.subcategory,
                    b.document_type,
                    b.mc_press_url,
                    b.article_url,
                    b.total_pages,
                    b.processed_at,
                    ARRAY_AGG(
                        json_build_object(
                            'id', a.id,
                            'name', a.name,
                            'site_url', a.site_url,
                            'order', da.author_order
                        ) ORDER BY da.author_order
                    ) FILTER (WHERE a.id IS NOT NULL) as authors_json,
                    STRING_AGG(a.name, '; ' ORDER BY da.author_order) as authors_string,
                    COUNT(d.id) as chunk_count
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                LEFT JOIN authors a ON da.author_id = a.id
                LEFT JOIN documents d ON b.filename = d.filename
                WHERE b.id = $1
                GROUP BY b.id, b.filename, b.title, b.category, b.subcategory, 
                         b.document_type, b.mc_press_url, b.article_url, 
                         b.total_pages, b.processed_at
            """, book_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Book not found")
            
            # Handle authors
            authors = row['authors_json'] or []
            authors_string = row['authors_string'] or 'Unknown'
            
            return {
                'id': row['id'],
                'filename': row['filename'],
                'title': row['title'] or row['filename'].replace('.pdf', ''),
                'authors': authors,  # Full author objects with metadata
                'author': authors_string,  # Legacy string format for compatibility
                'category': row['category'] or 'Uncategorized',
                'subcategory': row['subcategory'],
                'document_type': row['document_type'] or 'book',
                'mc_press_url': row['mc_press_url'],
                'article_url': row['article_url'],
                'total_pages': row['total_pages'],
                'chunk_count': row['chunk_count'] or 0,
                'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/authors/")
async def list_authors_v2(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search author names")
):
    """
    List all authors with their document counts
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Build WHERE clause for search
            where_clause = ""
            params = []
            if search:
                where_clause = "WHERE a.name ILIKE $1"
                params.append(f"%{search}%")
            
            # Calculate offset
            offset = (page - 1) * limit
            params.extend([limit, offset])
            
            # Main query
            query = f"""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    a.created_at,
                    COUNT(da.book_id) as document_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                {where_clause}
                GROUP BY a.id, a.name, a.site_url, a.created_at
                ORDER BY a.name
                LIMIT ${len(params)-1} OFFSET ${len(params)}
            """
            
            rows = await conn.fetch(query, *params)
            
            # Get total count
            count_query = f"""
                SELECT COUNT(DISTINCT a.id)
                FROM authors a
                {where_clause}
            """
            
            count_params = params[:-2] if search else []
            total_count = await conn.fetchval(count_query, *count_params)
            
            authors = []
            for row in rows:
                authors.append({
                    'id': row['id'],
                    'name': row['name'],
                    'site_url': row['site_url'],
                    'document_count': row['document_count'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {
                'authors': authors,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'pages': (total_count + limit - 1) // limit
                },
                'search': search
            }
            
    except Exception as e:
        logger.error(f"Error listing authors: {e}")
        raise HTTPException(status_code=500, detail=str(e))