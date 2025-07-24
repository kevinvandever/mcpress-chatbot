#!/usr/bin/env python3
"""
Test script for PDF Chatbot API with image processing
"""
import asyncio
import aiohttp
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

async def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

async def test_documents():
    """Test documents endpoint"""
    print("\n📚 Testing documents endpoint...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/documents") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Documents: {data['total_documents']} total")
                    for doc in data['documents']:
                        print(f"   - {doc['filename']}: {doc['total_chunks']} chunks, {doc['total_pages']} pages")
                    return data
                else:
                    print(f"❌ Documents failed: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Documents error: {e}")
            return None

async def test_upload(file_path):
    """Test file upload"""
    print(f"\n📤 Testing upload: {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    async with aiohttp.ClientSession() as session:
        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=Path(file_path).name, content_type='application/pdf')
                
                print("   Processing...")
                start_time = time.time()
                
                async with session.post(f"{BASE_URL}/upload", data=data) as response:
                    end_time = time.time()
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Upload successful ({end_time - start_time:.2f}s)")
                        print(f"   - Status: {result['status']}")
                        print(f"   - Chunks: {result['chunks_created']}")
                        print(f"   - Images: {result['images_processed']}")
                        print(f"   - Code blocks: {result['code_blocks_found']}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload failed: {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False

async def test_search(query, n_results=3):
    """Test search functionality"""
    print(f"\n🔍 Testing search: '{query}'")
    async with aiohttp.ClientSession() as session:
        try:
            # Use GET with query parameters
            async with session.get(f"{BASE_URL}/search", params={'q': query, 'n_results': n_results}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Search results: {len(data['results'])} found")
                    for i, result in enumerate(data['results'][:2]):  # Show first 2
                        print(f"   {i+1}. {result['metadata']['type']} chunk (distance: {result['distance']:.3f})")
                        print(f"      Content: {result['content'][:80]}...")
                        if result['metadata']['type'] == 'image':
                            print(f"      📸 Image from page {result['metadata']['page']}")
                        elif result['metadata']['type'] == 'code':
                            print(f"      💻 Code ({result['metadata']['language']}) from page {result['metadata']['page']}")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Search failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Search error: {e}")
            return None

async def test_chat(message):
    """Test chat functionality"""
    print(f"\n💬 Testing chat: '{message}'")
    async with aiohttp.ClientSession() as session:
        try:
            chat_data = {
                "message": message,
                "conversation_id": "test_conversation"
            }
            
            async with session.post(f"{BASE_URL}/chat", json=chat_data) as response:
                if response.status == 200:
                    # Handle streaming response
                    full_response = ""
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'content' in data:
                                    full_response += data['content']
                            except json.JSONDecodeError:
                                continue
                    
                    print(f"✅ Chat response ({len(full_response)} chars):")
                    print(f"   {full_response[:200]}...")
                    return full_response
                else:
                    error_text = await response.text()
                    print(f"❌ Chat failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return None

async def run_api_tests():
    """Run comprehensive API tests"""
    print("🧪 PDF Chatbot API Testing Suite")
    print("=" * 50)
    
    # Test 1: Health check
    if not await test_health():
        print("❌ Health check failed, stopping tests")
        return False
    
    # Test 2: Check existing documents
    docs_before = await test_documents()
    if docs_before is None:
        print("❌ Documents endpoint failed, stopping tests")
        return False
    
    # Test 3: Upload current PDF (simulate re-upload)
    upload_file = "uploads/5104 - 9781583470947_Text.pdf"
    if not await test_upload(upload_file):
        print("❌ Upload failed, continuing with existing data")
    
    # Test 4: Check documents after upload
    docs_after = await test_documents()
    
    # Test 5: Search tests
    search_queries = [
        "programming",
        "image",
        "code",
        "chapter",
        "RPG programming language"
    ]
    
    for query in search_queries:
        await test_search(query)
        await asyncio.sleep(0.5)  # Small delay between searches
    
    # Test 6: Chat tests
    chat_messages = [
        "What programming languages are mentioned in the document?",
        "Are there any images or diagrams in the document?",
        "Show me some code examples from the document",
        "What topics are covered in this book?"
    ]
    
    for message in chat_messages:
        await test_chat(message)
        await asyncio.sleep(1)  # Small delay between chats
    
    print("\n" + "=" * 50)
    print("✅ API testing completed!")
    return True

if __name__ == "__main__":
    asyncio.run(run_api_tests())