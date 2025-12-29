#!/usr/bin/env python3
"""
Test Chat Title Display
Tests the chat interface to see what titles are being displayed
"""

import requests
import json

def test_chat_titles():
    """Test what titles are being displayed in chat results"""
    
    print("🔍 TESTING CHAT TITLE DISPLAY")
    print("=" * 50)
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/chat"
    
    # Test with a query that should return articles
    test_query = "RPG programming techniques"
    
    print(f"🔍 Testing query: '{test_query}'")
    
    try:
        response = requests.post(api_url, json={
            "message": test_query,
            "conversation_id": "debug_test",
            "user_id": "debug"
        }, stream=True)
        
        if response.status_code != 200:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        print("✅ Chat request successful")
        
        # Parse the streaming response to find sources
        sources_found = False
        all_content = ""
        
        print("🔍 Parsing streaming response...")
        
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                print(f"📥 Raw line: {line_text[:100]}...")  # Show first 100 chars
                
                try:
                    # Handle Server-Sent Events format
                    if line_text.startswith('data: '):
                        json_data = line_text[6:]  # Remove 'data: ' prefix
                        data = json.loads(json_data)
                    else:
                        data = json.loads(line_text)
                    
                    if data.get('type') == 'content':
                        all_content += data.get('content', '')
                    elif data.get('type') == 'done' and 'sources' in data:
                        sources = data['sources']
                        sources_found = True
                        
                        print(f"\n📋 Found {len(sources)} sources:")
                        
                        for i, source in enumerate(sources[:5]):  # Show first 5
                            filename = source.get('filename', 'Unknown')
                            author = source.get('author', 'Unknown')
                            document_type = source.get('document_type', 'Unknown')
                            article_url = source.get('article_url', '')
                            mc_press_url = source.get('mc_press_url', '')
                            authors = source.get('authors', [])
                            
                            print(f"\n--- Source {i+1}: {filename} ---")
                            print(f"  Filename: {filename}")
                            print(f"  Author: {author}")
                            print(f"  Document Type: {document_type}")
                            print(f"  Article URL: {article_url}")
                            print(f"  MC Press URL: {mc_press_url}")
                            print(f"  Authors Array: {len(authors)} authors")
                            
                            if authors:
                                for j, auth in enumerate(authors):
                                    print(f"    Author {j+1}: {auth.get('name', 'Unknown')} (URL: {auth.get('site_url', 'None')})")
                            
                            # Check what the frontend would display
                            display_name = filename.replace('.pdf', '')
                            
                            print(f"  🎯 FRONTEND DISPLAY ANALYSIS:")
                            print(f"    Current display: '{display_name}' (filename without .pdf)")
                            
                            # Check if this looks like an article ID
                            if filename.replace('.pdf', '').isdigit():
                                print(f"    ❌ PROBLEM: Showing article ID '{display_name}' instead of title")
                                print(f"    🔧 NEEDED: Frontend should use title from enrichment data")
                            else:
                                print(f"    ✅ Showing proper title")
                        
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
                    print(f"   Line content: {line_text}")
                    continue
        
        if not sources_found:
            print("❌ No sources found in chat response")
            
    except Exception as e:
        print(f"❌ Error during chat test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_titles()