#!/usr/bin/env python3
"""
Compare CSV book list with database inventory
"""
import csv
import json
import requests
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    # Remove common variations and normalize
    title = title.strip()
    title = title.replace('.pdf', '')
    title = title.replace(':', '-')
    title = title.replace(' & ', ' and ')
    title = title.replace('–', '-')
    title = title.replace('—', '-')
    return title.lower()

def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def map_category(original_category: str) -> str:
    """Map original categories to database categories"""
    category_mappings = {
        'Programming': 'Programming',
        'Management and Career': 'Management and Career', 
        'Operating Systems': 'Operating Systems',
        'Database': 'Database',
        'Application Development': 'Application Development',
        'System Administration': 'System Administration'
    }
    return category_mappings.get(original_category, original_category)

def compare_books():
    print("📚 MC Press Books Comparison Report")
    print("=" * 60)
    
    # Read CSV file
    csv_books = {}
    with open('/Users/kevinvandever/Desktop/MC Press LIst of Books & File Size.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Title'] and row['Title'].strip():  # Skip empty rows
                csv_books[normalize_title(row['Title'])] = {
                    'title': row['Title'],
                    'filename': row['FileName'],
                    'category': row['Original Category'],
                    'pages': row.get('Pages', ''),
                    'sku': row.get('SKU', '')
                }
    
    # Get database inventory
    try:
        response = requests.get('http://localhost:8000/documents')
        db_data = response.json()
        db_books = {}
        
        for book in db_data['documents']:
            normalized_title = normalize_title(book['filename'])
            db_books[normalized_title] = book
            
    except Exception as e:
        print(f"❌ Error fetching database: {e}")
        return
    
    print(f"📊 CSV Books: {len(csv_books)}")
    print(f"📊 Database Books: {len(db_books)}")
    print()
    
    # Find missing books
    missing_books = []
    found_books = []
    potential_matches = []
    
    for csv_title, csv_book in csv_books.items():
        best_match = None
        best_similarity = 0
        
        # Check for exact match first
        if csv_title in db_books:
            found_books.append((csv_book, db_books[csv_title]))
        else:
            # Check for fuzzy matches
            for db_title, db_book in db_books.items():
                sim = similarity(csv_title, db_title)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = (db_title, db_book)
            
            if best_similarity > 0.8:  # High similarity threshold
                potential_matches.append((csv_book, best_match[1], best_similarity))
                found_books.append((csv_book, best_match[1]))
            else:
                missing_books.append(csv_book)
    
    # Category comparison
    category_mismatches = []
    for csv_book, db_book in found_books:
        expected_category = map_category(csv_book['category'])
        actual_category = db_book['category']
        
        if expected_category != actual_category:
            category_mismatches.append({
                'title': csv_book['title'],
                'expected': expected_category,
                'actual': actual_category
            })
    
    # Generate report
    print("🚫 MISSING BOOKS FROM DATABASE:")
    print("-" * 40)
    if missing_books:
        for book in sorted(missing_books, key=lambda x: x['title']):
            print(f"• {book['title']}")
            print(f"   File: {book['filename']}")
            print(f"   Category: {book['category']}")
            print(f"   Pages: {book['pages']}")
            print()
    else:
        print("✅ No missing books found!")
    
    print(f"\n📋 SUMMARY:")
    print(f"   Total CSV Books: {len(csv_books)}")
    print(f"   Found in Database: {len(found_books)}")
    print(f"   Missing from Database: {len(missing_books)}")
    print(f"   Potential Fuzzy Matches: {len(potential_matches)}")
    
    if potential_matches:
        print(f"\n🔍 POTENTIAL FUZZY MATCHES:")
        print("-" * 40)
        for csv_book, db_book, sim in potential_matches:
            print(f"CSV: {csv_book['title']}")
            print(f"DB:  {db_book['filename']}")  
            print(f"Similarity: {sim:.2%}")
            print()
    
    # Category mismatches
    print(f"\n⚠️  CATEGORY MISMATCHES:")
    print("-" * 40)
    if category_mismatches:
        for mismatch in sorted(category_mismatches, key=lambda x: x['title']):
            print(f"• {mismatch['title']}")
            print(f"   Expected: {mismatch['expected']}")
            print(f"   Actual: {mismatch['actual']}")
            print()
    else:
        print("✅ No category mismatches found!")
    
    print(f"\n📊 CATEGORY DISTRIBUTION:")
    print("-" * 40)
    
    # CSV categories
    csv_categories = {}
    for book in csv_books.values():
        cat = book['category']
        csv_categories[cat] = csv_categories.get(cat, 0) + 1
    
    # DB categories  
    db_categories = {}
    for book in db_books.values():
        cat = book['category']
        db_categories[cat] = db_categories.get(cat, 0) + 1
    
    print("CSV Categories:")
    for cat, count in sorted(csv_categories.items()):
        print(f"   {cat}: {count}")
    
    print("\nDatabase Categories:")
    for cat, count in sorted(db_categories.items()):
        print(f"   {cat}: {count}")
    
    # Books only in database (not in CSV)
    extra_books = []
    for db_title, db_book in db_books.items():
        found = False
        for csv_title in csv_books.keys():
            if similarity(db_title, csv_title) > 0.8:
                found = True
                break
        if not found:
            extra_books.append(db_book)
    
    if extra_books:
        print(f"\n📥 BOOKS IN DATABASE NOT IN CSV:")
        print("-" * 40)
        for book in sorted(extra_books, key=lambda x: x['filename']):
            print(f"• {book['filename']}")
            print(f"   Category: {book['category']}")
            print(f"   Author: {book['author']}")
            print()

if __name__ == "__main__":
    compare_books()