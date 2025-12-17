#!/usr/bin/env python3
"""
Test script to debug production enrichment issue.
This script will submit a test chat query and help monitor the enrichment process.
"""

import requests
import json
import time
import os

# Railway production URL
API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_chat_query():
    """Submit a test chat query to trigger enrichment"""
    print("🔍 Testing chat query: 'Tell me about DB2'")
    
    # Prepare the chat request
    chat_data = {
        "message": "Tell me about DB2",
        "conversation_id": "test-enrichment-debug"
    }
    
    try:
        # Submit the chat query
        print(f"📤 Sending request to {API_URL}/chat")
        response = requests.post(
            f"{API_URL}/chat",
            json=chat_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Chat request successful")
            
            # Try to parse the response
            try:
                # Handle streaming response
                response_text = response.text
                print(f"📝 Response length: {len(response_text)} characters")
                
                # Look for sources in the response
                if "sources" in response_text.lower():
                    print("✅ Response contains sources")
                else:
                    print("⚠️  Response does not contain sources")
                
                # Print first 500 characters of response
                print(f"📄 Response preview:\n{response_text[:500]}...")
                
            except Exception as e:
                print(f"❌ Error parsing response: {e}")
                print(f"Raw response: {response.text[:200]}...")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - Railway service may be down")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def check_health():
    """Check if the Railway service is healthy"""
    print("🏥 Checking Railway service health...")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Railway service is healthy")
            return True
        else:
            print(f"⚠️  Health check returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting production enrichment debug test")
    print("=" * 50)
    
    # Check service health first
    if not check_health():
        print("❌ Service is not healthy, aborting test")
        return
    
    print()
    
    # Submit test query
    test_chat_query()
    
    print()
    print("📋 Next steps:")
    print("1. Check Railway logs for enrichment messages:")
    print("   - Look for: 'About to enrich metadata for: [filename]'")
    print("   - Look for: 'Enriching metadata for filename: [filename]'")
    print("   - Look for: 'Found book: [title] by [author]'")
    print("   - Look for: 'Using multi-author data: [names]'")
    print("   - Look for: 'Enrichment result: {...}'")
    print()
    print("2. If no enrichment logs appear:")
    print("   - Check if _enrich_source_metadata() is being called")
    print("   - Verify DATABASE_URL environment variable is set")
    print()
    print("3. If error logs appear:")
    print("   - Check database connection issues")
    print("   - Verify SQL query syntax")
    print("   - Check table/column names")

if __name__ == "__main__":
    main()