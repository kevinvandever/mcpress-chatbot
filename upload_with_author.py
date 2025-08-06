#!/usr/bin/env python3
"""
Upload PDFs with author metadata to avoid the 'needs_metadata' issue
"""

import os
import requests
import time
from pathlib import Path
import sys

# Configuration
API_URL = "https://mcpress-chatbot-production.up.railway.app"
PDF_DIRECTORY = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

# The 7 remaining files
REMAINING_FILES = [
    "Advanced Java EE Development for Rational Application Developer 7.5.pdf",
    "The Modern RPG IV Language.pdf",
    "IBM System i APIs at Work.pdf",
    "You Want to Do What with PHP?.pdf",
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

def upload_and_complete(pdf_path):
    """Upload a file and immediately complete it with author metadata"""
    print(f"\n📤 Processing: {pdf_path.name}")
    print(f"   File size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Step 1: Upload the file
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            print("   Step 1: Uploading file...")
            response = requests.post(f"{API_URL}/upload", files=files, timeout=60)
        
        if response.status_code != 200:
            print(f"   ❌ Upload failed: {response.status_code}")
            return False
            
        result = response.json()
        
        # Check if it needs metadata
        if result.get('status') == 'needs_metadata':
            print("   📝 Upload succeeded, needs author metadata...")
            
            # Step 2: Complete with author metadata
            time.sleep(2)  # Small delay
            complete_data = {
                "filename": pdf_path.name,
                "author": "MC Press",  # Default author
                "mc_press_url": None
            }
            
            print("   Step 2: Completing with author metadata...")
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
                print(f"   Response: {complete_response.text[:200]}")
                return False
        else:
            # It processed without needing metadata
            print("   ✅ Upload completed directly!")
            return True
            
    except requests.exceptions.Timeout:
        print("   ⏰ Request timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    pdf_dir = Path(PDF_DIRECTORY)
    
    print("🚀 Upload with Author Metadata Script")
    print("="*50)
    print("This script uploads files and immediately provides author metadata")
    
    # Check initial count
    initial_count = get_document_count()
    print(f"📊 Current document count: {initial_count}/113")
    print(f"📋 Need to upload: {113 - initial_count} files")
    
    # Find files
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
    
    print(f"\n🎯 Ready to upload {len(found_files)} files")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Process files
    successful = 0
    for i, pdf_path in enumerate(found_files, 1):
        print(f"\n[{i}/{len(found_files)}]")
        
        # Check count before
        count_before = get_document_count()
        
        # Upload and complete
        if upload_and_complete(pdf_path):
            successful += 1
            
            # Verify count increased
            time.sleep(3)
            count_after = get_document_count()
            if count_after and count_before and count_after > count_before:
                print(f"   ✅ Verified: Count increased from {count_before} to {count_after}")
            else:
                print(f"   ⚠️  Warning: Count didn't increase")
        
        # Wait between files
        if i < len(found_files):
            print("   Waiting 5 seconds...")
            time.sleep(5)
    
    # Final summary
    final_count = get_document_count()
    print(f"\n" + "="*50)
    print(f"📊 Final Results:")
    print(f"   ✅ Successful: {successful}/{len(found_files)}")
    print(f"   📚 Final count: {final_count}/113")
    
    if final_count and initial_count:
        added = final_count - initial_count
        print(f"   📈 Total added: {added} documents")
    
    if final_count == 113:
        print(f"\n🎉 SUCCESS! You have all 113 documents!")
    elif final_count:
        remaining = 113 - final_count
        print(f"\n📋 Still need: {remaining} more documents")

if __name__ == "__main__":
    main()