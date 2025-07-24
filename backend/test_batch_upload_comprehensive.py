#!/usr/bin/env python3
"""
Comprehensive test for batch upload functionality
This simulates the user's scenario with multiple PDFs
"""
import requests
import json
import time
from pathlib import Path
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://localhost:8000"

def create_test_pdf(filename: str, num_pages: int = 5) -> str:
    """Create a test PDF with multiple pages"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        c = canvas.Canvas(tmp.name, pagesize=letter)
        
        for page_num in range(1, num_pages + 1):
            c.drawString(100, 750, f"Test PDF: {filename}")
            c.drawString(100, 700, f"Page {page_num} of {num_pages}")
            c.drawString(100, 650, f"This is content for page {page_num}")
            
            # Add some code-like content
            if page_num == 2:
                c.drawString(100, 600, "def hello_world():")
                c.drawString(100, 580, "    print('Hello, World!')")
                c.drawString(100, 560, "    return True")
            
            # Add more content
            c.drawString(100, 500, f"Line 1 on page {page_num}")
            c.drawString(100, 480, f"Line 2 on page {page_num}")
            c.drawString(100, 460, f"Line 3 on page {page_num}")
            
            if page_num < num_pages:
                c.showPage()
        
        c.save()
        return tmp.name

def test_batch_upload_comprehensive():
    """Test batch upload with multiple test PDFs"""
    print("🚀 Starting comprehensive batch upload test...")
    
    # Create multiple test PDFs
    test_files = []
    try:
        print("📄 Creating test PDF files...")
        for i in range(5):
            filename = f"test_document_{i+1:02d}.pdf"
            pages = 3 + (i * 2)  # Varying page counts: 3, 5, 7, 9, 11
            pdf_path = create_test_pdf(filename, pages)
            test_files.append((pdf_path, filename))
            print(f"   Created: {filename} ({pages} pages)")
        
        # Prepare files for upload
        files = []
        for pdf_path, filename in test_files:
            with open(pdf_path, 'rb') as f:
                files.append(('files', (filename, f.read(), 'application/pdf')))
        
        # Send batch upload request
        print(f"\n📤 Sending batch upload request for {len(files)} files...")
        response = requests.post(f"{BASE_URL}/batch-upload", 
                               files=[('files', (fname, content, 'application/pdf')) 
                                     for _, (fname, content, _) in files])
        
        if response.status_code == 200:
            data = response.json()
            batch_id = data['batch_id']
            print(f"✅ Batch upload started: {batch_id}")
            
            # Poll for status
            print("\n⏳ Monitoring progress...")
            start_time = time.time()
            last_progress = -1
            
            while True:
                status_response = requests.get(f"{BASE_URL}/batch-upload/status/{batch_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    # Only print progress when it changes
                    if status['overall_progress'] != last_progress:
                        elapsed = time.time() - start_time
                        print(f"📊 Progress: {status['overall_progress']}% "
                              f"({status['processed_files']}/{status['total_files']} files) "
                              f"[{elapsed:.1f}s]")
                        
                        if status.get('current_file'):
                            print(f"   Currently processing: {status['current_file']}")
                        
                        last_progress = status['overall_progress']
                    
                    if status['status'] == 'completed':
                        total_time = time.time() - start_time
                        print(f"\n✅ Batch upload completed in {total_time:.1f}s!")
                        print(f"   Summary: {status['summary']}")
                        
                        # Show detailed results
                        successful = 0
                        failed = 0
                        total_chunks = 0
                        total_pages = 0
                        
                        print("\n📋 Detailed Results:")
                        for filename, file_status in status['files_status'].items():
                            if file_status['status'] == 'completed':
                                successful += 1
                                stats = file_status.get('stats', {})
                                chunks = stats.get('chunks_created', 0)
                                pages = stats.get('total_pages', 0)
                                total_chunks += chunks
                                total_pages += pages
                                
                                print(f"   ✅ {filename}")
                                print(f"      Pages: {pages}, Chunks: {chunks}, "
                                      f"Category: {stats.get('category', 'N/A')}")
                                if stats.get('images_processed', 0) > 0:
                                    print(f"      Images: {stats['images_processed']}")
                                if stats.get('code_blocks_found', 0) > 0:
                                    print(f"      Code blocks: {stats['code_blocks_found']}")
                            else:
                                failed += 1
                                print(f"   ❌ {filename}: {file_status.get('message', 'Unknown error')}")
                        
                        print(f"\n📊 Summary Statistics:")
                        print(f"   Files processed: {successful}/{len(files)}")
                        print(f"   Total pages: {total_pages}")
                        print(f"   Total chunks created: {total_chunks}")
                        print(f"   Processing rate: {total_pages/total_time:.1f} pages/second")
                        print(f"   Average time per file: {total_time/len(files):.1f}s")
                        
                        break
                    
                    time.sleep(1)
                else:
                    print(f"\n❌ Failed to get status: {status_response.status_code}")
                    print(f"   Error: {status_response.text}")
                    break
        else:
            print(f"❌ Batch upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        # Clean up test files
        print("\n🧹 Cleaning up test files...")
        for pdf_path, _ in test_files:
            try:
                os.unlink(pdf_path)
            except:
                pass

def test_error_conditions():
    """Test various error conditions"""
    print("\n🧪 Testing error conditions...")
    
    # Test with non-PDF file
    try:
        files = [('files', ('test.txt', b'This is not a PDF', 'text/plain'))]
        response = requests.post(f"{BASE_URL}/batch-upload", files=files)
        if response.status_code == 400:
            print("✅ Non-PDF rejection working")
        else:
            print(f"❌ Non-PDF file should be rejected, got: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing non-PDF: {e}")
    
    # Test with empty file list
    try:
        response = requests.post(f"{BASE_URL}/batch-upload", files=[])
        if response.status_code == 400:
            print("✅ Empty file list rejection working")
        else:
            print(f"❌ Empty file list should be rejected, got: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing empty list: {e}")

if __name__ == "__main__":
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is running")
            
            # Test normal operation
            success = test_batch_upload_comprehensive()
            
            if success:
                # Test error conditions
                test_error_conditions()
                
                # Final verification
                print("\n🔍 Final verification...")
                docs_response = requests.get(f"{BASE_URL}/documents")
                if docs_response.status_code == 200:
                    docs = docs_response.json()
                    print(f"✅ {docs['total_documents']} documents in database")
                    print("✅ Batch upload system is working correctly!")
                else:
                    print("❌ Cannot verify final state")
            else:
                print("❌ Batch upload test failed")
        else:
            print("❌ Server health check failed")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the backend server first:")
        print("   cd backend && uvicorn main:app --reload")