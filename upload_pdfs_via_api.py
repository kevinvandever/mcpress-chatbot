#!/usr/bin/env python3
"""
Upload PDFs through the Railway API endpoint instead of direct database connection
This avoids Supabase connection timeout issues
"""
import os
import sys
import requests
import time
from pathlib import Path

# Configuration
API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIR = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"
CURRENT_DOC = "Advanced, Integrated RPG.pdf"

def upload_pdf_via_api(pdf_path):
    """Upload a single PDF through the API"""
    pdf_name = Path(pdf_path).name
    
    print(f"📄 Uploading: {pdf_name}")
    
    try:
        # Read the PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_name, f, 'application/pdf')}
            
            # Send to upload endpoint
            response = requests.post(
                f"{API_URL}/upload",
                files=files,
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success: {data.get('chunks_created', 0)} chunks created")
                return True
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text[:100]}")
                return False
                
    except requests.exceptions.Timeout:
        print(f"   ⚠️  Timeout - file may be too large or processing taking too long")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_current_status():
    """Check how many documents are currently in the system"""
    uploaded_files = []
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            print(f"📊 Current status: {len(docs)} documents in system")
            for doc in docs:
                print(f"   - {doc['filename']}: {doc['chunk_count']} chunks")
                uploaded_files.append(doc['filename'])
            return uploaded_files
    except Exception as e:
        print(f"❌ Could not check status: {e}")
    return uploaded_files

def main():
    print("🚀 PDF Upload Script for Railway API")
    print("=" * 50)
    
    # Check current status
    uploaded_files = check_current_status()
    
    # Get list of PDFs to upload
    all_pdfs = sorted([f for f in Path(PDF_DIR).glob("*.pdf")])
    
    # Filter out already uploaded
    pdfs_to_upload = []
    for pdf_path in all_pdfs:
        if pdf_path.name not in uploaded_files:  # Skip already uploaded files
            pdfs_to_upload.append(pdf_path)
    
    print(f"\n📚 Found {len(all_pdfs)} total PDFs")
    print(f"📋 Need to upload: {len(pdfs_to_upload)} PDFs")
    
    if not pdfs_to_upload:
        print("✅ All PDFs already uploaded!")
        return
    
    # Show first 5 to upload
    print("\nFirst 5 PDFs to upload:")
    for i, pdf in enumerate(pdfs_to_upload[:5]):
        print(f"  {i+1}. {pdf.name}")
    
    # Auto-proceed with upload
    print("\n✅ Auto-proceeding with upload...")
    
    # Upload PDFs one by one
    successful = 0
    failed = []
    
    print(f"\n🔄 Starting upload of {len(pdfs_to_upload)} PDFs...")
    print("This will take some time. Each PDF needs to be processed.\n")
    
    for i, pdf_path in enumerate(pdfs_to_upload):
        print(f"Progress: {i+1}/{len(pdfs_to_upload)} ({(i/len(pdfs_to_upload)*100):.1f}%)")
        
        success = upload_pdf_via_api(pdf_path)
        if success:
            successful += 1
        else:
            failed.append(pdf_path.name)
        
        # Small delay between uploads to avoid overwhelming the server
        if i < len(pdfs_to_upload) - 1:  # Don't wait after last one
            time.sleep(2)
        
        # Check status every 10 uploads
        if (i + 1) % 10 == 0:
            print(f"\n📊 Progress check:")
            check_current_status()
            print()
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 Upload Complete!")
    print(f"   ✅ Successful: {successful}/{len(pdfs_to_upload)}")
    print(f"   ❌ Failed: {len(failed)}")
    
    if failed:
        print("\n❌ Failed uploads:")
        for name in failed[:10]:  # Show first 10
            print(f"   - {name}")
        if len(failed) > 10:
            print(f"   ... and {len(failed) - 10} more")
    
    # Final status check
    print("\n📊 Final status:")
    check_current_status()

if __name__ == "__main__":
    main()