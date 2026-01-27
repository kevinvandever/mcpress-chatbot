#!/usr/bin/env python3
"""
Run Author Diagnostics via API
This script calls the Railway API endpoint to run diagnostics.
Can be run locally - no backend imports needed!
"""

import requests
import json
from datetime import datetime

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print("🔍 Author Data Quality Diagnostic Report (via API)")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📊 Calling Railway API...")
    
    try:
        response = requests.get(f"{API_URL}/api/diagnostics/authors", timeout=60)
        response.raise_for_status()
        report = response.json()
        
        # Print summary statistics
        print_section_header("SUMMARY STATISTICS")
        summary = report['summary']
        print(f"Total Books:                {summary['total_books']:,}")
        print(f"Total Authors:              {summary['total_authors']:,}")
        print(f"Total Associations:         {summary['total_associations']:,}")
        print(f"Books with Authors:         {summary['books_with_authors']:,}")
        print(f"Books without Authors:      {summary['books_without_authors_count']:,}")
        print(f"\n🚨 TOTAL ISSUES FOUND:      {summary['total_issues']:,}")
        
        # Books without authors
        print_section_header("BOOKS WITHOUT AUTHORS")
        books_without_authors = report['books_without_authors']
        print(f"Count: {len(books_without_authors)}")
        
        if books_without_authors:
            print("\nExamples (first 10):")
            for i, book in enumerate(books_without_authors[:10], 1):
                print(f"\n{i}. ID: {book['id']}")
                print(f"   Title: {book['title'] or 'N/A'}")
                print(f"   Filename: {book['filename']}")
                print(f"   Type: {book['document_type'] or 'N/A'}")
            
            if len(books_without_authors) > 10:
                print(f"\n... and {len(books_without_authors) - 10} more")
        else:
            print("✅ No books without authors found")
        
        # Placeholder authors
        print_section_header("PLACEHOLDER AUTHORS")
        placeholder_authors = report['placeholder_authors']
        print(f"Count: {len(placeholder_authors)}")
        
        if placeholder_authors:
            print("\nSuspicious author names:")
            for i, author in enumerate(placeholder_authors, 1):
                print(f"\n{i}. ID: {author['author_id']}")
                print(f"   Name: {author['author_name']}")
                print(f"   Documents: {author['document_count']}")
        else:
            print("✅ No placeholder authors found")
        
        # Orphaned authors
        print_section_header("ORPHANED AUTHORS")
        orphaned_authors = report['orphaned_authors']
        print(f"Count: {len(orphaned_authors)}")
        
        if orphaned_authors:
            print("\nAuthors with no document associations (first 10):")
            for i, author in enumerate(orphaned_authors[:10], 1):
                print(f"\n{i}. ID: {author['id']}")
                print(f"   Name: {author['name']}")
                print(f"   URL: {author['site_url'] or 'N/A'}")
            
            if len(orphaned_authors) > 10:
                print(f"\n... and {len(orphaned_authors) - 10} more")
        else:
            print("✅ No orphaned authors found")
        
        # Invalid references
        print_section_header("INVALID FOREIGN KEY REFERENCES")
        invalid_references = report['invalid_references']
        print(f"Count: {len(invalid_references)}")
        
        if invalid_references:
            print("\n⚠️  CRITICAL: Broken foreign key references found!")
            for i, error in enumerate(invalid_references, 1):
                print(f"{i}. {error}")
        else:
            print("✅ All foreign key references are valid")
        
        # Author order gaps
        print_section_header("AUTHOR ORDERING ISSUES")
        author_order_gaps = report['author_order_gaps']
        print(f"Count: {len(author_order_gaps)}")
        
        if author_order_gaps:
            print("\nBooks with incorrect author ordering:")
            for i, issue in enumerate(author_order_gaps, 1):
                print(f"\n{i}. Book ID: {issue['book_id']}")
                print(f"   Title: {issue['title'] or issue['filename']}")
                print(f"   Expected order: {issue['expected_orders']}")
                print(f"   Actual order:   {issue['actual_orders']}")
        else:
            print("✅ All author orderings are correct")
        
        # Duplicate associations
        print_section_header("DUPLICATE ASSOCIATIONS")
        duplicate_associations = report['duplicate_associations']
        print(f"Count: {len(duplicate_associations)}")
        
        if duplicate_associations:
            print("\nBooks with duplicate author associations:")
            for i, dup in enumerate(duplicate_associations, 1):
                print(f"\n{i}. Book ID: {dup['book_id']}")
                print(f"   Title: {dup['title'] or dup['filename']}")
                print(f"   Author: {dup['author_name']} (ID: {dup['author_id']})")
                print(f"   Duplicate count: {dup['association_count']}")
        else:
            print("✅ No duplicate associations found")
        
        # Save detailed report
        report_filename = f"author_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")
        print("\n" + "=" * 80)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error calling API: {e}")
        print("Make sure the Railway service is running and accessible.")
        return 1
    except Exception as e:
        print(f"\n❌ Error processing response: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
