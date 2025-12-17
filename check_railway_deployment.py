#!/usr/bin/env python3
"""
Check Railway deployment status by testing the API endpoints.
"""

import requests
import json
import sys

def test_railway_api():
    """Test if the Railway API is responding."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=== Testing Railway API Status ===")
    
    # Test health endpoint
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Railway API is responding")
            return True
        else:
            print(f"❌ Health endpoint returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Railway API: {e}")
        return False

def test_chat_endpoint():
    """Test a simple chat query to see if enrichment is working."""
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("=== Testing Chat Endpoint ===")
    
    try:
        # Test with a simple query
        payload = {
            "message": "Tell me about DB2",
            "conversation_id": "test-deployment-check"
        }
        
        response = requests.post(
            f"{api_url}/chat", 
            json=payload,
            timeout=30,
            stream=True
        )
        
        print(f"Chat endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Chat endpoint is responding")
            
            # Try to read some of the streaming response
            content_received = False
            for i, line in enumerate(response.iter_lines(decode_unicode=True)):
                if line and line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        if 'sources' in data:
                            print(f"✅ Received sources data: {len(data['sources'])} sources")
                            # Check if any source has enriched metadata
                            for source in data['sources']:
                                if source.get('author') and source['author'] != 'Unknown':
                                    print(f"✅ Found enriched source: {source['author']}")
                                    return True
                        content_received = True
                    except json.JSONDecodeError:
                        pass
                
                # Only read first few lines to avoid hanging
                if i > 10:
                    break
            
            if content_received:
                print("✅ Chat is streaming responses")
            else:
                print("⚠️  No streaming content received")
            
            return True
        else:
            print(f"❌ Chat endpoint returned {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to test chat endpoint: {e}")
        return False

def main():
    """Run deployment tests."""
    print("Checking Railway deployment status...")
    
    api_ok = test_railway_api()
    chat_ok = test_chat_endpoint()
    
    print("=== Summary ===")
    print(f"API Health: {'✅' if api_ok else '❌'}")
    print(f"Chat Endpoint: {'✅' if chat_ok else '❌'}")
    
    if api_ok and chat_ok:
        print("🎉 Railway deployment appears to be working!")
        return 0
    else:
        print("❌ Some issues detected with Railway deployment")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)