#!/usr/bin/env python3
"""
Test chat interface with image-heavy document queries
"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_chat_with_images():
    """Test chat interface specifically for image-related queries"""
    print("🖼️ Testing Chat Interface with Image-Heavy Queries")
    print("=" * 60)
    
    # Image-specific test queries
    image_queries = [
        "What images are in the document?",
        "Describe the image on page 83",
        "What can you see in the diagrams?",
        "Are there any screenshots or interface images?",
        "What text is shown in the images?",
        "Can you extract text from the images?",
        "Show me all the visual content in the document",
        "What graphics or charts are included?",
        "Are there any code examples shown as images?",
        "Describe any user interface elements in the images"
    ]
    
    # Code-specific queries to test mixed content
    code_queries = [
        "Show me RPG code examples",
        "What programming functions are demonstrated?",
        "Are there any code snippets with comments?",
        "Show me the most complex code example",
        "What programming concepts are illustrated with code?"
    ]
    
    # Mixed content queries
    mixed_queries = [
        "How do the images relate to the code examples?",
        "Are there diagrams that explain the programming concepts?",
        "What visual aids help understand the code?",
        "Do any images show code output or results?",
        "How do the text, images, and code work together?"
    ]
    
    all_queries = [
        ("📸 Image Queries", image_queries),
        ("💻 Code Queries", code_queries),
        ("🔗 Mixed Content Queries", mixed_queries)
    ]
    
    async with aiohttp.ClientSession() as session:
        for category, queries in all_queries:
            print(f"\n{category}")
            print("-" * 40)
            
            for i, query in enumerate(queries, 1):
                print(f"\n{i}. Query: '{query}'")
                
                try:
                    chat_data = {
                        "message": query,
                        "conversation_id": f"image_test_{i}"
                    }
                    
                    async with session.post(f"{BASE_URL}/chat", json=chat_data) as response:
                        if response.status == 200:
                            # Handle streaming response
                            full_response = ""
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
                            
                            print(f"   ✅ Response ({len(full_response)} chars):")
                            
                            # Show response with highlighting for different content types
                            if "image" in full_response.lower():
                                print(f"   📸 IMAGE CONTENT: {full_response[:150]}...")
                            elif "code" in full_response.lower():
                                print(f"   💻 CODE CONTENT: {full_response[:150]}...")
                            else:
                                print(f"   📝 TEXT CONTENT: {full_response[:150]}...")
                            
                            # Check for specific indicators
                            if "page 83" in full_response:
                                print(f"   🎯 Found page 83 reference!")
                            if "mAN" in full_response:
                                print(f"   🎯 Found OCR text 'mAN' from image!")
                            if "RPG" in full_response:
                                print(f"   🎯 Found RPG programming reference!")
                            if "```" in full_response:
                                print(f"   🎯 Found code block formatting!")
                        else:
                            print(f"   ❌ Chat failed: {response.status}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                await asyncio.sleep(0.5)  # Small delay between queries
    
    print("\n" + "=" * 60)
    print("✅ Chat interface image testing completed!")

if __name__ == "__main__":
    asyncio.run(test_chat_with_images())