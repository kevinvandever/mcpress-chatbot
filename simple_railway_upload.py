#!/usr/bin/env python3
"""
Simple, reliable upload script for Railway
Based on what worked successfully before
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIRECTORY = "./backend/uploads"
BATCH_SIZE = 1  # One at a time for reliability
DELAY_BETWEEN_UPLOADS = 5  # 5 seconds between uploads

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

def get_existing_documents():
    """Get list of already uploaded documents"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            filenames = []
            for doc in docs:
                if isinstance(doc, dict):
                    filenames.append(doc.get('filename', ''))
                elif isinstance(doc, str):
                    filenames.append(doc)
            return [f for f in filenames if f]
        else:
            print(f"Warning: Could not get documents list: {response.status_code}")
            return []
    except Exception as e:
        print(f"Warning: Could not get documents list: {e}")
        return []

def upload_pdf(pdf_path):
    """Upload a single PDF with retries"""
    filename = pdf_path.name
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            
            with open(pdf_path, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                response = requests.post(
                    f"{API_URL}/upload",
                    files=files,
                    timeout=300  # 5 minutes per file
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result.get('message', 'Uploaded')}")
                return True
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in 10 seconds...")
                    time.sleep(10)
                
        except requests.exceptions.Timeout:
            print(f"  ⏱️ Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(10)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
    
    return False

def main():
    """Main upload process"""
    print("=" * 60)
    print("🚀 Simple Railway Upload Script")
    print(f"📍 API: {API_URL}")
    print(f"📂 PDFs: {PDF_DIRECTORY}")
    print("=" * 60)
    
    # Check API health first
    if not check_api_health():
        print("❌ API is not responding. Please check Railway deployment.")
        sys.exit(1)
    
    # Get PDF files
    pdf_dir = Path(PDF_DIRECTORY)
    if not pdf_dir.exists():
        print(f"❌ Directory not found: {PDF_DIRECTORY}")
        sys.exit(1)
    
    pdf_files = sorted(list(pdf_dir.glob("*.pdf")))
    print(f"📚 Found {len(pdf_files)} PDF files")
    
    # Get existing documents
    print("\n🔍 Checking existing documents...")
    existing_docs = get_existing_documents()
    print(f"📋 {len(existing_docs)} documents already uploaded")
    
    # Filter out already uploaded files
    remaining_files = [f for f in pdf_files if f.name not in existing_docs]
    print(f"📤 {len(remaining_files)} files to upload")
    
    if not remaining_files:
        print("\n✅ All files already uploaded!")
        return
    
    # Show what will happen
    print(f"\n⚠️  This will upload {len(remaining_files)} files")
    print(f"⏱️  Estimated time: {len(remaining_files) * 45 // 60} minutes")
    print("\n🚀 Starting upload...")
    
    # Upload files one by one
    print("\n" + "=" * 60)
    print("Starting uploads...")
    print("=" * 60)
    
    successful = 0
    failed = []
    start_time = time.time()
    
    for i, pdf_file in enumerate(remaining_files, 1):
        print(f"\n[{i}/{len(remaining_files)}] Uploading: {pdf_file.name}")
        
        if upload_pdf(pdf_file):
            successful += 1
        else:
            failed.append(pdf_file.name)
        
        # Progress update every 5 files
        if i % 5 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining_count = len(remaining_files) - i
            eta = remaining_count / rate if rate > 0 else 0
            print(f"\n📊 Progress: {i}/{len(remaining_files)} files")
            print(f"⏱️  ETA: {int(eta/60)}m {int(eta%60)}s")
        
        # Delay between uploads (except for last one)
        if i < len(remaining_files):
            time.sleep(DELAY_BETWEEN_UPLOADS)
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎯 Upload Complete in {int(elapsed/60)}m {int(elapsed%60)}s")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print("\n⚠️  Failed uploads:")
        for name in failed[:10]:
            print(f"  - {name}")
        if len(failed) > 10:
            print(f"  ... and {len(failed)-10} more")
        print("\n💡 Tip: Run the script again to retry failed uploads")
    
    # Final verification
    print("\n🔍 Verifying final count...")
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            final_count = len(response.json()['documents'])
            print(f"📊 Total documents in system: {final_count}/115")
        else:
            print("❌ Could not verify final count")
    except Exception as e:
        print(f"❌ Error verifying: {e}")

if __name__ == "__main__":
    main()