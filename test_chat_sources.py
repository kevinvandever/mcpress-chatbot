#!/usr/bin/env python3
"""
Test chat API to see the sources section with MC Press URLs
"""

import requests
import json
import time

def test_chat_sources():
    """Test the chat API and capture the sources section"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/chat"
    
    payload = {
        "message": "Tell me about DB2 10 for z/OS upgrade",
        "conversation_id": "test",
        "user_id": "test"
    }
    
    print("🚀 Testing chat API for sources section...")
    
    try:
        response = requests.post(api_url, json=payload, stream=True, timeout=30)
        
        sources_found = False
        content_parts = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        
                        if data.get('type') == 'content':
                            content_parts.append(data.get('content', ''))
                        
                        elif data.get('type') == 'sources':
                            sources_found = True
                            print("📚 SOURCES SECTION FOUND:")
                            sources = data.get('sources', [])
                            
                            for i, source in enumerate(sources, 1):
                                print(f"\n📖 Source {i}:")
                                print(f"   Title: {source.get('title', 'N/A')}")
                                print(f"   Author: {source.get('author', 'N/A')}")
                                print(f"   Authors: {source.get('authors', [])}")
                                print(f"   MC Press URL: {source.get('mc_press_url', 'N/A')}")
                                print(f"   Article URL: {source.get('article_url', 'N/A')}")
                                print(f"   Document Type: {source.get('document_type', 'N/A')}")
                                
                                # Check author details
                                author_details = source.get('author_details', [])
                                if author_details:
                                    print(f"   Author Details:")
                                    for author in author_details:
                                        print(f"     - {author.get('name', 'N/A')}: {author.get('site_url', 'No URL')}")
                            
                            break  # Stop after getting sources
                            
                    except json.JSONDecodeError:
                        continue
        
        if not sources_found:
            print("❌ No sources section found in response")
            print("📝 Content received:")
            print(''.join(content_parts)[:500] + "...")
        
    except Exception as e:
        print(f"❌ Error testing chat API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_sources()