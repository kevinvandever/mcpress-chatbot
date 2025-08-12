#!/usr/bin/env python3
"""
Debug script to check PDF upload status and diagnose issues
"""

import requests
import sys
from pathlib import Path

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        return False

def get_documents():
    """Get list of documents in the database"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            return docs
        else:
            print(f"❌ Could not get documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
        return []

def check_pending_uploads():
    """Check if any uploads are pending metadata"""
    try:
        response = requests.get(f"{API_URL}/pending-uploads", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def test_single_upload(pdf_path):
    """Test upload of a single PDF to see what response we get"""
    filename = Path(pdf_path).name
    print(f"\n🧪 Testing upload of: {filename}")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = requests.post(
                f"{API_URL}/upload",
                files=files,
                timeout=60
            )
        
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response Data: {result}")
            
            # Check if it needs metadata
            if result.get('status') == 'needs_metadata':
                print(f"\n⚠️  PDF needs author metadata!")
                print(f"Message: {result.get('message')}")
                print(f"Needs Author: {result.get('needs_author')}")
                return 'needs_metadata', result
            else:
                print(f"\n✅ Upload successful!")
                return 'success', result
        else:
            print(f"Error: {response.text}")
            return 'error', response.text
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 'error', str(e)

def main():
    print("=" * 60)
    print("🔍 PDF Upload Diagnostic Tool")
    print("=" * 60)
    
    # Check API health
    if not check_api_health():
        print("❌ API is not responding")
        sys.exit(1)
    
    # Get current documents
    print("\n📚 Checking documents in database...")
    docs = get_documents()
    
    if isinstance(docs, list) and len(docs) > 0:
        # Get just filenames
        filenames = []
        for doc in docs:
            if isinstance(doc, dict):
                filenames.append(doc.get('filename', 'Unknown'))
            elif isinstance(doc, str):
                filenames.append(doc)
        
        print(f"Found {len(filenames)} documents in database")
        
        # Show last 5
        print("\nLast 5 documents:")
        for filename in filenames[-5:]:
            print(f"  - {filename}")
    else:
        print("No documents found or couldn't retrieve list")
    
    # Check pending uploads
    print("\n🔄 Checking for pending uploads...")
    pending = check_pending_uploads()
    if pending:
        print(f"Pending uploads: {pending}")
    else:
        print("No pending uploads endpoint or no pending uploads")
    
    # Test with one of the problem PDFs
    problem_pdfs = [
        "./backend/uploads/You Want to Do What with PHP.pdf",
        "./backend/uploads/WebSphere Application Server- Step by Step.pdf",
        "./backend/uploads/WDSC- Step by Step.pdf",
        "./backend/uploads/Understanding AS-400 System Operations.pdf",
        "./backend/uploads/The RPG Programmers Guide to RPG IV and ILE.pdf"
    ]
    
    # Find first PDF that exists
    test_pdf = None
    for pdf in problem_pdfs:
        if Path(pdf).exists():
            test_pdf = pdf
            break
    
    if test_pdf:
        status, result = test_single_upload(test_pdf)
        
        if status == 'needs_metadata':
            print("\n" + "=" * 60)
            print("🔑 DIAGNOSIS: PDFs are not completing upload due to missing author metadata")
            print("=" * 60)
            print("\nThe PDFs are being uploaded successfully but are stuck in temporary storage")
            print("waiting for author information. They won't appear in the database until")
            print("you provide the author metadata using the /complete-upload endpoint.")
            print("\nTo fix this, you need to:")
            print("1. Provide author information for each PDF")
            print("2. Call the /complete-upload endpoint with the author data")
            print("\nAlternatively, modify the upload process to handle missing authors automatically.")

if __name__ == "__main__":
    main()