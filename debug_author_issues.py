#!/usr/bin/env python3
"""
Debug script to investigate author display issues identified by user:

1. Control Language Programming for IBM i shows only Jim Buck (should show multiple authors)
2. Complete CL - Sixth Edition shows "annegrubb" but should be "Ted Holt"  
3. Subfiles in Free Format RPG shows "admin" but should be "Kevin Vandever"

This script will check the database state for these specific books.
"""

import os
import asyncio
import asyncpg
from urllib.parse import urlparse

# Railway database URL
DATABASE_URL = "postgresql://postgres:bRAiLwAyPASSWORD@viaduct.proxy.rlwy.net:47334/railway"

async def debug_specific_books():
    """Debug the specific books mentioned by the user"""
    
    print("🔍 Debugging Author Display Issues")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to Railway database")
        
        # Books to investigate
        books_to_check = [
            "Control Language Programming for IBM i",
            "Complete CL- Sixth Edition", 
            "Complete CL - Sixth Edition",
            "Subfiles in Free-Format RPG",
            "Subfiles in Free Format RPG"
        ]
        
        for book_title in books_to_check:
            print(f"\n📖 Checking: {book_title}")
            print("-" * 40)
            
            # Find book by title (partial match)
            books = await conn.fetch("""
                SELECT id, filename, title, author as legacy_author, 
                       mc_press_url, document_type
                FROM books 
                WHERE title ILIKE $1
                ORDER BY title
            """, f"%{book_title}%")
            
            if not books:
                print(f"   ❌ No books found matching '{book_title}'")
                continue
                
            for book in books:
                print(f"   📄 Found: {book['title']}")
                print(f"      ID: {book['id']}")
                print(f"      Filename: {book['filename']}")
                print(f"      Legacy Author: {book['legacy_author']}")
                print(f"      Type: {book['document_type']}")
                print(f"      MC Press URL: {book['mc_press_url']}")
                
                # Check document_authors table
                authors = await conn.fetch("""
                    SELECT a.id, a.name, a.site_url, da.author_order
                    FROM document_authors da
                    JOIN authors a ON da.author_id = a.id
                    WHERE da.book_id = $1
                    ORDER BY da.author_order
                """, book['id'])
                
                if authors:
                    print(f"      📝 Multi-Author Data ({len(authors)} authors):")
                    for i, author in enumerate(authors):
                        print(f"         {i+1}. {author['name']} (order: {author['author_order']})")
                        if author['site_url']:
                            print(f"            🔗 {author['site_url']}")
                else:
                    print(f"      ⚠️  No multi-author data found - using legacy author")
                
                print()
        
        # Check what the enrichment would return for these books
        print("\n🧪 Testing Enrichment Results")
        print("=" * 50)
        
        test_filenames = [
            "Control Language Programming for IBM i.pdf",
            "Complete CL- Sixth Edition.pdf", 
            "Complete CL - Sixth Edition.pdf",
            "Subfiles in Free-Format RPG.pdf",
            "Subfiles in Free Format RPG.pdf"
        ]
        
        for filename in test_filenames:
            print(f"\n🔍 Testing enrichment for: {filename}")
            
            # Simulate the enrichment query
            book_data = await conn.fetchrow("""
                SELECT id, filename, title, author as legacy_author,
                       mc_press_url, article_url, document_type
                FROM books
                WHERE filename = $1
            """, filename)
            
            if not book_data:
                print(f"   ❌ No book found for filename: {filename}")
                continue
                
            print(f"   📖 Book: {book_data['title']}")
            print(f"   👤 Legacy Author: {book_data['legacy_author']}")
            
            # Get authors
            authors = await conn.fetch("""
                SELECT a.id, a.name, a.site_url, da.author_order
                FROM document_authors da
                JOIN authors a ON da.author_id = a.id
                WHERE da.book_id = $1
                ORDER BY da.author_order
            """, book_data['id'])
            
            if authors:
                author_names = [author['name'] for author in authors]
                print(f"   📝 Multi-Author Display: {', '.join(author_names)}")
                print(f"   📊 Authors Array: {len(authors)} authors")
                for author in authors:
                    print(f"      - {author['name']} (order: {author['author_order']})")
            else:
                print(f"   ⚠️  Fallback to legacy: {book_data['legacy_author']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def check_author_parsing_issues():
    """Check for common author parsing issues in the database"""
    
    print("\n🔍 Checking for Author Parsing Issues")
    print("=" * 50)
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check for suspicious author names
        suspicious_authors = await conn.fetch("""
            SELECT name, COUNT(*) as book_count
            FROM authors
            WHERE name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales', 'Unknown')
               OR name ILIKE '%admin%'
               OR name ILIKE '%test%'
            GROUP BY name
            ORDER BY book_count DESC
        """)
        
        if suspicious_authors:
            print("⚠️  Found suspicious author names:")
            for author in suspicious_authors:
                print(f"   - '{author['name']}': {author['book_count']} books")
        
        # Check books with these suspicious authors
        print("\n📚 Books with suspicious authors:")
        books_with_issues = await conn.fetch("""
            SELECT b.title, b.filename, a.name as author_name, da.author_order
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE a.name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales')
            ORDER BY b.title, da.author_order
        """)
        
        current_book = None
        for book in books_with_issues:
            if book['title'] != current_book:
                print(f"\n   📖 {book['title']}")
                current_book = book['title']
            print(f"      👤 {book['author_name']} (order: {book['author_order']})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error checking author parsing: {e}")

if __name__ == "__main__":
    asyncio.run(debug_specific_books())
    asyncio.run(check_author_parsing_issues())