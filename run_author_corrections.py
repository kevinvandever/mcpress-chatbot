#!/usr/bin/env python3
"""
Run bulk author corrections from CSV.
This script calls the Railway API endpoint to fix all book authors.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def main():
    print("🔧 Bulk Author Correction Script")
    print("="*80)
    
    # First, run in dry-run mode to see what would be changed
    print("\n📋 Step 1: DRY RUN - Checking what would be corrected...")
    print(f"📡 Calling: {API_URL}/api/fix-book-authors-from-csv?dry_run=true")
    
    try:
        response = requests.post(
            f"{API_URL}/api/fix-book-authors-from-csv",
            params={"dry_run": True},
            timeout=180  # 3 minute timeout
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        dry_run_results = response.json()
        
        print(f"\n✅ Dry run complete!")
        print(f"   Total books checked: {dry_run_results['total_books_checked']}")
        print(f"   Corrections needed: {dry_run_results['corrections_made']}")
        
        if dry_run_results['corrections_made'] == 0:
            print("\n✅ No corrections needed - all books have correct authors!")
            return
        
        # Show first 10 corrections
        print(f"\n📋 First 10 corrections that would be made:")
        for i, correction in enumerate(dry_run_results['corrections'][:10], 1):
            print(f"\n  {i}. {correction['book_title']}")
            print(f"     Old authors: {', '.join(correction['old_authors'])}")
            print(f"     New authors: {', '.join(correction['new_authors'])}")
        
        if dry_run_results['total_corrections'] > 10:
            print(f"\n  ... and {dry_run_results['total_corrections'] - 10} more")
        
        # Save full dry run results
        with open('author_corrections_dry_run.json', 'w') as f:
            json.dump(dry_run_results, f, indent=2)
        print(f"\n💾 Full dry run results saved to: author_corrections_dry_run.json")
        
        # Ask for confirmation
        print("\n" + "="*80)
        response = input("\n⚠️  Apply these corrections? (yes/no): ")
        
        if response.lower() != 'yes':
            print("\n❌ Corrections cancelled.")
            return
        
        # Run actual corrections
        print("\n📋 Step 2: APPLYING CORRECTIONS...")
        print(f"📡 Calling: {API_URL}/api/fix-book-authors-from-csv?dry_run=false")
        
        response = requests.post(
            f"{API_URL}/api/fix-book-authors-from-csv",
            params={"dry_run": False},
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        results = response.json()
        
        print(f"\n✅ Corrections applied!")
        print(f"   Total corrections made: {results['corrections_made']}")
        
        # Save results
        with open('author_corrections_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: author_corrections_results.json")
        
        print("\n" + "="*80)
        print("✅ DONE - All book authors have been corrected!")
        print("="*80)
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The correction may be taking longer than expected.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
