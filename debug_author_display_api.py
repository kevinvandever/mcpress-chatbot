#!/usr/bin/env python3
"""
Debug author display issues using the API endpoints.
This will help identify if the issue is in the data or the display logic.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_chat_query_for_books():
    """Test specific chat queries to see what author data is returned"""
    
    print("🔍 Testing Chat Queries for Specific Books")
    print("=" * 60)
    
    test_queries = [
        "Control Language Programming for IBM i",
        "Complete CL Sixth Edition", 
        "Subfiles in Free Format RPG",
        "Ted Holt CL programming",
        "Kevin Vandever subfiles"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"   ❌ Error: {response.status_code}")
                continue
                
            # Parse the streaming response to extract sources
            content = response.text
            sources_found = []
            
            # Look for sources in the response
            lines = content.split('\n')
            for line in lines:
                if line.startswith('data: ') and '"type": "sources"' in line:
                    try:
                        data_part = line[6:]  # Remove 'data: '
                        data = json.loads(data_part)
                        if 'sources' in data:
                            sources_found = data['sources']
                            break
                    except json.JSONDecodeError:
                        continue
            
            if sources_found:
                print(f"   ✅ Found {len(sources_found)} sources")
                
                # Group by filename to see unique books
                books = {}
                for source in sources_found:
                    filename = source.get('filename', 'Unknown')
                    if filename not in books:
                        books[filename] = source
                
                for filename, source in books.items():
                    title = filename.replace('.pdf', '')
                    print(f"\n   📖 {title}")
                    print(f"      Author field: '{source.get('author', 'N/A')}'")
                    print(f"      Document type: {source.get('document_type', 'N/A')}")
                    print(f"      MC Press URL: {source.get('mc_press_url', 'N/A')}")
                    
                    authors_array = source.get('authors', [])
                    if authors_array:
                        print(f"      Authors array ({len(authors_array)} authors):")
                        for i, author in enumerate(authors_array):
                            site_info = f" -> {author.get('site_url')}" if author.get('site_url') else " (no website)"
                            print(f"         {i+1}. {author.get('name', 'N/A')}{site_info}")
                    else:
                        print(f"      Authors array: Empty (using fallback)")
            else:
                print(f"   ⚠️  No sources found in response")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_author_endpoints():
    """Check the author management endpoints to see what authors exist"""
    
    print(f"\n\n🔍 Checking Author Management Endpoints")
    print("=" * 60)
    
    # Search for specific authors
    author_searches = [
        "Jim Buck",
        "Ted Holt", 
        "Kevin Vandever",
        "annegrubb",
        "admin"
    ]
    
    for search_term in author_searches:
        print(f"\n🔍 Searching for: '{search_term}'")
        
        try:
            response = requests.get(
                f"{API_URL}/api/authors/search",
                params={"q": search_term, "limit": 10},
                timeout=10
            )
            
            if response.status_code == 200:
                authors = response.json()
                if authors:
                    print(f"   ✅ Found {len(authors)} authors:")
                    for author in authors:
                        site_info = f" -> {author.get('site_url')}" if author.get('site_url') else " (no website)"
                        doc_count = author.get('document_count', 0)
                        print(f"      - {author.get('name')}{site_info} ({doc_count} docs)")
                else:
                    print(f"   ❌ No authors found")
            else:
                print(f"   ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_specific_documents():
    """Check specific document endpoints if available"""
    
    print(f"\n\n🔍 Checking Document Information")
    print("=" * 60)
    
    # Try to get document list or search
    try:
        response = requests.get(f"{API_URL}/api/documents", timeout=10)
        if response.status_code == 200:
            print("✅ Documents endpoint available")
            # Could add more specific document checks here
        else:
            print(f"⚠️  Documents endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Documents endpoint not accessible: {e}")

if __name__ == "__main__":
    test_chat_query_for_books()
    check_author_endpoints() 
    check_specific_documents()
    
    print(f"\n\n📋 Summary of Issues to Investigate:")
    print("=" * 60)
    print("1. Multi-author display: Check if authors array is populated correctly")
    print("2. Author name accuracy: Verify correct authors are in the database")
    print("3. Author website buttons: Frontend should show clickable author names")
    print("4. Data source: Check if Excel import populated authors correctly")