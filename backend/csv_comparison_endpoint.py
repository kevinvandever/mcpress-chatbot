"""
API endpoint to compare CSV with database.
This runs on Railway where it can access the database directly.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import asyncpg
import os
import csv
from typing import Dict, List
import io

router = APIRouter()

PLACEHOLDER_PATTERNS = [
    "admin",
    "unknown",
    "annegrubb",
    "test",
    "default",
    "none",
    "n/a",
]

def is_placeholder_author(name: str) -> bool:
    """Check if author name is a placeholder"""
    if not name:
        return True
    name_lower = name.lower().strip()
    return any(pattern in name_lower for pattern in PLACEHOLDER_PATTERNS)

def normalize_author_name(name: str) -> str:
    """Normalize author name for comparison"""
    if not name:
        return ""
    name = name.strip()
    name = " ".join(name.split())
    return name

def parse_csv_authors(author_str: str) -> List[str]:
    """Parse comma-separated or 'and' separated author names"""
    if not author_str:
        return []
    
    author_str = author_str.replace(", and ", ",")
    author_str = author_str.replace(" and ", ",")
    
    authors = [normalize_author_name(a) for a in author_str.split(",")]
    return [a for a in authors if a]

@router.get("/api/compare-csv-database")
async def compare_csv_database():
    """
    Compare book-metadata.csv with database records.
    Returns detailed comparison results.
    """
    try:
        # Get database URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Get all books with mc_press_url
            query = """
                SELECT 
                    b.id,
                    b.title,
                    b.mc_press_url,
                    ARRAY_AGG(a.name ORDER BY da.author_order) as authors,
                    ARRAY_AGG(da.author_order ORDER BY da.author_order) as author_orders
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                LEFT JOIN authors a ON da.author_id = a.id
                WHERE b.document_type = 'book' 
                  AND b.mc_press_url IS NOT NULL
                  AND b.mc_press_url LIKE '%mc-store.com%'
                GROUP BY b.id, b.title, b.mc_press_url
                ORDER BY b.title
            """
            
            db_books = await conn.fetch(query)
            
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
                            'author': row.get('Author', '').strip()
                        }
            
            # Create lookup dict for database books
            db_books_dict = {}
            for book in db_books:
                db_books_dict[book['mc_press_url']] = {
                    'id': book['id'],
                    'title': book['title'],
                    'authors': [a for a in (book['authors'] or []) if a],
                    'author_orders': book.get('author_orders', [])
                }
            
            # Analysis results
            results = {
                'in_csv_only': [],
                'in_db_only': [],
                'author_mismatches': [],
                'placeholder_authors': [],
                'ordering_issues': [],
                'perfect_matches': [],
                'summary': {}
            }
            
            # Check books in CSV but not in DB
            for url, csv_data in csv_books.items():
                if url not in db_books_dict:
                    results['in_csv_only'].append({
                        'url': url,
                        'title': csv_data['title'],
                        'csv_author': csv_data['author']
                    })
            
            # Check books in DB but not in CSV
            for url, db_book in db_books_dict.items():
                if url not in csv_books:
                    results['in_db_only'].append({
                        'url': url,
                        'title': db_book['title'],
                        'db_authors': db_book['authors']
                    })
            
            # Check books in both for issues
            for url in csv_books.keys():
                if url in db_books_dict:
                    csv_data = csv_books[url]
                    db_book = db_books_dict[url]
                    
                    csv_authors = parse_csv_authors(csv_data['author'])
                    db_authors = db_book['authors']
                    
                    # Check for placeholders
                    has_placeholder = any(is_placeholder_author(a) for a in db_authors)
                    if has_placeholder:
                        results['placeholder_authors'].append({
                            'url': url,
                            'title': db_book['title'],
                            'csv_authors': csv_authors,
                            'db_authors': db_authors
                        })
                    
                    # Check for ordering issues
                    author_orders = db_book.get('author_orders', [])
                    if author_orders and any(o == -1 for o in author_orders):
                        results['ordering_issues'].append({
                            'url': url,
                            'title': db_book['title'],
                            'authors': db_authors,
                            'orders': author_orders
                        })
                    
                    # Check for author mismatches
                    if len(csv_authors) != len(db_authors):
                        results['author_mismatches'].append({
                            'url': url,
                            'title': db_book['title'],
                            'csv_authors': csv_authors,
                            'db_authors': db_authors,
                            'issue': 'count_mismatch'
                        })
                    else:
                        csv_normalized = [normalize_author_name(a) for a in csv_authors]
                        db_normalized = [normalize_author_name(a) for a in db_authors]
                        
                        if csv_normalized != db_normalized:
                            results['author_mismatches'].append({
                                'url': url,
                                'title': db_book['title'],
                                'csv_authors': csv_authors,
                                'db_authors': db_authors,
                                'issue': 'name_mismatch'
                            })
                        else:
                            results['perfect_matches'].append({
                                'url': url,
                                'title': db_book['title']
                            })
            
            # Add summary
            results['summary'] = {
                'total_csv_books': len(csv_books),
                'total_db_books': len(db_books_dict),
                'perfect_matches': len(results['perfect_matches']),
                'books_only_in_csv': len(results['in_csv_only']),
                'books_only_in_db': len(results['in_db_only']),
                'author_mismatches': len(results['author_mismatches']),
                'placeholder_authors': len(results['placeholder_authors']),
                'ordering_issues': len(results['ordering_issues'])
            }
            
            return JSONResponse(content=results)
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
