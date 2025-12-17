#!/usr/bin/env python3
"""
Test for authors with website URLs to verify clickable links functionality.
"""

import requests
import json
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def find_authors_with_websites():
    """Find authors that have website URLs"""
    print("🔍 Searching for Authors with Website URLs")
    print("=" * 50)
    
    try:
        # Search for authors
        response = requests.get(
            f"{API_URL}/api/authors/search",
            params={"q": "", "limit": 50},  # Get all authors
            timeout=10
        )
        
        if response.status_code == 200:
            authors = response.json()
            authors_with_sites = [a for a in authors if a.get('site_url')]
            
            print(f"📊 Total authors: {len(authors)}")
            print(f"📊 Authors with websites: {len(authors_with_sites)}")
            
            if authors_with_sites:
                print("\n🔗 Authors with website URLs:")
                for author in authors_with_sites[:5]:  # Show first 5
                    print(f"  • {author['name']} -> {author['site_url']}")
                    print(f"    Documents: {author.get('document_count', 0)}")
                
                # Test with a specific author
                test_author = authors_with_sites[0]
                return test_author
            else:
                print("ℹ️  No authors with website URLs found in database")
                return None
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_author_with_website(author):
    """Test chat with an author that has a website"""
    print(f"\n🧪 Testing Author Links with: {author['name']}")
    print("=" * 50)
    
    # Try to find documents by this author
    try:
        response = requests.get(
            f"{API_URL}/api/authors/{author['id']}/documents",
            timeout=10
        )
        
        if response.status_code == 200:
            documents = response.json()
            if documents:
                # Use the first document's title in a query
                doc_title = documents[0].get('title', '')
                if doc_title:
                    # Create a query that should return this document
                    query = f"Tell me about {doc_title[:30]}"
                    print(f"📝 Query: '{query}'")
                    
                    # Send chat request
                    chat_response = requests.post(
                        f"{API_URL}/chat",
                        json={
                            "message": query,
                            "conversation_id": f"author-link-test-{int(time.time())}",
                            "user_id": "author-link-test"
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    if chat_response.status_code == 200:
                        # Parse response
                        sources = None
                        for line in chat_response.text.strip().split('\n'):
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    if data.get('type') == 'done' and 'sources' in data:
                                        sources = data['sources']
                                        break
                                except json.JSONDecodeError:
                                    continue
                        
                        if sources:
                            print(f"✅ Found {len(sources)} sources")
                            
                            # Look for the author with website
                            found_author_link = False
                            for source in sources:
                                authors = source.get('authors', [])
                                for author_obj in authors:
                                    if (author_obj.get('name') == author['name'] and 
                                        author_obj.get('site_url')):
                                        print(f"🔗 Found clickable author link:")
                                        print(f"   Author: {author_obj['name']}")
                                        print(f"   URL: {author_obj['site_url']}")
                                        print(f"   Document: {source.get('filename', 'Unknown')}")
                                        found_author_link = True
                                        break
                                if found_author_link:
                                    break
                            
                            if found_author_link:
                                print("✅ Author website link functionality is working!")
                                return True
                            else:
                                print("⚠️  Author found but no website link in response")
                        else:
                            print("❌ No sources in chat response")
                    else:
                        print(f"❌ Chat request failed: {chat_response.status_code}")
                else:
                    print("❌ No document title available")
            else:
                print("❌ No documents found for this author")
        else:
            print(f"❌ Documents API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing author: {e}")
    
    return False

if __name__ == "__main__":
    # Find authors with websites
    author_with_site = find_authors_with_websites()
    
    if author_with_site:
        # Test the clickable link functionality
        success = test_author_with_website(author_with_site)
        
        if success:
            print("\n🎉 Author website links are working correctly!")
        else:
            print("\n⚠️  Could not verify author website links in chat response")
    else:
        print("\n📋 No authors with websites found to test")
        print("The clickable link functionality is implemented in the frontend")
        print("and will work when authors with site_url are present.")
    
    print("\n" + "=" * 50)
    print("🔗 Author Links Test Complete")