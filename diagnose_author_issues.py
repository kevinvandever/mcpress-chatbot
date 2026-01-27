#!/usr/bin/env python3
"""
Author Data Diagnostic Script
Feature: author-display-investigation

This script must be run on Railway: railway run python3 diagnose_author_issues.py

Generates a comprehensive report of author data quality issues including:
- Books without authors
- Placeholder author names
- Orphaned authors
- Invalid foreign key references
- Author ordering issues
- Duplicate associations
"""

import asyncio
import sys
import json
from datetime import datetime

try:
    from backend.author_data_validator import AuthorDataValidator
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This script must be run on Railway where dependencies are available.")
    print("Usage: railway run python3 diagnose_author_issues.py")
    sys.exit(1)


def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


async def main():
    """Run author data diagnostics and generate report"""
    print("🔍 Author Data Quality Diagnostic Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    validator = AuthorDataValidator()
    
    try:
        # Initialize database connection
        print("\n📊 Connecting to database...")
        await validator.init_database()
        print("✅ Connected successfully")
        
        # Generate comprehensive report
        print("\n🔄 Running diagnostics...")
        report = await validator.generate_data_quality_report()
        
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
                print(f"   Category: {book['category'] or 'N/A'}")
            
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
                print(f"   Created: {author['created_at']}")
            
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
                print(f"   Authors: {', '.join(issue['authors'])}")
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
        
        # Final summary
        print_section_header("RECOMMENDATIONS")
        
        if summary['total_issues'] == 0:
            print("✅ No data quality issues found!")
            print("   The author data is in good shape.")
        else:
            print("⚠️  Data quality issues detected. Recommended actions:")
            
            if books_without_authors:
                print(f"\n1. Fix {len(books_without_authors)} books without authors:")
                print("   - Review each book and assign correct author(s)")
                print("   - Use bulk correction tools if patterns are identified")
            
            if placeholder_authors:
                print(f"\n2. Replace {len(placeholder_authors)} placeholder authors:")
                print("   - Identify correct author names from source data")
                print("   - Use bulk author correction endpoint to fix")
            
            if orphaned_authors:
                print(f"\n3. Clean up {len(orphaned_authors)} orphaned authors:")
                print("   - Review if these authors should be deleted")
                print("   - Or associate them with appropriate documents")
            
            if invalid_references:
                print(f"\n4. CRITICAL: Fix {len(invalid_references)} broken references:")
                print("   - These indicate database integrity issues")
                print("   - Must be resolved before other corrections")
            
            if author_order_gaps:
                print(f"\n5. Fix {len(author_order_gaps)} author ordering issues:")
                print("   - Use reorder_authors endpoint to correct sequences")
            
            if duplicate_associations:
                print(f"\n6. Remove {len(duplicate_associations)} duplicate associations:")
                print("   - Use remove_author_from_document endpoint")
        
        # Save detailed report to JSON
        report_filename = f"author_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            # Convert datetime objects to strings for JSON serialization
            json_report = json.loads(json.dumps(report, default=str))
            json.dump(json_report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error running diagnostics: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Clean up database connection
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
