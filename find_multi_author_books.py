#!/usr/bin/env python3
"""
Find books with multiple authors where at least one author has a website URL.
This will help test the multi-author display in the chat interface.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def find_multi_author_books():
    """Find books with multiple authors that have website URLs"""
    print("Searching for books with multiple authors and author URLs...")
    
    try:
        response = requests.get(f"{API_URL}/documents", timeout=60)
        response.raise_for_status()
        data = response.json()
        
        documents = data.get('documents', [])
        print(f"Total documents: {len(documents)}")
        
        # Find books with multiple authors
        multi_author_books = []
        for doc in documents:
            authors = doc.get('authors', [])
            if len(authors) >= 2:
                # Check if any author has a site_url
                authors_with_urls = [a for a in authors if a.get('site_url')]
                multi_author_books.append({
                    'title': doc.get('title'),
                    'filename': doc.get('filename'),
                    'document_type': doc.get('document_type'),
                    'authors': authors,
                    'authors_with_urls': len(authors_with_urls),
                    'mc_press_url': doc.get('mc_press_url'),
                    'article_url': doc.get('article_url')
                })
        
        print(f"\nBooks with multiple authors: {len(multi_author_books)}")
        
        # Sort by number of authors with URLs (descending)
        multi_author_books.sort(key=lambda x: (x['authors_with_urls'], len(x['authors'])), reverse=True)
        
        # Show top results
        print("\n" + "=" * 80)
        print("BOOKS WITH MULTIPLE AUTHORS (sorted by authors with URLs)")
        print("=" * 80)
        
        for i, book in enumerate(multi_author_books[:20]):
            print(f"\n{i+1}. {book['title']}")
            print(f"   Filename: {book['filename']}")
            print(f"   Type: {book['document_type']}")
            print(f"   Authors ({len(book['authors'])}):")
            for author in book['authors']:
                url_status = f" - URL: {author.get('site_url')}" if author.get('site_url') else " - No URL"
                print(f"      • {author.get('name')}{url_status}")
            if book.get('mc_press_url'):
                print(f"   MC Press URL: {book['mc_press_url']}")
            if book.get('article_url'):
                print(f"   Article URL: {book['article_url']}")
        
        # Find the best candidates for testing
        print("\n" + "=" * 80)
        print("BEST CANDIDATES FOR TESTING MULTI-AUTHOR DISPLAY")
        print("(Books with 2+ authors where multiple authors have URLs)")
        print("=" * 80)
        
        best_candidates = [b for b in multi_author_books if b['authors_with_urls'] >= 2]
        
        if best_candidates:
            for i, book in enumerate(best_candidates[:10]):
                print(f"\n{i+1}. \"{book['title']}\"")
                print(f"   Query suggestion: Ask about \"{book['title'][:50]}\"")
                print(f"   Authors:")
                for author in book['authors']:
                    if author.get('site_url'):
                        print(f"      ✅ {author.get('name')} - {author.get('site_url')}")
                    else:
                        print(f"      ❌ {author.get('name')} - No URL")
        else:
            print("\nNo books found with multiple authors where 2+ have URLs.")
            print("Showing books with at least one author URL instead:")
            
            single_url_books = [b for b in multi_author_books if b['authors_with_urls'] >= 1][:10]
            for i, book in enumerate(single_url_books):
                print(f"\n{i+1}. \"{book['title']}\"")
                print(f"   Query suggestion: Ask about \"{book['title'][:50]}\"")
                print(f"   Authors:")
                for author in book['authors']:
                    if author.get('site_url'):
                        print(f"      ✅ {author.get('name')} - {author.get('site_url')}")
                    else:
                        print(f"      ❌ {author.get('name')} - No URL")
        
        return multi_author_books
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    find_multi_author_books()
