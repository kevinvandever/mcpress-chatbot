#!/usr/bin/env python3
"""
Check what author data actually exists in the books table
"""

import requests
import json

def main():
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 CHECKING BOOKS TABLE AUTHOR DATA")
    print("=" * 60)
    
    # Get a sample of documents to see what author data looks like
    try:
        print(f"📡 Getting sample documents...")
        response = requests.get(f"{api_url}/admin/documents?per_page=5", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            
            print(f"📊 Sample of {len(documents)} documents:")
            for i, doc in enumerate(documents[:3]):
                print(f"\n📄 Document {i+1}:")
                print(f"   ID: {doc.get('id')}")
                print(f"   Filename: {doc.get('filename')}")
                print(f"   Title: {doc.get('title', 'N/A')}")
                print(f"   Author field: '{doc.get('author', 'N/A')}'")
                print(f"   Category: {doc.get('category', 'N/A')}")
                
                # Check if there are any non-"Unknown Author" values
                author = doc.get('author', '')
                if author and author != 'Unknown Author':
                    print(f"   ✅ Found real author: {author}")
                else:
                    print(f"   ❌ Author is Unknown/missing")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    main()