#!/usr/bin/env python3
"""
Setup test data for multi-author button testing.

This script finds existing books and adds website URLs to their authors
to create test cases for the multi-author button functionality.
"""

import requests
import os
import sys

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-production.up.railway.app")

def find_multi_author_books():
    """Find books that have multiple authors"""
    print("🔍 Finding books with multiple authors...\n")
    
    response = requests.get(f"{API_URL}/api/books?limit=200")
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch books: {response.status_code}")
        return []
    
    books = response.json()
    multi_author_books = []
    
    for book in books:
        if 'authors' in book and len(book['authors']) >= 2:
            multi_author_books.append(book)
    
    print(f"📚 Found {len(multi_author_books)} books with multiple authors\n")
    return multi_author_books

def display_book_info(book):
    """Display book information"""
    print(f"  📖 {book.get('title', book['filename'])}")
    print(f"     ID: {book['id']}")
    print(f"     Authors ({len(book['authors'])}):")
    for author in book['authors']:
        site_status = "✓" if author.get('site_url') else "✗"
        print(f"       [{site_status}] {author['name']} (ID: {author['id']})")
        if author.get('site_url'):
            print(f"           {author['site_url']}")
    print()

def add_test_websites_to_authors(author_ids):
    """Add test website URLs to authors"""
    print("\n🔧 Adding test website URLs to authors...\n")
    
    test_domains = [
        "https://example-author1.com",
        "https://example-author2.com",
        "https://example-author3.com",
        "https://example-author4.com",
    ]
    
    for i, author_id in enumerate(author_ids):
        test_url = test_domains[i % len(test_domains)]
        
        print(f"  Updating author {author_id} with URL: {test_url}")
        
        response = requests.patch(
            f"{API_URL}/api/authors/{author_id}",
            json={"site_url": test_url}
        )
        
        if response.status_code == 200:
            print(f"  ✅ Updated author {author_id}")
        else:
            print(f"  ❌ Failed to update author {author_id}: {response.status_code}")
            print(f"     Response: {response.text}")
    
    print()

def main():
    print("=" * 70)
    print("Multi-Author Button Test Data Setup")
    print("=" * 70)
    print()
    
    # Find multi-author books
    multi_author_books = find_multi_author_books()
    
    if not multi_author_books:
        print("⚠️  No multi-author books found in database")
        print("   Cannot set up test data")
        return
    
    # Show first few books
    print("📋 Sample multi-author books:\n")
    for book in multi_author_books[:5]:
        display_book_info(book)
    
    # Find a good candidate for testing
    print("\n🎯 Looking for best test candidate...\n")
    
    # Prefer books with 2 authors, neither having websites
    candidates = [
        b for b in multi_author_books 
        if len(b['authors']) == 2 
        and not any(a.get('site_url') for a in b['authors'])
    ]
    
    if not candidates:
        # Fall back to any multi-author book
        candidates = multi_author_books
    
    if candidates:
        test_book = candidates[0]
        print("✨ Selected test book:")
        display_book_info(test_book)
        
        # Ask user if they want to add test URLs
        print("This script can add test website URLs to these authors.")
        print("This will allow you to test the multi-author button dropdown.")
        print()
        response = input("Add test URLs to these authors? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            author_ids = [a['id'] for a in test_book['authors']]
            add_test_websites_to_authors(author_ids)
            
            print("✅ Test data setup complete!")
            print()
            print("📝 To test the multi-author button:")
            print(f"   1. Go to the chatbot")
            print(f"   2. Ask: 'Tell me about {test_book.get('title', test_book['filename'])}'")
            print(f"   3. Verify the button shows 'Authors' (plural) with dropdown")
            print()
        else:
            print("❌ Cancelled - no changes made")
    else:
        print("⚠️  No suitable test candidates found")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
