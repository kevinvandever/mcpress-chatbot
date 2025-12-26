#!/usr/bin/env python3
"""
Upload all article PDFs from /Users/kevinvandever/kev-dev/article pdfs
This will upload all 6,285 article PDFs to make them searchable.
The metadata import will then set document_type='article' and populate URLs.
"""

import os
import requests
import time
from pathlib import Path

def upload_article_pdfs():
    """Upload all article PDFs in batches"""
    
    pdf_directory = "/Users/kevinvandever/kev-dev/article pdfs"
    api_url = "https://mcpress-chatbot-production.up.railway.app/batch-upload"
    
    # Get all PDF files
    pdf_files = list(Path(pdf_directory).glob("*.pdf"))
    total_files = len(pdf_files)
    
    print(f"🚀 Starting upload of {total_files} article PDFs...")
    print(f"📁 Directory: {pdf_directory}")
    print(f"🎯 API URL: {api_url}")
    
    # Upload in batches of 10 files at a time
    batch_size = 10
    uploaded = 0
    failed = 0
    
    for i in range(0, total_files, batch_size):
        batch_files = pdf_files[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_files + batch_size - 1) // batch_size
        
        print(f"\n📦 Batch {batch_num}/{total_batches} - Uploading {len(batch_files)} files...")
        
        try:
            # Prepare files for upload
            files = []
            for pdf_file in batch_files:
                files.append(('files', (pdf_file.name, open(pdf_file, 'rb'), 'application/pdf')))
            
            # Upload batch
            response = requests.post(api_url, files=files, timeout=300)  # 5 minute timeout
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                batch_uploaded = result.get('uploaded_count', len(batch_files))
                uploaded += batch_uploaded
                print(f"✅ Batch {batch_num} successful: {batch_uploaded} files uploaded")
                
                # Show processing details if available
                if 'processing_time' in result:
                    print(f"   ⏱️ Processing time: {result['processing_time']:.2f}s")
                if 'total_chunks' in result:
                    print(f"   📄 Total chunks created: {result['total_chunks']}")
                    
            else:
                print(f"❌ Batch {batch_num} failed: HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                failed += len(batch_files)
                
        except Exception as e:
            print(f"❌ Batch {batch_num} error: {e}")
            failed += len(batch_files)
            
        # Progress update
        processed = uploaded + failed
        progress = (processed / total_files) * 100
        print(f"📊 Progress: {processed}/{total_files} ({progress:.1f}%) - ✅ {uploaded} uploaded, ❌ {failed} failed")
        
        # Small delay between batches to avoid overwhelming the server
        if i + batch_size < total_files:
            time.sleep(2)
    
    print(f"\n🎉 Upload completed!")
    print(f"✅ Successfully uploaded: {uploaded} files")
    print(f"❌ Failed uploads: {failed} files")
    print(f"📊 Success rate: {(uploaded / total_files) * 100:.1f}%")
    
    if uploaded > 0:
        print(f"\n📝 Next steps:")
        print(f"1. Run article metadata import to set document_type='article'")
        print(f"2. Populate article URLs and author website URLs")
        print(f"3. Test chat interface for 'Read' buttons and clickable author names")

if __name__ == "__main__":
    upload_article_pdfs()