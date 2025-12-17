#!/usr/bin/env python3
"""
Test the Railway debug endpoints to verify database connection and enrichment functionality.
"""

import requests
import json
import time
import sys

def wait_for_deployment(max_wait=600):
    """Wait for Railway deployment to complete."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("Waiting for Railway deployment to complete...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            if response.status_code == 200:
                print("✅ Railway deployment is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print("⏳ Still waiting for deployment...")
        time.sleep(30)
    
    print("❌ Deployment wait timeout")
    return False

def test_environment_endpoint():
    """Test the environment debug endpoint."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=== Testing Environment Debug Endpoint ===")
    
    try:
        response = requests.get(f"{api_url}/debug-enrichment/env", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ DATABASE_URL set: {data['database_url_set']}")
            print(f"✅ DATABASE_URL length: {data['database_url_length']}")
            print(f"✅ DATABASE_URL prefix: {data['database_url_prefix']}")
            return True
        else:
            print(f"❌ Environment endpoint failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Environment endpoint error: {e}")
        return False

def test_connection_endpoint():
    """Test the database connection debug endpoint."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=== Testing Database Connection Debug Endpoint ===")
    
    try:
        response = requests.get(f"{api_url}/debug-enrichment/connection", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connection success: {data['connection_success']}")
            print(f"✅ Database version: {data['database_version']}")
            print(f"✅ Tables found: {data['tables_found']}")
            print(f"✅ Book count: {data['book_count']}")
            print(f"✅ Author count: {data['author_count']}")
            print(f"✅ Document-author count: {data['document_author_count']}")
            return True
        else:
            print(f"❌ Connection endpoint failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection endpoint error: {e}")
        return False

def test_sample_books_endpoint():
    """Test the sample books endpoint to get test filenames."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=== Testing Sample Books Debug Endpoint ===")
    
    try:
        response = requests.get(f"{api_url}/debug-enrichment/sample-books", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            books = data['sample_books']
            print(f"✅ Found {len(books)} sample books")
            
            for book in books[:3]:  # Show first 3
                print(f"  - {book['filename']}: {book['title']} by {book['legacy_author']}")
            
            return books
        else:
            print(f"❌ Sample books endpoint failed: {response.status_code}")
            print(response.text)
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Sample books endpoint error: {e}")
        return []

def test_enrichment_endpoint(filename):
    """Test the enrichment debug endpoint with a specific filename."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print(f"=== Testing Enrichment for: {filename} ===")
    
    try:
        response = requests.get(f"{api_url}/debug-enrichment/test/{filename}", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Enrichment success: {data['enrichment_success']}")
            
            if data['enrichment_success']:
                result = data['enrichment_result']
                print(f"✅ Author: {result.get('author', 'N/A')}")
                print(f"✅ Document type: {result.get('document_type', 'N/A')}")
                print(f"✅ MC Press URL: {result.get('mc_press_url', 'N/A')}")
                print(f"✅ Authors count: {len(result.get('authors', []))}")
                
                if result.get('authors'):
                    for i, author in enumerate(result['authors']):
                        print(f"  Author {i+1}: {author.get('name')} (order: {author.get('order')})")
                        if author.get('site_url'):
                            print(f"    Site: {author['site_url']}")
            else:
                print("⚠️  Enrichment returned empty result")
            
            return data['enrichment_success']
        else:
            print(f"❌ Enrichment endpoint failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Enrichment endpoint error: {e}")
        return False

def main():
    """Run all debug endpoint tests."""
    print("Testing Railway debug endpoints...")
    
    # Wait for deployment
    if not wait_for_deployment():
        return 1
    
    # Test environment
    env_ok = test_environment_endpoint()
    
    # Test database connection
    conn_ok = test_connection_endpoint()
    
    # Get sample books
    sample_books = test_sample_books_endpoint()
    
    # Test enrichment with sample books
    enrichment_results = []
    if sample_books:
        for book in sample_books[:3]:  # Test first 3 books
            filename = book['filename']
            success = test_enrichment_endpoint(filename)
            enrichment_results.append(success)
    
    # Summary
    print("=== Test Summary ===")
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"Database Connection: {'✅' if conn_ok else '❌'}")
    print(f"Sample Books: {'✅' if sample_books else '❌'}")
    print(f"Enrichment Tests: {sum(enrichment_results)}/{len(enrichment_results)} passed")
    
    if env_ok and conn_ok and sample_books and any(enrichment_results):
        print("🎉 Railway debug tests passed!")
        return 0
    else:
        print("❌ Some Railway debug tests failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)