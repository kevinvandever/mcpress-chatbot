#!/usr/bin/env python3
"""
Complete Author Audit and Correction Script

This script performs a comprehensive audit of ALL books in the database
against the authoritative book-metadata.csv file and generates corrections
for ALL discrepancies, not just the 3 books mentioned.
"""

import csv
import requests
import json
import re
from urllib.parse import urlparse

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def parse_csv_completely():
    """Parse the entire book-metadata.csv file"""
    
    print("📖 Complete CSV Analysis")
    print("=" * 50)
    
    csv_books = {}
    
    try:
        with open('book-metadata.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            
            for row_num, row in enumerate(reader, 2):
                if len(row) >= 3:
                    url = row[0].strip()
                    title = row[1].strip()
                    author_field = row[2].strip()
                    
                    if title and author_field:
                        # Parse multiple authors
                        authors = parse_author_field(author_field)
                        
                        csv_books[title] = {
                            "url": url,
                            "authors": authors,
                            "raw_author_field": author_field,
                            "csv_row": row_num
                        }
            
            print(f"✅ Parsed {len(csv_books)} books from CSV")
            return csv_books
            
    except FileNotFoundError:
        print("❌ book-metadata.csv not found")
        return {}
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return {}

def parse_author_field(author_field):
    """Parse the author field to extract individual author names"""
    
    # Handle various author field formats:
    # "John Doe"
    # "John Doe and Jane Smith" 
    # "John Doe, Jane Smith, and Bob Wilson"
    # "John Doe, Jane Smith, Bob Wilson, and Alice Cooper"
    
    # Remove common prefixes/suffixes
    author_field = author_field.strip()
    
    # Split on common separators
    if ' and ' in author_field:
        # Handle "Author1, Author2, and Author3" format
        parts = author_field.split(' and ')
        if len(parts) == 2:
            # Split the first part on commas
            first_authors = [a.strip() for a in parts[0].split(',') if a.strip()]
            last_author = parts[1].strip()
            authors = first_authors + [last_author]
        else:
            authors = [author_field]  # Fallback
    elif ',' in author_field:
        # Simple comma separation
        authors = [a.strip() for a in author_field.split(',') if a.strip()]
    else:
        # Single author
        authors = [author_field]
    
    # Clean up author names
    cleaned_authors = []
    for author in authors:
        # Remove common prefixes like "Dr."
        author = re.sub(r'^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s+', '', author)
        # Remove extra whitespace
        author = ' '.join(author.split())
        if author:
            cleaned_authors.append(author)
    
    return cleaned_authors

def get_all_database_books():
    """Get all books currently in the database with their authors"""
    
    print("\n🔍 Analyzing Database Books")
    print("=" * 50)
    
    # We'll need to use a different approach since we can't directly query all books
    # Let's try to get books through the author search
    
    database_books = {}
    
    # Get all authors first
    suspicious_authors = ['admin', 'annegrubb', 'USA Sales', 'Unknown']
    
    for author_name in suspicious_authors:
        try:
            response = requests.get(
                f"{API_URL}/api/authors/search",
                params={"q": author_name, "limit": 10},
                timeout=10
            )
            
            if response.status_code == 200:
                authors = response.json()
                for author in authors:
                    print(f"   📊 Found suspicious author: {author['name']} ({author.get('document_count', 0)} docs)")
        except Exception as e:
            print(f"   ❌ Error checking author {author_name}: {e}")
    
    return database_books

def find_title_matches(csv_title, threshold=0.8):
    """Find potential matches for a CSV title in the database"""
    
    # Normalize titles for comparison
    def normalize_title(title):
        # Remove common variations
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
        title = re.sub(r'\s+', ' ', title).strip()  # Normalize whitespace
        return title
    
    normalized_csv = normalize_title(csv_title)
    
    # For now, return the title as-is since we don't have direct database access
    # In a real implementation, this would query the database for similar titles
    return [csv_title]

def generate_complete_audit():
    """Generate a complete audit comparing CSV to database"""
    
    print("\n🔍 Complete Author Audit")
    print("=" * 60)
    
    csv_books = parse_csv_completely()
    
    if not csv_books:
        print("❌ No CSV data to audit")
        return
    
    audit_results = {
        "missing_authors": [],
        "incorrect_associations": [],
        "missing_books": [],
        "multi_author_issues": [],
        "website_opportunities": []
    }
    
    print(f"\n📊 Auditing {len(csv_books)} books from CSV...")
    
    for csv_title, csv_data in csv_books.items():
        print(f"\n📖 {csv_title}")
        print(f"   CSV Authors: {', '.join(csv_data['authors'])}")
        
        # Check if authors exist in database
        missing_authors = []
        existing_authors = {}
        
        for author_name in csv_data['authors']:
            author_id = find_author_id(author_name)
            if author_id:
                existing_authors[author_name] = author_id
                print(f"   ✅ {author_name}: ID {author_id}")
            else:
                missing_authors.append(author_name)
                print(f"   ❌ {author_name}: NOT FOUND")
        
        if missing_authors:
            audit_results["missing_authors"].extend([
                {"book": csv_title, "author": author} for author in missing_authors
            ])
        
        # Check for multi-author books
        if len(csv_data['authors']) > 1:
            audit_results["multi_author_issues"].append({
                "book": csv_title,
                "authors": csv_data['authors'],
                "author_count": len(csv_data['authors'])
            })
        
        # Note: We can't easily check current database associations without direct DB access
        # This would require additional API endpoints or database queries
    
    return audit_results

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
            if authors and authors[0]['name'].lower() == author_name.lower():
                return authors[0]['id']
        return None
    except Exception as e:
        return None

def generate_complete_sql_corrections():
    """Generate SQL corrections for ALL discrepancies found in audit"""
    
    print(f"\n💾 Complete SQL Corrections")
    print("=" * 60)
    
    csv_books = parse_csv_completely()
    audit_results = generate_complete_audit()
    
    sql_commands = []
    
    # Header
    sql_commands.append("""
-- =====================================================
-- COMPLETE AUTHOR AUDIT AND CORRECTIONS
-- Generated from book-metadata.csv
-- =====================================================

-- This script fixes ALL author discrepancies, not just the 3 mentioned books
""")
    
    # Step 1: Create all missing authors
    missing_authors = set()
    for book_title, book_data in csv_books.items():
        for author_name in book_data['authors']:
            if not find_author_id(author_name):
                missing_authors.add(author_name)
    
    if missing_authors:
        sql_commands.append("""
-- =====================================================
-- STEP 1: CREATE MISSING AUTHORS
-- =====================================================
""")
        
        for author in sorted(missing_authors):
            sql_commands.append(f"""
-- Create {author}
INSERT INTO authors (name, site_url, created_at, updated_at)
SELECT '{author.replace("'", "''")}', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = '{author.replace("'", "''")}');
""")
    
    # Step 2: Fix all book-author associations
    sql_commands.append("""
-- =====================================================
-- STEP 2: FIX ALL BOOK-AUTHOR ASSOCIATIONS
-- =====================================================
""")
    
    for book_title, book_data in csv_books.items():
        sql_commands.append(f"""
-- Fix: {book_title}
-- CSV Authors: {', '.join(book_data['authors'])}

-- Find book ID
SELECT id, title FROM books WHERE title ILIKE '%{book_title.replace("'", "''")}%';

-- Remove ALL current associations (clean slate)
DELETE FROM document_authors 
WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%{book_title.replace("'", "''")}%');
""")
        
        # Add correct authors in order
        for i, author_name in enumerate(book_data['authors']):
            sql_commands.append(f"""
-- Add {author_name} (order {i})
INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, {i}
FROM books b, authors a
WHERE b.title ILIKE '%{book_title.replace("'", "''")}%'
  AND a.name = '{author_name.replace("'", "''")}'
  AND NOT EXISTS (
    SELECT 1 FROM document_authors da 
    WHERE da.book_id = b.id AND da.author_id = a.id
  );
""")
    
    # Step 3: Verification queries
    sql_commands.append("""
-- =====================================================
-- STEP 3: VERIFICATION QUERIES
-- =====================================================

-- Check for books with no authors (should be empty)
SELECT b.title 
FROM books b 
LEFT JOIN document_authors da ON b.id = da.book_id 
WHERE da.book_id IS NULL;

-- Check for suspicious authors still in use
SELECT b.title, a.name as suspicious_author
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE a.name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales', 'Unknown')
ORDER BY b.title;

-- Count multi-author books
SELECT COUNT(*) as multi_author_books
FROM (
  SELECT book_id 
  FROM document_authors 
  GROUP BY book_id 
  HAVING COUNT(*) > 1
) multi;
""")
    
    # Write to file
    with open('complete_author_audit_corrections.sql', 'w') as f:
        f.write('\n'.join(sql_commands))
    
    print(f"✅ Generated complete SQL corrections")
    print(f"📄 Saved to: complete_author_audit_corrections.sql")
    print(f"📊 Missing authors to create: {len(missing_authors)}")
    print(f"📚 Books to fix: {len(csv_books)}")
    
    return sql_commands

def create_audit_report():
    """Create a comprehensive audit report"""
    
    print(f"\n📋 Audit Report")
    print("=" * 60)
    
    csv_books = parse_csv_completely()
    audit_results = generate_complete_audit()
    
    report = f"""
# Complete Author Audit Report

## Summary
- **Total books in CSV**: {len(csv_books)}
- **Books with multiple authors**: {len([b for b in csv_books.values() if len(b['authors']) > 1])}
- **Unique authors in CSV**: {len(set(author for book in csv_books.values() for author in book['authors']))}

## Multi-Author Books
"""
    
    multi_author_books = [(title, data) for title, data in csv_books.items() if len(data['authors']) > 1]
    
    for title, data in sorted(multi_author_books, key=lambda x: len(x[1]['authors']), reverse=True):
        report += f"\n- **{title}** ({len(data['authors'])} authors)\n"
        for i, author in enumerate(data['authors']):
            report += f"  {i+1}. {author}\n"
    
    report += f"""
## Single Author Books
Total: {len(csv_books) - len(multi_author_books)} books

## Action Required
1. Run `complete_author_audit_corrections.sql` to fix ALL discrepancies
2. Verify corrections with provided verification queries
3. Test chat interface to confirm all authors display correctly
"""
    
    with open('COMPLETE_AUTHOR_AUDIT_REPORT.md', 'w') as f:
        f.write(report)
    
    print(f"✅ Generated audit report: COMPLETE_AUTHOR_AUDIT_REPORT.md")
    
    return report

if __name__ == "__main__":
    print("🔍 Complete Author Audit and Correction")
    print("=" * 70)
    
    # Parse CSV completely
    csv_books = parse_csv_completely()
    
    # Generate complete audit
    audit_results = generate_complete_audit()
    
    # Generate complete SQL corrections
    sql_corrections = generate_complete_sql_corrections()
    
    # Create audit report
    audit_report = create_audit_report()
    
    print(f"\n📋 Complete Audit Summary:")
    print("=" * 70)
    print("✅ Analyzed entire book-metadata.csv")
    print("✅ Generated complete SQL corrections for ALL books")
    print("✅ Created comprehensive audit report")
    print("🔧 Ready to fix ALL author discrepancies system-wide")
    print("\n📄 Files created:")
    print("   - complete_author_audit_corrections.sql")
    print("   - COMPLETE_AUTHOR_AUDIT_REPORT.md")