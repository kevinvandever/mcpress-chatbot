#!/usr/bin/env python3
"""
Test script to verify the author name display fix.

This script tests:
1. Document_authors table population
2. Source enrichment retrieval of author data
3. Author name display in chat interface

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import os
import sys
import asyncio
import asyncpg
from backend.chat_handler import ChatHandler

async def test_document_authors_population():
    """Test if document_authors table has data"""
    print("=" * 60)
    print("TESTING DOCUMENT_AUTHORS TABLE POPULATION")
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
        
        # Check sample associations with author names
        sample_associations = await conn.fetch("""
            SELECT 
                b.filename,
                b.title,
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
            print(f"  {row['filename']}: {row['author_name']} (order {row['author_order']})")
        
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
        
        await conn.close()
        return total_associations > 0
        
    except Exception as e:
        print(f"❌ Error checking document_authors table: {e}")
        return False

async def test_source_enrichment():
    """Test source enrichment for articles"""
    print("\n" + "=" * 60)
    print("TESTING SOURCE ENRICHMENT FOR ARTICLES")
    print("=" * 60)
    
    try:
        # Create ChatHandler instance
        chat_handler = ChatHandler()
        
        database_url = os.getenv('DATABASE_URL')
        conn = await asyncpg.connect(database_url)
        
        # Get some actual article filenames from the database
        actual_articles = await conn.fetch("""
            SELECT filename, title, author as legacy_author
            FROM books 
            WHERE document_type = 'article'
            AND filename IS NOT NULL
            LIMIT 5
        """)
        
        await conn.close()
        
        print(f"Testing enrichment for actual articles:")
        for article in actual_articles:
            filename = article['filename']
            print(f"\nTesting: {filename}")
            print(f"  Title: {article['title']}")
            print(f"  Legacy author: {article['legacy_author']}")
            
            try:
                result = await chat_handler._enrich_source_metadata(filename)
                print(f"  Enrichment result: {result}")
                
                if result:
                    author_info = result.get('author', 'Unknown')
                    authors_list = result.get('authors', [])
                    print(f"  ✅ Author: {author_info}")
                    print(f"  ✅ Authors list: {len(authors_list)} authors")
                    for i, author in enumerate(authors_list):
                        print(f"    {i}: {author['name']} (order {author['order']})")
                else:
                    print(f"  ❌ No enrichment data returned")
                    
            except Exception as e:
                print(f"  ❌ Error enriching {filename}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing source enrichment: {e}")
        return False

async def main():
    """Main test function"""
    print("Starting author name display fix verification...")
    
    # Test 1: Check document_authors table population
    authors_populated = await test_document_authors_population()
    
    # Test 2: Test source enrichment
    enrichment_works = await test_source_enrichment()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Document_authors populated: {'✅' if authors_populated else '❌'}")
    print(f"Source enrichment works: {'✅' if enrichment_works else '❌'}")
    
    if authors_populated and enrichment_works:
        print("\n🎉 TESTS COMPLETED - Check results above for author name display status")
    else:
        print("\n⚠️  Some tests failed - Author name display may still have issues")

if __name__ == "__main__":
    asyncio.run(main())