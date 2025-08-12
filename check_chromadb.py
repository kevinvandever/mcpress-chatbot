#!/usr/bin/env python3
"""
Check ChromaDB directly on Railway
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

def check_documents_detailed():
    """Get detailed document information"""
    print("Checking documents in ChromaDB on Railway...")
    
    try:
        # Use shorter timeout for listing
        response = requests.get(f"{API_URL}/documents", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            
            print(f"\n✅ Found {len(docs)} documents in ChromaDB")
            print(f"Expected: 115 documents")
            print(f"Missing: {115 - len(docs)} documents")
            
            # Get filenames
            filenames = []
            for doc in docs:
                if isinstance(doc, dict):
                    filenames.append(doc.get('filename', 'Unknown'))
                elif isinstance(doc, str):
                    filenames.append(doc)
            
            # Check for the specific PDFs we're trying to upload
            problem_pdfs = [
                "You Want to Do What with PHP.pdf",
                "WebSphere Application Server- Step by Step.pdf",
                "WDSC- Step by Step.pdf",
                "Understanding AS-400 System Operations.pdf",
                "The RPG Programmers Guide to RPG IV and ILE.pdf"
            ]
            
            print("\n🔍 Checking for the 5 problem PDFs:")
            for pdf in problem_pdfs:
                if pdf in filenames:
                    print(f"  ✅ {pdf} - IN DATABASE")
                else:
                    print(f"  ❌ {pdf} - MISSING")
            
            return docs
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out - database might be overloaded")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_lightweight_endpoint():
    """Test a lightweight endpoint to see if API is responsive"""
    print("\n🏃 Testing API responsiveness...")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is responsive")
            return True
    except:
        print("❌ API is not responding quickly")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 ChromaDB Direct Check")
    print("=" * 60)
    
    # Test responsiveness first
    if test_lightweight_endpoint():
        # Check documents
        docs = check_documents_detailed()
    else:
        print("\n⚠️  API is not responding well - might be overloaded")
        print("Consider restarting the Railway deployment")