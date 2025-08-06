#!/usr/bin/env python3
"""
Upload the final 6 files with correct filenames and better handling for large files
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

# The 6 remaining files with CORRECT filenames (no ? or ! in filesystem)
REMAINING_FILES = [
    ("Advanced Java EE Development for Rational Application Developer 7.5.pdf", 64.3),
    ("IBM System i APIs at Work.pdf", 17.4),
    ("You Want to Do What with PHP.pdf", 2.3),  # No ? in filename
    ("IBM DB2 for z-OS- The Database for Gaining a Competitive Advantage!.pdf", 3.9),  # Keep ! here
    ("An Introduction to IBM Rational Application Developer.pdf", 30.9),
    ("Programming Portlets.pdf", 13.0)
]

def get_document_count():
    """Get current document count"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            return len(response.json()['documents'])
    except:
        pass
    return None

def upload_with_retries(pdf_path, max_retries=3):
    """Upload a file with retry logic for large files"""
    filename = pdf_path.name
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    
    print(f"\n📤 Processing: {filename}")
    print(f"   File size: {size_mb:.1f} MB")
    
    for attempt in range(max_retries):
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                print(f"   Attempt {attempt + 1}: Uploading...")
                
                # Longer timeout for large files
                timeout = min(300, int(60 + size_mb * 2))  # 60s base + 2s per MB, max 5 min
                
                response = requests.post(f"{API_URL}/upload", files=files, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if it needs metadata
                if result.get('status') == 'needs_metadata':
                    print("   📝 Upload succeeded, completing with metadata...")
                    
                    # Complete with author metadata
                    time.sleep(2)
                    complete_data = {
                        "filename": filename,
                        "author": "MC Press",
                        "mc_press_url": None
                    }
                    
                    complete_response = requests.post(
                        f"{API_URL}/complete-upload", 
                        json=complete_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=60
                    )
                    
                    if complete_response.status_code == 200:
                        print("   ✅ Successfully completed!")
                        return True
                    else:
                        print(f"   ❌ Complete failed: {complete_response.status_code}")
                        if attempt < max_retries - 1:
                            print(f"   Retrying in 10 seconds...")
                            time.sleep(10)
                        continue
                else:
                    print("   ✅ Upload completed directly!")
                    return True
            else:
                print(f"   ❌ Upload failed: {response.status_code}")
                if attempt < max_retries - 1:
                    print(f"   Retrying in 10 seconds...")
                    time.sleep(10)
                    
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout after {timeout} seconds")
            if attempt < max_retries - 1:
                print(f"   Retrying with longer timeout...")
                time.sleep(10)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            if attempt < max_retries - 1:
                print(f"   Retrying in 10 seconds...")
                time.sleep(10)
    
    return False

def main():
    pdf_dir = Path(PDF_DIRECTORY)
    
    print("🚀 Final 6 Files Upload Script")
    print("="*50)
    print("With retry logic for large files and correct filenames")
    
    # Check initial count
    initial_count = get_document_count()
    print(f"📊 Current document count: {initial_count}/113")
    
    # Prepare files
    files_to_upload = []
    for filename, expected_size in REMAINING_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            actual_size = pdf_path.stat().st_size / 1024 / 1024
            files_to_upload.append(pdf_path)
            print(f"✓ Found: {filename} ({actual_size:.1f} MB)")
        else:
            print(f"✗ Missing: {filename}")
    
    if not files_to_upload:
        print("\nNo files found!")
        return
    
    print(f"\n🎯 Ready to upload {len(files_to_upload)} files")
    print("Note: Large files may take several minutes each")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Upload files (smallest first to build confidence)
    files_to_upload.sort(key=lambda p: p.stat().st_size)
    
    successful = 0
    for i, pdf_path in enumerate(files_to_upload, 1):
        print(f"\n[{i}/{len(files_to_upload)}]")
        
        count_before = get_document_count()
        
        if upload_with_retries(pdf_path):
            successful += 1
            
            # Verify
            time.sleep(3)
            count_after = get_document_count()
            if count_after and count_before and count_after > count_before:
                print(f"   ✅ Verified: Count increased to {count_after}")
            else:
                print(f"   ⚠️  Warning: Count verification pending")
        
        # Wait between files
        if i < len(files_to_upload):
            print("   Waiting 10 seconds before next file...")
            time.sleep(10)
    
    # Summary
    final_count = get_document_count()
    print(f"\n" + "="*50)
    print(f"📊 Final Results:")
    print(f"   ✅ Successful: {successful}/{len(files_to_upload)}")
    print(f"   📚 Final count: {final_count}/113")
    
    if final_count == 113:
        print(f"\n🎉 SUCCESS! You have all 113 documents!")
        print("🎊 Your MC Press PDF library is complete!")
    else:
        remaining = 113 - final_count
        print(f"\n📋 Still need: {remaining} documents")
        print("\nFor the remaining large files, you may need to:")
        print("1. Try uploading through the UI one at a time")
        print("2. Contact Railway support about upload limits")
        print("3. Consider splitting large PDFs into smaller parts")

if __name__ == "__main__":
    main()