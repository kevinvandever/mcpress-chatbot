#!/usr/bin/env python3
"""
Run Migration 003: Multi-Author Metadata Enhancement
Creates authors table, document_authors junction table, and adds document_type fields
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

async def run_migration():
    """Execute the migration SQL script"""
    print("🚀 Starting Migration 003: Multi-Author Metadata Enhancement")
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    # Read migration SQL
    migration_file = Path(__file__).parent / "migrations" / "003_multi_author_support.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        exit(1)
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Connect to database
    print("🔌 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if books table exists
        books_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'books'
            )
        """)
        
        if not books_exists:
            print("⚠️  Warning: books table does not exist")
            print("   This migration requires an existing books table")
            response = input("   Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return
        
        print("✅ Books table found")
        print()
        
        # Execute migration
        print("📝 Executing migration SQL...")
        await conn.execute(migration_sql)
        print("✅ Migration SQL executed successfully")
        print()
        
        # Verify tables were created
        print("🔍 Verifying migration...")
        
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
        print(f"  {'✅' if authors_exists else '❌'} authors table")
        print(f"  {'✅' if document_authors_exists else '❌'} document_authors table")
        print(f"  {'✅' if document_type_exists else '❌'} books.document_type column")
        print(f"  {'✅' if article_url_exists else '❌'} books.article_url column")
        print()
        
        if all([authors_exists, document_authors_exists, document_type_exists, article_url_exists]):
            print("🎉 Migration 003 completed successfully!")
            print()
            print("📋 Next steps:")
            print("   1. Run data migration to populate authors from existing books.author column")
            print("   2. Update application code to use new multi-author schema")
            print("   3. Test the new functionality")
        else:
            print("⚠️  Migration completed with warnings - some objects may not have been created")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print()
        print("💡 To rollback, run:")
        print("   python backend/run_migration_003_rollback.py")
        raise
    finally:
        await conn.close()
        print()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    asyncio.run(run_migration())
