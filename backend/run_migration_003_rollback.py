#!/usr/bin/env python3
"""
Rollback Migration 003: Multi-Author Metadata Enhancement
WARNING: This will remove authors and document_authors tables and lose multi-author data
"""

import os
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    print("Please set DATABASE_URL in your .env file")
    exit(1)

async def rollback_migration():
    """Execute the rollback SQL script"""
    print("⚠️  WARNING: Rolling back Migration 003: Multi-Author Metadata Enhancement")
    print("⚠️  This will DELETE the authors and document_authors tables")
    print("⚠️  All multi-author data will be LOST")
    print()
    
    response = input("Are you sure you want to continue? Type 'ROLLBACK' to confirm: ")
    if response != 'ROLLBACK':
        print("❌ Rollback cancelled")
        return
    
    print()
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    # Read rollback SQL
    rollback_file = Path(__file__).parent / "migrations" / "003_multi_author_support_rollback.sql"
    
    if not rollback_file.exists():
        print(f"❌ Rollback file not found: {rollback_file}")
        exit(1)
    
    with open(rollback_file, 'r') as f:
        rollback_sql = f.read()
    
    # Connect to database
    print("🔌 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Execute rollback
        print("📝 Executing rollback SQL...")
        await conn.execute(rollback_sql)
        print("✅ Rollback SQL executed successfully")
        print()
        
        # Verify tables were removed
        print("🔍 Verifying rollback...")
        
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
        
        # Report results
        print(f"  {'❌ Still exists!' if authors_exists else '✅'} authors table removed")
        print(f"  {'❌ Still exists!' if document_authors_exists else '✅'} document_authors table removed")
        print(f"  {'❌ Still exists!' if document_type_exists else '✅'} books.document_type column removed")
        print(f"  {'❌ Still exists!' if article_url_exists else '✅'} books.article_url column removed")
        print()
        
        if not any([authors_exists, document_authors_exists, document_type_exists, article_url_exists]):
            print("🎉 Rollback completed successfully!")
        else:
            print("⚠️  Rollback completed with warnings - some objects may still exist")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        raise
    finally:
        await conn.close()
        print()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    asyncio.run(rollback_migration())
