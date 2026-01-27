#!/usr/bin/env python3
"""
Test script to verify multi-author button display in CompactSources component.

This script checks books with multiple authors to see if they have website URLs
and verifies the data structure being sent to the frontend.
"""

import requests
import os
import json

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-production.up.railway.app")

def find_multi_author_books_with_websites():
    """Find books that have multiple authors with website URLs"""
    
    print("🔍 Searching for multi-author books with websites...\n")
    
    # Get a sample of books
    response = requests.get(f"{API_URL}/api/books?limit=100")
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch books: {response.status_code}")
        return
    
    books = response.json()
    
    multi_author_books_with_sites = []
    
    for book in books:
        if 'authors' in book and len(book['authors']) > 1:
            # Check if multiple authors have websites
            authors_with_sites = [a for a in book['authors'] if a.get('site_url')]
            
            if len(authors_with_sites) > 1:
                multi_author_books_with_sites.append({
                    'id': book['id'],
                    'title': book.get('title', book['filename']),
                    'filename': book['filename'],
                    'authors': book['authors'],
                    'authors_with_sites_count': len(authors_with_sites)
                })
    
    print(f"📊 Found {len(multi_author_books_with_sites)} books with multiple authors having websites\n")
    
    if multi_author_books_with_sites:
        print("📚 Sample books:\n")
        for book in multi_author_books_with_sites[:5]:
            print(f"  • {book['title']}")
            print(f"    Authors with websites: {book['authors_with_sites_count']}")
            for author in book['authors']:
                site_indicator = "✓" if author.get('site_url') else "✗"
                print(f"      [{site_indicator}] {author['name']}")
                if author.get('site_url'):
                    print(f"          {author['site_url']}")
            print()
    else:
        print("⚠️  No books found with multiple authors having websites")
        print("    This might be why the bug hasn't been noticed!")
    
    return multi_author_books_with_sites

def test_chat_response_with_multi_author():
    """Test a chat query to see the actual data structure sent to frontend"""
    
    print("\n🧪 Testing chat response structure...\n")
    
    # Try a query that might return multi-author books
    test_query = "Tell me about RPG programming"
    
    print(f"Query: '{test_query}'")
    print("Sending request...\n")
    
    response = requests.post(
        f"{API_URL}/api/chat",
        json={
            "message": test_query,
            "conversation_id": "test-multi-author-check"
        },
        stream=True
    )
    
    if response.status_code != 200:
        print(f"❌ Chat request failed: {response.status_code}")
        return
    
    # Parse the streaming response to extract sources
    sources = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'sources':
                        sources = data.get('sources', [])
                        break
                except json.JSONDecodeError:
                    continue
    
    if sources:
        print(f"✅ Received {len(sources)} sources\n")
        
        # Check for multi-author sources
        multi_author_sources = [s for s in sources if len(s.get('authors', [])) > 1]
        
        if multi_author_sources:
            print(f"📚 Found {len(multi_author_sources)} multi-author sources:\n")
            for source in multi_author_sources[:3]:
                print(f"  • {source.get('title', source['filename'])}")
                authors = source.get('authors', [])
                authors_with_sites = [a for a in authors if a.get('site_url')]
                print(f"    Total authors: {len(authors)}")
                print(f"    Authors with websites: {len(authors_with_sites)}")
                
                for author in authors:
                    site_indicator = "✓" if author.get('site_url') else "✗"
                    print(f"      [{site_indicator}] {author['name']}")
                    if author.get('site_url'):
                        print(f"          {author['site_url']}")
                print()
                
                # Check what the frontend would see
                if len(authors_with_sites) > 1:
                    print(f"    ✅ Frontend should show 'Authors' (plural) with dropdown")
                elif len(authors_with_sites) == 1:
                    print(f"    ✅ Frontend should show 'Author' (singular) as direct link")
                else:
                    print(f"    ℹ️  No author websites - no button shown")
                print()
        else:
            print("⚠️  No multi-author sources in this response")
    else:
        print("❌ No sources found in response")

def main():
    print("=" * 70)
    print("Multi-Author Button Display Test")
    print("=" * 70)
    print()
    
    # First, check if we have books with multiple authors with websites
    books = find_multi_author_books_with_websites()
    
    # Then test the actual chat response
    test_chat_response_with_multi_author()
    
    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)

if __name__ == "__main__":
    main()
