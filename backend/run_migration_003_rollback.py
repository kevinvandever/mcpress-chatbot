#!/usr/bin/env python3
"""
Rollback Migration 003: Multi-Author Metadata Enhancement
Rollback script to undo the multi-author migration if needed

This script will:
1. Drop the new tables (authors, document_authors)
2. Remove new columns from books table (document_type, article_url)
3. Optionally restore books.author column from backup

Usage:
    python3 backend/run_migration_003_rollback.py

WARNING: This will permanently delete the new multi-author data!
"""

import os
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    exit(1)


async def rollback_migration():
    """Rollback the migration changes"""
    print("🔄 Rolling back Migration 003: Multi-Author Metadata Enhancement")
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    print("⚠️  WARNING: This will permanently delete:")
    print("   - authors table and all author data")
    print("   - document_authors table and all associations")
    print("   - document_type column from books table")
    print("   - article_url column from books table")
    print()
    
    confirm = input("Are you sure you want to rollback? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Rollback cancelled")
        return
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🔍 Checking current schema...")
        
        # Check what exists
        authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'authors'
            )
        """)
        
        document_authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'document_authors'
            )
        """)
        
        document_type_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'books' AND column_name = 'document_type'
            )
        """)
        
        article_url_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'books' AND column_name = 'article_url'
            )
        """)
        
        author_column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'books' AND column_name = 'author'
            )
        """)
        
        print(f"  {'✅' if authors_exists else '❌'} authors table")
        print(f"  {'✅' if document_authors_exists else '❌'} document_authors table")
        print(f"  {'✅' if document_type_exists else '❌'} books.document_type column")
        print(f"  {'✅' if article_url_exists else '❌'} books.article_url column")
        print(f"  {'✅' if author_column_exists else '❌'} books.author column (original)")
        print()
        
        if not any([authors_exists, document_authors_exists, document_type_exists, article_url_exists]):
            print("ℹ️  No migration artifacts found - nothing to rollback")
            return
        
        # Step 1: Drop document_authors table (has foreign keys)
        if document_authors_exists:
            print("🗑️  Dropping document_authors table...")
            await conn.execute("DROP TABLE IF EXISTS document_authors CASCADE")
            print("✅ document_authors table dropped")
        
        # Step 2: Drop authors table
        if authors_exists:
            print("🗑️  Dropping authors table...")
            await conn.execute("DROP TABLE IF EXISTS authors CASCADE")
            print("✅ authors table dropped")
        
        # Step 3: Remove new columns from books table
        if document_type_exists:
            print("🗑️  Removing document_type column from books table...")
            await conn.execute("ALTER TABLE books DROP COLUMN IF EXISTS document_type")
            print("✅ document_type column removed")
        
        if article_url_exists:
            print("🗑️  Removing article_url column from books table...")
            await conn.execute("ALTER TABLE books DROP COLUMN IF EXISTS article_url")
            print("✅ article_url column removed")
        
        # Step 4: Drop trigger function if it exists
        print("🗑️  Cleaning up trigger functions...")
        await conn.execute("DROP FUNCTION IF EXISTS update_authors_updated_at() CASCADE")
        print("✅ Trigger functions cleaned up")
        
        # Step 5: Optionally restore author column
        if not author_column_exists:
            print("\n❓ The original books.author column was removed during migration.")
            print("   Would you like to restore it?")
            print("   (This will create an empty author column)")
            
            restore = input("Restore books.author column? (y/N): ").strip().lower()
            
            if restore == 'y':
                print("🔄 Restoring books.author column...")
                await conn.execute("ALTER TABLE books ADD COLUMN author TEXT")
                print("✅ books.author column restored (empty)")
                print("   You will need to restore author data from backup")
        
        print("\n🎉 Migration 003 rollback completed successfully!")
        print()
        print("📋 What was rolled back:")
        if authors_exists:
            print("   ✅ Dropped authors table")
        if document_authors_exists:
            print("   ✅ Dropped document_authors table")
        if document_type_exists:
            print("   ✅ Removed document_type column")
        if article_url_exists:
            print("   ✅ Removed article_url column")
        
        print()
        print("📋 Next steps:")
        print("   1. Verify the application works with the original schema")
        print("   2. If you need author data, restore from database backup")
        print("   3. Consider re-running the migration if rollback was due to a fixable issue")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        print()
        print("💡 Manual rollback commands:")
        print("   DROP TABLE IF EXISTS document_authors CASCADE;")
        print("   DROP TABLE IF EXISTS authors CASCADE;")
        print("   ALTER TABLE books DROP COLUMN IF EXISTS document_type;")
        print("   ALTER TABLE books DROP COLUMN IF EXISTS article_url;")
        print("   DROP FUNCTION IF EXISTS update_authors_updated_at() CASCADE;")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(rollback_migration())