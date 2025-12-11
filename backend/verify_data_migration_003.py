#!/usr/bin/env python3
"""
Verify Data Migration 003: Check Authors Table Population
Feature: multi-author-metadata-enhancement

This script verifies that the data migration completed successfully by checking:
1. Authors table is populated
2. Document_authors associations exist
3. All documents have at least one author
4. Migration statistics

Usage:
    python backend/verify_data_migration_003.py

Requirements: 4.5, 4.6
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    exit(1)


async def verify_migration():
    """
    Verify the data migration completed successfully
    """
    print("🔍 Verifying Data Migration 003: Authors Table Population")
    print("=" * 60)
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if required tables exist
        print("📋 Step 1: Checking table structure...")
        
        tables_to_check = ['authors', 'document_authors', 'books']
        for table in tables_to_check:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            print(f"  {'✅' if exists else '❌'} {table} table")
            
            if not exists:
                print(f"❌ Required table '{table}' does not exist")
                print("   Please run the schema migration first:")
                print("   python backend/run_migration_003.py")
                return
        
        # Check if old author column still exists
        author_column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'books' AND column_name = 'author'
            )
        """)
        
        print(f"  {'⚠️' if author_column_exists else '✅'} books.author column {'exists' if author_column_exists else 'removed'}")
        
        print()
        
        # Get migration statistics
        print("📊 Step 2: Migration statistics...")
        
        total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
        total_associations = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        
        books_with_authors = await conn.fetchval("""
            SELECT COUNT(DISTINCT book_id) FROM document_authors
        """)
        
        books_without_authors = total_books - books_with_authors
        
        print(f"  📚 Total books: {total_books}")
        print(f"  👤 Total authors: {total_authors}")
        print(f"  🔗 Total associations: {total_associations}")
        print(f"  ✅ Books with authors: {books_with_authors}")
        print(f"  ⚠️  Books without authors: {books_without_authors}")
        
        print()
        
        # Check for books without authors
        if books_without_authors > 0:
            print("⚠️  Step 3: Books without authors...")
            
            orphaned_books = await conn.fetch("""
                SELECT b.id, b.filename, b.title
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                WHERE da.book_id IS NULL
                LIMIT 10
            """)
            
            for book in orphaned_books:
                print(f"  - Book {book['id']}: {book['filename']}")
                if book['title']:
                    print(f"    Title: {book['title']}")
            
            if len(orphaned_books) == 10:
                print(f"  ... and {books_without_authors - 10} more")
            
            print()
            print("💡 To fix orphaned books, run the migration again:")
            print("   python backend/run_data_migration_003.py")
        else:
            print("✅ Step 3: All books have authors")
        
        print()
        
        # Check for duplicate associations
        print("📋 Step 4: Checking for duplicate associations...")
        
        duplicates = await conn.fetch("""
            SELECT book_id, author_id, COUNT(*) as count
            FROM document_authors
            GROUP BY book_id, author_id
            HAVING COUNT(*) > 1
        """)
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate associations:")
            for dup in duplicates[:5]:
                print(f"  - Book {dup['book_id']}, Author {dup['author_id']}: {dup['count']} times")
            if len(duplicates) > 5:
                print(f"  ... and {len(duplicates) - 5} more")
        else:
            print("✅ No duplicate associations found")
        
        print()
        
        # Sample some authors
        print("📋 Step 5: Sample authors...")
        
        sample_authors = await conn.fetch("""
            SELECT 
                a.id,
                a.name,
                a.site_url,
                COUNT(da.book_id) as document_count
            FROM authors a
            LEFT JOIN document_authors da ON a.id = da.author_id
            GROUP BY a.id, a.name, a.site_url
            ORDER BY document_count DESC, a.name
            LIMIT 10
        """)
        
        for author in sample_authors:
            site_info = f" ({author['site_url']})" if author['site_url'] else ""
            print(f"  - {author['name']}{site_info}: {author['document_count']} documents")
        
        print()
        
        # Overall assessment
        migration_complete = (
            total_books > 0 and
            total_authors > 0 and
            books_without_authors == 0 and
            len(duplicates) == 0
        )
        
        if migration_complete:
            print("🎉 Migration verification PASSED!")
            print("   ✅ All tables exist")
            print("   ✅ All books have authors")
            print("   ✅ No duplicate associations")
            print("   ✅ Authors are properly populated")
        else:
            print("⚠️  Migration verification has WARNINGS:")
            if books_without_authors > 0:
                print(f"   ⚠️  {books_without_authors} books without authors")
            if len(duplicates) > 0:
                print(f"   ⚠️  {len(duplicates)} duplicate associations")
            if total_authors == 0:
                print("   ⚠️  No authors found")
            
            print()
            print("💡 Consider running the migration again to fix issues:")
            print("   python backend/run_data_migration_003.py")
        
        print()
        print("📋 Migration verification complete")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        print(traceback.format_exc())
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(verify_migration())