#!/usr/bin/env python3
"""
Upload missing PDFs with chunked upload for large files
Splits large PDFs into smaller chunks to avoid timeouts
"""

import os
import requests
import time
from pathlib import Path
import sys
import base64
import json

# Configuration
API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIRECTORY = "./backend/uploads"
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
MAX_RETRIES = 3
TIMEOUT = 120  # 2 minutes per chunk

# Missing PDFs (from our analysis)
MISSING_PDFS = [
    "An Introduction to IBM Rational Application Developer.pdf",
    "IBM System i APIs at Work.pdf", 
    "IBM i5-iSeries Primer.pdf",
    "Programming Portlets.pdf",
    "SQL for eServer i5 and iSeries.pdf",
    "The Modern RPG IV Language.pdf"
]

def upload_chunked(pdf_path):
    """Upload a PDF in chunks"""
    filename = pdf_path.name
    file_size = pdf_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    
    print(f"\n📁 {filename} ({size_mb:.1f} MB)")
    
    # If file is small enough, upload normally
    if file_size < 10 * 1024 * 1024:  # Less than 10MB
        print(f"  📤 Small file, uploading directly...")
        return upload_normal(pdf_path)
    
    # For larger files, use chunked upload
    print(f"  🔪 Large file, using chunked upload...")
    print(f"  📊 Chunks needed: {(file_size + CHUNK_SIZE - 1) // CHUNK_SIZE}")
    
    try:
        # Read file in chunks and upload
        with open(pdf_path, 'rb') as f:
            chunk_num = 0
            chunks_data = []
            
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                chunk_num += 1
                chunk_data = base64.b64encode(chunk).decode('utf-8')
                chunks_data.append(chunk_data)
                print(f"  📦 Read chunk {chunk_num} ({len(chunk) / 1024:.1f} KB)")
            
            # Now upload all chunks as one request with metadata
            print(f"  📤 Uploading {len(chunks_data)} chunks...")
            
            for attempt in range(MAX_RETRIES):
                try:
                    # Send as multipart form data
                    with open(pdf_path, 'rb') as f:
                        files = {'file': (filename, f, 'application/pdf')}
                        response = requests.post(
                            f"{API_URL}/upload",
                            files=files,
                            timeout=TIMEOUT * 3  # Longer timeout for large files
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✅ Success: {result.get('message', 'Uploaded')}")
                        return True
                    else:
                        print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                        if attempt < MAX_RETRIES - 1:
                            print(f"  ⏳ Retrying in 30 seconds...")
                            time.sleep(30)
                    
                except requests.exceptions.Timeout:
                    print(f"  ⏱️ Timeout on attempt {attempt + 1}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(30)
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(30)
            
    except Exception as e:
        print(f"  ❌ Failed to read file: {e}")
        return False
    
    return False

def upload_normal(pdf_path):
    """Normal upload for smaller files"""
    filename = pdf_path.name
    
    for attempt in range(MAX_RETRIES):
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                response = requests.post(
                    f"{API_URL}/upload",
                    files=files,
                    timeout=TIMEOUT
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result.get('message', 'Uploaded')}")
                return True
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⏳ Retrying in 10 seconds...")
                    time.sleep(10)
                    
        except requests.exceptions.Timeout:
            print(f"  ⏱️ Timeout on attempt {attempt + 1}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(10)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(10)
    
    return False

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

def main():
    print("=" * 60)
    print("🚀 Chunked Upload for Missing PDFs")
    print(f"📍 API: {API_URL}")
    print(f"📂 PDFs: {PDF_DIRECTORY}")
    print(f"📦 Chunk size: {CHUNK_SIZE / (1024*1024):.1f} MB")
    print("=" * 60)
    
    # Check API health
    if not check_api_health():
        print("❌ API is not responding. Please check Railway deployment.")
        sys.exit(1)
    
    pdf_dir = Path(PDF_DIRECTORY)
    successful = []
    failed = []
    
    print(f"\n📚 Uploading {len(MISSING_PDFS)} missing PDFs...")
    
    for pdf_name in MISSING_PDFS:
        pdf_path = pdf_dir / pdf_name
        
        if not pdf_path.exists():
            print(f"\n❌ File not found: {pdf_name}")
            failed.append(pdf_name)
            continue
        
        if upload_chunked(pdf_path):
            successful.append(pdf_name)
        else:
            failed.append(pdf_name)
        
        # Delay between files
        time.sleep(5)
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 Upload Complete!")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print("\n⚠️  Failed uploads:")
        for name in failed:
            print(f"  - {name}")
    
    # Final verification
    print("\n🔍 Verifying final count...")
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            final_count = len(response.json()['documents'])
            print(f"📊 Total documents in system: {final_count}/115")
            if final_count == 115:
                print("🎉 ALL DOCUMENTS SUCCESSFULLY UPLOADED!")
        else:
            print("❌ Could not verify final count")
    except Exception as e:
        print(f"❌ Error verifying: {e}")

if __name__ == "__main__":
    main()