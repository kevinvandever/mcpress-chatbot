"""
Debug Books Schema - Check what columns actually exist
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/books-schema")
async def debug_books_schema():
    """Check what columns actually exist in the books table"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            # Get all columns in books table
            columns = await conn.fetch("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = 'books'
                ORDER BY ordinal_position
            """)
            
            # Get sample data
            sample_books = await conn.fetch("""
                SELECT * FROM books LIMIT 3
            """)
            
            # Get count
            total_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            
            return {
                "table_exists": len(columns) > 0,
                "total_books": total_count,
                "columns": [
                    {
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "nullable": col["is_nullable"] == "YES",
                        "default": col["column_default"]
                    }
                    for col in columns
                ],
                "sample_data": [dict(book) for book in sample_books] if sample_books else []
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))