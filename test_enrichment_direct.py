#!/usr/bin/env python3
"""
Direct test of the _enrich_source_metadata method on Railway.
This script tests the enrichment logic in isolation to verify the fix works.
"""

import asyncio
import os
import sys
import logging
from typing import Dict, Any

# Add backend to path for imports
sys.path.append('backend')

try:
    import asyncpg
    from backend.chat_handler import ChatHandler
except ImportError as e:
    print(f"Import error: {e}")
    print("This script must be run on Railway where dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enrich_source_metadata():
    """Test the _enrich_source_metadata method directly"""
    
    # Create ChatHandler instance
    chat_handler = ChatHandler()
    
    # Test filenames - these should exist in the production database
    test_filenames = [
        "rpg-iv-jump-start-fourth-edition.pdf",  # Known book
        "modernizing-ibm-i-applications-from-the-database-up.pdf",  # Another known book
        "nonexistent-file.pdf"  # Should return empty dict
    ]
    
    print("=" * 60)
    print("TESTING _enrich_source_metadata METHOD DIRECTLY")
    print("=" * 60)
    
    # Check DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        return
    else:
        print(f"✅ DATABASE_URL is set: {database_url[:50]}...")
    
    print()
    
    for filename in test_filenames:
        print(f"Testing filename: {filename}")
        print("-" * 40)
        
        try:
            # Call the enrichment method
            result = await chat_handler._enrich_source_metadata(filename)
            
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
            
            if result:
                print("✅ Enrichment successful!")
                print(f"  Author: {result.get('author', 'N/A')}")
                print(f"  Document Type: {result.get('document_type', 'N/A')}")
                print(f"  MC Press URL: {result.get('mc_press_url', 'N/A')}")
                print(f"  Article URL: {result.get('article_url', 'N/A')}")
                print(f"  Authors count: {len(result.get('authors', []))}")
                
                # Show author details if available
                authors = result.get('authors', [])
                if authors:
                    print("  Author details:")
                    for i, author in enumerate(authors):
                        print(f"    {i+1}. {author.get('name', 'N/A')} (order: {author.get('order', 'N/A')})")
                        if author.get('site_url'):
                            print(f"       URL: {author['site_url']}")
            else:
                print("⚠️  Enrichment returned empty dict")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        
        print()
    
    print("=" * 60)
    print("TESTING DATABASE CONNECTION DIRECTLY")
    print("=" * 60)
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Direct database connection successful")
        
        # Test basic query
        result = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"✅ Books table accessible, count: {result}")
        
        # Test specific book lookup
        book = await conn.fetchrow("""
            SELECT id, filename, title, author as legacy_author 
            FROM books 
            WHERE filename LIKE '%rpg%' 
            LIMIT 1
        """)
        
        if book:
            print(f"✅ Sample book found: {book['title']} (ID: {book['id']})")
            
            # Test document_authors query with correct column name
            authors = await conn.fetch("""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    da.author_order
                FROM document_authors da
                JOIN authors a ON da.author_id = a.id
                WHERE da.book_id = $1
                ORDER BY da.author_order
            """, book['id'])
            
            print(f"✅ Authors query successful, found {len(authors)} authors")
            for author in authors:
                print(f"  - {author['name']} (order: {author['author_order']})")
        else:
            print("⚠️  No sample book found")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

async def main():
    """Main test function"""
    print("Starting direct enrichment test...")
    await test_enrich_source_metadata()
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main())