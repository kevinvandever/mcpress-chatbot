#!/usr/bin/env python3
"""
Test batch upload functionality
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_batch_upload():
    """Test batch upload endpoint"""
    print("🚀 Testing batch upload...")
    
    # Get existing PDFs in uploads directory
    upload_dir = Path("./uploads")
    pdf_files = list(upload_dir.glob("*.pdf"))[:3]  # Test with first 3 PDFs
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return
    
    print(f"📚 Found {len(pdf_files)} PDFs to test with:")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    
    # Prepare files for upload
    files = []
    for pdf in pdf_files:
        files.append(('files', (pdf.name, open(pdf, 'rb'), 'application/pdf')))
    
    try:
        # Send batch upload request
        print("\n📤 Sending batch upload request...")
        response = requests.post(f"{BASE_URL}/batch-upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            batch_id = data['batch_id']
            print(f"✅ Batch upload started: {batch_id}")
            print(f"   Status URL: {data['status_url']}")
            
            # Poll for status
            print("\n⏳ Monitoring progress...")
            while True:
                status_response = requests.get(f"{BASE_URL}/batch-upload/status/{batch_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    print(f"\r📊 Progress: {status['overall_progress']}% "
                          f"({status['processed_files']}/{status['total_files']} files)", 
                          end='', flush=True)
                    
                    if status['status'] == 'completed':
                        print("\n\n✅ Batch upload completed!")
                        print(f"   Summary: {status['summary']}")
                        
                        # Show file details
                        print("\n📋 File Details:")
                        for filename, file_status in status['files_status'].items():
                            print(f"\n   {filename}:")
                            print(f"     Status: {file_status['status']}")
                            if file_status['status'] == 'completed' and 'stats' in file_status:
                                stats = file_status['stats']
                                print(f"     Category: {stats['category']}")
                                print(f"     Pages: {stats['total_pages']}")
                                print(f"     Chunks: {stats['chunks_created']}")
                                print(f"     Images: {stats['images_processed']}")
                                print(f"     Code blocks: {stats['code_blocks_found']}")
                            elif file_status['status'] == 'error':
                                print(f"     Error: {file_status['message']}")
                        break
                    
                    time.sleep(1)
                else:
                    print(f"\n❌ Failed to get status: {status_response.status_code}")
                    break
        else:
            print(f"❌ Batch upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Close all file handles
        for _, file_tuple in files:
            file_tuple[1].close()

if __name__ == "__main__":
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is running")
            test_batch_upload()
        else:
            print("❌ Server health check failed")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the backend server first:")
        print("   cd backend && uvicorn main:app --reload")