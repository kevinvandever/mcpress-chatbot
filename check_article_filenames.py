#!/usr/bin/env python3
"""
Check what article filenames actually exist in the database
"""

import requests

def main():
    print("🔍 Checking article filenames in database...")
    
    # Get a sample of documents to see filename patterns
    print("\n📰 Step 1: Getting sample documents...")
    try:
        response = requests.get("https://mcpress-chatbot-production.up.railway.app/api/books?limit=50")
        if response.status_code == 200:
            books = response.json()
            
            # Look for numeric filenames (potential articles)
            numeric_files = []
            book_files = []
            
            for book in books:
                filename = book.get('filename', '')
                if filename:
                    # Check if filename is numeric (like 5805.pdf)
                    base_name = filename.replace('.pdf', '')
                    if base_name.isdigit():
                        numeric_files.append({
                            'id': book.get('id'),
                            'filename': filename,
                            'title': book.get('title', 'NO TITLE'),
                            'document_type': book.get('document_type', 'book'),
                            'author': book.get('author', 'Unknown')
                        })
                    else:
                        book_files.append(filename)
            
            print(f"   Total documents checked: {len(books)}")
            print(f"   Numeric filenames (potential articles): {len(numeric_files)}")
            print(f"   Non-numeric filenames (books): {len(book_files)}")
            
            if numeric_files:
                print(f"\n   Sample numeric filenames:")
                for i, file_info in enumerate(numeric_files[:10]):
                    print(f"     {i+1}. {file_info['filename']} -> Title: '{file_info['title']}'")
                    print(f"        Type: {file_info['document_type']}, Author: {file_info['author']}")
            
            # Check if any of our test IDs exist
            test_ids = ["5805", "6274", "7672", "15981"]
            found_test_ids = []
            for file_info in numeric_files:
                base_name = file_info['filename'].replace('.pdf', '')
                if base_name in test_ids:
                    found_test_ids.append(file_info)
            
            if found_test_ids:
                print(f"\n   Found test article IDs:")
                for file_info in found_test_ids:
                    print(f"     {file_info['filename']} -> '{file_info['title']}'")
            else:
                print(f"\n   ⚠️ None of the test IDs ({', '.join(test_ids)}) found in first 50 results")
        
        else:
            print(f"   ❌ API Error: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Search specifically for our test IDs
    print("\n📰 Step 2: Searching for specific test IDs...")
    test_ids = ["5805", "6274", "7672", "15981"]
    
    for test_id in test_ids:
        try:
            # Search for both with and without .pdf extension
            for search_term in [test_id, f"{test_id}.pdf"]:
                response = requests.get(f"https://mcpress-chatbot-production.up.railway.app/api/books?search={search_term}&limit=5")
                if response.status_code == 200:
                    books = response.json()
                    if books:
                        print(f"\n   Found matches for '{search_term}':")
                        for book in books:
                            print(f"     - {book.get('filename')} -> '{book.get('title', 'NO TITLE')}'")
                            print(f"       Type: {book.get('document_type', 'book')}, ID: {book.get('id')}")
                        break
            else:
                print(f"\n   ❌ No matches found for {test_id}")
        
        except Exception as e:
            print(f"   ❌ Error searching for {test_id}: {e}")
    
    print("\n" + "="*60)
    print("📊 ANALYSIS:")
    print("="*60)
    print("\nThe article import is failing because:")
    print("1. Article IDs in Excel don't match PDF filenames in database")
    print("2. Need to check if PDFs were uploaded with correct naming")
    print("3. May need to adjust the matching logic in import service")
    print("\nNext steps:")
    print("1. Verify article PDFs were uploaded correctly")
    print("2. Check if filename matching logic needs adjustment")
    print("3. Ensure Excel file has correct article IDs")

if __name__ == "__main__":
    main()