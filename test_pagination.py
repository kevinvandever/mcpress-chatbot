#!/usr/bin/env python3
"""
Test pagination functionality
"""

import requests
import json

def test_page(page_num):
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    endpoint = f"{api_url}/admin/documents?page={page_num}&per_page=20"
    
    print(f"📡 Testing page {page_num}: {endpoint}")
    
    try:
        response = requests.get(endpoint, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            
            print(f"✅ Page {page_num} success:")
            print(f"   Documents returned: {len(documents)}")
            print(f"   Page info: {data.get('page')}/{data.get('total_pages')} (Total: {data.get('total')})")
            
            if documents:
                print(f"   First document: {documents[0].get('title')} by {documents[0].get('author')}")
                print(f"   Last document: {documents[-1].get('title')} by {documents[-1].get('author')}")
            
            return True
        else:
            print(f"❌ Page {page_num} failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Page {page_num} error: {e}")
        return False

def main():
    print("🔍 TESTING PAGINATION FUNCTIONALITY")
    print("=" * 60)
    
    # Test first few pages
    for page in [1, 2, 3, 314]:  # Test first, middle, and last page
        test_page(page)
        print()

if __name__ == "__main__":
    main()