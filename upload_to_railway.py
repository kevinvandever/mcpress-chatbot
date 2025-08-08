#!/usr/bin/env python3
"""
Upload all PDFs to the Railway backend
This script uploads PDFs from your local backend/uploads directory 
to the Railway-deployed backend with full processing
"""

import os
import requests
import time
from pathlib import Path
import sys
import json

# Configuration
API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"
BATCH_SIZE = 2  # Number of files per batch (smaller for Railway)
DELAY_BETWEEN_BATCHES = 60  # Seconds to wait between batches (longer for processing)

def get_existing_documents():
    """Get list of already uploaded documents"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            docs = response.json()
            return [doc.get('filename', '') for doc in docs]
        else:
            print(f"Error getting documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting documents: {e}")
        return []

def upload_single_pdf(pdf_path, existing_docs):
    """Upload a single PDF with full processing"""
    filename = pdf_path.name
    
    # Skip if already uploaded
    if filename in existing_docs:
        print(f"  ⏭️  Skipping {filename} (already uploaded)")
        return True
    
    try:
        print(f"  📤 Uploading {filename}...")
        
        # Step 1: Upload PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/upload", files=files, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ {filename} uploaded and processed successfully")
            return True
        else:
            print(f"  ❌ Error uploading {filename}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error uploading {filename}: {e}")
        return False

def main():
    """Main upload process"""
    print(f"🚀 Starting PDF upload to Railway backend: {API_URL}")
    
    # Check if PDF directory exists
    pdf_dir = Path(PDF_DIRECTORY)
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {PDF_DIRECTORY}")
        sys.exit(1)
    
    # Get PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"📚 Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        print("❌ No PDF files found!")
        sys.exit(1)
    
    # Get existing documents
    print("🔍 Checking existing documents...")
    existing_docs = get_existing_documents()
    print(f"📋 Found {len(existing_docs)} existing documents")
    
    # Filter out already uploaded files
    remaining_files = [f for f in pdf_files if f.name not in existing_docs]
    print(f"📤 {len(remaining_files)} files need to be uploaded")
    
    if not remaining_files:
        print("✅ All files are already uploaded!")
        return
    
    # Process in batches
    successful_uploads = 0
    failed_uploads = 0
    
    for i in range(0, len(remaining_files), BATCH_SIZE):
        batch = remaining_files[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(remaining_files) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n=== Batch {batch_num}/{total_batches} ===")
        
        for pdf_file in batch:
            success = upload_single_pdf(pdf_file, existing_docs)
            if success:
                successful_uploads += 1
                existing_docs.append(pdf_file.name)  # Add to existing to avoid re-upload
            else:
                failed_uploads += 1
        
        # Wait between batches (except for the last batch)
        if i + BATCH_SIZE < len(remaining_files):
            print(f"⏱️  Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Final summary
    print(f"\n🎯 Upload Complete!")
    print(f"✅ Successful uploads: {successful_uploads}")
    print(f"❌ Failed uploads: {failed_uploads}")
    print(f"📊 Total documents in system: {len(existing_docs)}")
    
    if failed_uploads > 0:
        print("\n⚠️  Some uploads failed. You can run this script again to retry failed uploads.")

if __name__ == "__main__":
    main()