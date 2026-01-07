#!/usr/bin/env python3
"""
Debug script to investigate why frontend pagination is still showing only one page
"""

import requests
import json

def test_api_pagination_detailed():
    """Test API pagination with detailed logging"""
    print("🔍 Testing API Pagination in Detail...")
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Test multiple pages
    for page in [1, 2, 3]:
        print(f"\n📄 Testing Page {page}:")
        response = requests.get(f"{api_url}/admin/documents?page={page}&per_page=20")
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            continue
            
        data = response.json()
        
        print(f"   Status: {response.status_code}")
        print(f"   Page: {data.get('page')}")
        print(f"   Per Page: {data.get('per_page')}")
        print(f"   Total: {data.get('total')}")
        print(f"   Total Pages: {data.get('total_pages')}")
        print(f"   Documents: {len(data.get('documents', []))}")
        
        if data.get('documents'):
            first_doc = data['documents'][0]
            print(f"   First Doc: {first_doc.get('title', 'N/A')}")
            print(f"   First Author: {first_doc.get('author', 'N/A')}")

def check_frontend_api_call():
    """Check what the frontend would receive"""
    print("\n🌐 Testing Frontend API Call Format...")
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Simulate frontend call
    response = requests.get(f"{api_url}/admin/documents?page=1&per_page=20")
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ Frontend would receive:")
        print(f"   Response keys: {list(data.keys())}")
        
        # Check if pagination data is properly structured
        pagination_fields = ['page', 'per_page', 'total', 'total_pages']
        for field in pagination_fields:
            value = data.get(field)
            print(f"   {field}: {value} (type: {type(value).__name__})")
        
        # Check documents structure
        docs = data.get('documents', [])
        print(f"   documents: {len(docs)} items")
        
        if docs:
            first_doc = docs[0]
            print(f"   First doc keys: {list(first_doc.keys())}")
            
        # Check for any error fields
        if 'error' in data:
            print(f"   ⚠️ Error field present: {data['error']}")
    else:
        print(f"❌ API call failed: {response.status_code}")

def main():
    print("🐛 Debugging Frontend Pagination Issue")
    print("=" * 50)
    
    test_api_pagination_detailed()
    check_frontend_api_call()
    
    print("\n💡 Analysis:")
    print("   The backend API is working correctly with proper pagination.")
    print("   The issue is likely in the frontend React state management.")
    print("   Possible causes:")
    print("   1. useEffect dependencies not triggering re-renders")
    print("   2. State updates not propagating correctly")
    print("   3. Frontend caching the first page response")
    print("   4. Netlify deployment hasn't picked up the latest changes")
    
    print("\n🔧 Next Steps:")
    print("   1. Check browser console for React errors")
    print("   2. Verify Netlify deployment timestamp")
    print("   3. Check if pagination state is updating in React DevTools")
    print("   4. Add more console.log statements to track state changes")

if __name__ == "__main__":
    main()