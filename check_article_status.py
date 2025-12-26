#!/usr/bin/env python3
"""
Check the current status of articles in the database
Diagnose why articles are showing ID numbers instead of titles
"""

import requests
import json

def main():
    base_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 Checking article status in database...")
    
    # Test 1: Check if articles exist with document_type='article'
    print("\n📰 Test 1: Checking for articles in database...")
    try:
        response = requests.get(f"{base_url}/api/books?limit=10")
        if response.status_code == 200:
            books = response.json()
            
            # Count document types
            book_count = 0
            article_count = 0
            
            for book in books:
                doc_type = book.get('document_type', 'book')
                if doc_type == 'article':
                    article_count += 1
                else:
                    book_count += 1
            
            print(f"   Found {len(books)} documents in first 10 results:")
            print(f"   - Books: {book_count}")
            print(f"   - Articles: {article_count}")
            
            # Show sample articles if any
            articles = [b for b in books if b.get('document_type') == 'article']
            if articles:
                print(f"\n   Sample articles:")
                for article in articles[:3]:
                    print(f"   - ID: {article.get('id')}")
                    print(f"     Filename: {article.get('filename')}")
                    print(f"     Title: {article.get('title', 'NO TITLE')}")
                    print(f"     Article URL: {article.get('article_url', 'NO URL')}")
                    print(f"     Authors: {article.get('authors', [])}")
            else:
                print("   ⚠️ No articles found in first 10 results")
        else:
            print(f"   ❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Search for specific article IDs that were mentioned
    print("\n📰 Test 2: Checking specific article IDs...")
    test_ids = ["5805", "6274", "7672", "15981"]
    
    for article_id in test_ids:
        try:
            # Try searching by filename
            response = requests.get(f"{base_url}/api/books?search={article_id}&limit=1")
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = books[0]
                    print(f"\n   Article ID {article_id}:")
                    print(f"   - Filename: {book.get('filename')}")
                    print(f"   - Title: {book.get('title', 'NO TITLE')}")
                    print(f"   - Document Type: {book.get('document_type', 'book')}")
                    print(f"   - Article URL: {book.get('article_url', 'NO URL')}")
                    print(f"   - Authors: {book.get('authors', [])}")
                else:
                    print(f"   ❌ Article ID {article_id}: Not found")
            else:
                print(f"   ❌ Article ID {article_id}: API Error {response.status_code}")
        except Exception as e:
            print(f"   ❌ Article ID {article_id}: Error {e}")
    
    # Test 3: Test chat to see what sources are returned
    print("\n💬 Test 3: Testing chat response for article-related query...")
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={
                "message": "Tell me about RPG programming",
                "conversation_id": "test-article-check",
                "user_id": "test"
            },
            stream=True
        )
        
        if response.status_code == 200:
            sources = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'done':
                                sources = data.get('sources', [])
                                break
                        except:
                            pass
            
            if sources:
                print(f"   Found {len(sources)} sources:")
                for i, source in enumerate(sources[:5]):
                    print(f"\n   Source {i+1}:")
                    print(f"   - Filename: {source.get('filename')}")
                    print(f"   - Document Type: {source.get('document_type', 'book')}")
                    print(f"   - Author: {source.get('author', 'Unknown')}")
                    print(f"   - MC Press URL: {'Yes' if source.get('mc_press_url') else 'No'}")
                    print(f"   - Article URL: {'Yes' if source.get('article_url') else 'No'}")
                    print(f"   - Authors: {source.get('authors', [])}")
            else:
                print("   ⚠️ No sources returned")
        else:
            print(f"   ❌ Chat API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("📊 DIAGNOSIS:")
    print("="*60)
    print("\nThe issue is likely one of the following:")
    print("\n1. Articles don't have proper titles in the 'title' column")
    print("   - They may only have filenames like '5805.pdf'")
    print("   - The Excel import needs to populate the 'title' column")
    print("\n2. Article metadata import didn't run or failed")
    print("   - Check if document_type='article' is set")
    print("   - Check if article_url is populated")
    print("\n3. Frontend is displaying filename instead of title")
    print("   - CompactSources.tsx may need to handle missing titles")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
