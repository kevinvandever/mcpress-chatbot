#!/usr/bin/env python3
"""
Check Pete Helgren's author record in the database
"""

import requests
import os

API_URL = os.getenv('API_URL', 'https://mcpress-chatbot-production.up.railway.app')

print('=' * 70)
print('PETE HELGREN AUTHOR INVESTIGATION')
print('=' * 70)
print()

# Search for Helgren in authors table
print('Searching author table for Helgren:')
response = requests.get(f'{API_URL}/api/authors/search?q=helgren')
if response.status_code == 200:
    authors = response.json()
    if authors:
        for a in authors:
            print(f'  {a["name"]} (ID: {a["id"]})')
            print(f'    site_url: {a.get("site_url") or "MISSING!"}')
            print(f'    document_count: {a.get("document_count", "N/A")}')
    else:
        print('  No authors found with name containing "helgren"')
else:
    print(f'  Error: {response.status_code}')

print()

# Get books with Helgren as author
print('Books with Helgren as author:')
response = requests.get(f'{API_URL}/api/books?limit=500')
if response.status_code == 200:
    books = response.json().get('books', [])
    for book in books:
        authors = book.get('authors', [])
        if any('helgren' in a.get('name', '').lower() for a in authors):
            title = book.get('title', book['filename'])
            print(f'  Title: {title}')
            for a in authors:
                site = a.get('site_url')
                print(f'    Author: {a["name"]} - site_url: {site or "MISSING!"}')
            print()
