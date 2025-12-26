"""
Article Migration Endpoint
Migrates articles from documents table to books table so metadata import can find them
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migrate-articles-to-books", tags=["migration"])

@router.post("")
async def migrate_articles_to_books() -> Dict[str, Any]:
    """
    Migrate articles from documents table to books table
    
    This finds all unique article filenames in the documents table (numeric IDs like 972.pdf)
    and creates corresponding records in the books table so the metadata import can find them.
    """
    start_time = time.time()
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            logger.info("🔍 Finding articles in documents table...")
            
            # Find all unique filenames in documents table that look like articles (numeric IDs)
            article_filenames = await conn.fetch("""
                SELECT DISTINCT filename
                FROM documents
                WHERE filename ~ '^[0-9]+\.pdf$'
                ORDER BY filename
            """)
            
            articles_found = len(article_filenames)
            logger.info(f"Found {articles_found} unique article filenames in documents table")
            
            if articles_found == 0:
                return {
                    "success": True,
                    "articles_found": 0,
                    "books_created": 0,
                    "processing_time": time.time() - start_time,
                    "message": "No articles found to migrate"
                }
            
            # Check which articles already exist in books table
            existing_books = await conn.fetch("""
                SELECT filename
                FROM books
                WHERE filename = ANY($1)
            """, [row['filename'] for row in article_filenames])
            
            existing_filenames = {row['filename'] for row in existing_books}
            logger.info(f"Found {len(existing_filenames)} articles already in books table")
            
            # Filter to only new articles
            new_articles = [row['filename'] for row in article_filenames if row['filename'] not in existing_filenames]
            logger.info(f"Need to create {len(new_articles)} new book records")
            
            books_created = 0
            errors = []
            
            # Create book records for each new article
            for filename in new_articles:
                try:
                    # Extract article ID from filename for title
                    article_id = filename.replace('.pdf', '')
                    title = f"Article {article_id}"  # Temporary title, will be updated by metadata import
                    
                    await conn.execute("""
                        INSERT INTO books (filename, title, document_type, author, category, processed_at)
                        VALUES ($1, $2, 'book', 'Unknown Author', 'Article', CURRENT_TIMESTAMP)
                        ON CONFLICT (filename) DO NOTHING
                    """, filename, title)
                    
                    books_created += 1
                    
                    if books_created % 100 == 0:
                        logger.info(f"Created {books_created} book records...")
                
                except Exception as e:
                    error_msg = f"Error creating book record for {filename}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Migration completed: {books_created} books created in {processing_time:.2f}s")
            
            return {
                "success": True,
                "articles_found": articles_found,
                "books_created": books_created,
                "already_existed": len(existing_filenames),
                "processing_time": processing_time,
                "errors": errors,
                "message": f"Successfully migrated {books_created} articles to books table"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time
        }

@router.get("/status")
async def migration_status() -> Dict[str, Any]:
    """
    Check the current migration status
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            # Count articles in documents table
            articles_in_docs = await conn.fetchval("""
                SELECT COUNT(DISTINCT filename)
                FROM documents
                WHERE filename ~ '^[0-9]+\.pdf$'
            """)
            
            # Count articles in books table
            articles_in_books = await conn.fetchval("""
                SELECT COUNT(*)
                FROM books
                WHERE filename ~ '^[0-9]+\.pdf$'
            """)
            
            # Count total books
            total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
            
            return {
                "articles_in_documents_table": articles_in_docs,
                "articles_in_books_table": articles_in_books,
                "total_books": total_books,
                "migration_needed": articles_in_docs > articles_in_books,
                "articles_to_migrate": max(0, articles_in_docs - articles_in_books)
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))