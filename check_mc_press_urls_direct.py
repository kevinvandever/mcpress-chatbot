#!/usr/bin/env python3
"""
Direct database query to check MC Press URLs in Railway database
"""

import asyncio
import asyncpg
import os

async def check_mc_press_urls():
    """Check MC Press URLs directly in the database"""
    
    # Use Railway environment variable
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        print("Run: railway run python3 check_mc_press_urls_direct.py")
        return
    
    try:
        print("🔗 Connecting to Railway database...")
        conn = await asyncpg.connect(database_url)
        
        # Check total books
        total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"📚 Total books: {total_books}")
        
        # Check books with MC Press URLs
        books_with_urls = await conn.fetchval(
            "SELECT COUNT(*) FROM books WHERE mc_press_url IS NOT NULL AND mc_press_url != ''"
        )
        print(f"🔗 Books with MC Press URLs: {books_with_urls}")
        
        # Sample some books with URLs
        print("\n=== SAMPLE BOOKS WITH MC PRESS URLS ===")
        sample_books = await conn.fetch("""
            SELECT title, author, mc_press_url
            FROM books 
            WHERE mc_press_url IS NOT NULL AND mc_press_url != ''
            LIMIT 5
        """)
        
        for book in sample_books:
            print(f"📖 {book['title']}")
            print(f"   Author: {book['author']}")
            print(f"   MC Press URL: {book['mc_press_url']}")
            print()
        
        # Check specific books mentioned in testing
        print("=== CHECKING SPECIFIC TEST BOOKS ===")
        test_books = [
            "DB2 10 for z-OS- Cost Savings...Right Out of the Box.pdf",
            "DB2 10 for z-OS- The Smarter, Faster Way to Upgrade.pdf"
        ]
        
        for filename in test_books:
            book = await conn.fetchrow(
                "SELECT title, author, mc_press_url FROM books WHERE filename = $1",
                filename
            )
            if book:
                print(f"✅ {book['title']}")
                print(f"   Author: {book['author']}")
                print(f"   MC Press URL: {book['mc_press_url'] or 'MISSING'}")
            else:
                print(f"❌ Not found: {filename}")
            print()
        
        await conn.close()
        
        # Summary
        print("=== SUMMARY ===")
        if books_with_urls == 0:
            print("🚨 NO BOOKS HAVE MC PRESS URLS")
            print("   The Excel import did NOT work or data was not saved")
        elif books_with_urls < 50:
            print(f"⚠️ Only {books_with_urls} books have MC Press URLs")
            print("   Import may be incomplete")
        else:
            print(f"✅ {books_with_urls} books have MC Press URLs")
            print("   Import appears successful")
            
        print(f"\n📊 Coverage: {books_with_urls}/{total_books} ({books_with_urls/total_books*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_mc_press_urls())