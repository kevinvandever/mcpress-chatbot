#!/usr/bin/env python3
"""
Test clean PDF processing with reduced log noise
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_clean_batch_upload():
    """Test batch upload with cleaner output"""
    print("🚀 Testing clean batch upload...")
    
    # Get a few PDFs to test with
    upload_dir = Path("./uploads")
    pdf_files = list(upload_dir.glob("*.pdf"))[:2]  # Test with 2 PDFs
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return
    
    print(f"📚 Testing with {len(pdf_files)} PDFs:")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    
    # Prepare files for upload
    files = []
    for pdf in pdf_files:
        files.append(('files', (pdf.name, open(pdf, 'rb'), 'application/pdf')))
    
    try:
        # Send batch upload request
        print("\n📤 Uploading and processing...")
        response = requests.post(f"{BASE_URL}/batch-upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            batch_id = data['batch_id']
            
            # Poll for status with less noise
            start_time = time.time()
            while True:
                status_response = requests.get(f"{BASE_URL}/batch-upload/status/{batch_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    if status['status'] == 'completed':
                        elapsed = time.time() - start_time
                        print(f"\n✅ Processing completed in {elapsed:.1f}s")
                        print(f"   Results: {status['summary']}")
                        
                        # Show processing stats
                        total_pages = sum(file_info.get('stats', {}).get('total_pages', 0) 
                                        for file_info in status['files_status'].values() 
                                        if file_info.get('stats'))
                        total_chunks = sum(file_info.get('stats', {}).get('chunks_created', 0) 
                                         for file_info in status['files_status'].values() 
                                         if file_info.get('stats'))
                        total_images = sum(file_info.get('stats', {}).get('images_processed', 0) 
                                         for file_info in status['files_status'].values() 
                                         if file_info.get('stats'))
                        total_code = sum(file_info.get('stats', {}).get('code_blocks_found', 0) 
                                       for file_info in status['files_status'].values() 
                                       if file_info.get('stats'))
                        
                        print(f"\n📊 Total processed:")
                        print(f"   📄 Pages: {total_pages}")
                        print(f"   📝 Chunks: {total_chunks}")
                        print(f"   🖼️  Images: {total_images}")
                        print(f"   💻 Code blocks: {total_code}")
                        break
                    
                    # Show progress without spamming
                    print(f"\r⏳ Processing... {status['overall_progress']}%", end='', flush=True)
                    time.sleep(2)
                else:
                    print(f"\n❌ Failed to get status: {status_response.status_code}")
                    break
        else:
            print(f"❌ Upload failed: {response.status_code}")
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
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Server is running")
            test_clean_batch_upload()
        else:
            print("❌ Server health check failed")
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start the backend server first:")
        print("   cd backend && uvicorn main:app --reload")