#!/usr/bin/env python3
"""
Database Diagnostic Tool
Find where the books/documents are actually stored in the production database
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os

diagnostic_router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])

@diagnostic_router.get("/tables")
async def list_all_tables():
    """List all tables in the database"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_name, table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        result = {}
        
        for table in tables:
            table_name = table['table_name']
            
            # Get row count
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            except:
                count = "Error"
            
            # Get column info
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            result[table_name] = {
                "type": table['table_type'],
                "row_count": count,
                "columns": [
                    {
                        "name": col['column_name'],
                        "type": col['data_type'],
                        "nullable": col['is_nullable'] == 'YES'
                    }
                    for col in columns
                ]
            }
        
        await conn.close()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnostic failed: {str(e)}")


@diagnostic_router.get("/search-documents")
async def search_for_documents():
    """Search for documents/books in all possible tables"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        results = {}
        
        # Check documents table (vector store)
        try:
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            if doc_count > 0:
                # Get sample documents
                sample_docs = await conn.fetch("""
                    SELECT DISTINCT filename, 
                           COUNT(*) as chunk_count,
                           MIN(created_at) as first_seen
                    FROM documents 
                    WHERE filename IS NOT NULL
                    GROUP BY filename
                    ORDER BY first_seen DESC
                    LIMIT 10
                """)
                
                results['documents_table'] = {
                    "total_chunks": doc_count,
                    "unique_files": len(sample_docs),
                    "sample_files": [
                        {
                            "filename": doc['filename'],
                            "chunk_count": doc['chunk_count'],
                            "first_seen": doc['first_seen'].isoformat() if doc['first_seen'] else None
                        }
                        for doc in sample_docs
                    ]
                }
        except Exception as e:
            results['documents_table'] = {"error": str(e)}
        
        # Check books table
        try:
            books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            if books_count > 0:
                sample_books = await conn.fetch("""
                    SELECT id, filename, title, author, 
                           document_type, article_url, mc_press_url
                    FROM books 
                    ORDER BY id DESC
                    LIMIT 10
                """)
                
                results['books_table'] = {
                    "total_books": books_count,
                    "sample_books": [dict(book) for book in sample_books]
                }
            else:
                results['books_table'] = {"total_books": 0, "message": "No books found"}
        except Exception as e:
            results['books_table'] = {"error": str(e)}
        
        # Check for other possible tables with book-like data
        possible_tables = ['book_metadata', 'document_metadata', 'files', 'uploads', 'pdfs']
        
        for table_name in possible_tables:
            try:
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = $1
                    )
                """, table_name)
                
                if exists:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    results[f"{table_name}_table"] = {"exists": True, "count": count}
                else:
                    results[f"{table_name}_table"] = {"exists": False}
            except Exception as e:
                results[f"{table_name}_table"] = {"error": str(e)}
        
        await conn.close()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@diagnostic_router.get("/sample-data/{table_name}")
async def get_sample_data(table_name: str, limit: int = 5):
    """Get sample data from any table"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        
        # Verify table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, table_name)
        
        if not exists:
            await conn.close()
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist")
        
        # Get sample data
        rows = await conn.fetch(f"SELECT * FROM {table_name} LIMIT $1", limit)
        
        await conn.close()
        
        return {
            "table": table_name,
            "sample_count": len(rows),
            "data": [dict(row) for row in rows]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample data failed: {str(e)}")