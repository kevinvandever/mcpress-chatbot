#!/usr/bin/env python3
"""
Upload the 3 files that failed in batch 3
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

# The 3 files that failed in batch 3
FAILED_FILES = [
    "The IBM i Programmer's Guide to PHP.pdf",
    "DB2 9 System Administration for z-OS (Exam 737).pdf", 
    "You Want to Do What with PHP?.pdf"
]

def upload_single_file(pdf_path):
    """Upload a single PDF file"""
    print(f"\nUploading: {pdf_path.name}")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/batch-upload", files=files, timeout=300)
        
        if response.status_code == 200:
            print(f"  ✅ Successfully uploaded: {pdf_path.name}")
            return True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ Timed out - file might still be processing")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    pdf_dir = Path(PDF_DIRECTORY)
    
    print("Uploading 3 failed files one at a time...")
    print("This approach is slower but more reliable for problematic files.\n")
    
    successful = 0
    for filename in FAILED_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            if upload_single_file(pdf_path):
                successful += 1
            # Wait between uploads to avoid overwhelming the server
            time.sleep(30)
        else:
            print(f"WARNING: File not found: {filename}")
    
    print(f"\n=== Upload Complete ===")
    print(f"Successfully uploaded: {successful}/{len(FAILED_FILES)} files")
    
    # Check final count
    time.sleep(5)
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total = len(data.get('documents', []))
            print(f"\nTotal documents now: {total}/113")
            if total >= 110:
                print("🎉 You're very close to having all 113 documents!")
    except:
        pass

if __name__ == "__main__":
    main()