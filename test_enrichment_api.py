#!/usr/bin/env python3
"""
Test the enrichment API endpoint to see if author names are being displayed correctly.
"""

import requests
import json

def test_enrichment_endpoint():
    """Test the enrichment endpoint"""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=" * 60)
    print("TESTING ENRICHMENT API ENDPOINT")
    print("=" * 60)
    
    # Test the enrichment endpoint with a known filename
    test_filename = "4247.pdf"  # Common article format
    
    try:
        response = requests.get(f"{api_url}/test-enrichment/{test_filename}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Enrichment API responded successfully")
            print(f"Filename: {test_filename}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Check if we got real author data
            author = data.get('author', 'Unknown')
            authors_list = data.get('authors', [])
            
            if author and author != 'Unknown' and 'Unknown Author' not in author:
                print(f"✅ SUCCESS: Got real author name: {author}")
                if authors_list:
                    print(f"✅ Multi-author data: {len(authors_list)} authors")
                    for i, auth in enumerate(authors_list):
                        print(f"  {i}: {auth.get('name', 'N/A')} (order {auth.get('order', 'N/A')})")
                return True
            else:
                print(f"❌ Still showing Unknown Author: {author}")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing enrichment API: {e}")
        return False

def test_chat_with_article_query():
    """Test a chat query that should return articles with author names"""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("\n" + "=" * 60)
    print("TESTING CHAT QUERY FOR ARTICLES")
    print("=" * 60)
    
    try:
        # Test a query that should return articles
        query = "RPG programming"
        
        response = requests.post(f"{api_url}/api/chat", json={
            "message": query,
            "conversation_id": None
        })
        
        if response.status_code == 200:
            # This is a streaming response, so we need to handle it differently
            print(f"✅ Chat API responded successfully")
            print(f"Query: {query}")
            
            # For now, just check that we got a response
            # In a real test, we'd parse the streaming response to check sources
            print("✅ Chat response received (streaming)")
            return True
        else:
            print(f"❌ Chat API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing chat API: {e}")
        return False

def main():
    """Main test function"""
    print("Testing author name display via API...")
    
    # Test 1: Direct enrichment endpoint
    enrichment_works = test_enrichment_endpoint()
    
    # Test 2: Chat query (basic test)
    chat_works = test_chat_with_article_query()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Enrichment API test: {'✅' if enrichment_works else '❌'}")
    print(f"Chat API test: {'✅' if chat_works else '❌'}")
    
    if enrichment_works:
        print("\n🎉 Author name display appears to be working!")
    else:
        print("\n⚠️  Author name display may still have issues")

if __name__ == "__main__":
    main()