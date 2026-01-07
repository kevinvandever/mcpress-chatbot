#!/usr/bin/env python3
"""
Admin Documents API Diagnostic Script

This script tests the /admin/documents endpoint directly via HTTP to diagnose
the root cause of the document list showing "0 documents" issue.

Requirements: 2.1, 2.3, 4.1
"""

import requests
import json
import sys
from datetime import datetime

# Railway production URL
API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_admin_documents_endpoint():
    """Test the admin documents API endpoint with comprehensive diagnostics"""
    
    print("=" * 60)
    print("ADMIN DOCUMENTS API DIAGNOSTIC")
    print("=" * 60)
    print(f"Testing endpoint: {API_URL}/admin/documents")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Test 1: Basic endpoint without refresh parameter
    print("TEST 1: Basic endpoint (no refresh parameter)")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_URL}/admin/documents", timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response JSON Structure:")
                print(f"  Type: {type(data)}")
                print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if isinstance(data, dict):
                    if 'documents' in data:
                        docs = data['documents']
                        print(f"  Documents array length: {len(docs) if isinstance(docs, list) else 'Not a list'}")
                        
                        if isinstance(docs, list) and len(docs) > 0:
                            print(f"  First document keys: {list(docs[0].keys()) if isinstance(docs[0], dict) else 'Not a dict'}")
                            print(f"  Sample document:")
                            print(f"    {json.dumps(docs[0], indent=4, default=str)}")
                        else:
                            print(f"  Documents array is empty or not a list")
                    else:
                        print(f"  No 'documents' key found in response")
                        print(f"  Full response: {json.dumps(data, indent=2, default=str)}")
                else:
                    print(f"  Response is not a JSON object")
                    print(f"  Raw response: {data}")
                    
            except json.JSONDecodeError as e:
                print(f"  JSON decode error: {e}")
                print(f"  Raw response text: {response.text[:500]}...")
                
        else:
            print(f"Error Response:")
            print(f"  Status: {response.status_code}")
            print(f"  Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    
    print()
    
    # Test 2: Endpoint with refresh parameter
    print("TEST 2: Endpoint with refresh parameter")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_URL}/admin/documents?refresh=true", timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response with refresh=true:")
                print(f"  Type: {type(data)}")
                print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if isinstance(data, dict) and 'documents' in data:
                    docs = data['documents']
                    print(f"  Documents count: {len(docs) if isinstance(docs, list) else 'Not a list'}")
                else:
                    print(f"  No documents array found")
                    
            except json.JSONDecodeError as e:
                print(f"  JSON decode error: {e}")
                
        else:
            print(f"Error Response: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request with refresh failed: {e}")
    
    print()
    
    # Test 3: Check if endpoint exists at all
    print("TEST 3: Endpoint existence check")
    print("-" * 40)
    
    try:
        response = requests.options(f"{API_URL}/admin/documents", timeout=10)
        print(f"OPTIONS request status: {response.status_code}")
        print(f"Allowed methods: {response.headers.get('Allow', 'Not specified')}")
        
    except requests.exceptions.RequestException as e:
        print(f"OPTIONS request failed: {e}")
    
    print()
    
    # Test 4: Test related endpoints for comparison
    print("TEST 4: Related endpoints check")
    print("-" * 40)
    
    # Test health endpoint
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        print(f"Health endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.text}")
    except:
        print("Health endpoint failed")
    
    # Test root endpoint
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"Root endpoint: {response.status_code}")
    except:
        print("Root endpoint failed")
    
    # Test if there are any admin endpoints
    try:
        response = requests.get(f"{API_URL}/admin", timeout=10)
        print(f"Admin base endpoint: {response.status_code}")
    except:
        print("Admin base endpoint failed")
    
    print()
    
    # Test 5: Check response timing
    print("TEST 5: Response timing analysis")
    print("-" * 40)
    
    import time
    
    try:
        start_time = time.time()
        response = requests.get(f"{API_URL}/admin/documents", timeout=30)
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"Response time: {response_time:.2f} seconds")
        
        if response_time > 5:
            print("  WARNING: Response time exceeds 5 seconds (Requirement 7.1)")
        else:
            print("  Response time is acceptable")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 30 seconds")
    except Exception as e:
        print(f"Timing test failed: {e}")
    
    print()
    print("=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    
    return True

def main():
    """Main diagnostic function"""
    
    print("Starting Admin Documents API Diagnostic...")
    print()
    
    success = test_admin_documents_endpoint()
    
    if success:
        print("\nDiagnostic completed successfully.")
        print("\nNext steps:")
        print("1. Review the output above to identify issues")
        print("2. Run database verification script")
        print("3. Check frontend logging")
        return 0
    else:
        print("\nDiagnostic failed to complete.")
        return 1

if __name__ == "__main__":
    sys.exit(main())