#!/usr/bin/env python3
"""
Test chat with different queries to find articles
"""

import requests
import json

def test_article_search():
    """Test different queries to find articles"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/chat"
    
    queries = [
        "Tell me about IBM i programming",
        "RPG programming tips",
        "System i administration",
        "AS/400 development"
    ]
    
    for query in queries:
        print(f"\n🔍 Testing query: '{query}'")
        
        payload = {
            "message": query,
            "conversation_id": f"test-{hash(query)}",
            "user_id": "test"
        }
        
        try:
            response = requests.post(api_url, json=payload, stream=True, timeout=30)
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            
                            if data.get('type') == 'done':
                                sources = data.get('sources', [])
                                
                                print(f"📚 Found {len(sources)} sources:")
                                
                                articles_found = 0
                                books_found = 0
                                
                                for source in sources:
                                    doc_type = source.get('document_type', 'book')
                                    if doc_type == 'article':
                                        articles_found += 1
                                        print(f"   📄 ARTICLE: {source.get('filename', 'N/A')}")
                                        print(f"      Article URL: {source.get('article_url', 'N/A')}")
                                    else:
                                        books_found += 1
                                
                                print(f"   📊 Summary: {articles_found} articles, {books_found} books")
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
        except Exception as e:
            print(f"❌ Error with query '{query}': {e}")

if __name__ == "__main__":
    test_article_search()