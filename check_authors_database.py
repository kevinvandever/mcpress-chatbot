#!/usr/bin/env python3
"""
Check the current state of the authors database
This will help us understand what authors exist and their associations
"""

import os
import asyncio
import asyncpg

async def check_authors_database():
    """Check the current state of authors and their book associations"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not found")
        return False
    
    print("🔗 Connecting to Railway database...")
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database successfully")
        
        # Check total authors
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
        print(f"📊 Total authors in database: {total_authors}")
        
        # Check authors with books
        authors_with_books = await conn.fetch("""
            SELECT a.id, a.name, a.site_url, COUNT(da.book_id) as book_count
            FROM authors a
            LEFT JOIN document_authors da ON a.id = da.author_id
            GROUP BY a.id, a.name, a.site_url
            ORDER BY book_count DESC, a.name
        """)
        
        print(f"\n📚 Authors and their book counts:")
        print("-" * 60)
        
        authors_with_books_count = 0
        authors_without_books = []
        
        for author in authors_with_books:
            book_count = author['book_count']
            site_url = author['site_url'] or "No website"
            
            if book_count > 0:
                authors_with_books_count += 1
                print(f"{author['name']:<30} | {book_count:>3} books | {site_url}")
            else:
                authors_without_books.append(author['name'])
        
        print(f"\n📈 Summary:")
        print(f"   Authors with books: {authors_with_books_count}")
        print(f"   Authors without books: {len(authors_without_books)}")
        
        if authors_without_books:
            print(f"\n👻 Authors with no books (first 10):")
            for author in authors_without_books[:10]:
                print(f"   - {author}")
        
        # Check for the specific problematic authors
        print(f"\n🔍 Checking specific problematic authors:")
        problematic_authors = ['admin', 'annegrubb', 'USA Sales', 'Unknown']
        
        for author_name in problematic_authors:
            author_info = await conn.fetchrow("""
                SELECT a.id, a.name, COUNT(da.book_id) as book_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE a.name ILIKE $1
                GROUP BY a.id, a.name
            """, f"%{author_name}%")
            
            if author_info:
                print(f"   ⚠️  {author_info['name']} (ID: {author_info['id']}) has {author_info['book_count']} books")
            else:
                print(f"   ✅ {author_name} not found")
        
        # Check for the specific books mentioned by user
        print(f"\n🎯 Checking specific books mentioned by user:")
        test_books = [
            "Complete CL: Sixth Edition",
            "Subfiles in Free-Format RPG", 
            "Control Language Programming for IBM i"
        ]
        
        for book_title in test_books:
            book_authors = await conn.fetch("""
                SELECT b.title, a.name, da.author_order
                FROM books b
                JOIN document_authors da ON b.id = da.book_id
                JOIN authors a ON da.author_id = a.id
                WHERE b.title ILIKE $1
                ORDER BY da.author_order
            """, f"%{book_title}%")
            
            if book_authors:
                author_names = ", ".join([author['name'] for author in book_authors])
                print(f"   📖 {book_title}")
                print(f"      Current authors: {author_names}")
            else:
                # Check if book exists but has no authors
                book_exists = await conn.fetchrow("""
                    SELECT id, title FROM books WHERE title ILIKE $1
                """, f"%{book_title}%")
                
                if book_exists:
                    print(f"   📖 {book_title}")
                    print(f"      ❌ Book exists but has NO AUTHORS")
                else:
                    print(f"   ❌ {book_title} - Book not found")
        
        # Check if the correct authors exist
        print(f"\n✅ Checking if correct authors exist:")
        correct_authors = ['Ted Holt', 'Kevin Vandever', 'Jim Buck', 'Bryan Meyers', 'Dan Riehl']
        
        for author_name in correct_authors:
            author_info = await conn.fetchrow("""
                SELECT a.id, a.name, COUNT(da.book_id) as book_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE a.name = $1
                GROUP BY a.id, a.name
            """, author_name)
            
            if author_info:
                print(f"   ✅ {author_info['name']} (ID: {author_info['id']}) has {author_info['book_count']} books")
            else:
                print(f"   ❌ {author_name} not found in database")
        
        # Check migration 003 status
        print(f"\n🔧 Checking migration 003 status:")
        try:
            # Check if document_authors table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'document_authors'
                )
            """)
            
            if table_exists:
                doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
                print(f"   ✅ document_authors table exists with {doc_author_count} records")
            else:
                print(f"   ❌ document_authors table does not exist - migration 003 not run?")
                
        except Exception as e:
            print(f"   ⚠️  Error checking migration status: {e}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_authors_database())
    if not success:
        print("\n❌ Failed to check database. Make sure DATABASE_URL is set correctly.")