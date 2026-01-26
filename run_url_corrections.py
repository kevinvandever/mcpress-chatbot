#!/usr/bin/env python3
"""
Run bulk URL corrections from CSV.
This script calls the Railway API endpoint to fix all book URLs.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def main():
    print("🔧 Bulk URL Correction Script")
    print("="*80)
    
    # Ask about batch size
    print("\n⚙️  Processing Options:")
    print("   1. Process in small batches (10 books at a time) - RECOMMENDED")
    print("   2. Process all books at once")
    
    choice = input("\nChoose option (1 or 2): ").strip()
    
    if choice == "1":
        batch_size = 10
        print(f"\n✅ Will process {batch_size} books at a time")
    else:
        batch_size = 0
        print("\n⚠️  Will process all books at once")
    
    # First, run in dry-run mode to see what would be changed
    print("\n📋 Step 1: DRY RUN - Checking what would be corrected...")
    print(f"📡 Calling: {API_URL}/api/fix-book-urls-from-csv?dry_run=true&limit={batch_size}")
    
    try:
        response = requests.post(
            f"{API_URL}/api/fix-book-urls-from-csv",
            params={"dry_run": True, "limit": batch_size},
            timeout=180  # 3 minute timeout
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        dry_run_results = response.json()
        
        print(f"\n✅ Dry run complete!")
        print(f"   Total books in database: {dry_run_results['total_books_in_db']}")
        print(f"   Books processed: {dry_run_results['books_processed']}")
        print(f"   URL corrections needed: {dry_run_results['corrections_made']}")
        print(f"   Books not in CSV: {dry_run_results['total_errors']}")
        
        if dry_run_results['corrections_made'] == 0:
            print("\n✅ No corrections needed - all book URLs are correct!")
            return
        
        # Show first 10 corrections
        print(f"\n📋 First 10 URL corrections that would be made:")
        for i, correction in enumerate(dry_run_results['corrections'][:10], 1):
            print(f"\n  {i}. {correction['book_title']}")
            print(f"     Old URL: {correction['old_url']}")
            print(f"     New URL: {correction['new_url']}")
        
        if dry_run_results['total_corrections'] > 10:
            print(f"\n  ... and {dry_run_results['total_corrections'] - 10} more")
        
        # Save full dry run results
        with open('url_corrections_dry_run.json', 'w') as f:
            json.dump(dry_run_results, f, indent=2)
        print(f"\n💾 Full dry run results saved to: url_corrections_dry_run.json")
        
        # Ask for confirmation
        print("\n" + "="*80)
        response = input("\n⚠️  Apply these URL corrections? (yes/no): ")
        
        if response.lower() != 'yes':
            print("\n❌ Corrections cancelled.")
            return
        
        # Run actual corrections
        print("\n📋 Step 2: APPLYING CORRECTIONS...")
        print(f"📡 Calling: {API_URL}/api/fix-book-urls-from-csv?dry_run=false&limit={batch_size}")
        
        response = requests.post(
            f"{API_URL}/api/fix-book-urls-from-csv",
            params={"dry_run": False, "limit": batch_size},
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        results = response.json()
        
        print(f"\n✅ Corrections applied!")
        print(f"   Books processed: {results['books_processed']}")
        print(f"   URL corrections made: {results['corrections_made']}")
        
        # Save results
        with open('url_corrections_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: url_corrections_results.json")
        
        # Check if there are more books to process
        if batch_size > 0 and results['books_processed'] < results['total_books_in_db']:
            remaining = results['total_books_in_db'] - results['books_processed']
            print(f"\n⚠️  Note: {remaining} books remaining. Run script again to process next batch.")
        
        print("\n" + "="*80)
        if batch_size == 0 or results['books_processed'] >= results['total_books_in_db']:
            print("✅ DONE - All book URLs have been corrected!")
        else:
            print(f"✅ Batch complete - {results['corrections_made']} URL corrections made")
        print("="*80)
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The correction may be taking longer than expected.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
