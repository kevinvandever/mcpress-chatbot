#!/usr/bin/env python3
"""
Admin Documents Database Verification Script

This script must be run on Railway: railway run python3 test_admin_documents_database_verification.py

Verifies that documents exist in the database and that queries work correctly.
Tests document count, sample retrieval, and table joins for author data.

Requirements: 5.1, 5.2, 5.5
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime

async def verify_database_connection():
    """Test basic database connectivity"""
    
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return None
    
    print(f"Database URL configured: {database_url[:50]}...")
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful")
        
        # Test basic query
        result = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL version: {result}")
        
        return conn
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

async def verify_documents_table(conn):
    """Verify documents table exists and has data"""
    
    print("\n" + "=" * 60)
    print("DOCUMENTS TABLE VERIFICATION")
    print("=" * 60)
    
    try:
        # Check if documents table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'documents'
            )
        """)
        
        print(f"Documents table exists: {table_exists}")
        
        if not table_exists:
            print("❌ Documents table does not exist!")
            return False
        
        # Get table schema
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        
        print(f"\nDocuments table schema:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Count total documents
        total_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"\nTotal documents in table: {total_count}")
        
        if total_count == 0:
            print("❌ No documents found in documents table!")
            return False
        
        # Get sample documents
        sample_docs = await conn.fetch("""
            SELECT id, filename, title, created_at, metadata
            FROM documents 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        print(f"\nSample documents (latest 5):")
        for doc in sample_docs:
            print(f"  ID: {doc['id']}")
            print(f"    Filename: {doc['filename']}")
            print(f"    Title: {doc['title']}")
            print(f"    Created: {doc['created_at']}")
            print(f"    Metadata keys: {list(doc['metadata'].keys()) if doc['metadata'] else 'None'}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Documents table verification failed: {e}")
        return False

async def verify_books_table(conn):
    """Verify books table exists and has data (alternative to documents)"""
    
    print("\n" + "=" * 60)
    print("BOOKS TABLE VERIFICATION")
    print("=" * 60)
    
    try:
        # Check if books table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'books'
            )
        """)
        
        print(f"Books table exists: {table_exists}")
        
        if not table_exists:
            print("Books table does not exist")
            return False
        
        # Get table schema
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)
        
        print(f"\nBooks table schema:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Count total books
        total_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"\nTotal books in table: {total_count}")
        
        if total_count == 0:
            print("No books found in books table")
            return False
        
        # Get sample books
        sample_books = await conn.fetch("""
            SELECT id, filename, title, document_type, total_pages, created_at
            FROM books 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        print(f"\nSample books (latest 5):")
        for book in sample_books:
            print(f"  ID: {book['id']}")
            print(f"    Filename: {book['filename']}")
            print(f"    Title: {book['title']}")
            print(f"    Type: {book['document_type']}")
            print(f"    Pages: {book['total_pages']}")
            print(f"    Created: {book['created_at']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Books table verification failed: {e}")
        return False

async def verify_author_tables(conn):
    """Verify author-related tables and joins"""
    
    print("\n" + "=" * 60)
    print("AUTHOR TABLES VERIFICATION")
    print("=" * 60)
    
    try:
        # Check authors table
        authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'authors'
            )
        """)
        
        print(f"Authors table exists: {authors_exists}")
        
        if authors_exists:
            author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
            print(f"Total authors: {author_count}")
            
            # Sample authors
            sample_authors = await conn.fetch("""
                SELECT id, name, site_url
                FROM authors 
                LIMIT 5
            """)
            
            print(f"Sample authors:")
            for author in sample_authors:
                print(f"  ID: {author['id']}, Name: {author['name']}, URL: {author['site_url']}")
        
        # Check document_authors junction table
        doc_authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'document_authors'
            )
        """)
        
        print(f"\nDocument_authors table exists: {doc_authors_exists}")
        
        if doc_authors_exists:
            doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
            print(f"Total document-author associations: {doc_author_count}")
        
        return authors_exists and doc_authors_exists
        
    except Exception as e:
        print(f"❌ Author tables verification failed: {e}")
        return False

async def test_admin_documents_query(conn):
    """Test the actual query that the admin documents endpoint should use"""
    
    print("\n" + "=" * 60)
    print("ADMIN DOCUMENTS QUERY TEST")
    print("=" * 60)
    
    # Try different query variations to see what works
    
    # Query 1: Simple documents query
    try:
        print("Testing simple documents query...")
        docs = await conn.fetch("""
            SELECT id, filename, title, created_at
            FROM documents 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        print(f"✅ Simple documents query returned {len(docs)} results")
        
        if docs:
            print("Sample result:")
            doc = docs[0]
            print(f"  ID: {doc['id']}, Filename: {doc['filename']}, Title: {doc['title']}")
        
    except Exception as e:
        print(f"❌ Simple documents query failed: {e}")
    
    # Query 2: Books query (if documents is empty)
    try:
        print("\nTesting books query...")
        books = await conn.fetch("""
            SELECT id, filename, title, document_type, total_pages, created_at
            FROM books 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        print(f"✅ Books query returned {len(books)} results")
        
        if books:
            print("Sample result:")
            book = books[0]
            print(f"  ID: {book['id']}, Filename: {book['filename']}, Title: {book['title']}")
        
    except Exception as e:
        print(f"❌ Books query failed: {e}")
    
    # Query 3: Documents with authors join
    try:
        print("\nTesting documents with authors join...")
        docs_with_authors = await conn.fetch("""
            SELECT d.id, d.filename, d.title, d.created_at,
                   a.name as author_name, a.site_url as author_site_url
            FROM documents d
            LEFT JOIN document_authors da ON d.id = da.document_id
            LEFT JOIN authors a ON da.author_id = a.id
            ORDER BY d.created_at DESC 
            LIMIT 10
        """)
        
        print(f"✅ Documents with authors join returned {len(docs_with_authors)} results")
        
        if docs_with_authors:
            print("Sample result:")
            doc = docs_with_authors[0]
            print(f"  ID: {doc['id']}, Filename: {doc['filename']}")
            print(f"  Author: {doc['author_name']}, URL: {doc['author_site_url']}")
        
    except Exception as e:
        print(f"❌ Documents with authors join failed: {e}")
    
    # Query 4: Books with authors join
    try:
        print("\nTesting books with authors join...")
        books_with_authors = await conn.fetch("""
            SELECT b.id, b.filename, b.title, b.document_type, b.created_at,
                   a.name as author_name, a.site_url as author_site_url
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.document_id
            LEFT JOIN authors a ON da.author_id = a.id
            ORDER BY b.created_at DESC 
            LIMIT 10
        """)
        
        print(f"✅ Books with authors join returned {len(books_with_authors)} results")
        
        if books_with_authors:
            print("Sample result:")
            book = books_with_authors[0]
            print(f"  ID: {book['id']}, Filename: {book['filename']}")
            print(f"  Author: {book['author_name']}, URL: {book['author_site_url']}")
        
    except Exception as e:
        print(f"❌ Books with authors join failed: {e}")

async def main():
    """Main verification function"""
    
    print("Starting Admin Documents Database Verification...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Connect to database
    conn = await verify_database_connection()
    if not conn:
        return 1
    
    try:
        # Verify tables
        docs_ok = await verify_documents_table(conn)
        books_ok = await verify_books_table(conn)
        authors_ok = await verify_author_tables(conn)
        
        # Test queries
        await test_admin_documents_query(conn)
        
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Documents table: {'✅' if docs_ok else '❌'}")
        print(f"Books table: {'✅' if books_ok else '❌'}")
        print(f"Author tables: {'✅' if authors_ok else '❌'}")
        
        if not docs_ok and not books_ok:
            print("\n❌ CRITICAL: No document data found in either documents or books table!")
            print("This explains why the admin documents endpoint returns empty results.")
        elif docs_ok or books_ok:
            print("\n✅ Document data exists in database")
            print("The issue may be in the API endpoint query or response formatting.")
        
        return 0 if (docs_ok or books_ok) else 1
        
    finally:
        await conn.close()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nVerification failed with error: {e}")
        sys.exit(1)