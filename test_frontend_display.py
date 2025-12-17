#!/usr/bin/env python3
"""
Test script to verify frontend display after chat metadata enrichment fix.
This script tests the chat endpoint and verifies that enriched metadata is returned.
"""

import requests
import json
import sys
import time

# Railway backend URL
API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_chat_enrichment():
    """Test chat endpoint to verify enriched metadata is returned"""
    print("🧪 Testing Chat Enrichment Frontend Display")
    print("=" * 50)
    
    # Test query that should return known books
    test_queries = [
        "Tell me about DB2 10 for z/OS",
        "What is RPG programming?",
        "How do I use ILE concepts?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: '{query}'")
        print("-" * 30)
        
        try:
            # Send chat request
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "message": query,
                    "conversation_id": f"test-frontend-{int(time.time())}",
                    "user_id": "test-user"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                continue
            
            # Parse streaming response
            sources = None
            for line in response.text.strip().split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        if data.get('type') == 'done' and 'sources' in data:
                            sources = data['sources']
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not sources:
                print("❌ No sources found in response")
                continue
            
            print(f"✅ Found {len(sources)} sources")
            
            # Verify enrichment for each source
            enriched_count = 0
            buy_button_count = 0
            read_button_count = 0
            author_link_count = 0
            
            for j, source in enumerate(sources[:3], 1):  # Check first 3 sources
                print(f"\n  📖 Source {j}: {source.get('filename', 'Unknown')}")
                
                # Check author enrichment
                author = source.get('author', 'Unknown')
                authors = source.get('authors', [])
                
                if author != 'Unknown':
                    print(f"    ✅ Author: {author}")
                    enriched_count += 1
                else:
                    print(f"    ❌ Author: {author} (not enriched)")
                
                # Check multi-author data
                if authors:
                    print(f"    ✅ Authors array: {len(authors)} authors")
                    for author_obj in authors:
                        if author_obj.get('site_url'):
                            print(f"      🔗 {author_obj['name']} -> {author_obj['site_url']}")
                            author_link_count += 1
                        else:
                            print(f"      👤 {author_obj['name']} (no website)")
                else:
                    print(f"    ⚠️  Authors array: empty")
                
                # Check purchase/article links
                document_type = source.get('document_type', 'book')
                mc_press_url = source.get('mc_press_url', '')
                article_url = source.get('article_url')
                
                if document_type == 'book' and mc_press_url:
                    print(f"    ✅ Buy button: {mc_press_url}")
                    buy_button_count += 1
                elif document_type == 'article' and article_url:
                    print(f"    ✅ Read button: {article_url}")
                    read_button_count += 1
                else:
                    print(f"    ⚠️  No action button (type: {document_type})")
                
                print(f"    📄 Document type: {document_type}")
            
            # Summary for this query
            print(f"\n  📊 Summary:")
            print(f"    • Enriched sources: {enriched_count}/{min(3, len(sources))}")
            print(f"    • Buy buttons: {buy_button_count}")
            print(f"    • Read buttons: {read_button_count}")
            print(f"    • Author links: {author_link_count}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Frontend Display Verification Complete")
    print("\nTo manually verify in browser:")
    print("1. Open https://mcpress-chatbot.netlify.app")
    print("2. Submit a query like 'Tell me about DB2'")
    print("3. Check that sources show:")
    print("   - Actual author names (not 'Unknown')")
    print("   - Blue 'Buy' buttons for books with MC Store URLs")
    print("   - Green 'Read' buttons for articles")
    print("   - Clickable author names with website links")

if __name__ == "__main__":
    test_chat_enrichment()