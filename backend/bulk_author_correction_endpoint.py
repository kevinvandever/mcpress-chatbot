"""
API endpoint to bulk-correct book authors from CSV.
This runs on Railway where it can access the database directly.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import asyncpg
import os
import csv
from typing import Dict, List

router = APIRouter()

def parse_csv_authors(author_str: str) -> List[str]:
    """Parse comma-separated or 'and' separated author names"""
    if not author_str:
        return []
    
    author_str = author_str.replace(", and ", ",")
    author_str = author_str.replace(" and ", ",")
    
    authors = [a.strip() for a in author_str.split(",")]
    return [a for a in authors if a]

@router.post("/api/fix-book-authors-from-csv")
async def fix_book_authors_from_csv(dry_run: bool = True, limit: int = 0):
    """
    Fix book authors based on book-metadata.csv (authoritative source).
    
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
            
            csv_books = {}
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('URL', '').strip()
                    if url and 'mc-store.com' in url and 'gift-card' not in url.lower() and 'template' not in url.lower():
                        csv_books[url] = {
                            'title': row.get('Title', '').strip(),
                            'authors': parse_csv_authors(row.get('Author', ''))
                        }
            
            # Get all books from database
            query = """
                SELECT 
                    b.id,
                    b.title,
                    b.mc_press_url,
                    ARRAY_AGG(a.id ORDER BY da.author_order) as author_ids,
                    ARRAY_AGG(a.name ORDER BY da.author_order) as author_names
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                LEFT JOIN authors a ON da.author_id = a.id
                WHERE b.document_type = 'book' 
                  AND b.mc_press_url IS NOT NULL
                  AND b.mc_press_url LIKE '%mc-store.com%'
                GROUP BY b.id, b.title, b.mc_press_url
            """
            
            db_books = await conn.fetch(query)
            
            corrections = []
            errors = []
            processed_count = 0
            
            for db_book in db_books:
                # Apply limit if specified
                if limit > 0 and processed_count >= limit:
                    break
                url = db_book['mc_press_url']
                if url not in csv_books:
                    continue
                
                csv_data = csv_books[url]
                csv_authors = csv_data['authors']
                db_authors = [a for a in (db_book['author_names'] or []) if a]
                
                # Check if authors match
                if len(csv_authors) != len(db_authors) or \
                   [a.lower() for a in csv_authors] != [a.lower() for a in db_authors]:
                    
                    # Need to fix this book
                    book_id = db_book['id']
                    book_title = db_book['title']
                    
                    # Get or create author IDs for CSV authors
                    new_author_ids = []
                    for author_name in csv_authors:
                        # Check if author exists
                        author_query = "SELECT id FROM authors WHERE LOWER(name) = LOWER($1)"
                        author_row = await conn.fetchrow(author_query, author_name)
                        
                        if author_row:
                            author_id = author_row['id']
                        else:
                            # Create new author
                            if not dry_run:
                                insert_query = """
                                    INSERT INTO authors (name, created_at, updated_at)
                                    VALUES ($1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                    RETURNING id
                                """
                                author_row = await conn.fetchrow(insert_query, author_name)
                                author_id = author_row['id']
                            else:
                                author_id = -1  # Placeholder for dry run
                        
                        new_author_ids.append((author_id, author_name))
                    
                    # Remove old author associations
                    if not dry_run:
                        delete_query = "DELETE FROM document_authors WHERE book_id = $1"
                        await conn.execute(delete_query, book_id)
                    
                    # Add new author associations with correct ordering
                    if not dry_run:
                        for order, (author_id, author_name) in enumerate(new_author_ids):
                            insert_query = """
                                INSERT INTO document_authors (book_id, author_id, author_order, created_at)
                                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                            """
                            await conn.execute(insert_query, book_id, author_id, order)
                    
                    corrections.append({
                        'book_id': book_id,
                        'book_title': book_title,
                        'url': url,
                        'old_authors': db_authors,
                        'new_authors': csv_authors,
                        'action': 'would_fix' if dry_run else 'fixed'
                    })
                    
                    processed_count += 1
            
            result = {
                'dry_run': dry_run,
                'limit_applied': limit if limit > 0 else None,
                'total_books_in_db': len(db_books),
                'books_processed': processed_count,
                'corrections_made': len(corrections),
                'errors': errors,
                'corrections': corrections[:50],  # Limit to first 50 for response size
                'total_corrections': len(corrections)
            }
            
            return JSONResponse(content=result)
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correction failed: {str(e)}")
