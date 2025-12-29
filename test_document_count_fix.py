#!/usr/bin/env python3
"""
Test script to verify the document count fix
"""

import requests
import json

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_document_count():
    """Test the document count after the fix"""
    print("🔍 Testing document count fix...")
    
    # First, refresh the cache to ensure we get the latest data
    print("📊 Refreshing documents cache...")
    refresh_response = requests.get(f"{BASE_URL}/documents/refresh")
    
    if refresh_response.status_code == 200:
        refresh_data = refresh_response.json()
        print(f"✅ Cache refresh successful")
        print(f"📋 Documents found: {len(refresh_data.get('documents', []))}")
    else:
        print(f"❌ Cache refresh failed: {refresh_response.status_code}")
        return
    
    # Now test the main documents endpoint
    print("\n🔍 Testing main documents endpoint...")
    response = requests.get(f"{BASE_URL}/documents")
    
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        print(f"✅ Documents endpoint successful")
        print(f"📊 Total documents: {len(documents)}")
        
        # Check if we have the expected number (should be 6,270+ not 200)
        if len(documents) > 6000:
            print(f"🎉 SUCCESS: Document count is {len(documents)} (expected 6,270+)")
        elif len(documents) == 200:
            print(f"❌ STILL BROKEN: Document count is still limited to 200")
        else:
            print(f"⚠️ UNEXPECTED: Document count is {len(documents)}")
        
        # Show some sample documents
        print(f"\n📋 Sample documents:")
        for i, doc in enumerate(documents[:3]):
            print(f"  {i+1}. {doc.get('filename', 'Unknown')} - {doc.get('title', 'No title')}")
            
    else:
        print(f"❌ Documents endpoint failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_document_count()