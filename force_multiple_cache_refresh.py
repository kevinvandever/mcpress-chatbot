#!/usr/bin/env python3
"""
Force multiple cache refreshes to see if the import data shows up
"""

import requests
import time

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def force_multiple_refreshes():
    """Force multiple cache refreshes"""
    print("🔄 Forcing multiple cache refreshes...")
    
    for i in range(5):
        print(f"  Refresh {i+1}/5...")
        
        response = requests.get(f"{BASE_URL}/documents/refresh")
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            
            # Check a specific article
            test_article = next((doc for doc in documents if doc.get('filename') == '9998.pdf'), None)
            
            if test_article:
                print(f"    9998.pdf - Document Type: {test_article.get('document_type')}, Author: {test_article.get('author')}")
                
                if test_article.get('document_type') == 'article':
                    print(f"    ✅ SUCCESS! Document type is now 'article'")
                    return True
            else:
                print(f"    ❌ Test article not found")
        else:
            print(f"    ❌ Refresh failed: {response.status_code}")
        
        # Wait between refreshes
        time.sleep(2)
    
    return False

def main():
    print("🔄 FORCE MULTIPLE CACHE REFRESHES")
    print("=" * 50)
    
    success = force_multiple_refreshes()
    
    if not success:
        print("\n❌ Cache refreshes didn't show updated data")
        print("🔍 This suggests the database wasn't actually updated")
        print("\n💡 POSSIBLE SOLUTIONS:")
        print("1. Check if the import API endpoint is working correctly")
        print("2. Check if there are database transaction issues")
        print("3. Check if the import is updating the wrong table")
        print("4. Re-run the import with debugging enabled")
    else:
        print("\n✅ Cache refresh worked! Data is now updated")

if __name__ == "__main__":
    main()