#!/usr/bin/env python3
"""
Test direct database queries to see if article metadata was actually updated
"""

import requests
import json

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_direct_database_query():
    """Test if we can query the database directly to see article data"""
    print("🔍 Testing direct database query for article data...")
    
    # We'll use a simple API call to test specific articles
    # Let's try to get a specific article by making a targeted request
    
    # First, let's see if there's a way to query specific documents
    # We can try the chat enrichment which should query the database directly
    
    chat_data = {
        "message": "Tell me about XML programming",  # Should match "Advances in XML" article
        "conversation_id": "test_db_query",
        "user_id": "test"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=chat_data, stream=True, timeout=30)
        
        if response.status_code == 200:
            print("✅ Chat request successful")
            
            # Parse streaming response to get enrichment data
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get('type') == 'done' and 'sources' in data:
                            sources = data['sources']
                            print(f"📋 Found {len(sources)} sources from database enrichment")
                            
                            # Look for the XML article specifically
                            xml_article = None
                            for source in sources:
                                if 'xml' in source.get('filename', '').lower() or 'xml' in source.get('author', '').lower():
                                    xml_article = source
                                    break
                            
                            if xml_article:
                                print(f"\n🎯 Found XML-related article:")
                                print(f"  Filename: {xml_article.get('filename')}")
                                print(f"  Author: {xml_article.get('author')}")
                                print(f"  Document Type: {xml_article.get('document_type')}")
                                print(f"  Article URL: {xml_article.get('article_url')}")
                                print(f"  Authors Array: {xml_article.get('authors', [])}")
                                
                                # Check if enrichment shows updated data
                                if xml_article.get('document_type') == 'article':
                                    print(f"  ✅ Database enrichment shows document_type = 'article'!")
                                else:
                                    print(f"  ❌ Database enrichment shows document_type = '{xml_article.get('document_type')}'")
                                
                                if xml_article.get('author') != 'Unknown Author':
                                    print(f"  ✅ Database enrichment shows real author!")
                                else:
                                    print(f"  ❌ Database enrichment shows 'Unknown Author'")
                                
                                if xml_article.get('article_url'):
                                    print(f"  ✅ Database enrichment shows article URL!")
                                else:
                                    print(f"  ❌ Database enrichment missing article URL")
                            else:
                                print("❌ No XML-related article found in sources")
                                
                                # Show first few sources for debugging
                                print(f"\n📋 First few sources:")
                                for i, source in enumerate(sources[:3]):
                                    print(f"  Source {i+1}: {source.get('filename')} - {source.get('document_type')}")
                            
                            return
                    except:
                        continue
            
            print("❌ No sources found in chat response")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Chat test failed: {e}")

def main():
    print("🔍 TESTING DIRECT DATABASE QUERY")
    print("=" * 50)
    
    test_direct_database_query()
    
    print("\n" + "=" * 50)
    print("🎯 ANALYSIS:")
    print("This test uses chat enrichment which queries the database directly")
    print("If enrichment shows updated data but /documents doesn't, it's a cache issue")
    print("If enrichment also shows old data, the database wasn't actually updated")

if __name__ == "__main__":
    main()