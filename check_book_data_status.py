#!/usr/bin/env python3
"""
Check the current status of book data in Railway database
This will help us understand what data has been loaded and what's missing
"""

import os
import asyncio
import asyncpg

async def check_book_data_status():
    """Check the current status of book data in Railway database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print("Please set your Railway DATABASE_URL in .env file or environment")
        return
    
    try:
        print("🔗 Connecting to Railway database...")
        conn = await asyncpg.connect(database_url)
        
        # Check total books
        total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"📚 Total books in database: {total_books}")
        
        # Check books with MC Press URLs
        books_with_urls = await conn.fetchval(
            "SELECT COUNT(*) FROM books WHERE mc_press_url IS NOT NULL AND mc_press_url != ''"
        )
        print(f"🔗 Books with MC Press URLs: {books_with_urls}")
        
        # Check authors table
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
        print(f"👥 Total authors in database: {total_authors}")
        
        # Check authors with website URLs
        authors_with_urls = await conn.fetchval(
            "SELECT COUNT(*) FROM authors WHERE site_url IS NOT NULL AND site_url != ''"
        )
        print(f"🌐 Authors with website URLs: {authors_with_urls}")
        
        # Check document_authors associations
        total_associations = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        print(f"🔗 Document-author associations: {total_associations}")
        
        # Check document types
        books_count = await conn.fetchval("SELECT COUNT(*) FROM books WHERE document_type = 'book'")
        articles_count = await conn.fetchval("SELECT COUNT(*) FROM books WHERE document_type = 'article'")
        print(f"📖 Books: {books_count}")
        print(f"📄 Articles: {articles_count}")
        
        # Sample some books to see what data we have
        print("\n=== SAMPLE BOOK DATA ===")
        sample_books = await conn.fetch("""
            SELECT b.id, b.title, b.author, b.mc_press_url, b.document_type,
                   array_agg(a.name ORDER BY da.author_order) as authors,
                   array_agg(a.site_url ORDER BY da.author_order) as author_urls
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            LEFT JOIN authors a ON da.author_id = a.id
            WHERE b.mc_press_url IS NOT NULL AND b.mc_press_url != ''
            GROUP BY b.id, b.title, b.author, b.mc_press_url, b.document_type
            LIMIT 5
        """)
        
        for book in sample_books:
            print(f"\n📚 {book['title']}")
            print(f"   Legacy author: {book['author']}")
            print(f"   New authors: {book['authors']}")
            print(f"   Author URLs: {book['author_urls']}")
            print(f"   MC Press URL: {book['mc_press_url']}")
            print(f"   Type: {book['document_type']}")
        
        # Check for specific books from our CSV
        print("\n=== CHECKING SPECIFIC BOOKS FROM CSV ===")
        test_titles = [
            "21st Century RPG: /Free, ILE, and MVC",
            "5 Keys to Business Analytics Program Success",
            "Active Server Pages Primer"
        ]
        
        for title in test_titles:
            book = await conn.fetchrow(
                "SELECT id, title, author, mc_press_url FROM books WHERE title ILIKE $1",
                f"%{title}%"
            )
            if book:
                print(f"✅ Found: {book['title']}")
                print(f"   Author: {book['author']}")
                print(f"   MC Press URL: {book['mc_press_url'] or 'MISSING'}")
            else:
                print(f"❌ Not found: {title}")
        
        await conn.close()
        
        # Summary
        print("\n=== SUMMARY ===")
        if books_with_urls == 0:
            print("🚨 NO BOOKS HAVE MC PRESS URLS - Excel data has NOT been imported")
        elif books_with_urls < 50:
            print("⚠️ Very few books have MC Press URLs - Import may be incomplete")
        else:
            print("✅ Many books have MC Press URLs - Import appears successful")
            
        if authors_with_urls == 0:
            print("🚨 NO AUTHORS HAVE WEBSITE URLS - Author URLs not populated")
        elif authors_with_urls < 10:
            print("⚠️ Very few authors have website URLs")
        else:
            print("✅ Many authors have website URLs")
            
        print(f"\n📊 Data completeness:")
        print(f"   Books with URLs: {books_with_urls}/{total_books} ({books_with_urls/total_books*100:.1f}%)")
        print(f"   Authors with URLs: {authors_with_urls}/{total_authors} ({authors_with_urls/total_authors*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_book_data_status())