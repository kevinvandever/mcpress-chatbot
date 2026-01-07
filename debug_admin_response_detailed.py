#!/usr/bin/env python3
"""
Detailed diagnostic of admin documents API response
"""

import requests
import json
import sys

def main():
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    endpoint = f"{api_url}/admin/documents"
    
    print("🔍 DETAILED ADMIN DOCUMENTS API DIAGNOSTIC")
    print("=" * 60)
    
    try:
        # Make request
        print(f"📡 Requesting: {endpoint}")
        response = requests.get(endpoint, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        # Parse response
        try:
            data = response.json()
            print(f"📄 Response Type: {type(data)}")
            print(f"📄 Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Print full response for debugging
            print("\n📝 FULL RESPONSE:")
            print(json.dumps(data, indent=2, default=str))
            
            # Check specific fields
            if isinstance(data, dict):
                documents = data.get('documents', [])
                total = data.get('total', 0)
                error = data.get('error')
                
                print(f"\n📊 ANALYSIS:")
                print(f"   Documents count: {len(documents) if isinstance(documents, list) else 'Not a list'}")
                print(f"   Total reported: {total}")
                print(f"   Error field: {error}")
                
                if error:
                    print(f"❌ ERROR DETECTED: {error}")
                
                if isinstance(documents, list) and len(documents) > 0:
                    print(f"✅ Sample document: {documents[0]}")
                elif total > 0 and len(documents) == 0:
                    print("⚠️  Total > 0 but documents array is empty - possible query issue")
                else:
                    print("❌ No documents returned")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"📄 Raw response: {response.text[:500]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return 1
    
    # Also test the stats endpoint
    print("\n" + "=" * 60)
    print("🔍 TESTING ADMIN STATS ENDPOINT")
    
    try:
        stats_response = requests.get(f"{api_url}/admin/stats", timeout=30)
        print(f"📊 Stats Status: {stats_response.status_code}")
        
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print(f"📊 Stats Response: {json.dumps(stats_data, indent=2, default=str)}")
        else:
            print(f"❌ Stats error: {stats_response.text}")
            
    except Exception as e:
        print(f"❌ Stats request error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())