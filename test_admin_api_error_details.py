#!/usr/bin/env python3
"""
Simple test to check what error is being returned by the admin documents API
"""

import requests
import json

def test_admin_api_error():
    """Test admin API and show detailed error information"""
    
    url = "https://mcpress-chatbot-production.up.railway.app/admin/documents"
    
    try:
        print("🔍 Testing admin documents API...")
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Response Structure:")
            print(f"  - Keys: {list(data.keys())}")
            print(f"  - Documents count: {len(data.get('documents', []))}")
            print(f"  - Total: {data.get('total', 'N/A')}")
            print(f"  - Page: {data.get('page', 'N/A')}")
            print(f"  - Per page: {data.get('per_page', 'N/A')}")
            print(f"  - Total pages: {data.get('total_pages', 'N/A')}")
            
            # Check for error field
            if 'error' in data:
                print(f"\n❌ ERROR FIELD FOUND:")
                print(f"  - Error: {data['error']}")
            else:
                print(f"\n✅ No error field in response")
            
            # Show full response if small
            if len(str(data)) < 1000:
                print(f"\n📋 Full Response:")
                print(json.dumps(data, indent=2))
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_admin_api_error()