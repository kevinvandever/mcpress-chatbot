#!/usr/bin/env python3
"""
Railway Database Cleanup Script
Removes old/incomplete book data before fresh preprocessing
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def cleanup_database():
    """Clean up Railway PostgreSQL database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    print("🧹 Railway Database Cleanup Script")
    print("="*50)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        # Get current statistics
        print("\n📊 Current Database Status:")
        
        # Check books
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"   Books: {book_count}")
        
        # Check embeddings
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
        print(f"   Embeddings: {embedding_count}")
        
        # Check database size
        db_size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        print(f"   Database size: {db_size}")
        
        # Show sample of books
        print("\n📚 Sample of current books:")
        sample_books = await conn.fetch("""
            SELECT title, author, total_pages, 
                   (SELECT COUNT(*) FROM embeddings WHERE book_id = books.id) as chunks
            FROM books 
            LIMIT 5
        """)
        for book in sample_books:
            print(f"   - {book['title'][:50]}... ({book['chunks']} chunks)")
        
        # Ask for confirmation
        print("\n" + "="*50)
        print("⚠️  WARNING: This will DELETE all book data!")
        print("   This includes:")
        print(f"   - {book_count} books")
        print(f"   - {embedding_count} embeddings/vectors")
        print("\n   This action cannot be undone!")
        print("="*50)
        
        response = input("\n🔴 Type 'DELETE ALL' to confirm cleanup: ")
        
        if response == 'DELETE ALL':
            print("\n🗑️  Deleting all data...")
            
            # Delete embeddings first (foreign key constraint)
            print("   Deleting embeddings...")
            deleted_embeddings = await conn.fetchval("DELETE FROM embeddings RETURNING COUNT(*)")
            
            # Delete books
            print("   Deleting books...")
            deleted_books = await conn.fetchval("DELETE FROM books RETURNING COUNT(*)")
            
            # Vacuum to reclaim space
            print("   Reclaiming space (VACUUM)...")
            await conn.execute("VACUUM ANALYZE")
            
            # Get new size
            new_db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            
            print("\n✅ Cleanup Complete!")
            print(f"   Deleted {deleted_books} books")
            print(f"   Deleted {deleted_embeddings} embeddings")
            print(f"   Database size: {db_size} → {new_db_size}")
            
            # Create fresh tables if they don't exist
            print("\n🔧 Ensuring tables exist for fresh import...")
            
            # Ensure vector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create books table
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
            
            # Create embeddings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                    chunk_index INTEGER,
                    content TEXT,
                    embedding vector(384),
                    page_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for vector search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
                ON embeddings USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            print("✅ Tables ready for fresh data import!")
            print("\n📝 Next step: Run 'python preprocess_books_locally.py'")
            
        else:
            print("\n❌ Cleanup cancelled. No changes made.")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check your DATABASE_URL in .env")
        print("2. Ensure Railway PostgreSQL is running")
        print("3. Check Railway dashboard for database status")

async def check_specific_issues():
    """Check for specific issues like duplicate entries or orphaned records"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return
    
    print("\n🔍 Checking for data issues...")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check for duplicate filenames
        duplicates = await conn.fetch("""
            SELECT filename, COUNT(*) as count
            FROM books
            GROUP BY filename
            HAVING COUNT(*) > 1
        """)
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate book entries")
            for dup in duplicates:
                print(f"   - {dup['filename']}: {dup['count']} copies")
        
        # Check for books without embeddings
        no_embeddings = await conn.fetch("""
            SELECT b.title, b.filename
            FROM books b
            LEFT JOIN embeddings e ON b.id = e.book_id
            WHERE e.id IS NULL
        """)
        
        if no_embeddings:
            print(f"⚠️  Found {len(no_embeddings)} books without embeddings")
            for book in no_embeddings[:5]:  # Show first 5
                print(f"   - {book['title'][:50]}...")
        
        # Check for orphaned embeddings
        orphaned = await conn.fetchval("""
            SELECT COUNT(*)
            FROM embeddings e
            LEFT JOIN books b ON e.book_id = b.id
            WHERE b.id IS NULL
        """)
        
        if orphaned > 0:
            print(f"⚠️  Found {orphaned} orphaned embeddings")
        
        await conn.close()
        
    except Exception as e:
        print(f"Could not check for issues: {str(e)}")

if __name__ == "__main__":
    print("🚀 Railway Database Cleanup Utility")
    print("Choose an option:")
    print("1. Clean up database (delete all book data)")
    print("2. Check for data issues")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ")
    
    if choice == "1":
        asyncio.run(cleanup_database())
    elif choice == "2":
        asyncio.run(check_specific_issues())
    else:
        print("Goodbye!")