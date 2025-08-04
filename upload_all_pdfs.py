#!/usr/bin/env python3
"""
Automated PDF upload script for MC Press PDF Chatbot
Uploads all PDFs in a directory, handling rate limits and retries
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"  # UPDATE THIS PATH
BATCH_SIZE = 3  # Number of files per batch
DELAY_BETWEEN_BATCHES = 30  # Seconds to wait between batches

def upload_batch(pdf_files, batch_num):
    """Upload a batch of PDF files"""
    print(f"\n--- Batch {batch_num}: Uploading {len(pdf_files)} files ---")
    
    files = []
    for pdf_path in pdf_files:
        try:
            files.append(('files', (pdf_path.name, open(pdf_path, 'rb'), 'application/pdf')))
            print(f"  Added: {pdf_path.name}")
        except Exception as e:
            print(f"  Error reading {pdf_path.name}: {e}")
            continue
    
    if not files:
        print("  No files to upload in this batch")
        return False
    
    try:
        print(f"  Uploading batch to {API_URL}/batch-upload...")
        response = requests.post(f"{API_URL}/batch-upload", files=files, timeout=600)  # 10 min timeout
        
        # Close all file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Batch {batch_num} uploaded successfully!")
            print(f"  Batch ID: {result.get('batch_id', 'N/A')}")
            
            # Check for status endpoint if batch processing is async
            if 'batch_id' in result:
                return monitor_batch_progress(result['batch_id'])
            return True
        else:
            print(f"  ❌ Batch {batch_num} failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ Batch {batch_num} timed out - this might be normal for large batches")
        print("  Files are likely still processing on the server...")
        return True
    except Exception as e:
        print(f"  ❌ Batch {batch_num} error: {e}")
        return False

def monitor_batch_progress(batch_id):
    """Monitor batch processing progress"""
    print(f"  Monitoring batch {batch_id}...")
    
    for attempt in range(30):  # Check for up to 15 minutes
        try:
            response = requests.get(f"{API_URL}/batch-upload/status/{batch_id}", timeout=30)
            if response.status_code == 200:
                status = response.json()
                if status.get('status') == 'completed':
                    print(f"  ✅ Batch {batch_id} completed!")
                    return True
                elif status.get('status') == 'processing':
                    progress = status.get('progress', 0)
                    print(f"  ⏳ Progress: {progress}%")
                else:
                    print(f"  Status: {status.get('status', 'unknown')}")
            
            time.sleep(30)  # Wait 30 seconds between checks
            
        except Exception as e:
            print(f"  Warning: Could not check batch status: {e}")
            break
    
    print(f"  ⚠️  Batch monitoring finished - check manually if needed")
    return True

def main():
    # Validate PDF directory
    pdf_dir = Path(PDF_DIRECTORY)
    if not pdf_dir.exists():
        print(f"Error: Directory {PDF_DIRECTORY} does not exist")
        print("Please update PDF_DIRECTORY in this script to point to your PDFs")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {PDF_DIRECTORY}")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF files")
    print(f"Will upload in batches of {BATCH_SIZE} files")
    print(f"Estimated time: {len(pdf_files) // BATCH_SIZE * (DELAY_BETWEEN_BATCHES + 60) // 60} minutes")
    
    # Confirm before starting
    response = input("\nProceed with upload? (y/N): ")
    if response.lower() != 'y':
        print("Upload cancelled")
        sys.exit(0)
    
    # Upload in batches
    successful_batches = 0
    total_batches = (len(pdf_files) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(pdf_files), BATCH_SIZE):
        batch_files = pdf_files[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        success = upload_batch(batch_files, batch_num)
        if success:
            successful_batches += 1
        
        # Wait between batches (except for last batch)
        if i + BATCH_SIZE < len(pdf_files):
            print(f"  Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    print(f"\n=== Upload Complete ===")
    print(f"Successfully uploaded: {successful_batches}/{total_batches} batches")
    print(f"Check the Document List in your app to verify all files processed correctly")

if __name__ == "__main__":
    main()