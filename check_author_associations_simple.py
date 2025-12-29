#!/usr/bin/env python3
"""
Simple script to check if document_authors associations exist.
This can be run on Railway to verify the fix.
"""

import os
import asyncio
import asyncpg

async def check_associations():
    """Check document_authors table status"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check total associations
        total = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        print(f"Total document_authors associations: {total}")
        
        # Check articles with associations
        article_associations = await conn.fetchval("""
            SELECT COUNT(DISTINCT da.book_id) 
            FROM document_authors da
            JOIN books b ON da.book_id = b.id
            WHERE b.document_type = 'article'
        """)
        print(f"Articles with author associations: {article_associations}")
        
        # Check articles without associations
        articles_without = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            WHERE b.document_type = 'article' AND da.book_id IS NULL
        """)
        print(f"Articles without author associations: {articles_without}")
        
        # Sample of articles with authors
        sample = await conn.fetch("""
            SELECT b.filename, a.name as author_name
            FROM document_authors da
            JOIN books b ON da.book_id = b.id
            JOIN authors a ON da.author_id = a.id
            WHERE b.document_type = 'article'
            LIMIT 5
        """)
        
        print("\nSample articles with authors:")
        for row in sample:
            print(f"  {row['filename']}: {row['author_name']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_associations())