#!/usr/bin/env python3
"""
Debug Source Enrichment Title Display
Investigates why chat interface shows ID numbers instead of titles
"""

import asyncio
import asyncpg
import os
import json

async def debug_enrichment():
    """Debug the source enrichment process for title display"""
    
    print("🔍 DEBUGGING SOURCE ENRICHMENT TITLE DISPLAY")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    conn = await asyncpg.connect(database_url)
    
    try:
        # Test the exact query used in chat_handler.py _enrich_source_metadata
        print("🔍 Testing enrichment query for sample articles...")
        
        # Get some sample article filenames
        sample_articles = await conn.fetch("""
            SELECT filename, title, document_type, author, article_url
            FROM books 
            WHERE filename ~ '^[0-9]+\.pdf$'
            LIMIT 5
        """)
        
        print(f"📋 Found {len(sample_articles)} sample articles:")
        for article in sample_articles:
            print(f"  {article['filename']}: '{article['title']}' (type: {article['document_type']})")
        
        print("\n🔍 Testing enrichment query for each sample...")
        
        for article in sample_articles:
            filename = article['filename']
            print(f"\n--- Testing enrichment for {filename} ---")
            
            # This is the exact query from chat_handler.py
            book_data = await conn.fetchrow("""
                SELECT 
                    b.id,
                    b.filename,
                    b.title,
                    b.author as legacy_author,
                    b.mc_press_url,
                    b.article_url,
                    b.document_type
                FROM books b
                WHERE b.filename = $1
                LIMIT 1
            """, filename)
            
            if book_data:
                print(f"  ✅ Found book data:")
                print(f"    ID: {book_data['id']}")
                print(f"    Filename: {book_data['filename']}")
                print(f"    Title: '{book_data['title']}'")
                print(f"    Author: '{book_data['legacy_author']}'")
                print(f"    Document Type: '{book_data['document_type']}'")
                print(f"    Article URL: '{book_data['article_url']}'")
                
                # Test multi-author query
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
                """, book_data['id'])
                
                if authors:
                    print(f"  ✅ Found {len(authors)} multi-author records:")
                    for author in authors:
                        print(f"    - {author['name']} (URL: {author['site_url']})")
                else:
                    print(f"  ⚠️ No multi-author records found")
                
                # Simulate the enrichment response
                if authors:
                    author_names = ", ".join([author['name'] for author in authors])
                    authors_list = [
                        {
                            "id": author['id'],
                            "name": author['name'],
                            "site_url": author['site_url'],
                            "order": author['author_order']
                        }
                        for author in authors
                    ]
                else:
                    author_names = book_data['legacy_author'] or "Unknown"
                    authors_list = []
                
                enrichment_result = {
                    "author": author_names,
                    "mc_press_url": book_data['mc_press_url'] or "",
                    "article_url": book_data['article_url'],
                    "document_type": book_data['document_type'] or "book",
                    "authors": authors_list
                }
                
                print(f"  📤 Enrichment result:")
                print(f"    {json.dumps(enrichment_result, indent=4)}")
                
            else:
                print(f"  ❌ No book data found for {filename}")
        
        print("\n🔍 Testing a sample chat enrichment call...")
        
        # Test what happens in the chat handler _format_sources method
        if sample_articles:
            test_filename = sample_articles[0]['filename']
            print(f"Testing _format_sources logic for {test_filename}...")
            
            # Simulate the source data structure that comes from vector search
            mock_source = {
                "metadata": {
                    "filename": test_filename,
                    "page": 1,
                    "author": "Unknown"  # This is what comes from vector search initially
                },
                "distance": 0.3
            }
            
            print(f"  📥 Mock source input: {json.dumps(mock_source, indent=4)}")
            
            # Run the enrichment query
            enriched_metadata = {}
            book_data = await conn.fetchrow("""
                SELECT 
                    b.id,
                    b.filename,
                    b.title,
                    b.author as legacy_author,
                    b.mc_press_url,
                    b.article_url,
                    b.document_type
                FROM books b
                WHERE b.filename = $1
                LIMIT 1
            """, test_filename)
            
            if book_data:
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
                """, book_data['id'])
                
                if authors:
                    author_names = ", ".join([author['name'] for author in authors])
                    authors_list = [
                        {
                            "id": author['id'],
                            "name": author['name'],
                            "site_url": author['site_url'],
                            "order": author['author_order']
                        }
                        for author in authors
                    ]
                else:
                    author_names = book_data['legacy_author'] or "Unknown"
                    authors_list = []
                
                enriched_metadata = {
                    "author": author_names,
                    "mc_press_url": book_data['mc_press_url'] or "",
                    "article_url": book_data['article_url'],
                    "document_type": book_data['document_type'] or "book",
                    "authors": authors_list
                }
            
            # Simulate the final source object that gets sent to frontend
            final_source = {
                "filename": test_filename,
                "page": mock_source["metadata"]["page"],
                "type": "text",
                "distance": mock_source["distance"],
                "author": enriched_metadata.get("author", "Unknown"),
                "mc_press_url": enriched_metadata.get("mc_press_url", ""),
                "article_url": enriched_metadata.get("article_url"),
                "document_type": enriched_metadata.get("document_type", "book"),
                "authors": enriched_metadata.get("authors", [])
            }
            
            print(f"  📤 Final source object sent to frontend:")
            print(f"    {json.dumps(final_source, indent=4)}")
            
            # Check what the frontend should display
            display_title = test_filename.replace('.pdf', '')  # This is what frontend currently does
            expected_title = book_data['title'] if book_data else test_filename.replace('.pdf', '')
            
            print(f"\n🎯 TITLE ANALYSIS:")
            print(f"  Current frontend display: '{display_title}' (filename without .pdf)")
            print(f"  Expected display: '{expected_title}' (from books.title)")
            print(f"  Title in database: '{book_data['title'] if book_data else 'NOT FOUND'}'")
            
            if display_title != expected_title:
                print(f"  ❌ PROBLEM: Frontend is not using the title from enrichment!")
                print(f"  🔧 SOLUTION: Frontend needs to use enriched title data")
            else:
                print(f"  ✅ Title display is correct")
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_enrichment())