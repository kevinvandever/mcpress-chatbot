#!/usr/bin/env python3
"""
Run CSV comparison via Railway API endpoint.
This script calls the /api/compare-csv-database endpoint which runs on Railway.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def main():
    print("🔍 Running CSV vs Database comparison via API...")
    print(f"📡 API URL: {API_URL}/api/compare-csv-database")
    print()
    
    try:
        print("⏳ Fetching comparison results (this may take a minute)...")
        response = requests.get(
            f"{API_URL}/api/compare-csv-database",
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        results = response.json()
        
        # Display results
        print("\n" + "="*80)
        print("DETAILED COMPARISON RESULTS")
        print("="*80)
        
        # Books in CSV only
        print("\n📋 Books in CSV but NOT in database:")
        if results['in_csv_only']:
            for i, book in enumerate(results['in_csv_only'][:10], 1):
                print(f"  {i}. {book['title']}")
                print(f"     CSV Author: {book['csv_author']}")
                print(f"     URL: {book['url']}")
                print()
            if len(results['in_csv_only']) > 10:
                print(f"  ... and {len(results['in_csv_only']) - 10} more")
        else:
            print("  ✅ None - all CSV books are in database!")
        
        # Books in DB only
        print(f"\n📋 Books in database but NOT in CSV:")
        if results['in_db_only']:
            for i, book in enumerate(results['in_db_only'][:10], 1):
                print(f"  {i}. {book['title']}")
                print(f"     DB Authors: {', '.join(book['db_authors'])}")
                print(f"     URL: {book['url']}")
                print()
            if len(results['in_db_only']) > 10:
                print(f"  ... and {len(results['in_db_only']) - 10} more")
        else:
            print("  ✅ None - no extra books in database!")
        
        # Author mismatches
        print(f"\n📋 Books with AUTHOR MISMATCHES:")
        if results['author_mismatches']:
            for i, book in enumerate(results['author_mismatches'][:10], 1):
                print(f"  {i}. {book['title']}")
                print(f"     CSV Authors: {', '.join(book['csv_authors'])}")
                print(f"     DB Authors:  {', '.join(book['db_authors'])}")
                print(f"     Issue: {book['issue']}")
                print()
            if len(results['author_mismatches']) > 10:
                print(f"  ... and {len(results['author_mismatches']) - 10} more")
        else:
            print("  ✅ None - all authors match!")
        
        # Placeholder authors
        print(f"\n📋 Books with PLACEHOLDER AUTHORS:")
        if results['placeholder_authors']:
            for i, book in enumerate(results['placeholder_authors'][:10], 1):
                print(f"  {i}. {book['title']}")
                print(f"     CSV Authors: {', '.join(book['csv_authors'])}")
                print(f"     DB Authors:  {', '.join(book['db_authors'])} ⚠️")
                print()
            if len(results['placeholder_authors']) > 10:
                print(f"  ... and {len(results['placeholder_authors']) - 10} more")
        else:
            print("  ✅ None - no placeholder authors!")
        
        # Ordering issues
        print(f"\n📋 Books with ORDERING ISSUES:")
        if results['ordering_issues']:
            for i, book in enumerate(results['ordering_issues'][:10], 1):
                print(f"  {i}. {book['title']}")
                print(f"     Authors: {', '.join(book['authors'])}")
                print(f"     Orders: {book['orders']} ⚠️")
                print()
            if len(results['ordering_issues']) > 10:
                print(f"  ... and {len(results['ordering_issues']) - 10} more")
        else:
            print("  ✅ None - all ordering is correct!")
        
        # Summary
        summary = results['summary']
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total books in CSV: {summary['total_csv_books']}")
        print(f"Total books in database: {summary['total_db_books']}")
        print(f"Perfect matches: {summary['perfect_matches']}")
        print(f"\nIssues found:")
        print(f"  - Books only in CSV: {summary['books_only_in_csv']}")
        print(f"  - Books only in DB: {summary['books_only_in_db']}")
        print(f"  - Author mismatches: {summary['author_mismatches']}")
        print(f"  - Placeholder authors: {summary['placeholder_authors']}")
        print(f"  - Ordering issues: {summary['ordering_issues']}")
        print("="*80)
        
        # Save detailed results to JSON
        output_file = 'csv_database_comparison_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed results saved to: {output_file}")
        print("\n✅ Done")
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The comparison may be taking longer than expected.")
        print("Try again in a moment.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
