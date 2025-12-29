#!/usr/bin/env python3
"""
Force refresh the cache and test if article metadata is working
"""

import requests
import json
import time

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def force_refresh_cache():
    """Force refresh the documents cache"""
    print("🔄 Force refreshing documents cache...")
    
    response = requests.get(f"{BASE_URL}/documents/refresh")
    
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        print(f"✅ Cache refreshed successfully")
        print(f"📊 Documents in cache: {len(documents)}")
        return True
    else:
        print(f"❌ Cache refresh failed: {response.status_code}")
        return False

def test_specific_article_data():
    """Test specific article data to see if metadata import worked"""
    print("\n🔍 Testing specific article data...")
    
    # Get documents and look for a specific article
    response = requests.get(f"{BASE_URL}/documents")
    
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        
        # Find a specific article we know should exist
        test_articles = ['9998.pdf', '9989.pdf', '9988.pdf']
        
        for filename in test_articles:
            article = next((doc for doc in documents if doc.get('filename') == filename), None)
            
            if article:
                print(f"\n--- Testing {filename} ---")
                print(f"  Title: {article.get('title')}")
                print(f"  Author: {article.get('author')}")
                print(f"  Document Type: {article.get('document_type')}")
                print(f"  Category: {article.get('category')}")
                
                # Check if this looks like it was updated
                if article.get('document_type') == 'article':
                    print(f"  ✅ Document type is correct!")
                else:
                    print(f"  ❌ Document type is still '{article.get('document_type')}' not 'article'")
                
                if article.get('author') != 'Unknown Author':
                    print(f"  ✅ Author is populated!")
                else:
                    print(f"  ❌ Author is still 'Unknown Author'")
            else:
                print(f"❌ Article {filename} not found")
    else:
        print(f"❌ Documents request failed: {response.status_code}")

def test_chat_enrichment():
    """Test if chat enrichment is working with articles"""
    print("\n🔍 Testing chat enrichment with articles...")
    
    chat_data = {
        "message": "What is RPG programming?",
        "conversation_id": "test_enrichment",
        "user_id": "test"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=chat_data, stream=True, timeout=30)
        
        if response.status_code == 200:
            print("✅ Chat request successful")
            
            # Parse streaming response
            sources_found = False
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('type') == 'done' and 'sources' in data:
                            sources = data['sources']
                            print(f"📋 Found {len(sources)} sources")
                            
                            # Check for articles in sources
                            article_sources = [s for s in sources if s.get('filename', '').replace('.pdf', '').isdigit()]
                            
                            if article_sources:
                                print(f"📰 Found {len(article_sources)} article sources:")
                                for i, source in enumerate(article_sources[:3]):
                                    print(f"  Article {i+1}: {source.get('filename')}")
                                    print(f"    Document Type: {source.get('document_type')}")
                                    print(f"    Author: {source.get('author')}")
                                    print(f"    Article URL: {source.get('article_url')}")
                                    
                                    if source.get('document_type') == 'article':
                                        print(f"    ✅ Enrichment shows correct document type!")
                                    else:
                                        print(f"    ❌ Enrichment shows wrong document type")
                            else:
                                print("❌ No article sources found in chat response")
                            
                            sources_found = True
                            break
                    except:
                        continue
            
            if not sources_found:
                print("❌ No sources found in chat response")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Chat test failed: {e}")

def main():
    print("🔄 FORCE CACHE REFRESH AND TEST")
    print("=" * 50)
    
    # Step 1: Force refresh cache
    if force_refresh_cache():
        # Wait a moment for cache to update
        time.sleep(2)
        
        # Step 2: Test specific article data
        test_specific_article_data()
        
        # Step 3: Test chat enrichment
        test_chat_enrichment()
    
    print("\n" + "=" * 50)
    print("🎯 ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()