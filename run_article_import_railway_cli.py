#!/usr/bin/env python3
"""
Simple script to run article import via Railway CLI.
This will be executed on Railway with all dependencies available.
"""

import asyncio
import sys
import os

# Add backend to Python path
sys.path.insert(0, '/app/backend')

async def main():
    """Run article import on Railway"""
    print("🚀 Starting article metadata import on Railway...")
    
    try:
        from excel_import_service import ExcelImportService
        from author_service import AuthorService
        
        # Initialize services
        author_service = AuthorService()
        excel_service = ExcelImportService(author_service)
        
        # Initialize database connections
        await author_service.init_database()
        await excel_service.init_database()
        
        # Path to the article Excel file (should be in the deployed code)
        file_path = "/app/.kiro/specs/multi-author-metadata-enhancement/data/article-links.xlsm"
        
        if not os.path.exists(file_path):
            print(f"❌ Excel file not found: {file_path}")
            print("Available files in .kiro/specs/multi-author-metadata-enhancement/:")
            try:
                import os
                for root, dirs, files in os.walk("/app/.kiro/specs/multi-author-metadata-enhancement/"):
                    for file in files:
                        print(f"  {os.path.join(root, file)}")
            except:
                pass
            return False
        
        print(f"📋 Found Excel file: {file_path}")
        
        # Run the import
        print(f"📤 Importing article metadata...")
        import_result = await excel_service.import_article_metadata(file_path)
        
        print(f"✅ Import success: {import_result.success}")
        print(f"📰 Articles processed: {import_result.articles_processed}")
        print(f"🎯 Articles matched: {import_result.articles_matched}")
        print(f"📝 Documents updated: {import_result.documents_updated}")
        print(f"👥 Authors created: {import_result.authors_created}")
        print(f"👥 Authors updated: {import_result.authors_updated}")
        print(f"⏱️ Processing time: {import_result.processing_time:.2f}s")
        
        # Show import errors
        if import_result.errors:
            print(f"\n⚠️ Import errors:")
            for error in import_result.errors:
                print(f"  Row {error.row}: {error.message} ({error.severity})")
        
        if import_result.success:
            print(f"\n🎉 Article import completed successfully!")
            print("This populated:")
            print("- document_authors table with author associations")
            print("- authors table with author names and URLs")
            print("- books.article_url and document_type='article'")
            
            # Test enrichment
            print(f"\n🔍 Testing source enrichment...")
            await test_enrichment(excel_service)
            
        # Clean up
        await author_service.close()
        await excel_service.close()
        
        return import_result.success
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enrichment(excel_service):
    """Test source enrichment with a few articles"""
    try:
        from chat_handler import ChatHandler
        
        chat_handler = ChatHandler()
        
        # Get some article filenames from database
        async with excel_service.pool.acquire() as conn:
            articles = await conn.fetch("""
                SELECT filename, title, author as legacy_author
                FROM books 
                WHERE document_type = 'article'
                AND filename IS NOT NULL
                LIMIT 3
            """)
        
        print(f"Testing enrichment for {len(articles)} articles:")
        
        success_count = 0
        for article in articles:
            filename = article['filename']
            print(f"\n  Testing: {filename}")
            
            try:
                result = await chat_handler._enrich_source_metadata(filename)
                
                if result:
                    author_info = result.get('author', 'Unknown')
                    authors_list = result.get('authors', [])
                    print(f"    ✅ Enriched author: {author_info}")
                    print(f"    ✅ Authors list: {len(authors_list)} authors")
                    
                    # Check if we got real names instead of "Unknown Author"
                    if author_info and author_info != 'Unknown' and 'Unknown Author' not in author_info:
                        print(f"    🎉 SUCCESS: Real author name displayed!")
                        success_count += 1
                    else:
                        print(f"    ⚠️  Still showing Unknown Author")
                else:
                    print(f"    ❌ No enrichment data returned")
                    
            except Exception as e:
                print(f"    ❌ Error enriching {filename}: {e}")
        
        print(f"\n📊 Enrichment test results: {success_count}/{len(articles)} articles showing real author names")
        
        if success_count > 0:
            print("🎉 TASK 5 SUCCESS: Author name display fix is working!")
        else:
            print("⚠️  Author name display may still need additional fixes")
        
    except Exception as e:
        print(f"❌ Error testing enrichment: {e}")

if __name__ == "__main__":
    asyncio.run(main())