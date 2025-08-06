#!/usr/bin/env python3
"""
Initialize Railway PostgreSQL Database (Simple Version)
Creates tables for PDF chatbot without pgvector
Uses array storage for embeddings instead
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def init_database():
    """Initialize database with required tables (no pgvector required)"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    print("🔧 Initializing Railway PostgreSQL Database (Simple Version)")
    print("="*50)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to Railway PostgreSQL")
        
        # Check current database size
        db_size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        print(f"📊 Current database size: {db_size}")
        
        # Create books table
        print("\n📚 Creating books table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                category TEXT,
                total_pages INTEGER,
                file_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Books table created")
        
        # Create embeddings table with array storage
        print("\n🔤 Creating embeddings table (array-based)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                chunk_index INTEGER,
                content TEXT,
                embedding REAL[],  -- Store as array instead of vector type
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Embeddings table created")
        
        # Create indexes
        print("\n🔍 Creating indexes...")
        
        # Book lookup indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_filename ON books(filename)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_book_id ON embeddings(book_id)
        """)
        print("✅ Lookup indexes created")
        
        # Verify tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('books', 'embeddings')
        """)
        
        print("\n✅ Database initialization complete!")
        print("\n📋 Tables created:")
        for table in tables:
            print(f"   - {table['tablename']}")
        
        # Check if any data exists
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
        
        print(f"\n📊 Current data:")
        print(f"   Books: {book_count}")
        print(f"   Embeddings: {embedding_count}")
        
        # Check for old data that might be taking up space
        if book_count > 0:
            # Get sample of books
            sample_books = await conn.fetch("""
                SELECT title, author, 
                       (SELECT COUNT(*) FROM embeddings WHERE book_id = books.id) as chunks
                FROM books 
                LIMIT 5
            """)
            print(f"\n📚 Sample of existing books:")
            for book in sample_books:
                print(f"   - {book['title'][:50]}... ({book['chunks']} chunks)")
            
            print(f"\n⚠️  Database contains {book_count} books")
            print("   To clean up old data, run: python cleanup_railway_db.py")
        else:
            print("\n📝 Database is ready for data import!")
            print("   Next step: Run 'python preprocess_books_locally.py'")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check your DATABASE_URL in .env")
        print("2. Ensure Railway PostgreSQL is running")
        print("3. Check Railway dashboard for database status")

if __name__ == "__main__":
    asyncio.run(init_database())