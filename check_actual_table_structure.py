#!/usr/bin/env python3
"""
Check the actual table structure on Railway to understand the multi-author table issue
"""

import requests
import json

def main():
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 CHECKING ACTUAL TABLE STRUCTURE")
    print("=" * 60)
    
    # Check if there's a debug endpoint for table structure
    endpoints_to_try = [
        "/debug/tables",
        "/debug/schema", 
        "/admin/debug/tables",
        "/api/debug/tables"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            print(f"📡 Trying: {api_url}{endpoint}")
            response = requests.get(f"{api_url}{endpoint}", timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS: {endpoint}")
                print(json.dumps(data, indent=2, default=str))
                return
                
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n❌ No debug endpoints found")
    print("Let's check if we can create a simple diagnostic endpoint...")
    
    # Try to get some basic info from the working endpoints
    try:
        print(f"\n📊 Checking /admin/stats for clues...")
        response = requests.get(f"{api_url}/admin/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(json.dumps(stats, indent=2, default=str))
            
    except Exception as e:
        print(f"Stats error: {e}")

if __name__ == "__main__":
    main()