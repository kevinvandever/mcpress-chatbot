#!/usr/bin/env python3
"""
Simple test of article import without pandas dependency
"""

import requests

def main():
    print("🔍 Testing article import process...")
    
    # Test the validation endpoint
    print("\n📋 Step 1: Testing validation endpoint...")
    try:
        file_path = ".kiro/specs/multi-author-metadata-enhancement/data/article-links.xlsm"
        api_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            data = {'file_type': 'article'}
            
            response = requests.post(api_url, files=files, data=data)
            result = response.json()
            
            print(f"   Validation result: {result.get('valid', False)}")
            print(f"   Preview rows: {len(result.get('preview_rows', []))}")
            
            # Show validation errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n   Validation errors:")
                for error in errors:
                    print(f"     {error}")
            
            # Show preview data
            preview_rows = result.get('preview_rows', [])
            if preview_rows:
                print(f"\n   Preview of first 3 rows:")
                for i, row in enumerate(preview_rows[:3]):
                    print(f"     Row {i+1}:")
                    data = row.get('data', {})
                    for key, value in data.items():
                        print(f"       {key}: {value}")
                    print(f"       Status: {row.get('status', 'unknown')}")
                    if row.get('errors'):
                        print(f"       Errors: {row.get('errors')}")
    
    except Exception as e:
        print(f"   ❌ Error testing validation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the import endpoint
    print("\n📤 Step 2: Testing import endpoint...")
    try:
        import_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/import/articles"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            
            response = requests.post(import_url, files=files)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"   Import success: {result.get('success', False)}")
                print(f"   Articles processed: {result.get('articles_processed', 0)}")
                print(f"   Articles matched: {result.get('articles_matched', 0)}")
                print(f"   Documents updated: {result.get('documents_updated', 0)}")
                print(f"   Authors created: {result.get('authors_created', 0)}")
                print(f"   Authors updated: {result.get('authors_updated', 0)}")
                print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
                
                # Show import errors
                errors = result.get('errors', [])
                if errors:
                    print(f"\n   Import errors (first 10):")
                    for error in errors[:10]:
                        print(f"     Row {error.get('row', 'N/A')}: {error.get('message', 'Unknown error')}")
            else:
                print(f"   ❌ Import failed with status {response.status_code}")
                print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"   ❌ Error testing import: {e}")
        import traceback
        traceback.print_exc()
    
    # Check specific articles after import
    print("\n📰 Step 3: Checking specific articles after import...")
    test_ids = ["5805", "6274", "7672", "15981"]
    
    for article_id in test_ids:
        try:
            response = requests.get(f"https://mcpress-chatbot-production.up.railway.app/api/books?search={article_id}&limit=1")
            if response.status_code == 200:
                books = response.json()
                if books and len(books) > 0:
                    book = books[0]
                    print(f"\n   Article {article_id}:")
                    print(f"     Filename: {book.get('filename')}")
                    print(f"     Title: {book.get('title', 'NO TITLE')}")
                    print(f"     Document Type: {book.get('document_type', 'book')}")
                    print(f"     Article URL: {book.get('article_url', 'NO URL')}")
                    print(f"     Authors: {len(book.get('authors', []))} authors")
                else:
                    print(f"   ❌ Article {article_id}: Not found")
            else:
                print(f"   ❌ Article {article_id}: API Error {response.status_code}")
        except Exception as e:
            print(f"   ❌ Article {article_id}: Error {e}")

if __name__ == "__main__":
    main()