"""
Debug endpoint for testing enrichment functionality on Railway.
This creates a temporary endpoint that can be called to test database connection and enrichment.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import asyncpg
import logging
from chat_handler import ChatHandler

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/debug/enrichment/env")
async def debug_environment():
    """Check environment variables."""
    database_url = os.getenv('DATABASE_URL')
    return {
        "database_url_set": bool(database_url),
        "database_url_length": len(database_url) if database_url else 0,
        "database_url_prefix": database_url[:20] + "..." if database_url else None
    }

@router.get("/debug/enrichment/connection")
async def debug_database_connection():
    """Test database connection."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Test basic query
        version = await conn.fetchval("SELECT version()")
        
        # Check required tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('books', 'authors', 'document_authors')
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        
        # Check sample data
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
        doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        
        await conn.close()
        
        return {
            "connection_success": True,
            "database_version": version[:100],
            "tables_found": table_names,
            "book_count": book_count,
            "author_count": author_count,
            "document_author_count": doc_author_count
        }
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@router.get("/debug/enrichment/test/{filename}")
async def debug_enrichment_method(filename: str):
    """Test the enrichment method with a specific filename."""
    try:
        chat_handler = ChatHandler()
        result = await chat_handler._enrich_source_metadata(filename)
        
        return {
            "filename": filename,
            "enrichment_success": bool(result),
            "enrichment_result": result
        }
        
    except Exception as e:
        logger.error(f"Enrichment test failed for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")

@router.get("/debug/enrichment/sample-books")
async def debug_sample_books():
    """Get a sample of books from the database to test with."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Get sample books
        books = await conn.fetch("""
            SELECT filename, title, author as legacy_author, document_type
            FROM books 
            WHERE filename IS NOT NULL 
            ORDER BY id 
            LIMIT 10
        """)
        
        await conn.close()
        
        return {
            "sample_books": [dict(book) for book in books]
        }
        
    except Exception as e:
        logger.error(f"Sample books query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")