#!/usr/bin/env python3
"""
Simple test to check if chat enrichment is working with MC Press URLs
"""

import requests
import json
import time

def test_chat_enrichment():
    """Test chat enrichment for MC Press URLs"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/chat"
    
    payload = {
        "message": "Tell me about DB2 10 for z/OS",
        "conversation_id": "test-enrichment",
        "user_id": "test"
    }
    
    print("🚀 Testing chat enrichment...")
    
    try:
        response = requests.post(api_url, json=payload, stream=True, timeout=60)
        
        all_data = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        all_data.append(data)
                        
                        if data.get('type') == 'done':
                            print("✅ Chat completed, checking sources...")
                            sources = data.get('sources', [])
                            
                            if not sources:
                                print("❌ No sources found in response")
                                return
                            
                            print(f"📚 Found {len(sources)} sources:")
                            
                            for i, source in enumerate(sources, 1):
                                print(f"\n📖 Source {i}:")
                                print(f"   Filename: {source.get('filename', 'N/A')}")
                                print(f"   Author: {source.get('author', 'N/A')}")
                                print(f"   MC Press URL: {source.get('mc_press_url', 'N/A')}")
                                print(f"   Document Type: {source.get('document_type', 'N/A')}")
                                
                                # Check if MC Press URL exists
                                mc_url = source.get('mc_press_url', '')
                                if mc_url and mc_url != 'N/A':
                                    print(f"   ✅ HAS MC PRESS URL: {mc_url}")
                                else:
                                    print(f"   ❌ NO MC PRESS URL")
                                
                                # Check authors array
                                authors = source.get('authors', [])
                                if authors:
                                    print(f"   👥 Authors ({len(authors)}):")
                                    for author in authors:
                                        name = author.get('name', 'N/A')
                                        site_url = author.get('site_url', '')
                                        if site_url:
                                            print(f"     - {name}: {site_url} ✅")
                                        else:
                                            print(f"     - {name}: No URL ❌")
                            
                            return
                            
                    except json.JSONDecodeError:
                        continue
        
        print("❌ No 'done' message found in response")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_enrichment()