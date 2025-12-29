#!/usr/bin/env python3
"""
Investigate why articles still show ID numbers and "Unknown Author"
"""

import requests
import json

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_chat_with_articles():
    """Test a chat query that should return articles and check the source data"""
    print("🔍 Testing chat query to see article source data...")
    
    # Test query that should return articles
    chat_data = {
        "message": "Tell me about RPG programming",
        "conversation_id": "test_articles",
        "user_id": "test"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=chat_data, stream=True)
    
    if response.status_code == 200:
        print("✅ Chat request successful")
        
        # Parse the streaming response to get sources
        sources_data = None
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if data.get('type') == 'done' and 'sources' in data:
                        sources_data = data['sources']
                        break
                except:
                    continue
        
        if sources_data:
            print(f"\n📋 Found {len(sources_data)} sources:")
            
            article_count = 0
            book_count = 0
            
            for i, source in enumerate(sources_data[:5]):  # Show first 5 sources
                print(f"\n--- Source {i+1} ---")
                print(f"Filename: {source.get('filename', 'Unknown')}")
                print(f"Document Type: {source.get('document_type', 'Unknown')}")
                print(f"Author: {source.get('author', 'Unknown')}")
                print(f"Authors Array: {source.get('authors', [])}")
                print(f"Article URL: {source.get('article_url', 'None')}")
                print(f"MC Press URL: {source.get('mc_press_url', 'None')}")
                
                if source.get('document_type') == 'article':
                    article_count += 1
                elif source.get('document_type') == 'book':
                    book_count += 1
            
            print(f"\n📊 Summary:")
            print(f"  Articles: {article_count}")
            print(f"  Books: {book_count}")
            
            # Check for issues
            issues = []
            for source in sources_data:
                filename = source.get('filename', '')
                if filename.replace('.pdf', '').isdigit():  # ID number filename
                    if source.get('document_type') == 'article':
                        issues.append(f"Article {filename} shows ID instead of title")
                
                if source.get('author') == 'Unknown' or source.get('author') == 'Unknown Author':
                    if source.get('document_type') == 'article':
                        issues.append(f"Article {filename} shows Unknown Author")
            
            if issues:
                print(f"\n❌ Issues found:")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"  - {issue}")
            else:
                print(f"\n✅ No obvious issues found in sources")
                
        else:
            print("❌ No sources found in chat response")
    else:
        print(f"❌ Chat request failed: {response.status_code}")

def check_books_table_articles():
    """Check what article data looks like in the books table"""
    print("\n🔍 Checking article data in books table...")
    
    # We'll need to create a simple endpoint test or check existing data
    # For now, let's see what the documents endpoint returns for articles
    response = requests.get(f"{BASE_URL}/documents")
    
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        
        # Look for articles (filenames that are just numbers)
        articles = []
        for doc in documents:
            filename = doc.get('filename', '')
            if filename.replace('.pdf', '').isdigit():
                articles.append(doc)
        
        print(f"📊 Found {len(articles)} potential articles in documents list")
        
        if articles:
            print(f"\n📋 Sample articles:")
            for i, article in enumerate(articles[:3]):
                print(f"\n--- Article {i+1} ---")
                print(f"Filename: {article.get('filename')}")
                print(f"Title: {article.get('title')}")
                print(f"Author: {article.get('author')}")
                print(f"Document Type: {article.get('document_type', 'Not set')}")
                
                # Check if title is just the ID number
                title = article.get('title', '')
                filename_id = article.get('filename', '').replace('.pdf', '')
                if title == filename_id or title.startswith('Article '):
                    print(f"  ⚠️ Title issue: Shows '{title}' instead of proper title")
                
                if article.get('author') in ['Unknown', 'Unknown Author']:
                    print(f"  ⚠️ Author issue: Shows '{article.get('author')}'")
    else:
        print(f"❌ Documents endpoint failed: {response.status_code}")

def main():
    print("🔍 INVESTIGATING ARTICLE TITLES AND AUTHORS")
    print("=" * 50)
    
    # Test 1: Check chat sources
    test_chat_with_articles()
    
    # Test 2: Check books table data
    check_books_table_articles()
    
    print("\n" + "=" * 50)
    print("🎯 INVESTIGATION COMPLETE")
    print("\nNext steps:")
    print("1. If articles show ID numbers: Check if metadata import worked")
    print("2. If articles show Unknown Author: Check author associations")
    print("3. If document_type is wrong: Check migration settings")

if __name__ == "__main__":
    main()