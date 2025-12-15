"""
Multi-Author Books API Endpoint
Provides clean API for frontend to access book data with proper multi-author support
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
import os
import asyncpg
import json

router = APIRouter(prefix="/api/v2", tags=["books-v2"])

# Global database connection
_pool = None

async def get_db_pool():
    """Get database connection pool"""
    global _pool
    if not _pool:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        _pool = await asyncpg.create_pool(database_url)
    return _pool

@router.get("/books")
async def list_books_v2(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    document_type: Optional[str] = Query(None, description="Filter by document type (book/article)"),
    author: Optional[str] = Query(None, description="Filter by author name")
) -> Dict[str, Any]:
    """
    List books with proper multi-author support and metadata.
    
    This endpoint reads from the books table (not document chunks) and provides:
    - Proper multi-author data with author order
    - Real metadata (categories, page counts, etc.)
    - Document type information (book/article)
    - Pagination support
    - Filtering capabilities
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
                    detail="Books table not available. Migration may be needed."
                )
            
            # Build WHERE clause for filtering
            where_conditions = []
            params = []
            param_count = 0
            
            if category:
                param_count += 1
                where_conditions.append(f"b.category ILIKE ${param_count}")
                params.append(f"%{category}%")
            
            if document_type:
                param_count += 1
                where_conditions.append(f"b.document_type = ${param_count}")
                params.append(document_type)
            
            if author:
                param_count += 1
                where_conditions.append(f"EXISTS (SELECT 1 FROM document_authors da JOIN authors a ON da.author_id = a.id WHERE da.book_id = b.id AND a.name ILIKE ${param_count})")
                params.append(f"%{author}%")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(DISTINCT b.id)
                FROM books b
                {where_clause}
            """
            
            total_count = await conn.fetchval(count_query, *params)
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = (total_count + limit - 1) // limit
            
            # Add pagination parameters
            param_count += 1
            limit_param = param_count
            param_count += 1
            offset_param = param_count
            params.extend([limit, offset])
            
            # Main query with authors
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
                        COALESCE(
                            JSON_AGG(
                                JSON_BUILD_OBJECT(
                                    'id', a.id,
                                    'name', a.name,
                                    'site_url', a.site_url,
                                    'order', da.author_order
                                ) ORDER BY da.author_order
                            ) FILTER (WHERE a.id IS NOT NULL),
                            '[]'::json
                        ) as authors_json,
                        COALESCE(
                            STRING_AGG(a.name, '; ' ORDER BY da.author_order),
                            'Unknown'
                        ) as authors_string
                    FROM books b
                    LEFT JOIN document_authors da ON b.id = da.book_id
                    LEFT JOIN authors a ON da.author_id = a.id
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
            
            books = []
            for row in rows:
                # Parse authors JSON
                authors_data = row['authors_json']
                if isinstance(authors_data, str):
                    try:
                        authors_data = json.loads(authors_data)
                    except:
                        authors_data = []
                
                # Ensure authors_data is a list
                if not isinstance(authors_data, list):
                    authors_data = []
                
                # Fallback to string if no structured data
                if not authors_data and row['authors_string'] and row['authors_string'] != 'Unknown':
                    authors_data = [{'name': name.strip(), 'site_url': None, 'order': i} 
                                  for i, name in enumerate(row['authors_string'].split(';'))]
                
                books.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'] or row['filename'].replace('.pdf', ''),
                    'authors': authors_data,
                    'author': row['authors_string'],  # Legacy field for compatibility
                    'category': row['category'] or 'Uncategorized',
                    'subcategory': row['subcategory'],
                    'document_type': row['document_type'] or 'book',
                    'mc_press_url': row['mc_press_url'],
                    'article_url': row['article_url'],
                    'total_pages': row['total_pages'],
                    'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None
                })
            
            return {
                'books': books,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters': {
                    'category': category,
                    'document_type': document_type,
                    'author': author
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/books/{book_id}")
async def get_book_v2(book_id: int) -> Dict[str, Any]:
    """
    Get a single book with full multi-author details.
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
                    COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'id', a.id,
                                'name', a.name,
                                'site_url', a.site_url,
                                'order', da.author_order
                            ) ORDER BY da.author_order
                        ) FILTER (WHERE a.id IS NOT NULL),
                        '[]'::json
                    ) as authors_json,
                    COALESCE(
                        STRING_AGG(a.name, '; ' ORDER BY da.author_order),
                        'Unknown'
                    ) as authors_string
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                LEFT JOIN authors a ON da.author_id = a.id
                WHERE b.id = $1
                GROUP BY b.id, b.filename, b.title, b.category, b.subcategory, 
                         b.document_type, b.mc_press_url, b.article_url, 
                         b.total_pages, b.processed_at
            """, book_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Book not found")
            
            # Parse authors JSON
            authors_data = row['authors_json']
            if isinstance(authors_data, str):
                try:
                    authors_data = json.loads(authors_data)
                except:
                    authors_data = []
            
            # Ensure authors_data is a list
            if not isinstance(authors_data, list):
                authors_data = []
            
            # Fallback to string if no structured data
            if not authors_data and row['authors_string'] and row['authors_string'] != 'Unknown':
                authors_data = [{'name': name.strip(), 'site_url': None, 'order': i} 
                              for i, name in enumerate(row['authors_string'].split(';'))]
            
            return {
                'id': row['id'],
                'filename': row['filename'],
                'title': row['title'] or row['filename'].replace('.pdf', ''),
                'authors': authors_data,
                'author': row['authors_string'],  # Legacy field for compatibility
                'category': row['category'] or 'Uncategorized',
                'subcategory': row['subcategory'],
                'document_type': row['document_type'] or 'book',
                'mc_press_url': row['mc_press_url'],
                'article_url': row['article_url'],
                'total_pages': row['total_pages'],
                'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/authors")
async def list_authors_v2(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search author names")
) -> Dict[str, Any]:
    """
    List all authors with their document counts.
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
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*)
                FROM authors a
                {where_clause}
            """
            
            total_count = await conn.fetchval(count_query, *params)
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = (total_count + limit - 1) // limit
            
            # Add pagination parameters
            params.extend([limit, offset])
            param_offset = len(params) - 1
            param_limit = len(params)
            
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
                LIMIT ${param_limit} OFFSET ${param_offset}
            """
            
            rows = await conn.fetch(query, *params)
            
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
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'search': search
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")