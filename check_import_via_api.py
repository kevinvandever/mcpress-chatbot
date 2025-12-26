#!/usr/bin/env python3
"""
Check the import status using the Railway API endpoints
"""

import requests
import json

def main():
    base_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 Checking author import status via API...")
    
    # Check authors endpoint
    print("\n👥 Checking authors...")
    try:
        response = requests.get(f"{base_url}/api/authors/search?q=John&limit=10")
        if response.status_code == 200:
            authors = response.json()
            print(f"   Found {len(authors)} authors matching 'John'")
            for author in authors[:3]:
                site_url = author.get('site_url', 'No URL')
                print(f"   - {author['name']}: {site_url}")
        else:
            print(f"   ❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check books endpoint
    print("\n📚 Checking books...")
    try:
        response = requests.get(f"{base_url}/api/books?search=DB2&limit=5")
        if response.status_code == 200:
            books = response.json()
            print(f"   Found {len(books)} books matching 'DB2'")
            for book in books[:3]:
                mc_url = book.get('mc_press_url', 'No URL')
                authors = book.get('authors', [])
                if authors:
                    author_names = [a['name'] for a in authors]
                else:
                    author_names = [book.get('author', 'Unknown')]
                print(f"   - {book['title']}")
                print(f"     Authors: {', '.join(author_names)}")
                print(f"     MC Press URL: {mc_url}")
        else:
            print(f"   ❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test a specific book that should have multiple authors
    print("\n🔗 Testing multi-author book...")
    try:
        response = requests.get(f"{base_url}/api/books?search=DB2%2010%20for%20z-OS%20Smarter&limit=1")
        if response.status_code == 200:
            books = response.json()
            if books and len(books) > 0:
                book = books[0]
                print(f"   Book: {book['title']}")
                print(f"   Legacy author: {book.get('author', 'None')}")
                print(f"   MC Press URL: {book.get('mc_press_url', 'None')}")
                authors = book.get('authors', [])
                if authors:
                    print(f"   Multi-authors ({len(authors)}):")
                    for author in authors:
                        site_url = author.get('site_url', 'No URL')
                        print(f"     - {author['name']}: {site_url}")
                else:
                    print("   No multi-author data found")
            else:
                print("   Book not found")
        else:
            print(f"   ❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test chat enrichment
    print("\n💬 Testing chat enrichment...")
    try:
        response = requests.post(f"{base_url}/chat", 
                               json={"message": "Tell me about DB2 10 for z/OS upgrade", 
                                    "conversation_id": "test", 
                                    "user_id": "test"},
                               headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            # Parse streaming response
            lines = response.text.strip().split('\n')
            sources_found = False
            for line in lines:
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        if data.get('type') == 'done' and 'sources' in data:
                            sources = data['sources']
                            print(f"   Found {len(sources)} sources")
                            for i, source in enumerate(sources[:2]):
                                print(f"   Source {i+1}:")
                                print(f"     File: {source.get('filename', 'Unknown')}")
                                print(f"     Author: {source.get('author', 'Unknown')}")
                                print(f"     MC Press URL: {source.get('mc_press_url', 'None')}")
                                print(f"     Authors array: {len(source.get('authors', []))} authors")
                            sources_found = True
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not sources_found:
                print("   No sources found in chat response")
        else:
            print(f"   ❌ Chat API Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Chat Error: {e}")

if __name__ == "__main__":
    main()