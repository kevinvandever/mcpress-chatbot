#!/usr/bin/env python3
"""
Find and merge duplicate authors in the database.

This script:
1. Finds all duplicate author records (same name, different case/spacing)
2. Shows which author to keep (one with site_url or most documents)
3. Optionally merges duplicates into the canonical author

Usage:
    python3 find_and_merge_duplicate_authors.py           # Find duplicates (dry run)
    python3 find_and_merge_duplicate_authors.py --merge   # Actually merge duplicates
    python3 find_and_merge_duplicate_authors.py --helgren # Check Pete Helgren specifically
"""

import requests
import sys
import os
import json

API_URL = os.getenv('API_URL', 'https://mcpress-chatbot-production.up.railway.app')

def find_duplicates():
    """Find all duplicate authors."""
    print("=" * 70)
    print("FINDING DUPLICATE AUTHORS")
    print("=" * 70)
    print()
    
    response = requests.get(f'{API_URL}/api/authors/duplicates', timeout=60)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    print(f"Found {data['total_duplicate_groups']} groups of duplicate authors")
    print()
    
    for i, group in enumerate(data['duplicates'][:20], 1):
        print(f"{i}. '{group['canonical_name']}' ({group['total_documents']} total documents)")
        print(f"   Recommended to keep: ID {group['recommended_keep_id']}")
        for author in group['authors']:
            marker = "✓ KEEP" if author['id'] == group['recommended_keep_id'] else "  merge"
            site = f"site: {author['site_url']}" if author['site_url'] else "no site"
            print(f"   [{marker}] ID {author['id']}: '{author['name']}' ({author['document_count']} docs, {site})")
        print()
    
    if len(data['duplicates']) > 20:
        print(f"... and {len(data['duplicates']) - 20} more duplicate groups")
    
    return data

def check_helgren():
    """Check Pete Helgren's author records specifically."""
    print("=" * 70)
    print("PETE HELGREN AUTHOR RECORDS")
    print("=" * 70)
    print()
    
    response = requests.get(f'{API_URL}/api/authors/helgren', timeout=60)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    
    print("Found author records:")
    for author in data['authors']:
        site = f"site: {author['site_url']}" if author['site_url'] else "NO SITE"
        print(f"  ID {author['id']}: '{author['name']}' ({author['document_count']} docs, {site})")
    
    print()
    print("Recommendation:")
    print(f"  Keep ID: {data['recommendation']['keep_id']}")
    print(f"  Merge IDs: {data['recommendation']['merge_ids']}")
    
    return data

def merge_authors(keep_id, merge_ids, dry_run=True):
    """Merge duplicate authors."""
    print("=" * 70)
    print(f"MERGING AUTHORS {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print("=" * 70)
    print()
    
    payload = {
        'keep_author_id': keep_id,
        'merge_author_ids': merge_ids,
        'dry_run': dry_run
    }
    
    response = requests.post(
        f'{API_URL}/api/authors/merge',
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    
    print(f"Keep author: {data['keep_author']}")
    print(f"Merge authors: {data['merge_authors']}")
    print(f"Documents to reassign: {data['documents_to_reassign']}")
    print(f"Conflicts to remove: {data['conflicts_to_remove']}")
    print(f"Status: {data['status']}")
    
    if data.get('details', {}).get('reassign'):
        print()
        print("Documents to reassign:")
        for doc in data['details']['reassign'][:10]:
            print(f"  - {doc['title']}")
        if len(data['details']['reassign']) > 10:
            print(f"  ... and {len(data['details']['reassign']) - 10} more")
    
    return data

def merge_all_duplicates(dry_run=True):
    """Merge all duplicate author groups."""
    print("=" * 70)
    print(f"MERGING ALL DUPLICATES {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print("=" * 70)
    print()
    
    # First get all duplicates
    response = requests.get(f'{API_URL}/api/authors/duplicates', timeout=60)
    if response.status_code != 200:
        print(f"Error getting duplicates: {response.status_code}")
        return
    
    data = response.json()
    
    if data['total_duplicate_groups'] == 0:
        print("No duplicates found!")
        return
    
    print(f"Processing {data['total_duplicate_groups']} duplicate groups...")
    print()
    
    success_count = 0
    error_count = 0
    
    for group in data['duplicates']:
        keep_id = group['recommended_keep_id']
        merge_ids = [a['id'] for a in group['authors'] if a['id'] != keep_id]
        
        if not merge_ids:
            continue
        
        print(f"Merging '{group['canonical_name']}'...")
        print(f"  Keep: {keep_id}, Merge: {merge_ids}")
        
        result = merge_authors(keep_id, merge_ids, dry_run=dry_run)
        
        if result and result.get('status') in ['completed', 'dry_run']:
            success_count += 1
        else:
            error_count += 1
        
        print()
    
    print("=" * 70)
    print(f"SUMMARY: {success_count} successful, {error_count} errors")
    print("=" * 70)

def main():
    args = sys.argv[1:]
    
    if '--helgren' in args:
        data = check_helgren()
        if data and '--merge' in args:
            keep_id = data['recommendation']['keep_id']
            merge_ids = data['recommendation']['merge_ids']
            if merge_ids:
                merge_authors(keep_id, merge_ids, dry_run=False)
            else:
                print("No authors to merge")
    elif '--merge-all' in args:
        dry_run = '--live' not in args
        merge_all_duplicates(dry_run=dry_run)
    elif '--merge' in args:
        # Merge specific IDs from command line
        if len(args) >= 3:
            keep_id = int(args[1])
            merge_ids = [int(x) for x in args[2:] if x != '--merge']
            merge_authors(keep_id, merge_ids, dry_run=False)
        else:
            print("Usage: python3 find_and_merge_duplicate_authors.py --merge <keep_id> <merge_id1> <merge_id2> ...")
    else:
        find_duplicates()
        print()
        print("To merge duplicates, run with --merge-all flag")
        print("To merge Pete Helgren specifically, run with --helgren --merge")

if __name__ == '__main__':
    main()
