#!/usr/bin/env python3
"""
Test script to verify the frontend pagination fix is working correctly.
This script tests the admin documents page pagination functionality.
"""

import requests
import time
import json

def test_backend_pagination():
    """Test that backend API pagination is working correctly"""
    print("🔍 Testing Backend API Pagination...")
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Test page 1
    response1 = requests.get(f"{api_url}/admin/documents?page=1&per_page=20")
    if response1.status_code != 200:
        print(f"❌ Page 1 failed: {response1.status_code}")
        return False
    
    data1 = response1.json()
    
    # Test page 2  
    response2 = requests.get(f"{api_url}/admin/documents?page=2&per_page=20")
    if response2.status_code != 200:
        print(f"❌ Page 2 failed: {response2.status_code}")
        return False
    
    data2 = response2.json()
    
    # Verify pagination data
    if data1.get('page') != 1:
        print(f"❌ Page 1 returned wrong page number: {data1.get('page')}")
        return False
        
    if data2.get('page') != 2:
        print(f"❌ Page 2 returned wrong page number: {data2.get('page')}")
        return False
    
    if data1.get('total_pages') != data2.get('total_pages'):
        print(f"❌ Total pages mismatch: {data1.get('total_pages')} vs {data2.get('total_pages')}")
        return False
    
    # Verify different documents on different pages
    docs1 = data1.get('documents', [])
    docs2 = data2.get('documents', [])
    
    if not docs1 or not docs2:
        print(f"❌ Missing documents: page1={len(docs1)}, page2={len(docs2)}")
        return False
    
    # Check that documents are different between pages
    titles1 = {doc['title'] for doc in docs1}
    titles2 = {doc['title'] for doc in docs2}
    
    if titles1.intersection(titles2):
        print(f"❌ Pages have overlapping documents")
        return False
    
    print(f"✅ Backend pagination working correctly:")
    print(f"   - Page 1: {len(docs1)} documents")
    print(f"   - Page 2: {len(docs2)} documents") 
    print(f"   - Total pages: {data1.get('total_pages')}")
    print(f"   - Total documents: {data1.get('total')}")
    
    return True

def test_frontend_deployment():
    """Test that frontend is deployed and accessible"""
    print("\n🌐 Testing Frontend Deployment...")
    
    frontend_url = "https://mcpress-chatbot.netlify.app"
    
    try:
        response = requests.get(f"{frontend_url}/admin/documents", timeout=10)
        if response.status_code == 200:
            print(f"✅ Frontend accessible at {frontend_url}")
            return True
        else:
            print(f"❌ Frontend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend not accessible: {e}")
        return False

def main():
    print("🧪 Testing Admin Documents Pagination Fix")
    print("=" * 50)
    
    # Test backend first
    backend_ok = test_backend_pagination()
    
    # Test frontend deployment
    frontend_ok = test_frontend_deployment()
    
    print("\n📊 Test Results:")
    print(f"   Backend API: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"   Frontend:    {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 All tests passed! The pagination fix should be working.")
        print("\n📝 Next steps:")
        print("   1. Open https://mcpress-chatbot.netlify.app/admin/documents")
        print("   2. Verify you see documents with real author names")
        print("   3. Check pagination shows 'X / 314' instead of '1 / 1'")
        print("   4. Test clicking Next/Prev buttons to navigate pages")
        return True
    else:
        print("\n❌ Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)