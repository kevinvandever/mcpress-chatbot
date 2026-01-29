#!/usr/bin/env python3
"""
Analyze specific display issues from screenshots
"""

import requests
import os

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-production.up.railway.app")

def get_books():
    response = requests.get(f"{API_URL}/api/books?limit=500")
    data = response.json()
    return data.get('books', [])

def main():
    books = get_books()
    
    print("=" * 70)
    print("ISSUE 1: Carol Woodbury's Books - Missing Buy Button")
    print("=" * 70)
    print()
    
    # Find Carol Woodbury's books
    for book in books:
        authors = book.get('authors', [])
        if any('carol woodbury' in a.get('name', '').lower() for a in authors):
            title = book.get('title', book['filename'])
            mc_url = book.get('mc_press_url')
            doc_type = book.get('document_type')
            
            print(f"Title: {title}")
            print(f"  document_type: {doc_type}")
            print(f"  mc_press_url: {mc_url or 'MISSING!'}")
            print()
    
    print()
    print("=" * 70)
    print("ISSUE 2: Pete Helgren - Missing Author Button")
    print("=" * 70)
    print()
    
    # Find Pete Helgren's books
    for book in books:
        authors = book.get('authors', [])
        if any('helgren' in a.get('name', '').lower() for a in authors):
            title = book.get('title', book['filename'])
            print(f"Title: {title}")
            for a in authors:
                site = a.get('site_url')
                print(f"  Author: {a['name']} - site_url: {site or 'MISSING!'}")
            print()
    
    # Check author table
    print("\nSearching author table for Helgren:")
    response = requests.get(f"{API_URL}/api/authors/search?q=helgren")
    if response.status_code == 200:
        for a in response.json():
            print(f"  {a['name']} (ID: {a['id']})")
            print(f"    site_url: {a.get('site_url') or 'MISSING!'}")
    
    print()
    print("=" * 70)
    print("ISSUE 2b: Two Authors, One Website - Shows 'Author' (singular)")
    print("=" * 70)
    print()
    print("This is CORRECT behavior!")
    print("When 2 authors exist but only 1 has a website, we show 'Author' (singular)")
    print("because only 1 author link is available.")
    print()
    print("Examples from database:")
    
    count = 0
    for book in books:
        authors = book.get('authors', [])
        if len(authors) == 2:
            with_sites = [a for a in authors if a.get('site_url')]
            if len(with_sites) == 1:
                if count < 5:
                    title = book.get('title', book['filename'])
                    print(f"\n  {title}")
                    for a in authors:
                        site = a.get('site_url')
                        indicator = "HAS SITE" if site else "NO SITE"
                        print(f"    [{indicator}] {a['name']}")
                count += 1
    
    print(f"\n  ... and {count - 5} more books with this pattern")
    
    print()
    print("=" * 70)
    print("ISSUE 3: Source Selection Criteria")
    print("=" * 70)
    print()
    print("Sources are selected using vector similarity search:")
    print()
    print("1. Query is converted to 384-dimensional embedding")
    print("2. Top 30 most similar document chunks are retrieved")
    print("3. Chunks with distance > 0.55 are filtered out")
    print("4. Remaining chunks are grouped by source document")
    print("5. Up to 12 unique sources are returned")
    print()
    print("The 9 sources you see means 9 unique documents had")
    print("relevant content matching your query.")

if __name__ == "__main__":
    main()
