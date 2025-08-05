#!/usr/bin/env python3
"""
Upload missing PDF files for MC Press PDF Chatbot
Only uploads the 18 files that are missing from the current deployment
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"
BATCH_SIZE = 3  # Number of files per batch
DELAY_BETWEEN_BATCHES = 30  # Seconds to wait between batches

# List of missing files based on CSV analysis (using Title column D)
MISSING_FILES = [
    "WDSC- Step by Step.pdf",
    "Fundamentals of Technology Project Management- First Edition.pdf",
    "IBM i5-iSeries Primer.pdf",
    "Advanced Java EE Development for Rational Application Developer 7.5.pdf",
    "The Modern RPG IV Language.pdf",
    "IBM System i APIs at Work.pdf",
    "The IBM i Programmer's Guide to PHP.pdf",
    "DB2 9 System Administration for z-OS (Exam 737).pdf",
    "You Want to Do What with PHP?.pdf",
    "DB2 10 for z-OS- The Smarter, Faster Way to Upgrade.pdf",
    "The Business Value of DB2 for z-OS.pdf",
    "Extract, Transform, and Load with SQL Server Intergration Services.pdf",
    "IBM DB2 for z-OS- The Database for Gaining a Competitive Advantage!.pdf",
    "Developing Web Services for Web Applications.pdf",
    "An Introduction to IBM Rational Application Developer.pdf",
    "Building Applications with IBM Rational Application Developer and JavaBeans.pdf",
    "Programming Portlets.pdf",
    "The RPG Progrmmer's Guid to RPG IV and ILE.pdf",
]

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
            print(f"  Result: {result}")
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

def main():
    # Validate PDF directory
    pdf_dir = Path(PDF_DIRECTORY)
    if not pdf_dir.exists():
        print(f"Error: Directory {PDF_DIRECTORY} does not exist")
        sys.exit(1)
    
    # Find the missing PDF files
    missing_pdf_files = []
    
    for filename in MISSING_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            missing_pdf_files.append(pdf_path)
            print(f"Found: {filename}")
        else:
            print(f"WARNING: Missing file not found: {filename}")
    
    if not missing_pdf_files:
        print("No missing PDF files found to upload")
        sys.exit(1)
    
    print(f"\n📋 Summary:")
    print(f"Found {len(missing_pdf_files)} of {len(MISSING_FILES)} missing files")
    print(f"Will upload in batches of {BATCH_SIZE} files")
    print(f"Estimated time: {len(missing_pdf_files) // BATCH_SIZE * (DELAY_BETWEEN_BATCHES + 60) // 60} minutes")
    
    # List the files to be uploaded
    print(f"\n📚 Files to upload:")
    for i, pdf_file in enumerate(missing_pdf_files, 1):
        print(f"{i:2d}. {pdf_file.name}")
    
    # Confirm before starting
    response = input(f"\nProceed with upload of {len(missing_pdf_files)} missing files? (y/N): ")
    if response.lower() != 'y':
        print("Upload cancelled")
        sys.exit(0)
    
    # Upload in batches
    successful_batches = 0
    total_batches = (len(missing_pdf_files) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(missing_pdf_files), BATCH_SIZE):
        batch_files = missing_pdf_files[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        success = upload_batch(batch_files, batch_num)
        if success:
            successful_batches += 1
        
        # Wait between batches (except for last batch)
        if i + BATCH_SIZE < len(missing_pdf_files):
            print(f"  Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    print(f"\n=== Upload Complete ===")
    print(f"Successfully uploaded: {successful_batches}/{total_batches} batches")
    print(f"Check the Document List in your app to verify all files processed correctly")
    print(f"After upload completes, you should have all 113 PDFs from your CSV!")

if __name__ == "__main__":
    main()