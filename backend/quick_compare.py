#!/usr/bin/env python3
import csv
import json
import requests

# Get database books
response = requests.get('http://localhost:8000/documents')
db_data = response.json()
db_books = {book['filename'].replace('.pdf', '').lower(): book for book in db_data['documents']}

# Read CSV books
csv_books = {}
with open('/Users/kevinvandever/Desktop/MC Press LIst of Books & File Size.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Title'] and row['Title'].strip():
            title_key = row['Title'].lower()
            csv_books[title_key] = {
                'title': row['Title'],
                'category': row['Original Category'],
                'filename': row['FileName']
            }

print(f"CSV Books: {len(csv_books)}")
print(f"Database Books: {len(db_books)}")
print()

# Simple exact match check
missing_count = 0
found_count = 0
category_mismatches = []

for csv_title, csv_book in csv_books.items():
    # Try to find match
    found = False
    for db_title, db_book in db_books.items():
        if csv_title in db_title or db_title in csv_title:
            found = True
            found_count += 1
            
            # Check category
            if csv_book['category'] != db_book['category']:
                category_mismatches.append({
                    'title': csv_book['title'][:50] + '...' if len(csv_book['title']) > 50 else csv_book['title'],
                    'csv_category': csv_book['category'],
                    'db_category': db_book['category']
                })
            break
    
    if not found:
        missing_count += 1
        print(f"MISSING: {csv_book['title']}")

print(f"\nSUMMARY:")
print(f"Found: {found_count}")
print(f"Missing: {missing_count}")
print(f"Category mismatches: {len(category_mismatches)}")

if category_mismatches:
    print(f"\nCATEGORY MISMATCHES:")
    for mismatch in category_mismatches[:10]:  # Show first 10
        print(f"• {mismatch['title']}")
        print(f"  CSV: {mismatch['csv_category']} → DB: {mismatch['db_category']}")