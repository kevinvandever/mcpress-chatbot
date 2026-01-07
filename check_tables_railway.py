#!/usr/bin/env python3
"""
Check what tables exist on Railway and if books table has data
This script must be run on Railway: railway run python3 check_tables_railway.py
"""

import asyncio
import asyncpg
import os
import sys

async def check_tables():
    """Check what tables exist and their data"""
    
    try:
        # Connect to database
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return
            
        print(f"🔗 Connecting to Railway database...")
        conn = await asyncpg.connect(database_url)
        print("✅ Connected successfully")
        
        # Check what tables exist
        print("\n📋 CHECKING EXISTING TABLES:")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        print(f"Available tables: {table_names}")
        
        # Check if books table exists and has data
        if 'books' in table_names:
            print(f"\n📚 BOOKS TABLE STATUS:")
            books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            print(f"  - Books count: {books_count}")
            
            if books_count > 0:
                # Show sample books
                sample_books = await conn.fetch("SELECT id, filename, title, author FROM books LIMIT 5")
                print(f"  - Sample books:")
                for book in sample_books:
                    print(f"    ID {book['id']}: {book['filename']} - {book['title']} by {book['author']}")
            else:
                print("  - ❌ Books table is empty!")
        else:
            print(f"\n❌ BOOKS TABLE DOES NOT EXIST")
            
        # Check documents table
        if 'documents' in table_names:
            print(f"\n📄 DOCUMENTS TABLE STATUS:")
            docs_count = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
            print(f"  - Unique documents: {docs_count}")
            
            if docs_count > 0:
                sample_docs = await conn.fetch("SELECT DISTINCT filename FROM documents LIMIT 5")
                print(f"  - Sample filenames:")
                for doc in sample_docs:
                    print(f"    - {doc['filename']}")
        
        await conn.close()
        print(f"\n✅ Check complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 RAILWAY DATABASE TABLE CHECK")
    print("=" * 50)
    asyncio.run(check_tables())