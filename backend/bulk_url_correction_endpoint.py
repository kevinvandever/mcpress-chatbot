"""
API endpoint to bulk-correct book URLs from CSV.
This runs on Railway where it can access the database directly.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import asyncpg
import os
import csv
from typing import Dict, List

router = APIRouter()

@router.post("/api/fix-book-urls-from-csv")
async def fix_book_urls_from_csv(dry_run: bool = True, limit: int = 0):
    """
    Fix book mc_press_url based on book-metadata.csv (authoritative source).
    
    Parameters:
    - dry_run: If True, only report what would be changed without making changes
    - limit: Maximum number of books to process (default 0 = all books)
    
    Returns detailed report of corrections made/planned.
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            # Read CSV file
            csv_path = 'book-metadata.csv'
            if not os.path.exists(csv_path):
                raise HTTPException(status_code=404, detail="book-metadata.csv not found")
            
            # Build a mapping of title -> URL from CSV
            csv_urls = {}
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('URL', '').strip()
                    title = row.get('Title', '').strip()
                    if url and title and 'gift-card' not in url.lower() and 'template' not in url.lower():
                        # Normalize title for matching (lowercase, strip)
                        normalized_title = title.lower().strip()
                        csv_urls[normalized_title] = url
            
            # Get all books from database
            query = """
                SELECT id, title, mc_press_url
                FROM books
                WHERE document_type = 'book'
            """
            
            db_books = await conn.fetch(query)
            
            corrections = []
            errors = []
            processed_count = 0
            
            for db_book in db_books:
                # Apply limit if specified
                if limit > 0 and processed_count >= limit:
                    break
                
                book_id = db_book['id']
                db_title = db_book['title']
                db_url = db_book['mc_press_url']
                
                # Normalize title for matching
                normalized_title = db_title.lower().strip() if db_title else ''
                
                # Check if we have a URL for this title in CSV
                if normalized_title in csv_urls:
                    csv_url = csv_urls[normalized_title]
                    
                    # Check if URL needs updating
                    if db_url != csv_url:
                        # Update the URL
                        if not dry_run:
                            update_query = """
                                UPDATE books
                                SET mc_press_url = $1, updated_at = CURRENT_TIMESTAMP
                                WHERE id = $2
                            """
                            await conn.execute(update_query, csv_url, book_id)
                        
                        corrections.append({
                            'book_id': book_id,
                            'book_title': db_title,
                            'old_url': db_url or '(none)',
                            'new_url': csv_url,
                            'action': 'would_fix' if dry_run else 'fixed'
                        })
                        
                        processed_count += 1
                else:
                    # Book not found in CSV
                    if db_url:
                        # Has a URL but not in CSV - might be extra book
                        errors.append({
                            'book_id': book_id,
                            'book_title': db_title,
                            'current_url': db_url,
                            'issue': 'not_in_csv'
                        })
            
            result = {
                'dry_run': dry_run,
                'limit_applied': limit if limit > 0 else None,
                'total_books_in_db': len(db_books),
                'books_processed': processed_count,
                'corrections_made': len(corrections),
                'errors': errors[:20],  # Limit errors to first 20
                'total_errors': len(errors),
                'corrections': corrections[:50],  # Limit to first 50 for response size
                'total_corrections': len(corrections)
            }
            
            return JSONResponse(content=result)
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL correction failed: {str(e)}")
