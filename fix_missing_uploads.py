#!/usr/bin/env python3
"""
Fix the missing PDF uploads by providing author metadata
"""

import requests
import time
from pathlib import Path

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

# The 5 PDFs that need to be fixed with author information
MISSING_PDFS = [
    {
        "filename": "You Want to Do What with PHP.pdf",
        "author": "Matt Wade",  # You'll need to provide correct author
        "mc_press_url": ""
    },
    {
        "filename": "WebSphere Application Server- Step by Step.pdf", 
        "author": "Rama Turaga",  # You'll need to provide correct author
        "mc_press_url": ""
    },
    {
        "filename": "WDSC- Step by Step.pdf",
        "author": "Rama Turaga",  # You'll need to provide correct author
        "mc_press_url": ""
    },
    {
        "filename": "Understanding AS-400 System Operations.pdf",
        "author": "Mike Dawson and Marge Hohly",  # You'll need to provide correct author
        "mc_press_url": ""
    },
    {
        "filename": "The RPG Programmers Guide to RPG IV and ILE.pdf",
        "author": "Bryan Meyers",  # You'll need to provide correct author
        "mc_press_url": ""
    }
]

def complete_upload_with_metadata(filename, author, mc_press_url=""):
    """Complete the upload of a PDF that was missing author metadata"""
    
    print(f"\n📝 Completing upload for: {filename}")
    print(f"   Author: {author}")
    
    try:
        # First, re-upload the file to get it into temp storage
        pdf_path = f"./backend/uploads/{filename}"
        
        if not Path(pdf_path).exists():
            print(f"   ❌ File not found locally: {pdf_path}")
            return False
        
        # Upload the file
        print(f"   📤 Uploading file...")
        with open(pdf_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = requests.post(
                f"{API_URL}/upload",
                files=files,
                timeout=120
            )
        
        if response.status_code != 200:
            print(f"   ❌ Upload failed: {response.status_code}")
            return False
        
        result = response.json()
        
        # Check if it needs metadata
        if result.get('status') == 'needs_metadata':
            print(f"   ⏳ File needs metadata, completing upload...")
            
            # Complete the upload with metadata
            complete_data = {
                "filename": filename,
                "author": author,
                "mc_press_url": mc_press_url
            }
            
            response = requests.post(
                f"{API_URL}/complete-upload",
                json=complete_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {result.get('message', 'Success')}")
                return True
            else:
                print(f"   ❌ Complete upload failed: {response.text}")
                return False
                
        elif result.get('status') == 'success':
            print(f"   ✅ File uploaded successfully (author was extracted)")
            return True
        else:
            print(f"   ⚠️  Unexpected response: {result}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️ Request timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 Fix Missing PDF Uploads")
    print("=" * 60)
    print("\nThis script will re-upload the 5 missing PDFs with author metadata")
    
    # Check API health
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
        else:
            print("❌ API health check failed")
            return
    except:
        print("❌ Cannot reach API")
        return
    
    print(f"\n📚 Processing {len(MISSING_PDFS)} PDFs...")
    
    successful = 0
    failed = []
    
    for pdf_info in MISSING_PDFS:
        if complete_upload_with_metadata(
            pdf_info["filename"],
            pdf_info["author"],
            pdf_info["mc_press_url"]
        ):
            successful += 1
        else:
            failed.append(pdf_info["filename"])
        
        # Wait between uploads
        time.sleep(3)
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print("\n❌ Failed uploads:")
        for filename in failed:
            print(f"  - {filename}")

if __name__ == "__main__":
    main()