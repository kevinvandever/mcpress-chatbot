#!/usr/bin/env python3
"""
Batch upload PDFs to Railway backend with progress tracking
"""

import os
import requests
import time
from pathlib import Path
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIRECTORY = "./backend/uploads"
MAX_WORKERS = 2  # Parallel uploads
TIMEOUT = 300  # 5 minutes per file

def get_existing_documents():
    """Get list of already uploaded documents"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', []) if isinstance(data, dict) else data
            filenames = []
            for doc in docs:
                if isinstance(doc, dict):
                    filenames.append(doc.get('filename', ''))
                elif isinstance(doc, str):
                    filenames.append(doc)
            return [f for f in filenames if f]
        return []
    except Exception as e:
        print(f"Error getting documents: {e}")
        return []

def upload_pdf(pdf_path):
    """Upload a single PDF"""
    filename = pdf_path.name
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/upload", files=files, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            return True, filename, result.get('message', 'Success')
        else:
            return False, filename, f"HTTP {response.status_code}"
    except Exception as e:
        return False, filename, str(e)

def main():
    """Main upload process"""
    print(f"🚀 Railway PDF Batch Upload")
    print(f"📍 API: {API_URL}")
    print(f"📂 Directory: {PDF_DIRECTORY}\n")
    
    # Get PDF files
    pdf_dir = Path(PDF_DIRECTORY)
    if not pdf_dir.exists():
        print(f"❌ Directory not found: {PDF_DIRECTORY}")
        sys.exit(1)
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"📚 Found {len(pdf_files)} PDF files")
    
    # Get existing documents
    print("🔍 Checking existing documents...")
    existing_docs = get_existing_documents()
    print(f"📋 {len(existing_docs)} documents already uploaded")
    
    # Filter out already uploaded files
    remaining_files = [f for f in pdf_files if f.name not in existing_docs]
    print(f"📤 {len(remaining_files)} files to upload\n")
    
    if not remaining_files:
        print("✅ All files already uploaded!")
        return
    
    # Upload with progress tracking
    successful = []
    failed = []
    
    print("Starting uploads...")
    print("-" * 50)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all upload tasks
        future_to_file = {executor.submit(upload_pdf, pdf): pdf for pdf in remaining_files}
        
        # Process completed uploads
        for i, future in enumerate(as_completed(future_to_file), 1):
            pdf_file = future_to_file[future]
            success, filename, message = future.result()
            
            if success:
                successful.append(filename)
                print(f"✅ [{i}/{len(remaining_files)}] {filename}")
            else:
                failed.append((filename, message))
                print(f"❌ [{i}/{len(remaining_files)}] {filename}: {message}")
            
            # Show progress
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (len(remaining_files) - i) / rate
                print(f"   ⏱️  {i} done, ~{int(remaining/60)}m {int(remaining%60)}s remaining")
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"🎯 Upload Complete in {int(elapsed/60)}m {int(elapsed%60)}s")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"📊 Total in system: {len(existing_docs) + len(successful)}")
    
    if failed:
        print("\n⚠️  Failed uploads:")
        for name, error in failed[:5]:  # Show first 5 failures
            print(f"  - {name}: {error}")
        if len(failed) > 5:
            print(f"  ... and {len(failed)-5} more")

if __name__ == "__main__":
    main()