#!/usr/bin/env python3
"""
Upload missing PDF books to the chatbot database

This script:
1. Checks which books are already in the database
2. Scans a directory for PDF files
3. Uploads only the missing ones using the backend API
"""

import os
import sys
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "https://mcpress-chatbot-production.up.railway.app")
PDF_DIRECTORY = input("Enter path to directory containing PDFs: ").strip()

async def get_existing_books():
    """Get list of books already in database"""
    import asyncpg

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return set()

    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("SELECT DISTINCT filename FROM documents")
        return {row['filename'] for row in rows}
    finally:
        await conn.close()

def find_pdfs(directory):
    """Find all PDF files in directory"""
    pdf_dir = Path(directory)
    if not pdf_dir.exists():
        print(f"❌ Directory not found: {directory}")
        return []

    pdfs = list(pdf_dir.glob("*.pdf"))
    print(f"📁 Found {len(pdfs)} PDF files in {directory}")
    return pdfs

def upload_pdf(pdf_path, api_url):
    """Upload a single PDF to the API"""
    print(f"\n📤 Uploading: {pdf_path.name}")

    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}

            # You can also pass metadata if needed:
            # data = {
            #     'author': 'Author Name',
            #     'category': 'Category'
            # }

            response = requests.post(
                f"{api_url}/upload",
                files=files,
                # data=data,  # Uncomment if you want to pass metadata
                timeout=300  # 5 minutes timeout for large files
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success: {result.get('message', 'Uploaded')}")
                return True
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    """Main upload process"""
    print("="*60)
    print("📚 MC Press Books - Upload Missing PDFs")
    print("="*60)
    print()

    # Check current books in database
    print("🔍 Checking existing books in database...")
    existing_books = await get_existing_books()
    print(f"   Found {len(existing_books)} books already in database")
    print()

    # Find PDFs
    if not PDF_DIRECTORY or not Path(PDF_DIRECTORY).exists():
        print("❌ Invalid PDF directory")
        return

    pdfs = find_pdfs(PDF_DIRECTORY)
    if not pdfs:
        return

    # Filter out already-uploaded books
    missing_pdfs = [pdf for pdf in pdfs if pdf.name not in existing_books]

    print()
    print(f"📊 Summary:")
    print(f"   Total PDFs found: {len(pdfs)}")
    print(f"   Already in database: {len(existing_books)}")
    print(f"   Missing (to upload): {len(missing_pdfs)}")
    print()

    if not missing_pdfs:
        print("✅ All PDFs already uploaded!")
        return

    print("📋 Missing PDFs:")
    for i, pdf in enumerate(missing_pdfs, 1):
        print(f"   {i}. {pdf.name}")
    print()

    # Confirm upload
    response = input(f"Upload {len(missing_pdfs)} missing PDFs? (y/n): ").lower()
    if response != 'y':
        print("❌ Upload cancelled")
        return

    # Upload each missing PDF
    print()
    print("="*60)
    print("🚀 Starting uploads...")
    print("="*60)

    success_count = 0
    fail_count = 0

    for i, pdf in enumerate(missing_pdfs, 1):
        print(f"\n[{i}/{len(missing_pdfs)}]", end=" ")
        if upload_pdf(pdf, API_URL):
            success_count += 1
        else:
            fail_count += 1

        # Small delay between uploads
        if i < len(missing_pdfs):
            print("   ⏳ Waiting 2 seconds before next upload...")
            await asyncio.sleep(2)

    # Final summary
    print()
    print("="*60)
    print("📊 Upload Complete!")
    print("="*60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📚 Total books now: {len(existing_books) + success_count}")
    print()

    if success_count > 0:
        print("🎉 New books uploaded successfully!")
        print()
        print("📝 Next steps:")
        print("1. Test queries with new book content")
        print("2. Verify embeddings are generated (may take a few minutes)")
        print("3. Check /documents endpoint to see all books")

if __name__ == "__main__":
    asyncio.run(main())
