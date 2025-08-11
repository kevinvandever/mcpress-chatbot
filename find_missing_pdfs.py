#!/usr/bin/env python3
"""
Find which PDFs are missing from Railway
"""

import requests
from pathlib import Path
import sys

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
PDF_DIRECTORY = "./backend/uploads"

def get_uploaded_documents():
    """Get list of uploaded documents from Railway"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            filenames = []
            for doc in docs:
                if isinstance(doc, dict):
                    filenames.append(doc.get('filename', ''))
                elif isinstance(doc, str):
                    filenames.append(doc)
            return [f for f in filenames if f]
        return []
    except Exception as e:
        print(f"Error getting documents: {e}")
        return []

def main():
    print("🔍 Finding missing PDFs...")
    
    # Get all local PDFs
    pdf_dir = Path(PDF_DIRECTORY)
    local_pdfs = sorted([f.name for f in pdf_dir.glob("*.pdf")])
    print(f"📚 Local PDFs: {len(local_pdfs)}")
    
    # Get uploaded PDFs
    uploaded = get_uploaded_documents()
    print(f"☁️  Uploaded PDFs: {len(uploaded)}")
    
    # Find missing
    uploaded_set = set(uploaded)
    missing = [pdf for pdf in local_pdfs if pdf not in uploaded_set]
    
    print(f"\n❌ Missing PDFs: {len(missing)}")
    print("=" * 60)
    
    for i, pdf in enumerate(missing, 1):
        # Get file size
        file_path = pdf_dir / pdf
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"{i}. {pdf} ({size_mb:.1f} MB)")
    
    # Save to file
    with open("missing_pdfs.txt", "w") as f:
        for pdf in missing:
            f.write(f"{pdf}\n")
    
    print("\n📝 Missing PDFs saved to missing_pdfs.txt")

if __name__ == "__main__":
    main()