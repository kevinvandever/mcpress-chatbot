#!/usr/bin/env python3
"""
Import article metadata from article-links.xlsm
This will populate:
- books.article_url from "Article URL" column
- books.document_type = 'article' 
- authors.site_url from "Arthor URL" column (misspelled)
- author names from "vlookup created-by" column
"""

import requests

def main():
    print("🚀 Starting article metadata import...")
    
    # Use the Railway API to import the article Excel file
    api_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/import/articles"
    file_path = ".kiro/specs/multi-author-metadata-enhancement/data/article-links.xlsm"
    
    try:
        # First, validate the file structure
        print("📋 Validating article Excel file structure...")
        validate_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            data = {'file_type': 'article'}
            
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
        
        # Now import the articles
        print(f"\n📤 Importing article metadata...")
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            
            response = requests.post(api_url, files=files)
            result = response.json()
            
            print(f"✅ Import success: {result.get('success', False)}")
            print(f"📰 Articles processed: {result.get('articles_processed', 0)}")
            print(f"🎯 Articles matched: {result.get('articles_matched', 0)}")
            print(f"📝 Documents updated: {result.get('documents_updated', 0)}")
            print(f"👥 Authors created: {result.get('authors_created', 0)}")
            print(f"👥 Authors updated: {result.get('authors_updated', 0)}")
            print(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Show any errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n⚠️ Import errors:")
                for error in errors:
                    print(f"  Row {error.get('row', 'N/A')}: {error.get('message', 'Unknown error')}")
        
        print(f"\n🎉 Article import completed!")
        print("This should have populated:")
        print("- books.article_url for articles")
        print("- books.document_type = 'article'")
        print("- authors.site_url from 'Arthor URL' column")
        print("- Author names from 'vlookup created-by' column")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()