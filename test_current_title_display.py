#!/usr/bin/env python3
"""
Test the current title display functionality on Railway deployment.
This will help us understand the difference between what should work and what's actually working.
"""

import asyncio
import aiohttp
import json

async def test_chat_and_sources():
    """Test a chat query and examine the sources returned"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Test chat endpoint
    chat_data = {
        "message": "Tell me about RPG programming",
        "conversation_id": "test-conversation"
    }
    
    print("🔍 Testing chat endpoint to see source enrichment...")
    print(f"API URL: {api_url}")
    print(f"Query: {chat_data['message']}")
    print("=" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Send chat request
            async with session.post(
                f"{api_url}/api/chat", 
                json=chat_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"Response Status: {response.status}")
                
                if response.status == 200:
                    # Read the streaming response
                    full_response = ""
                    sources_data = None
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            data_json = line_text[6:]  # Remove 'data: ' prefix
                            if data_json and data_json != '[DONE]':
                                try:
                                    data = json.loads(data_json)
                                    if 'content' in data:
                                        full_response += data['content']
                                    if 'sources' in data:
                                        sources_data = data['sources']
                                        print("📚 SOURCES FOUND:")
                                        print(json.dumps(sources_data, indent=2))
                                        break  # We got sources, that's what we need
                                except json.JSONDecodeError:
                                    continue
                    
                    if sources_data:
                        print("\n🔍 ANALYZING SOURCES:")
                        for i, source in enumerate(sources_data):
                            print(f"\nSource {i+1}:")
                            print(f"  Filename: {source.get('filename', 'N/A')}")
                            print(f"  Title: {source.get('title', 'NOT PROVIDED')}")
                            print(f"  Author: {source.get('author', 'NOT PROVIDED')}")
                            print(f"  Document Type: {source.get('document_type', 'NOT PROVIDED')}")
                            print(f"  MC Press URL: {source.get('mc_press_url', 'NOT PROVIDED')}")
                            print(f"  Article URL: {source.get('article_url', 'NOT PROVIDED')}")
                            
                            # Check if this looks like an article (numeric filename)
                            filename = source.get('filename', '')
                            if filename.replace('.pdf', '').isdigit():
                                print(f"  🔍 This appears to be an ARTICLE (numeric filename)")
                                if source.get('title') == filename.replace('.pdf', ''):
                                    print(f"  ❌ ISSUE: Title matches filename - enrichment not working")
                                else:
                                    print(f"  ✅ Title is different from filename - enrichment working")
                    else:
                        print("❌ No sources returned in response")
                        print(f"Full response: {full_response[:500]}...")
                        
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {response.status}")
                    print(f"Error details: {error_text}")
                    
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

async def test_enrichment_directly():
    """Test the enrichment endpoint directly"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Test with a known article filename
    test_filenames = ["4247.pdf", "5765.pdf", "9998.pdf"]  # These should be articles
    
    print("\n" + "=" * 60)
    print("🔍 Testing enrichment endpoint directly...")
    
    for filename in test_filenames:
        print(f"\nTesting enrichment for: {filename}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/api/debug/enrich/{filename}",
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Enrichment successful:")
                        print(f"  Title: {data.get('title', 'NOT PROVIDED')}")
                        print(f"  Author: {data.get('author', 'NOT PROVIDED')}")
                        print(f"  Document Type: {data.get('document_type', 'NOT PROVIDED')}")
                        print(f"  Article URL: {data.get('article_url', 'NOT PROVIDED')}")
                        
                        # Check if enrichment is working
                        if data.get('title') == filename.replace('.pdf', ''):
                            print(f"  ❌ ISSUE: Title matches filename - database not updated")
                        else:
                            print(f"  ✅ Title is enriched - database has correct data")
                            
                    else:
                        error_text = await response.text()
                        print(f"❌ Enrichment failed: {response.status}")
                        print(f"Error: {error_text}")
                        
        except Exception as e:
            print(f"❌ Exception testing {filename}: {e}")

async def main():
    """Main test function"""
    print("🚀 Testing Current Title Display Status")
    print("This will help identify the difference between expected and actual behavior")
    print("=" * 80)
    
    await test_chat_and_sources()
    await test_enrichment_directly()
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY:")
    print("1. If sources show titles matching filenames (4247, 5765, etc.) - enrichment not working")
    print("2. If sources show real titles - enrichment working, frontend issue")
    print("3. If enrichment endpoint works but chat doesn't - integration issue")
    print("4. If both fail - backend deployment issue")

if __name__ == "__main__":
    asyncio.run(main())