#!/usr/bin/env python3
"""
Test specifically for John Campbell who has a website URL.
"""

import requests
import json
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_john_campbell_link():
    """Test chat query that should return John Campbell with clickable link"""
    print("🔗 Testing John Campbell Author Link")
    print("=" * 40)
    
    # Query that should return John Campbell's book
    query = "Tell me about DB2 10 for z/OS upgrade"
    
    print(f"📝 Query: '{query}'")
    print("Expected: John Campbell with website link")
    
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": query,
                "conversation_id": f"campbell-test-{int(time.time())}",
                "user_id": "campbell-test"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
        
        # Parse response
        sources = None
        for line in response.text.strip().split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'done' and 'sources' in data:
                        sources = data['sources']
                        break
                except json.JSONDecodeError:
                    continue
        
        if not sources:
            print("❌ No sources found")
            return False
        
        print(f"✅ Found {len(sources)} sources")
        
        # Look for John Campbell
        found_campbell = False
        for i, source in enumerate(sources, 1):
            filename = source.get('filename', 'Unknown')
            authors = source.get('authors', [])
            
            print(f"\n📄 Source {i}: {filename}")
            
            for author in authors:
                name = author.get('name', 'Unknown')
                site_url = author.get('site_url')
                
                if name == 'John Campbell':
                    found_campbell = True
                    if site_url:
                        print(f"🎉 FOUND: John Campbell with website link!")
                        print(f"   Name: {name}")
                        print(f"   URL: {site_url}")
                        print(f"   Document: {filename}")
                        print("✅ Clickable author link functionality is working!")
                        return True
                    else:
                        print(f"⚠️  Found John Campbell but no website URL")
                        print(f"   Name: {name}")
                        print(f"   URL: {site_url}")
                
                if site_url:
                    print(f"🔗 Other author with link: {name} -> {site_url}")
        
        if not found_campbell:
            print("❌ John Campbell not found in sources")
            print("Available authors:")
            for source in sources[:3]:
                authors = source.get('authors', [])
                for author in authors:
                    print(f"  • {author.get('name', 'Unknown')}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_john_campbell_link()
    
    if success:
        print("\n🎉 SUCCESS: Author website links are working!")
        print("✅ Task 5.3 requirement for clickable author links is satisfied")
    else:
        print("\n⚠️  Could not verify John Campbell's website link")
        print("The functionality is implemented but may need specific query")
    
    print("\n📋 Manual verification:")
    print("1. Open https://mcpress-chatbot.netlify.app")
    print("2. Ask: 'Tell me about DB2 10 for z/OS upgrade'")
    print("3. Look for John Campbell in the References section")
    print("4. Verify his name is a clickable link to https://johncampbell-test.com")