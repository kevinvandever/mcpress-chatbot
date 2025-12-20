#!/usr/bin/env python3
"""
Check if ALL authors from CSV were fixed and if website links are included
"""
import csv
import requests
import json
import time

def load_csv_data():
    """Load the CSV data to compare against"""
    books = []
    with open('book-metadata.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Title'] and row['Author']:
                books.append({
                    'title': row['Title'],
                    'authors': row['Author'],
                    'url': row['URL']
                })
    return books

def test_random_books_from_csv():
    """Test a sample of books from the CSV to see if authors are correct"""
    
    csv_books = load_csv_data()
    print(f"📊 Total books in CSV: {len(csv_books)}")
    
    # Test a sample of books
    test_books = [
        # Books you specifically mentioned
        "Complete CL: Sixth Edition",
        "Subfiles in Free-Format RPG", 
        "Control Language Programming for IBM i",
        
        # Random sample from CSV
        "Big Data Analytics",
        "Java for RPG Programmers",
        "SQL for IBM i: A Database Modernization Guide",
        "The Modern RPG IV Language",
        "IBM i Security Administration and Compliance",
        "Mastering IBM i",
        "Programming in ILE RPG, Fifth Edition"
    ]
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("\n🔍 Testing sample books from CSV...\n")
    
    correct_count = 0
    total_tested = 0
    
    for book_title in test_books:
        print(f"Testing: {book_title}")
        
        # Find expected authors from CSV
        csv_book = None
        for book in csv_books:
            if book_title.lower() in book['title'].lower():
                csv_book = book
                break
        
        if not csv_book:
            print(f"  ⚠️ Not found in CSV")
            continue
            
        expected_authors = csv_book['authors']
        print(f"  📋 Expected: {expected_authors}")
        
        try:
            # Query the chatbot
            response = requests.post(
                f"{api_url}/chat",
                json={"message": book_title},
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse streaming response for sources
                sources_found = []
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                if data.get('type') == 'done' and 'sources' in data:
                                    sources_found = data.get('sources', [])
                                    break
                            except json.JSONDecodeError:
                                continue
                
                # Check if we found the right book
                found_correct_book = False
                for source in sources_found:
                    source_title = source.get('filename', '').replace('.pdf', '')
                    if book_title.lower() in source_title.lower():
                        found_correct_book = True
                        authors = source.get('authors', [])
                        author_names = [author.get('name', '') for author in authors]
                        site_urls = [author.get('site_url') for author in authors]
                        
                        print(f"  ✅ Found: {source_title}")
                        print(f"  👥 Actual: {', '.join(author_names)}")
                        
                        # Check for website URLs
                        has_urls = any(url for url in site_urls)
                        if has_urls:
                            print(f"  🔗 Has website URLs: {[url for url in site_urls if url]}")
                        else:
                            print(f"  ❌ No website URLs found")
                        
                        # Simple check if authors match (basic comparison)
                        if any(name in expected_authors for name in author_names):
                            print(f"  ✅ Authors match CSV!")
                            correct_count += 1
                        else:
                            print(f"  ❌ Authors don't match CSV")
                        
                        break
                
                if not found_correct_book:
                    print(f"  ❌ Book not found in search results")
                    
            else:
                print(f"  ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        total_tested += 1
        print()
        
        # Small delay to avoid overwhelming the API
        time.sleep(1)
    
    print("="*60)
    print(f"📊 SUMMARY: {correct_count}/{total_tested} books have correct authors")
    print(f"📊 Success rate: {(correct_count/total_tested)*100:.1f}%")
    
    if correct_count == total_tested:
        print("🎉 All tested books have correct authors!")
    elif correct_count > total_tested * 0.8:
        print("✅ Most books have correct authors - looking good!")
    else:
        print("⚠️ Some books still need author corrections")
    
    print("="*60)

def check_database_for_website_urls():
    """Check if the database has website URLs for authors"""
    print("\n🔍 Checking database for author website URLs...\n")
    
    # We can't directly query the database, but we can check via the API
    # by looking at the author data in chat responses
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # Test a few books to see if any authors have website URLs
    test_queries = [
        "Kevin Schroeder PHP",  # Should have website
        "Ted Holt CL",          # Might have website
        "Bob Cozzi RPG"         # Might have website
    ]
    
    urls_found = 0
    total_authors = 0
    
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
                                            total_authors += 1
                                            site_url = author.get('site_url')
                                            if site_url:
                                                urls_found += 1
                                                print(f"✅ {author.get('name')}: {site_url}")
                                            else:
                                                print(f"❌ {author.get('name')}: No URL")
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"Error testing {query}: {e}")
        
        time.sleep(1)
    
    print(f"\n📊 Website URLs: {urls_found}/{total_authors} authors have website URLs")
    
    if urls_found == 0:
        print("❌ No website URLs found in database")
        print("💡 The SQL script created authors but didn't add website URLs")
        print("💡 You can add them manually or run another script to populate URLs")
    else:
        print(f"✅ Some authors have website URLs ({(urls_found/total_authors)*100:.1f}%)")

if __name__ == "__main__":
    print("="*60)
    print("🧪 COMPREHENSIVE AUTHOR VERIFICATION")
    print("="*60)
    
    # Test if CSV authors were fixed
    test_random_books_from_csv()
    
    # Check for website URLs
    check_database_for_website_urls()
    
    print("\n💡 NEXT STEPS:")
    print("1. If authors are correct but no URLs: Add website URLs to authors table")
    print("2. If some authors are wrong: Check which books weren't covered by SQL")
    print("3. Purple 'Author' buttons will appear once URLs are added")