#!/usr/bin/env python3
"""
Check which books from CSV are missing from the SQL corrections
"""
import csv

def analyze_csv_coverage():
    """Check which books from CSV might not have been covered by SQL"""
    
    # Load CSV books
    csv_books = []
    with open('book-metadata.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Title'] and row['Author']:
                csv_books.append({
                    'title': row['Title'],
                    'authors': row['Author'],
                    'url': row['URL']
                })
    
    print(f"📊 Total books in CSV: {len(csv_books)}")
    
    # Read the SQL file to see which books were covered
    with open('complete_author_audit_corrections.sql', 'r') as f:
        sql_content = f.read()
    
    covered_books = []
    missing_books = []
    
    for book in csv_books:
        title = book['title']
        # Check if this book title appears in the SQL
        if title in sql_content:
            covered_books.append(book)
        else:
            missing_books.append(book)
    
    print(f"✅ Books covered by SQL: {len(covered_books)}")
    print(f"❌ Books NOT covered by SQL: {len(missing_books)}")
    
    if missing_books:
        print(f"\n📋 MISSING BOOKS (first 10):")
        for i, book in enumerate(missing_books[:10]):
            print(f"  {i+1}. {book['title']} - {book['authors']}")
        
        if len(missing_books) > 10:
            print(f"  ... and {len(missing_books) - 10} more")
    
    # Check for books with suspicious authors that should have been fixed
    suspicious_authors = ['USA Sales', 'Admin', 'annegrubb', 'Unknown']
    
    print(f"\n🔍 BOOKS THAT SHOULD HAVE BEEN FIXED:")
    for book in missing_books:
        for sus in suspicious_authors:
            if sus.lower() in book['authors'].lower():
                print(f"  ❌ {book['title']} - Still has '{sus}' (should be: {book['authors']})")
                break

if __name__ == "__main__":
    analyze_csv_coverage()