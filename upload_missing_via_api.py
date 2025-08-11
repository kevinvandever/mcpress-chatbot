#!/usr/bin/env python3
"""
Upload missing documents via the backend API
"""

import requests
import os
from pathlib import Path
import time

def upload_missing_documents():
    """Upload the 5 missing documents via API"""
    
    missing_files = [
        'Advanced Java EE Development for Rational Application Developer 7.5.pdf',
        'An Introduction to IBM Rational Application Developer.pdf', 
        'IBM System i APIs at Work.pdf',
        'Programming Portlets.pdf',
        'The Modern RPG IV Language.pdf'
    ]
    
    uploads_dir = Path("backend/uploads")
    api_url = "http://localhost:8000"
    
    print("🔄 Uploading missing documents via API...")
    
    successful = 0
    failed = 0
    
    for filename in missing_files:
        pdf_path = uploads_dir / filename
        if not pdf_path.exists():
            print(f"❌ File not found: {filename}")
            failed += 1
            continue
            
        print(f"\n📤 Uploading: {filename}")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                
                response = requests.post(
                    f"{api_url}/upload",
                    files=files,
                    timeout=300  # 5 minute timeout per file
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('status') == 'needs_metadata':
                        print(f"  ⚠️ Needs metadata, completing upload...")
                        # Complete upload with Unknown author
                        complete_response = requests.post(
                            f"{api_url}/complete-upload",
                            json={
                                "filename": filename,
                                "author": "Unknown Author"
                            },
                            timeout=60
                        )
                        
                        if complete_response.status_code == 200:
                            print(f"  ✅ Upload completed successfully!")
                            successful += 1
                        else:
                            print(f"  ❌ Failed to complete upload: {complete_response.text}")
                            failed += 1
                    else:
                        print(f"  ✅ Upload successful!")
                        successful += 1
                        
                else:
                    print(f"  ❌ Upload failed: {response.status_code} - {response.text}")
                    failed += 1
                    
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1
        
        # Small delay between uploads
        time.sleep(1)

    print(f"\n🎉 Upload Complete!")
    print(f"✅ Successfully uploaded: {successful}")
    print(f"❌ Failed: {failed}")
    
    # Check final count
    try:
        response = requests.get(f"{api_url}/documents")
        if response.status_code == 200:
            doc_count = len(response.json()['documents'])
            print(f"📊 Total documents now: {doc_count}/115")
        else:
            print("❌ Could not verify document count")
    except Exception as e:
        print(f"❌ Error checking count: {e}")

if __name__ == "__main__":
    upload_missing_documents()