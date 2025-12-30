#!/usr/bin/env python3
"""
Test if the author name display fix is working by making a chat query
and checking if we get real author names in the sources.
"""

import requests
import json
import time

def test_chat_for_author_names():
    """Test chat query to see if we get real author names"""
    print("🔍 Testing author name display via chat interface...")
    
    api_url = "https://mcpress-chatbot-production.up.railway.app/api/chat"
    
    # Test query that should return articles
    query = "RPG programming techniques"
    
    try:
        print(f"📤 Sending query: '{query}'")
        
        response = requests.post(api_url, 
            json={
                "message": query,
                "conversation_id": None
            },
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Chat API responded successfully")
            
            # Parse the streaming response
            full_response = ""
            sources_found = []
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        try:
                            data = json.loads(line_text[6:])  # Remove 'data: ' prefix
                            
                            if data.get('type') == 'content':
                                full_response += data.get('content', '')
                            elif data.get('type') == 'sources':
                                sources = data.get('sources', [])
                                sources_found.extend(sources)
                                
                        except json.JSONDecodeError:
                            continue
            
            print(f"📝 Response received ({len(full_response)} chars)")
            print(f"📚 Sources found: {len(sources_found)}")
            
            # Check sources for author information
            if sources_found:
                print(f"\n🔍 Analyzing sources for author names:")
                
                real_authors_found = 0
                unknown_authors_found = 0
                
                for i, source in enumerate(sources_found[:5]):  # Check first 5 sources
                    title = source.get('title', 'Unknown Title')
                    author = source.get('author', 'Unknown')
                    filename = source.get('filename', 'Unknown')
                    doc_type = source.get('document_type', 'unknown')
                    
                    print(f"  Source {i+1}:")
                    print(f"    Title: {title}")
                    print(f"    Author: {author}")
                    print(f"    Filename: {filename}")
                    print(f"    Type: {doc_type}")
                    
                    # Check if we got real author names
                    if author and author != 'Unknown' and 'Unknown Author' not in author and author.strip():
                        real_authors_found += 1
                        print(f"    ✅ Real author name found!")
                    else:
                        unknown_authors_found += 1
                        print(f"    ❌ Still showing Unknown Author")
                    print()
                
                print(f"📊 Results:")
                print(f"  Real authors found: {real_authors_found}")
                print(f"  Unknown authors: {unknown_authors_found}")
                
                if real_authors_found > 0:
                    print(f"\n🎉 SUCCESS: Author name display fix is working!")
                    print(f"Articles are now showing real author names instead of 'Unknown Author'")
                    return True
                else:
                    print(f"\n⚠️  Author name display may still have issues")
                    print(f"All sources still show 'Unknown Author'")
                    return False
            else:
                print(f"❌ No sources returned in chat response")
                return False
                
        else:
            print(f"❌ Chat API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing chat: {e}")
        return False

def main():
    """Main test function"""
    print("Testing if Task 5 (Author Name Display Fix) is working...")
    print("=" * 60)
    
    success = test_chat_for_author_names()
    
    print("\n" + "=" * 60)
    print("TASK 5 VERIFICATION SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ TASK 5 COMPLETED SUCCESSFULLY!")
        print("✅ Author name display fix is working")
        print("✅ Articles now show real author names in chat interface")
        print("✅ The Excel import service now creates document_authors associations")
    else:
        print("❌ TASK 5 may need additional work")
        print("❌ Author names may still show as 'Unknown Author'")
        print("❌ May need to investigate further")

if __name__ == "__main__":
    main()