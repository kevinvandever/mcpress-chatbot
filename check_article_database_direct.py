#!/usr/bin/env python3
"""
Direct check of what's in the Railway database for articles
"""

import requests

def main():
    print("🔍 Checking Railway database for articles...")
    
    # Check total count
    response = requests.get("https://mcpress-chatbot-production.up.railway.app/api/books?limit=1")
    result = response.json()
    print(f"📊 Total books in database: {result.get('total', 0)}")
    
    # Search for specific article IDs we know exist from chat
    article_ids = ["972", "9185", "25497", "12887", "16797", "6736"]
    
    for article_id in article_ids:
        print(f"\n🔍 Searching for article {article_id}...")
        
        # Try different search patterns
        search_patterns = [
            article_id,
            f"{article_id}.pdf",
            f"filename:{article_id}",
        ]
        
        for pattern in search_patterns:
            response = requests.get(f"https://mcpress-chatbot-production.up.railway.app/api/books?search={pattern}&limit=1")
            result = response.json()
            
            if result.get('total', 0) > 0:
                book = result['books'][0]
                print(f"  ✅ Found with pattern '{pattern}':")
                print(f"     ID: {book['id']}")
                print(f"     Filename: {book['filename']}")
                print(f"     Title: {book['title']}")
                print(f"     Document Type: {book['document_type']}")
                print(f"     Article URL: {book['article_url']}")
                print(f"     Authors: {book.get('authors', [])}")
                break
        else:
            print(f"  ❌ Not found with any search pattern")
    
    # Check if there are any documents with numeric filenames
    print(f"\n🔍 Checking for any numeric filenames...")
    response = requests.get("https://mcpress-chatbot-production.up.railway.app/api/books?limit=50")
    result = response.json()
    
    numeric_files = []
    for book in result.get('books', []):
        filename = book['filename']
        # Check if filename starts with digits
        if filename.split('.')[0].isdigit():
            numeric_files.append({
                'id': book['id'],
                'filename': filename,
                'title': book['title'],
                'document_type': book['document_type']
            })
    
    if numeric_files:
        print(f"  ✅ Found {len(numeric_files)} files with numeric names:")
        for file in numeric_files[:10]:  # Show first 10
            print(f"     {file['filename']} -> {file['title']} ({file['document_type']})")
    else:
        print(f"  ❌ No files with numeric names found in first 50 results")

if __name__ == "__main__":
    main()