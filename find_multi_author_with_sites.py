#!/usr/bin/env python3
"""
Find books with multiple authors where BOTH authors have websites.
These should show "Authors" (plural) button with dropdown.
"""

import requests
import os

API_URL = os.getenv('API_URL', 'https://mcpress-chatbot-production.up.railway.app')

print('=' * 70)
print('BOOKS WITH MULTIPLE AUTHORS - BOTH HAVE WEBSITES')
print('(These should show "Authors" plural button with dropdown)')
print('=' * 70)
print()

response = requests.get(f'{API_URL}/api/books?limit=500')
if response.status_code != 200:
    print(f'Error: {response.status_code}')
    exit(1)

books = response.json().get('books', [])

# Find books where 2+ authors have websites
multi_author_with_sites = []
for book in books:
    authors = book.get('authors', [])
    authors_with_sites = [a for a in authors if a.get('site_url') and a.get('site_url').strip()]
    
    if len(authors_with_sites) >= 2:
        multi_author_with_sites.append({
            'title': book.get('title', book['filename']),
            'document_type': book.get('document_type'),
            'authors': authors_with_sites
        })

print(f'Found {len(multi_author_with_sites)} books with 2+ authors having websites:')
print()

for i, book in enumerate(multi_author_with_sites[:20], 1):
    print(f'{i}. {book["title"]}')
    print(f'   Type: {book["document_type"]}')
    for a in book['authors']:
        print(f'   - {a["name"]}: {a.get("site_url", "N/A")}')
    print()

if len(multi_author_with_sites) > 20:
    print(f'... and {len(multi_author_with_sites) - 20} more')

print()
print('=' * 70)
print('SUMMARY')
print('=' * 70)
print(f'Total books with 2+ authors having websites: {len(multi_author_with_sites)}')
print()
print('To test the "Authors" dropdown, search for any of these titles in the chatbot.')
