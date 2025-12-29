#!/usr/bin/env python3
"""
Simple script to check document_authors table population on Railway.
This script only uses asyncpg to avoid import issues.
"""

import os
import asyncio
import asyncpg

async def check_document_authors():
    """Check if document_authors table has data"""
    print("=" * 60)
    print("CHECKING DOCUMENT_AUTHORS TABLE")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check total count of document_authors associations
        total_associations = await conn.fetchval("""
            SELECT COUNT(*) FROM document_authors
        """)
        print(f"Total document_authors associations: {total_associations}")
        
        # Check sample associations with author names for articles
        sample_associations = await conn.fetch("""
            SELECT 
                b.filename,
                b.title,
                b.author as legacy_author,
                a.name as author_name,
                da.author_order
            FROM document_authors da
            JOIN books b ON da.book_id = b.id
            JOIN authors a ON da.author_id = a.id
            WHERE b.document_type = 'article'
            ORDER BY b.filename
            LIMIT 10
        """)
        
        print(f"\nSample article associations:")
        for row in sample_associations:
            print(f"  {row['filename']}: {row['author_name']} (order {row['author_order']}) | legacy: {row['legacy_author']}")
        
        # Check for articles without author associations
        articles_without_authors = await conn.fetch("""
            SELECT b.filename, b.title, b.author as legacy_author
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            WHERE b.document_type = 'article' 
            AND da.book_id IS NULL
            LIMIT 5
        """)
        
        print(f"\nArticles without author associations (showing first 5):")
        for row in articles_without_authors:
            print(f"  {row['filename']}: legacy_author='{row['legacy_author']}'")
        
        # Check if we have any articles with both legacy and multi-author data
        articles_with_both = await conn.fetch("""
            SELECT 
                b.filename,
                b.title,
                b.author as legacy_author,
                COUNT(da.author_id) as author_count,
                STRING_AGG(a.name, ', ' ORDER BY da.author_order) as multi_authors
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            LEFT JOIN authors a ON da.author_id = a.id
            WHERE b.document_type = 'article'
            AND b.author IS NOT NULL
            AND b.author != ''
            GROUP BY b.id, b.filename, b.title, b.author
            HAVING COUNT(da.author_id) > 0
            LIMIT 5
        """)
        
        print(f"\nArticles with both legacy and multi-author data:")
        for row in articles_with_both:
            print(f"  {row['filename']}: legacy='{row['legacy_author']}' | multi='{row['multi_authors']}' ({row['author_count']} authors)")
        
        await conn.close()
        return total_associations > 0
        
    except Exception as e:
        print(f"❌ Error checking document_authors table: {e}")
        return False

async def main():
    """Main function"""
    print("Checking author associations after Excel import fix...")
    
    success = await check_document_authors()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ Document_authors table has data")
        print("✅ The Excel import fix should now create author associations")
        print("✅ Source enrichment should be able to retrieve real author names")
    else:
        print("❌ Document_authors table is empty or has issues")
        print("❌ Need to run article metadata import to populate associations")

if __name__ == "__main__":
    asyncio.run(main())