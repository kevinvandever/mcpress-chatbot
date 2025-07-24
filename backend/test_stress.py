#!/usr/bin/env python3
"""
Stress test for batch upload - simulates the user's scenario
"""
import requests
import json
import time
import io
import tempfile

BASE_URL = "http://localhost:8000"

def create_simple_pdf(filename: str, content: str) -> bytes:
    """Create a minimal PDF with just text content"""
    # Simple PDF structure
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

5 0 obj
<<
/Length {len(content) + 50}
>>
stream
BT
/F1 12 Tf
100 700 Td
({content}) Tj
ET
endstream
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
0000000380 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
{450 + len(content)}
%%EOF"""
    
    return pdf_content.encode('latin-1')

def test_large_batch():
    """Test with a larger batch of PDFs to simulate user scenario"""
    print("🚀 Testing large batch upload (simulating 113 PDFs)...")
    
    # Create test data for multiple files
    num_files = 10  # Start with 10 for testing
    print(f"📄 Creating {num_files} test PDF files...")
    
    files = []
    for i in range(num_files):
        filename = f"test_book_{i+1:03d}.pdf"
        content = f"This is test book {i+1}. It contains sample content for testing the batch upload system. " * 5
        pdf_bytes = create_simple_pdf(filename, content)
        files.append(('files', (filename, pdf_bytes, 'application/pdf')))
        if (i + 1) % 25 == 0:
            print(f"   Created {i+1}/{num_files} files...")
    
    print(f"📤 Sending batch upload request for {len(files)} files...")
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/batch-upload", files=files, timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            batch_id = data['batch_id']
            print(f"✅ Batch upload started: {batch_id}")
            print(f"   Request took: {time.time() - start_time:.1f}s")
            
            # Monitor progress
            print("\n⏳ Monitoring progress...")
            last_progress = -1
            monitor_start = time.time()
            
            while True:
                try:
                    status_response = requests.get(f"{BASE_URL}/batch-upload/status/{batch_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        
                        if status['overall_progress'] != last_progress:
                            elapsed = time.time() - monitor_start
                            print(f"📊 Progress: {status['overall_progress']}% "
                                  f"({status['processed_files']}/{status['total_files']} files) "
                                  f"[{elapsed:.1f}s]")
                            last_progress = status['overall_progress']
                        
                        if status['status'] == 'completed':
                            total_time = time.time() - start_time
                            print(f"\n✅ Batch completed in {total_time:.1f}s!")
                            
                            summary = status.get('summary', {})
                            successful = summary.get('successful', 0)
                            failed = summary.get('failed', 0)
                            
                            print(f"📊 Results: {successful} successful, {failed} failed")
                            
                            if failed > 0:
                                print("\n❌ Failed files:")
                                for filename, file_status in status['files_status'].items():
                                    if file_status['status'] == 'error':
                                        print(f"   - {filename}: {file_status['message']}")
                            
                            return successful == num_files
                        
                        time.sleep(0.5)
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        return False
                        
                except requests.exceptions.Timeout:
                    print("⏰ Status check timeout, continuing...")
                    continue
                    
        else:
            print(f"❌ Batch upload failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout - this might indicate server overload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_memory_limits():
    """Test memory and size limits"""
    print("\n🧪 Testing size limits...")
    
    # Test large file
    large_content = "X" * (1024 * 1024)  # 1MB of content
    large_pdf = create_simple_pdf("large_test.pdf", large_content)
    
    files = [('files', ('large_test.pdf', large_pdf, 'application/pdf'))]
    
    try:
        response = requests.post(f"{BASE_URL}/batch-upload", files=files)
        print(f"   Large file test: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Large file test error: {e}")

if __name__ == "__main__":
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Server is running")
            
            # Test batch upload
            success = test_large_batch()
            
            if success:
                print("\n✅ All tests passed!")
                
                # Check final state
                docs = requests.get(f"{BASE_URL}/documents")
                if docs.status_code == 200:
                    data = docs.json()
                    print(f"✅ Final state: {data['total_documents']} documents in database")
                
                # Test memory limits
                test_memory_limits()
            else:
                print("\n❌ Batch upload test failed")
                
        else:
            print(f"❌ Server health check failed: {health.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the backend server first:")
        print("   cd backend && uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")