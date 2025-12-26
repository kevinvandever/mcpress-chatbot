#!/usr/bin/env python3
"""
Check what authors are actually in the database via API calls
"""
import requests
import json
import time

def check_suspicious_authors_in_database():
    """Find books that still have suspicious authors"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Search for books with suspicious authors
    suspicious_queries = [
        "USA Sales",
        "Admin", 
        "annegrubb",
        "Unknown",
        "Katie",  # Saw this in results
        "ILE RPG"  # Saw this too
    ]
    
    print("🔍 Searching for books with suspicious authors...\n")
    
    suspicious_books = []
    
    for query in suspicious_queries:
        print(f"Searching for: {query}")
        
        try:
            response = requests.post(
                f"{api_url}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                if data.get('type') == 'done' and 'sources' in data:
                                    sources = data.get('sources', [])
                                    for source in sources:
                                        authors = source.get('authors', [])
                                        for author in authors:
                                            author_name = author.get('name', '')
                                            if query.lower() in author_name.lower():
                                                book_info = {
                                                    'title': source.get('filename', '').replace('.pdf', ''),
                                                    'suspicious_author': author_name,
                                                    'all_authors': [a.get('name') for a in authors]
                                                }
                                                if book_info not in suspicious_books:
                                                    suspicious_books.append(book_info)
                                                    print(f"  ❌ Found: {book_info['title']} - Author: {author_name}")
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(1)
        print()
    
    print("="*60)
    print(f"📊 SUSPICIOUS AUTHORS SUMMARY:")
    print(f"Found {len(suspicious_books)} books with suspicious authors")
    print("="*60)
    
    if suspicious_books:
        print("\n📋 BOOKS THAT STILL NEED FIXING:")
        for i, book in enumerate(suspicious_books, 1):
            print(f"{i}. {book['title']}")
            print(f"   ❌ Suspicious: {book['suspicious_author']}")
            print(f"   👥 All authors: {', '.join(book['all_authors'])}")
            print()
    
    return suspicious_books

def check_website_urls():
    """Check if any authors have website URLs"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 Checking for author website URLs...\n")
    
    # Test some well-known authors who should have websites
    test_queries = [
        "Ted Holt",
        "Kevin Vandever", 
        "Bob Cozzi",
        "Jim Buck"
    ]
    
    authors_with_urls = []
    authors_without_urls = []
    
    for query in test_queries:
        try:
            response = requests.post(
                f"{api_url}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                if data.get('type') == 'done' and 'sources' in data:
                                    sources = data.get('sources', [])
                                    for source in sources:
                                        authors = source.get('authors', [])
                                        for author in authors:
                                            author_name = author.get('name', '')
                                            site_url = author.get('site_url')
                                            
                                            if query.lower() in author_name.lower():
                                                if site_url:
                                                    authors_with_urls.append((author_name, site_url))
                                                    print(f"✅ {author_name}: {site_url}")
                                                else:
                                                    authors_without_urls.append(author_name)
                                                    print(f"❌ {author_name}: No URL")
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"Error checking {query}: {e}")
        
        time.sleep(1)
    
    print(f"\n📊 WEBSITE URL SUMMARY:")
    print(f"✅ Authors with URLs: {len(authors_with_urls)}")
    print(f"❌ Authors without URLs: {len(authors_without_urls)}")
    
    return len(authors_with_urls) > 0

if __name__ == "__main__":
    print("="*60)
    print("🔍 DATABASE AUTHOR ANALYSIS")
    print("="*60)
    
    # Check for suspicious authors
    suspicious_books = check_suspicious_authors_in_database()
    
    # Check for website URLs
    has_urls = check_website_urls()
    
    print("\n" + "="*60)
    print("📋 CONCLUSIONS:")
    
    if len(suspicious_books) > 0:
        print(f"❌ {len(suspicious_books)} books still have suspicious authors")
        print("💡 The SQL script may not have covered all books in your database")
        print("💡 Your database might have more books than the 115 in the CSV")
    else:
        print("✅ No suspicious authors found!")
    
    if not has_urls:
        print("❌ No author website URLs found")
        print("💡 Need to populate author website URLs for purple buttons")
    else:
        print("✅ Some authors have website URLs")
    
    print("="*60)