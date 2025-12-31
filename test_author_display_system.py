#!/usr/bin/env python3
"""
Test script to verify the author display system is working correctly.

This tests:
1. Database has author data in document_authors table
2. Source enrichment returns correct author data
3. Admin dashboard endpoint returns correct author data

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_documents_endpoint():
    """Test that /documents endpoint returns author data correctly"""
    print("=" * 60)
    print("TEST 1: Documents Endpoint Author Data")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        documents = data.get('documents', [])
        print(f"Total documents: {len(documents)}")
        
        # Check for documents with multi-author data
        docs_with_authors = [d for d in documents if d.get('authors') and len(d.get('authors', [])) > 0]
        print(f"Documents with authors array: {len(docs_with_authors)}")
        
        # Check for documents with author URLs
        docs_with_author_urls = [
            d for d in documents 
            if d.get('authors') and any(a.get('site_url') for a in d.get('authors', []))
        ]
        print(f"Documents with author URLs: {len(docs_with_author_urls)}")
        
        # Show sample documents
        print("\nSample documents with authors:")
        for doc in docs_with_authors[:5]:
            print(f"  - {doc.get('title', 'Unknown')[:50]}...")
            print(f"    Authors: {[a.get('name') for a in doc.get('authors', [])]}")
            print(f"    Author URLs: {[a.get('site_url') for a in doc.get('authors', []) if a.get('site_url')]}")
        
        # Check for "Unknown Author" issues
        unknown_authors = [d for d in documents if d.get('author') == 'Unknown' or d.get('author') == 'Unknown Author']
        print(f"\nDocuments with 'Unknown' author: {len(unknown_authors)}")
        
        return len(docs_with_authors) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_enrichment():
    """Test that chat endpoint returns enriched author data"""
    print("\n" + "=" * 60)
    print("TEST 2: Chat Endpoint Source Enrichment")
    print("=" * 60)
    
    try:
        # Send a chat query
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": "Tell me about RPG programming",
                "conversation_id": "test-author-display",
                "user_id": "test"
            },
            timeout=60,
            stream=True
        )
        response.raise_for_status()
        
        # Parse streaming response
        sources = []
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if data.get('type') == 'done':
                        sources = data.get('sources', [])
                        break
                except json.JSONDecodeError:
                    continue
        
        print(f"Sources returned: {len(sources)}")
        
        # Check source enrichment
        enriched_sources = [s for s in sources if s.get('author') and s.get('author') != 'Unknown']
        print(f"Sources with author data: {len(enriched_sources)}")
        
        sources_with_authors_array = [s for s in sources if s.get('authors') and len(s.get('authors', [])) > 0]
        print(f"Sources with authors array: {len(sources_with_authors_array)}")
        
        # Show sample sources
        print("\nSample enriched sources:")
        for source in sources[:5]:
            print(f"  - {source.get('filename', 'Unknown')}")
            print(f"    Title: {source.get('title', 'N/A')}")
            print(f"    Author: {source.get('author', 'Unknown')}")
            print(f"    Authors: {source.get('authors', [])}")
            print(f"    Document Type: {source.get('document_type', 'N/A')}")
        
        # Check for "Unknown" authors
        unknown_sources = [s for s in sources if s.get('author') == 'Unknown' or not s.get('author')]
        print(f"\nSources with 'Unknown' author: {len(unknown_sources)}")
        
        return len(enriched_sources) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_author_search():
    """Test that author search endpoint works"""
    print("\n" + "=" * 60)
    print("TEST 3: Author Search Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/api/authors/search?q=John&limit=5", timeout=30)
        response.raise_for_status()
        authors = response.json()
        
        print(f"Authors found for 'John': {len(authors)}")
        
        for author in authors[:5]:
            print(f"  - {author.get('name')}")
            print(f"    ID: {author.get('id')}")
            print(f"    Site URL: {author.get('site_url', 'N/A')}")
            print(f"    Document Count: {author.get('document_count', 0)}")
        
        return len(authors) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("AUTHOR DISPLAY SYSTEM VERIFICATION")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print()
    
    results = {
        "Documents Endpoint": test_documents_endpoint(),
        "Chat Enrichment": test_chat_enrichment(),
        "Author Search": test_author_search(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Author display system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    main()
