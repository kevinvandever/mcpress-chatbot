#!/usr/bin/env python3
"""
Debug chat sources by using broader queries to see what's actually being returned
"""

import requests
import json
import re

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def extract_sources_from_chat_response(response_text):
    """Extract sources from the streaming chat response"""
    sources = []
    
    # Split into lines and look for sources data
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith('data: '):
            try:
                data_part = line[6:]  # Remove 'data: '
                if data_part.strip():
                    data = json.loads(data_part)
                    if data.get('type') == 'sources' and 'sources' in data:
                        sources = data['sources']
                        break
            except json.JSONDecodeError:
                continue
    
    return sources

def test_broad_queries():
    """Test broader queries to see what sources are returned"""
    
    print("🔍 Testing Broad Queries to Find Sources")
    print("=" * 60)
    
    queries = [
        "CL programming",
        "subfiles RPG", 
        "IBM i programming",
        "Control Language"
    ]
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 30)
        
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                sources = extract_sources_from_chat_response(response.text)
                
                if sources:
                    print(f"   ✅ Found {len(sources)} sources")
                    
                    # Look for the specific books we're interested in
                    target_books = [
                        "Control Language Programming",
                        "Complete CL",
                        "Subfiles in Free",
                        "subfiles"
                    ]
                    
                    relevant_sources = []
                    for source in sources:
                        filename = source.get('filename', '').lower()
                        for target in target_books:
                            if target.lower() in filename:
                                relevant_sources.append(source)
                                break
                    
                    if relevant_sources:
                        print(f"   🎯 Found {len(relevant_sources)} relevant sources:")
                        
                        for source in relevant_sources:
                            filename = source.get('filename', 'Unknown').replace('.pdf', '')
                            print(f"\n      📖 {filename}")
                            print(f"         Author: '{source.get('author', 'N/A')}'")
                            print(f"         Type: {source.get('document_type', 'N/A')}")
                            print(f"         MC Press URL: {bool(source.get('mc_press_url'))}")
                            
                            authors = source.get('authors', [])
                            if authors:
                                print(f"         Authors array ({len(authors)}):")
                                for i, author in enumerate(authors):
                                    site = f" -> {author.get('site_url')}" if author.get('site_url') else ""
                                    print(f"            {i+1}. {author.get('name', 'N/A')}{site}")
                            else:
                                print(f"         Authors array: Empty")
                    else:
                        print(f"   ⚠️  No relevant sources found")
                        # Show first few sources for reference
                        print(f"   📚 Sample sources:")
                        for i, source in enumerate(sources[:3]):
                            filename = source.get('filename', 'Unknown').replace('.pdf', '')
                            print(f"      {i+1}. {filename}")
                else:
                    print(f"   ❌ No sources in response")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_author_document_associations():
    """Check which documents are associated with specific authors"""
    
    print(f"\n\n🔍 Checking Author-Document Associations")
    print("=" * 60)
    
    authors_to_check = [
        ("Ted Holt", "Should have CL books"),
        ("Kevin Vandever", "Should have Subfiles book"),
        ("Jim Buck", "Should have CL Programming book"),
        ("Annegrubb", "Should NOT have many books"),
        ("Admin", "Should NOT have books")
    ]
    
    for author_name, expected in authors_to_check:
        print(f"\n👤 {author_name} ({expected})")
        
        try:
            # Search for the author first
            search_response = requests.get(
                f"{API_URL}/api/authors/search",
                params={"q": author_name, "limit": 1},
                timeout=10
            )
            
            if search_response.status_code == 200:
                authors = search_response.json()
                if authors:
                    author = authors[0]
                    author_id = author['id']
                    doc_count = author.get('document_count', 0)
                    
                    print(f"   📊 Found: {author['name']} (ID: {author_id}, {doc_count} docs)")
                    
                    # Try to get documents for this author
                    try:
                        docs_response = requests.get(
                            f"{API_URL}/api/authors/{author_id}/documents",
                            timeout=10
                        )
                        
                        if docs_response.status_code == 200:
                            documents = docs_response.json()
                            if documents:
                                print(f"   📚 Documents ({len(documents)}):")
                                for doc in documents[:5]:  # Show first 5
                                    title = doc.get('title', 'Unknown')
                                    doc_type = doc.get('document_type', 'unknown')
                                    print(f"      - {title} ({doc_type})")
                                if len(documents) > 5:
                                    print(f"      ... and {len(documents) - 5} more")
                            else:
                                print(f"   📚 No documents found")
                        else:
                            print(f"   ⚠️  Documents API error: {docs_response.status_code}")
                            
                    except Exception as e:
                        print(f"   ⚠️  Error getting documents: {e}")
                else:
                    print(f"   ❌ Author not found")
            else:
                print(f"   ❌ Search error: {search_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_broad_queries()
    check_author_document_associations()
    
    print(f"\n\n📋 Diagnosis Summary:")
    print("=" * 60)
    print("Based on the API results, the issues appear to be:")
    print("1. 📊 Data Quality: Wrong authors assigned to books (annegrubb, admin)")
    print("2. 🔗 Missing Associations: Correct authors exist but aren't linked to books")
    print("3. 📝 Import Issues: The Excel import may not have processed correctly")
    print("4. 🎯 Need to verify: Multi-author display vs single author fallback")