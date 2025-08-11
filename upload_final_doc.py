#!/usr/bin/env python3
"""
Upload the final 64MB document with extended timeout
"""

import requests
import os
from pathlib import Path
import time

def upload_final_document():
    """Upload the final large document with extended timeout"""
    
    filename = 'Advanced Java EE Development for Rational Application Developer 7.5.pdf'
    uploads_dir = Path("backend/uploads")
    api_url = "http://localhost:8000"
    
    pdf_path = uploads_dir / filename
    if not pdf_path.exists():
        print(f"❌ File not found: {filename}")
        return False
        
    print(f"📤 Uploading final document: {filename}")
    print(f"📊 File size: {pdf_path.stat().st_size / (1024*1024):.1f} MB")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            
            print("⏳ Starting upload with 15-minute timeout...")
            response = requests.post(
                f"{api_url}/upload",
                files=files,
                timeout=900  # 15 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload response: {result}")
                
                if result.get('status') == 'needs_metadata':
                    print(f"⚠️ Needs metadata, completing upload...")
                    # Complete upload with Unknown author
                    complete_response = requests.post(
                        f"{api_url}/complete-upload",
                        json={
                            "filename": filename,
                            "author": "Unknown Author"
                        },
                        timeout=900  # 15 minute timeout
                    )
                    
                    if complete_response.status_code == 200:
                        print(f"✅ Upload completed successfully!")
                        return True
                    else:
                        print(f"❌ Failed to complete upload: {complete_response.status_code} - {complete_response.text}")
                        return False
                else:
                    print(f"✅ Upload successful without metadata step!")
                    return True
                    
            else:
                print(f"❌ Upload failed: {response.status_code} - {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("⏰ Upload timed out after 15 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_final_count():
    """Check if we now have 115 documents"""
    try:
        response = requests.get("http://localhost:8000/documents", timeout=10)
        if response.status_code == 200:
            doc_count = len(response.json()['documents'])
            print(f"📊 Final document count: {doc_count}/115")
            return doc_count == 115
        else:
            print("❌ Could not verify document count")
            return False
    except Exception as e:
        print(f"❌ Error checking count: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Attempting to upload final document to reach 115/115...")
    
    success = upload_final_document()
    
    if success:
        print("\n⏳ Waiting a moment for processing to complete...")
        time.sleep(5)
        
        if check_final_count():
            print("\n🎉 SUCCESS! All 115 documents now loaded!")
        else:
            print("\n⚠️ Upload completed but count verification failed")
    else:
        print("\n❌ Failed to upload final document")