#!/usr/bin/env python3
"""
Performance testing for PDF Chatbot with image processing
"""
import asyncio
import aiohttp
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

async def test_performance_metrics():
    """Test performance metrics for the PDF chatbot"""
    print("⚡ Performance Testing Suite")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Search Performance
        print("\n🔍 Search Performance Tests")
        print("-" * 30)
        
        search_queries = [
            "programming",
            "RPG IV",
            "subfiles",
            "image",
            "code examples",
            "ILE",
            "development environment",
            "system programming",
            "user interface",
            "database integration"
        ]
        
        search_times = []
        
        for query in search_queries:
            start_time = time.time()
            
            try:
                async with session.get(f"{BASE_URL}/search", params={'q': query, 'n_results': 5}) as response:
                    if response.status == 200:
                        data = await response.json()
                        end_time = time.time()
                        search_time = end_time - start_time
                        search_times.append(search_time)
                        
                        print(f"✅ '{query}': {search_time:.3f}s ({len(data['results'])} results)")
                    else:
                        print(f"❌ '{query}': Failed ({response.status})")
                        
            except Exception as e:
                print(f"❌ '{query}': Error - {e}")
            
            await asyncio.sleep(0.1)  # Small delay
        
        if search_times:
            avg_search_time = sum(search_times) / len(search_times)
            min_search_time = min(search_times)
            max_search_time = max(search_times)
            
            print(f"\n📊 Search Performance Summary:")
            print(f"   Average: {avg_search_time:.3f}s")
            print(f"   Min: {min_search_time:.3f}s")
            print(f"   Max: {max_search_time:.3f}s")
        
        # Test 2: Chat Performance
        print("\n💬 Chat Performance Tests")
        print("-" * 30)
        
        chat_queries = [
            "What is this document about?",
            "Show me a code example",
            "What images are in the document?",
            "Explain RPG programming",
            "What are subfiles?"
        ]
        
        chat_times = []
        response_lengths = []
        
        for i, query in enumerate(chat_queries):
            start_time = time.time()
            
            try:
                chat_data = {
                    "message": query,
                    "conversation_id": f"perf_test_{i}"
                }
                
                async with session.post(f"{BASE_URL}/chat", json=chat_data) as response:
                    if response.status == 200:
                        full_response = ""
                        
                        # Collect streaming response
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'content' in data:
                                        full_response += data['content']
                                except json.JSONDecodeError:
                                    continue
                        
                        end_time = time.time()
                        chat_time = end_time - start_time
                        chat_times.append(chat_time)
                        response_lengths.append(len(full_response))
                        
                        print(f"✅ '{query}': {chat_time:.3f}s ({len(full_response)} chars)")
                    else:
                        print(f"❌ '{query}': Failed ({response.status})")
                        
            except Exception as e:
                print(f"❌ '{query}': Error - {e}")
            
            await asyncio.sleep(0.5)  # Small delay
        
        if chat_times:
            avg_chat_time = sum(chat_times) / len(chat_times)
            min_chat_time = min(chat_times)
            max_chat_time = max(chat_times)
            avg_response_length = sum(response_lengths) / len(response_lengths)
            
            print(f"\n📊 Chat Performance Summary:")
            print(f"   Average time: {avg_chat_time:.3f}s")
            print(f"   Min time: {min_chat_time:.3f}s")
            print(f"   Max time: {max_chat_time:.3f}s")
            print(f"   Average response length: {avg_response_length:.0f} chars")
        
        # Test 3: Content Type Analysis
        print("\n📚 Content Analysis")
        print("-" * 30)
        
        # Get documents info
        try:
            async with session.get(f"{BASE_URL}/documents") as response:
                if response.status == 200:
                    docs_data = await response.json()
                    print(f"✅ Total documents: {docs_data['total_documents']}")
                    
                    for doc in docs_data['documents']:
                        print(f"   📄 {doc['filename']}:")
                        print(f"      - Chunks: {doc['total_chunks']}")
                        print(f"      - Pages: {doc['total_pages']}")
                        print(f"      - Has images: {doc.get('has_images', 'unknown')}")
                        print(f"      - Has code: {doc.get('has_code', 'unknown')}")
                        
        except Exception as e:
            print(f"❌ Documents analysis error: {e}")
        
        # Test 4: Content Type Distribution
        print("\n🎯 Content Type Distribution")
        print("-" * 30)
        
        content_types = ["text", "image", "code"]
        type_counts = {}
        
        for content_type in content_types:
            try:
                async with session.get(f"{BASE_URL}/search", params={'q': content_type, 'n_results': 100}) as response:
                    if response.status == 200:
                        data = await response.json()
                        type_specific_results = [r for r in data['results'] if r['metadata']['type'] == content_type]
                        type_counts[content_type] = len(type_specific_results)
                        print(f"✅ {content_type.title()} chunks: {len(type_specific_results)}")
                    else:
                        print(f"❌ {content_type.title()} search failed")
                        
            except Exception as e:
                print(f"❌ {content_type.title()} analysis error: {e}")
        
        # Test 5: Memory and Resource Usage
        print("\n🔧 System Resource Analysis")
        print("-" * 30)
        
        try:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ System status: {health_data['status']}")
                    print(f"✅ Vector store: {health_data['vector_store']}")
                    print(f"✅ OpenAI API: {health_data['openai']}")
                else:
                    print(f"❌ Health check failed")
                    
        except Exception as e:
            print(f"❌ Health check error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Performance testing completed!")
    
    # Summary
    print("\n📈 Performance Summary:")
    if search_times:
        print(f"   🔍 Average search time: {sum(search_times) / len(search_times):.3f}s")
    if chat_times:
        print(f"   💬 Average chat time: {sum(chat_times) / len(chat_times):.3f}s")
    if type_counts:
        print(f"   📊 Content distribution: {type_counts}")

if __name__ == "__main__":
    asyncio.run(test_performance_metrics())