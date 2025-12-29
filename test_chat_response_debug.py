#!/usr/bin/env python3
"""
Debug Chat Response
Tests the chat interface and shows all response data
"""

import requests
import json

def debug_chat_response():
    """Debug the complete chat response"""
    
    print("🔍 DEBUGGING CHAT RESPONSE")
    print("=" * 50)
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/chat"
    
    # Test with a simple query
    test_query = "RPG"
    
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
        print("\n📋 Raw response data:")
        
        line_count = 0
        for line in response.iter_lines():
            if line:
                line_count += 1
                try:
                    data = json.loads(line.decode('utf-8'))
                    print(f"\nLine {line_count}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'content':
                        content = data.get('content', '')
                        print(f"  Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                    
                    elif data.get('type') == 'metadata':
                        print(f"  Confidence: {data.get('confidence', 'N/A')}")
                        print(f"  Source count: {data.get('source_count', 'N/A')}")
                        print(f"  Context tokens: {data.get('context_tokens', 'N/A')}")
                    
                    elif data.get('type') == 'done':
                        sources = data.get('sources', [])
                        print(f"  Sources found: {len(sources)}")
                        
                        if sources:
                            print(f"\n🎯 ANALYZING FIRST SOURCE:")
                            source = sources[0]
                            print(f"    Raw source data: {json.dumps(source, indent=6)}")
                            
                            filename = source.get('filename', 'Unknown')
                            print(f"\n    Filename: {filename}")
                            
                            # This is what the frontend does in CompactSources.tsx
                            display_name = filename.replace('.pdf', '')
                            print(f"    Frontend display: '{display_name}'")
                            
                            if display_name.isdigit():
                                print(f"    ❌ PROBLEM: Displaying article ID instead of title")
                            else:
                                print(f"    ✅ Displaying proper name")
                        else:
                            print(f"    ❌ No sources in response")
                    
                    elif data.get('type') == 'error':
                        print(f"  Error: {data.get('error', 'Unknown error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"  JSON decode error: {e}")
                    print(f"  Raw line: {line.decode('utf-8')[:200]}")
        
        print(f"\n📊 Total response lines: {line_count}")
        
    except Exception as e:
        print(f"❌ Error during chat test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chat_response()