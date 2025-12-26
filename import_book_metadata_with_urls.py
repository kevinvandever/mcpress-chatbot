#!/usr/bin/env python3
"""
Import book metadata from MC Press Books - URL-Title-Author.xlsx
This script specifically handles author site URLs which are missing from the current import logic.
"""

import os
import asyncio
import asyncpg
import requests
import json

async def import_book_metadata_with_urls():
    """Import book metadata including author site URLs"""
    
    print("🚀 Starting book metadata import with author URLs...")
    
    # Use the Railway API to import the Excel file
    api_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/import/books"
    file_path = ".kiro/specs/multi-author-metadata-enhancement/data/MC Press Books - URL-Title-Author.xlsx"
    
    try:
        # First, let's validate the file to see its structure
        print("📋 Validating Excel file structure...")
        validate_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('MC Press Books - URL-Title-Author.xlsx', f)}
            data = {'file_type': 'book'}
            
            response = requests.post(validate_url, files=files, data=data)
            result = response.json()
            
            print(f"✅ Validation result: {result.get('valid', False)}")
            print(f"📊 Preview rows: {len(result.get('preview_rows', []))}")
            
            # Show first few rows to understand structure
            preview_rows = result.get('preview_rows', [])
            if preview_rows:
                print("\n📋 First few rows:")
                for i, row in enumerate(preview_rows[:3]):
                    print(f"  Row {i+1}: {row.get('data', {})}")
            
            # Show any errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n⚠️ Validation errors/warnings:")
                for error in errors:
                    print(f"  {error}")
        
        # Now import the file
        print(f"\n📤 Importing book metadata...")
        
        with open(file_path, 'rb') as f:
            files = {'file': ('MC Press Books - URL-Title-Author.xlsx', f)}
            
            response = requests.post(api_url, files=files)
            result = response.json()
            
            print(f"✅ Import success: {result.get('success', False)}")
            print(f"📚 Books processed: {result.get('books_processed', 0)}")
            print(f"🎯 Books matched: {result.get('books_matched', 0)}")
            print(f"📝 Books updated: {result.get('books_updated', 0)}")
            print(f"👥 Authors created: {result.get('authors_created', 0)}")
            print(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Show any errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n⚠️ Import errors:")
                for error in errors:
                    print(f"  Row {error.get('row', 'N/A')}: {error.get('message', 'Unknown error')}")
        
        # Now check if author URLs were imported
        print(f"\n🔍 Checking author URL import status...")
        await check_author_urls()
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        import traceback
        traceback.print_exc()

async def check_author_urls():
    """Check if author URLs were properly imported"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found - cannot check author URLs")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check authors with URLs
        authors_with_urls = await conn.fetchval(
            "SELECT COUNT(*) FROM authors WHERE site_url IS NOT NULL AND site_url != ''"
        )
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
        
        print(f"🌐 Authors with URLs: {authors_with_urls}/{total_authors}")
        
        # Show some examples
        if authors_with_urls > 0:
            sample_authors = await conn.fetch("""
                SELECT name, site_url 
                FROM authors 
                WHERE site_url IS NOT NULL AND site_url != ''
                LIMIT 5
            """)
            
            print("📋 Sample authors with URLs:")
            for author in sample_authors:
                print(f"  {author['name']}: {author['site_url']}")
        else:
            print("⚠️ No authors have site URLs - the import may not have included author URLs")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error checking author URLs: {e}")

if __name__ == "__main__":
    asyncio.run(import_book_metadata_with_urls())