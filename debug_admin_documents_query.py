#!/usr/bin/env python3
"""
Debug script to diagnose the admin documents query issue.
This script must be run on Railway: railway run python3 debug_admin_documents_query.py
"""

import asyncio
import asyncpg
import os
import sys
import json
from datetime import datetime

async def debug_admin_documents():
    """Debug the admin documents query step by step"""
    
    try:
        # Connect to database
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return
            
        print(f"🔗 Connecting to database...")
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
        
        # Check if key tables exist
        has_books = 'books' in table_names
        has_documents = 'documents' in table_names
        has_authors = 'authors' in table_names
        has_document_authors = 'document_authors' in table_names
        
        print(f"\n📊 TABLE STATUS:")
        print(f"  - books: {'✅' if has_books else '❌'}")
        print(f"  - documents: {'✅' if has_documents else '❌'}")
        print(f"  - authors: {'✅' if has_authors else '❌'}")
        print(f"  - document_authors: {'✅' if has_document_authors else '❌'}")
        
        # Count records in each table
        if has_books:
            books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            print(f"  - books count: {books_count}")
            
            if books_count > 0:
                # Show sample books
                sample_books = await conn.fetch("SELECT id, filename, title, author FROM books LIMIT 3")
                print(f"  - sample books:")
                for book in sample_books:
                    print(f"    ID {book['id']}: {book['filename']} - {book['title']} by {book['author']}")
        
        if has_documents:
            docs_count = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
            print(f"  - documents count (unique filenames): {docs_count}")
        
        if has_authors:
            authors_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
            print(f"  - authors count: {authors_count}")
            
            if authors_count > 0:
                sample_authors = await conn.fetch("SELECT id, name FROM authors LIMIT 3")
                print(f"  - sample authors:")
                for author in sample_authors:
                    print(f"    ID {author['id']}: {author['name']}")
        
        if has_document_authors:
            doc_authors_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
            print(f"  - document_authors count: {doc_authors_count}")
        
        # Test the current failing query
        print(f"\n🔍 TESTING CURRENT ADMIN QUERY:")
        try:
            current_query = """
                SELECT DISTINCT b.id, b.filename, b.title, b.category, 
                       COALESCE(b.document_type, 'book') as document_type, 
                       b.mc_press_url, 
                       COALESCE(b.article_url, '') as article_url,
                       b.created_at,
                       COALESCE(a.name, b.author, 'Unknown Author') as author_name,
                       a.site_url as author_site_url,
                       da.author_order
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.document_id
                LEFT JOIN authors a ON da.author_id = a.id
                WHERE 1=1
                ORDER BY b.title ASC, da.author_order ASC
                LIMIT 5
            """
            
            current_results = await conn.fetch(current_query)
            print(f"Current query returned {len(current_results)} rows")
            
            if current_results:
                print("Sample results:")
                for i, row in enumerate(current_results[:3]):
                    print(f"  Row {i+1}: ID={row['id']}, filename={row['filename']}, title={row['title']}, author={row['author_name']}")
            else:
                print("❌ Current query returns no results!")
                
        except Exception as e:
            print(f"❌ Current query failed: {e}")
        
        # Test simplified query without joins
        print(f"\n🔍 TESTING SIMPLIFIED QUERY (books only):")
        try:
            simple_query = """
                SELECT id, filename, title, author, category, 
                       COALESCE(document_type, 'book') as document_type,
                       mc_press_url, article_url, created_at
                FROM books 
                ORDER BY title ASC
                LIMIT 10
            """
            
            simple_results = await conn.fetch(simple_query)
            print(f"Simplified query returned {len(simple_results)} rows")
            
            if simple_results:
                print("Sample results:")
                for i, row in enumerate(simple_results[:5]):
                    print(f"  Row {i+1}: ID={row['id']}, filename={row['filename']}, title={row['title']}, author={row['author']}")
            else:
                print("❌ Even simplified query returns no results!")
                
        except Exception as e:
            print(f"❌ Simplified query failed: {e}")
        
        # Check books table schema
        if has_books:
            print(f"\n📋 BOOKS TABLE SCHEMA:")
            schema = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'books' 
                ORDER BY ordinal_position
            """)
            
            for col in schema:
                print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        await conn.close()
        print(f"\n✅ Diagnosis complete")
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 ADMIN DOCUMENTS QUERY DIAGNOSTIC")
    print("=" * 50)
    asyncio.run(debug_admin_documents())