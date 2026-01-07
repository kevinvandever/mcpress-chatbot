#!/usr/bin/env python3
"""
Debug script for admin documents endpoint.
This script must be run on Railway: railway run python3 test_admin_endpoint_debug.py
"""

import requests
import json
import sys

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_admin_documents_endpoint():
    """Test the admin documents endpoint and debug issues"""
    print("🔍 Testing Admin Documents Endpoint")
    print("=" * 50)
    
    try:
        # Test the admin documents endpoint
        print("1. Testing /admin/documents endpoint...")
        response = requests.get(f"{API_URL}/admin/documents", timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {list(data.keys())}")
            
            documents = data.get('documents', [])
            print(f"Number of documents returned: {len(documents)}")
            
            if documents:
                print("\nFirst document structure:")
                first_doc = documents[0]
                for key, value in first_doc.items():
                    print(f"  {key}: {type(value).__name__} = {str(value)[:100]}")
            else:
                print("❌ No documents returned!")
                
                # Let's check if there are documents in the database
                print("\n2. Testing regular documents endpoint...")
                reg_response = requests.get(f"{API_URL}/api/documents", timeout=30)
                print(f"Regular documents status: {reg_response.status_code}")
                
                if reg_response.status_code == 200:
                    reg_data = reg_response.json()
                    print(f"Regular documents count: {len(reg_data)}")
                    if reg_data:
                        print("Regular documents exist, but admin endpoint returns none!")
                        print("This suggests an issue with the admin documents query.")
                
        else:
            print(f"❌ Admin documents endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing admin documents endpoint: {e}")

def test_health_endpoint():
    """Test if the API is responding"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def test_database_connection():
    """Test if we can get any documents at all"""
    try:
        # Try the search endpoint which should return documents
        response = requests.post(f"{API_URL}/search", 
                               json={"query": "programming", "limit": 5}, 
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get('sources', [])
            print(f"✅ Search endpoint works - found {len(sources)} sources")
            if sources:
                print("Database has documents, admin endpoint issue is isolated")
            return True
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search endpoint error: {e}")
        return False

def main():
    print("🚀 Admin Documents Endpoint Debug")
    print("=" * 60)
    
    # Test 1: API Health
    print("\n📋 Step 1: API Health Check")
    if not test_health_endpoint():
        print("API is not responding. Check deployment status.")
        sys.exit(1)
    
    # Test 2: Database Connection
    print("\n📋 Step 2: Database Connection Test")
    if not test_database_connection():
        print("Database connection issues detected.")
    
    # Test 3: Admin Documents Endpoint
    print("\n📋 Step 3: Admin Documents Endpoint Test")
    test_admin_documents_endpoint()
    
    print("\n" + "=" * 60)
    print("Debug complete. Check the output above for issues.")

if __name__ == "__main__":
    main()