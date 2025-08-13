#!/usr/bin/env python3
"""
Test uploading a small batch of 3 PDFs via Railway API
"""
import requests
import time

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

# Test with 3 smaller PDFs
test_pdfs = [
    "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads/HTML for the Business Developer.pdf",
    "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads/JavaScript for the Business Developer.pdf", 
    "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads/Leadership in My Rearview Mirror.pdf"
]

def upload_single_pdf(pdf_path):
    """Upload a single PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_URL}/upload", files=files, timeout=120)
            return response.status_code == 200
    except Exception as e:
        print(f"Error uploading {pdf_path}: {e}")
        return False

def main():
    print("🧪 Testing manual upload of 3 PDFs...")
    
    # Check starting count
    response = requests.get(f"{API_URL}/documents")
    if response.status_code == 200:
        start_count = len(response.json()['documents'])
        print(f"📊 Starting with {start_count} documents")
    
    # Upload test PDFs
    for i, pdf_path in enumerate(test_pdfs, 1):
        pdf_name = pdf_path.split('/')[-1]
        print(f"\n[{i}/3] Uploading {pdf_name}...")
        
        success = upload_single_pdf(pdf_path)
        if success:
            print(f"  ✅ Success")
        else:
            print(f"  ❌ Failed")
        
        time.sleep(5)  # Brief pause
    
    # Check final count
    time.sleep(10)  # Wait for processing
    response = requests.get(f"{API_URL}/documents")
    if response.status_code == 200:
        final_count = len(response.json()['documents'])
        print(f"\n📊 Final count: {final_count} documents")
        print(f"✅ Added {final_count - start_count} new documents")

if __name__ == "__main__":
    main()