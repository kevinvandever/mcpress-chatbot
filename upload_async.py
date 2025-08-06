#!/usr/bin/env python3
"""
Async upload script that avoids timeouts by using background processing
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

# List of remaining files to upload
REMAINING_FILES = [
    "Fundamentals of Technology Project Management- First Edition.pdf",
    "IBM i5-iSeries Primer.pdf",
    "Advanced Java EE Development for Rational Application Developer 7.5.pdf",
    "The Modern RPG IV Language.pdf",
    "IBM System i APIs at Work.pdf",
    "You Want to Do What with PHP?.pdf",
    "DB2 10 for z-OS- The Smarter, Faster Way to Upgrade.pdf",
    "IBM DB2 for z-OS- The Database for Gaining a Competitive Advantage!.pdf",
    "An Introduction to IBM Rational Application Developer.pdf",
    "Programming Portlets.pdf"
]

def upload_file_async(pdf_path):
    """Upload a single file using async endpoint"""
    print(f"\n📤 Uploading: {pdf_path.name}")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/upload-async", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Upload accepted! Job ID: {job_id}")
            return job_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out - but file might still be processing")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_job_status(job_id):
    """Check the status of an upload job"""
    try:
        response = requests.get(f"{API_URL}/upload-status/{job_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def main():
    pdf_dir = Path(PDF_DIRECTORY)
    
    print("🚀 Async Upload Script - Avoids Timeouts!")
    print("=" * 50)
    print("This script uploads files in the background to prevent timeouts.")
    print(f"Will upload {len(REMAINING_FILES)} remaining files.\n")
    
    # Find the PDF files
    found_files = []
    for filename in REMAINING_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            found_files.append(pdf_path)
            print(f"✓ Found: {filename}")
        else:
            print(f"✗ Missing: {filename}")
    
    if not found_files:
        print("\nNo files found to upload!")
        return
    
    print(f"\nReady to upload {len(found_files)} files.")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Upload files one by one
    jobs = []
    for pdf_path in found_files:
        job_id = upload_file_async(pdf_path)
        if job_id:
            jobs.append((pdf_path.name, job_id))
        time.sleep(5)  # Small delay between uploads
    
    if not jobs:
        print("\nNo jobs were created successfully.")
        return
    
    # Monitor jobs
    print(f"\n📊 Monitoring {len(jobs)} upload jobs...")
    print("This may take a few minutes. The uploads are processing in the background.\n")
    
    completed = 0
    failed = 0
    timeout = 300  # 5 minutes total
    start_time = time.time()
    
    while jobs and (time.time() - start_time) < timeout:
        remaining_jobs = []
        
        for filename, job_id in jobs:
            status = check_job_status(job_id)
            if status:
                if status['status'] == 'completed':
                    print(f"✅ {filename} - Completed!")
                    completed += 1
                elif status['status'] == 'failed':
                    print(f"❌ {filename} - Failed: {status.get('message', 'Unknown error')}")
                    failed += 1
                else:
                    remaining_jobs.append((filename, job_id))
            else:
                remaining_jobs.append((filename, job_id))
        
        jobs = remaining_jobs
        
        if jobs:
            print(f"⏳ Still processing: {len(jobs)} files...")
            time.sleep(10)
    
    print(f"\n=== Summary ===")
    print(f"✅ Completed: {completed}")
    print(f"❌ Failed: {failed}")
    print(f"⏳ Still processing: {len(jobs)}")
    
    # Check final document count
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            total = len(response.json()['documents'])
            print(f"\n📚 Total documents in system: {total}/113")
    except:
        pass

if __name__ == "__main__":
    main()