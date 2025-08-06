#!/usr/bin/env python3
"""
Simple, reliable upload script - one file at a time
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

# The exact 10 missing files
MISSING_FILES = [
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

def get_document_count():
    """Get current document count"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            return len(response.json()['documents'])
    except:
        pass
    return None

def upload_single_file(pdf_path):
    """Upload a single file using regular upload endpoint"""
    print(f"\n📤 Uploading: {pdf_path.name}")
    print(f"   File size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Get count before upload
    count_before = get_document_count()
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': (pdf_path.name, f, 'application/pdf')}
            print("   Sending request to batch-upload...")
            response = requests.post(f"{API_URL}/batch-upload", files=files, timeout=300)  # 5 min timeout
        
        print(f"   Response code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result.get('message', 'Uploaded')}")
            
            # Verify count increased
            time.sleep(3)  # Wait for processing
            count_after = get_document_count()
            if count_after and count_before and count_after > count_before:
                print(f"   ✅ Verified: Document count increased from {count_before} to {count_after}")
                return True
            else:
                print(f"   ⚠️  Warning: Document count didn't increase ({count_before} -> {count_after})")
                return False
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ Timeout after 2 minutes")
        # Check if it processed anyway
        time.sleep(5)
        count_after = get_document_count()
        if count_after and count_before and count_after > count_before:
            print(f"   ✅ Processed despite timeout: {count_before} -> {count_after}")
            return True
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    pdf_dir = Path(PDF_DIRECTORY)
    
    print("🎯 Simple Upload Script - Final 10 Files")
    print("=" * 50)
    
    # Check initial count
    initial_count = get_document_count()
    print(f"📊 Initial document count: {initial_count}/113")
    
    # Find files
    found_files = []
    missing_files = []
    
    for filename in MISSING_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            found_files.append(pdf_path)
            print(f"✓ Found: {filename}")
        else:
            missing_files.append(filename)
            print(f"✗ Missing: {filename}")
    
    if missing_files:
        print(f"\n⚠️  {len(missing_files)} files not found in uploads directory!")
        for f in missing_files:
            print(f"   - {f}")
    
    if not found_files:
        print("\nNo files found to upload!")
        return
    
    print(f"\n🚀 Ready to upload {len(found_files)} files")
    print("This will upload ONE file at a time to avoid timeouts.")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Upload files
    successful = 0
    failed = 0
    
    for i, pdf_path in enumerate(found_files, 1):
        print(f"\n[{i}/{len(found_files)}] Processing: {pdf_path.name}")
        
        if upload_single_file(pdf_path):
            successful += 1
        else:
            failed += 1
        
        # Wait between uploads
        if i < len(found_files):
            print("   Waiting 10 seconds before next upload...")
            time.sleep(10)
    
    # Final summary
    final_count = get_document_count()
    print(f"\n" + "=" * 50)
    print(f"📊 Results:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📚 Final count: {final_count}/113")
    print(f"   📈 Added: {final_count - initial_count if final_count and initial_count else '?'} documents")
    
    if final_count and final_count >= 113:
        print(f"\n🎉 SUCCESS! You have all 113 documents!")
    elif final_count:
        remaining = 113 - final_count
        print(f"\n📋 Still missing: {remaining} documents")

if __name__ == "__main__":
    main()