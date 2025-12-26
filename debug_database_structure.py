#!/usr/bin/env python3
"""
Debug the actual database structure to understand where articles are stored
"""

import asyncio
import asyncpg
import os

async def main():
    print("🔍 Debugging database structure...")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        print("\n1. Checking table structure...")
        
        # Check what tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print("Available tables:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # Check books table structure
        print(f"\n2. Books table structure:")
        books_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)
        
        for col in books_columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Check documents table structure  
        print(f"\n3. Documents table structure:")
        docs_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        
        for col in docs_columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Count records in each table
        print(f"\n4. Record counts:")
        
        books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"  - books: {books_count}")
        
        docs_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"  - documents: {docs_count}")
        
        # Check for numeric filenames in documents table
        print(f"\n5. Looking for numeric filenames in documents table...")
        
        numeric_docs = await conn.fetch("""
            SELECT DISTINCT filename
            FROM documents
            WHERE filename ~ '^[0-9]+\.pdf$'
            ORDER BY filename
            LIMIT 10
        """)
        
        print(f"Found {len(numeric_docs)} numeric filenames in documents table:")
        for doc in numeric_docs:
            print(f"  - {doc['filename']}")
        
        # Check for numeric filenames in books table
        print(f"\n6. Looking for numeric filenames in books table...")
        
        numeric_books = await conn.fetch("""
            SELECT filename, title, document_type
            FROM books
            WHERE filename ~ '^[0-9]+\.pdf$'
            ORDER BY filename
            LIMIT 10
        """)
        
        print(f"Found {len(numeric_books)} numeric filenames in books table:")
        for book in numeric_books:
            print(f"  - {book['filename']}: {book['title']} ({book['document_type']})")
        
        # Sample some documents to see their metadata
        print(f"\n7. Sample documents with numeric filenames:")
        
        sample_docs = await conn.fetch("""
            SELECT filename, metadata, page_number
            FROM documents
            WHERE filename ~ '^[0-9]+\.pdf$'
            ORDER BY filename
            LIMIT 5
        """)
        
        for doc in sample_docs:
            print(f"  - {doc['filename']} (page {doc['page_number']})")
            if doc['metadata']:
                import json
                try:
                    metadata = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
                    print(f"    Metadata: {metadata}")
                except:
                    print(f"    Metadata: {doc['metadata']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())