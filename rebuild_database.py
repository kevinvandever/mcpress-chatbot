#!/usr/bin/env python3
"""
Rebuild the ChromaDB database by batch uploading all PDF files
"""
import requests
import os
from pathlib import Path
import time

def batch_upload_pdfs():
    """Upload all PDFs to rebuild the database"""
    
    print("🔄 Starting database rebuild...")
    
    # Find all PDFs
    uploads_dir = Path("./backend/uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads folder")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files to upload")
    
    # Prepare files for batch upload
    files = []
    for pdf_path in pdf_files:
        files.append(('files', (pdf_path.name, open(pdf_path, 'rb'), 'application/pdf')))
    
    try:
        # Send batch upload request
        print("📤 Sending batch upload request...")
        response = requests.post('http://localhost:8000/batch-upload', files=files)
        
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 200:
            batch_data = response.json()
            batch_id = batch_data['batch_id']
            print(f"✅ Batch upload started: {batch_id}")
            
            # Monitor progress
            while True:
                time.sleep(5)
                status_response = requests.get(f'http://localhost:8000/batch-upload/status/{batch_id}')
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    processed = status_data['processed_files']
                    total = status_data['total_files']
                    progress = status_data['overall_progress']
                    
                    print(f"📊 Progress: {processed}/{total} files processed ({progress}%)")
                    
                    if status_data['status'] == 'completed':
                        print("🎉 Batch upload completed!")
                        
                        # Show summary
                        if 'summary' in status_data:
                            summary = status_data['summary']
                            print(f"✅ Successful: {summary['successful']}")
                            print(f"❌ Failed: {summary['failed']}")
                        break
                else:
                    print(f"❌ Error checking status: {status_response.status_code}")
                    break
        else:
            print(f"❌ Batch upload failed: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Error during batch upload: {e}")
    
    print("\n✨ Database rebuild complete!")

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE REBUILD SCRIPT")
    print("This will upload all 115 PDFs to rebuild the vector database")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
            batch_upload_pdfs()
        else:
            print("❌ Backend server is not responding correctly")
    except Exception as e:
        print(f"❌ Cannot connect to backend server: {e}")
        print("Make sure the backend is running on http://localhost:8000")