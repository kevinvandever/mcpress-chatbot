#!/usr/bin/env python3
"""
Check the status of author imports on Railway database
"""

import subprocess
import json

def run_railway_sql(query):
    """Execute SQL query on Railway database"""
    try:
        # Use railway run to execute psql command
        cmd = ['railway', 'run', 'psql', '$DATABASE_URL', '-c', query]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ SQL Error: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print("❌ Query timed out")
        return None
    except Exception as e:
        print(f"❌ Error executing query: {e}")
        return None

def main():
    print("🔍 Checking author import status on Railway...")
    
    # Check total authors
    print("\n📊 Author Statistics:")
    authors_count = run_railway_sql("SELECT COUNT(*) FROM authors;")
    if authors_count:
        print(f"   Total authors: {authors_count}")
    
    # Check authors with URLs
    authors_with_urls = run_railway_sql("SELECT COUNT(*) FROM authors WHERE site_url IS NOT NULL AND site_url != '';")
    if authors_with_urls:
        print(f"   Authors with URLs: {authors_with_urls}")
    
    # Check books with MC Press URLs
    print("\n📚 Book Statistics:")
    books_with_urls = run_railway_sql("SELECT COUNT(*) FROM books WHERE mc_press_url IS NOT NULL AND mc_press_url != '';")
    if books_with_urls:
        print(f"   Books with MC Press URLs: {books_with_urls}")
    
    # Check document-author associations
    doc_author_count = run_railway_sql("SELECT COUNT(*) FROM document_authors;")
    if doc_author_count:
        print(f"   Document-author associations: {doc_author_count}")
    
    # Show sample authors with URLs
    print("\n👥 Sample authors with URLs:")
    sample_authors = run_railway_sql("""
        SELECT name, site_url 
        FROM authors 
        WHERE site_url IS NOT NULL AND site_url != '' 
        LIMIT 5;
    """)
    if sample_authors:
        print(sample_authors)
    else:
        print("   No authors with URLs found")
    
    # Show sample books with MC Press URLs
    print("\n📖 Sample books with MC Press URLs:")
    sample_books = run_railway_sql("""
        SELECT title, mc_press_url 
        FROM books 
        WHERE mc_press_url IS NOT NULL AND mc_press_url != '' 
        LIMIT 5;
    """)
    if sample_books:
        print(sample_books)
    else:
        print("   No books with MC Press URLs found")
    
    # Check for multi-author books
    print("\n🔗 Multi-author book example:")
    multi_author_example = run_railway_sql("""
        SELECT b.title, a.name, a.site_url, da.author_order
        FROM books b
        JOIN document_authors da ON b.id = da.book_id
        JOIN authors a ON da.author_id = a.id
        WHERE b.title LIKE '%DB2 10 for z/OS%'
        ORDER BY da.author_order
        LIMIT 5;
    """)
    if multi_author_example:
        print(multi_author_example)
    else:
        print("   No multi-author example found")

if __name__ == "__main__":
    main()