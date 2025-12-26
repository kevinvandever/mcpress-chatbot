#!/usr/bin/env python3
"""
Test upload of a few article PDFs to verify the process works
"""

import os
import requests
from pathlib import Path

def test_article_upload():
    """Test upload of first 3 article PDFs"""
    
    pdf_directory = "/Users/kevinvandever/kev-dev/article pdfs"
    api_url = "https://mcpress-chatbot-production.up.railway.app/batch-upload"
    
    # Get first 3 PDF files
    pdf_files = sorted(list(Path(pdf_directory).glob("*.pdf")))[:3]
    
    print(f"🧪 Testing upload of {len(pdf_files)} article PDFs...")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    try:
        # Prepare files for upload (correct format for batch-upload)
        files = []
        for pdf_file in pdf_files:
            files.append(('files', (pdf_file.name, open(pdf_file, 'rb'), 'application/pdf')))
        
        print(f"\n📤 Uploading to {api_url}...")
        response = requests.post(api_url, files=files, timeout=120)
        
        # Close file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   📄 Files uploaded: {result.get('uploaded_count', len(pdf_files))}")
            print(f"   ⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"   📊 Total chunks: {result.get('total_chunks', 0)}")
            
            # Show any errors
            if 'errors' in result and result['errors']:
                print(f"   ⚠️ Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     - {error}")
                    
        else:
            print(f"❌ Upload failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Upload error: {e}")

if __name__ == "__main__":
    test_article_upload()