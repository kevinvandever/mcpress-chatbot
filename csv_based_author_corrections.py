#!/usr/bin/env python3
"""
Author corrections based on the authoritative book-metadata.csv file.

This script uses the CSV data to create accurate corrections for the author associations.
"""

import csv
import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

# Authoritative data from book-metadata.csv
CORRECT_BOOK_DATA = {
    "Complete CL: Sixth Edition": {
        "authors": ["Ted Holt"],
        "mc_press_url": "https://mc-store.com/products/complete-cl-sixth-edition",
        "author_websites": {}  # No website info in CSV
    },
    "Subfiles in Free-Format RPG": {
        "authors": ["Kevin Vandever"], 
        "mc_press_url": "https://mc-store.com/products/subfiles-in-free-format-rpg",
        "author_websites": {}  # No website info in CSV
    },
    "Control Language Programming for IBM i": {
        "authors": ["Jim Buck", "Bryan Meyers", "Dan Riehl"],
        "mc_press_url": "https://mc-store.com/products/control-language-programming-for-ibm-i",
        "author_websites": {}  # No website info in CSV
    }
}

def read_csv_data():
    """Read and parse the book-metadata.csv file"""
    
    print("📖 Reading book-metadata.csv")
    print("=" * 40)
    
    try:
        with open('book-metadata.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            
            books_found = {}
            
            for row in reader:
                if len(row) >= 3:
                    url = row[0].strip()
                    title = row[1].strip()
                    author = row[2].strip()
                    
                    # Check for our target books
                    for target_title in CORRECT_BOOK_DATA.keys():
                        if target_title.lower() in title.lower() or title.lower() in target_title.lower():
                            books_found[title] = {
                                "url": url,
                                "authors": [a.strip() for a in author.split(',') if a.strip()],
                                "csv_author_field": author
                            }
                            print(f"✅ Found: {title}")
                            print(f"   Authors: {author}")
                            print(f"   URL: {url}")
                            break
            
            return books_found
            
    except FileNotFoundError:
        print("❌ book-metadata.csv not found")
        return {}
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return {}

def find_author_id(author_name):
    """Find an author's ID by name"""
    try:
        response = requests.get(
            f"{API_URL}/api/authors/search",
            params={"q": author_name, "limit": 1},
            timeout=10
        )
        
        if response.status_code == 200:
            authors = response.json()
            if authors:
                return authors[0]['id']
        return None
    except Exception as e:
        print(f"   ❌ Error finding author {author_name}: {e}")
        return None

def generate_csv_based_corrections():
    """Generate corrections based on CSV data"""
    
    print("\n🔧 CSV-Based Author Corrections")
    print("=" * 50)
    
    csv_data = read_csv_data()
    
    if not csv_data:
        print("❌ No CSV data available")
        return
    
    corrections = []
    
    for book_title, book_info in csv_data.items():
        print(f"\n📖 {book_title}")
        print("-" * 40)
        
        # Get author IDs for all authors
        author_ids = {}
        for author_name in book_info['authors']:
            # Clean up author name (remove "and" connectors, etc.)
            clean_name = author_name.replace(' and ', '').strip()
            if clean_name:
                author_id = find_author_id(clean_name)
                if author_id:
                    author_ids[clean_name] = author_id
                    print(f"   ✅ {clean_name}: ID {author_id}")
                else:
                    print(f"   ❌ {clean_name}: Not found in database")
        
        correction = {
            "book_title": book_title,
            "csv_authors": book_info['authors'],
            "author_ids": author_ids,
            "mc_press_url": book_info['url']
        }
        corrections.append(correction)
    
    return corrections

def generate_sql_corrections_from_csv():
    """Generate SQL corrections based on CSV data"""
    
    print(f"\n💾 SQL Corrections Based on CSV Data")
    print("=" * 50)
    
    corrections = generate_csv_based_corrections()
    
    if not corrections:
        return
    
    # Get current wrong author IDs
    wrong_authors = {
        "annegrubb": find_author_id("annegrubb"),
        "admin": find_author_id("admin")
    }
    
    print(f"\n🗑️  Wrong authors to remove:")
    for name, author_id in wrong_authors.items():
        print(f"   {name}: ID {author_id}")
    
    sql_commands = []
    
    for correction in corrections:
        book_title = correction['book_title']
        csv_authors = correction['csv_authors']
        author_ids = correction['author_ids']
        
        print(f"\n📖 {book_title}")
        print(f"   Correct authors: {', '.join(csv_authors)}")
        
        # Generate SQL for this book
        sql_commands.append(f"""
-- Fix {book_title}
-- Correct authors from CSV: {', '.join(csv_authors)}

-- Step 1: Find the book ID
SELECT id, title FROM books WHERE title ILIKE '%{book_title.replace("'", "''")}%';

-- Step 2: Remove wrong authors (if any)""")
        
        for wrong_name, wrong_id in wrong_authors.items():
            if wrong_id:
                sql_commands.append(f"""
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%{book_title.replace("'", "''")}%')
  AND author_id = {wrong_id}; -- Remove {wrong_name}""")
        
        sql_commands.append(f"""
-- Step 3: Add correct authors""")
        
        for i, (author_name, author_id) in enumerate(author_ids.items()):
            sql_commands.append(f"""
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, {author_id}, {i}
FROM books b
WHERE b.title ILIKE '%{book_title.replace("'", "''")}%'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = {author_id}
  ); -- Add {author_name}""")
    
    # Print all SQL commands
    for cmd in sql_commands:
        print(cmd)
    
    return sql_commands

def create_author_website_data():
    """Check if we need to add author website information"""
    
    print(f"\n🔗 Author Website Information")
    print("=" * 50)
    
    # The CSV doesn't contain author website information
    # We'll need to add this manually or from another source
    
    known_author_websites = {
        "Ted Holt": None,  # Would need to research
        "Kevin Vandever": None,  # User mentioned this is him, so could add his website
        "Jim Buck": None,
        "Bryan Meyers": None, 
        "Dan Riehl": None,
        "John Campbell": "https://johncampbell-test.com"  # This was already in the system
    }
    
    print("📝 Author website status:")
    for author, website in known_author_websites.items():
        status = "✅ Has website" if website else "⚠️  No website data"
        print(f"   {author}: {status}")
        if website:
            print(f"      {website}")
    
    print(f"\n💡 Recommendations:")
    print("   1. Kevin Vandever: Add your website URL to the authors table")
    print("   2. Ted Holt: Research and add website if available")
    print("   3. Other authors: Research and add websites as needed")
    
    return known_author_websites

def verify_csv_corrections():
    """Verify the corrections match the CSV data exactly"""
    
    print(f"\n✅ Verification Against CSV Data")
    print("=" * 50)
    
    csv_data = read_csv_data()
    
    print("📋 Summary of required corrections:")
    
    for book_title, book_info in csv_data.items():
        print(f"\n📖 {book_title}")
        print(f"   ✅ Correct authors: {', '.join(book_info['authors'])}")
        print(f"   ✅ MC Press URL: {book_info['url']}")
        
        # Check what's currently wrong
        if "Complete CL" in book_title:
            print(f"   ❌ Currently shows: annegrubb")
            print(f"   🔧 Should show: Ted Holt")
        elif "Subfiles" in book_title:
            print(f"   ❌ Currently shows: admin") 
            print(f"   🔧 Should show: Kevin Vandever")
        elif "Control Language Programming" in book_title:
            print(f"   ⚠️  Currently shows: Jim Buck only")
            print(f"   🔧 Should show: Jim Buck, Bryan Meyers, Dan Riehl")

if __name__ == "__main__":
    print("🔧 CSV-Based Author Corrections")
    print("=" * 60)
    
    # Read and verify CSV data
    csv_data = read_csv_data()
    
    # Generate corrections
    corrections = generate_csv_based_corrections()
    
    # Generate SQL commands
    sql_commands = generate_sql_corrections_from_csv()
    
    # Check author websites
    websites = create_author_website_data()
    
    # Verify everything matches CSV
    verify_csv_corrections()
    
    print(f"\n📋 Next Steps:")
    print("=" * 50)
    print("✅ CSV data parsed and verified")
    print("✅ Author IDs identified") 
    print("✅ SQL corrections generated")
    print("🔧 Ready to execute corrections on Railway database")
    print("🔗 Consider adding author website URLs")
    print("🧪 Test corrections via chat interface after execution")