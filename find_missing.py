#!/usr/bin/env python3
"""
Find exactly which documents are missing from ChromaDB
"""

import os
from pathlib import Path
import chromadb

def find_missing_documents():
    # Get all PDF files in uploads
    uploads_dir = Path('backend/uploads')
    all_pdfs = set([f.name for f in uploads_dir.glob('*.pdf')])
    print(f'Total PDF files in uploads: {len(all_pdfs)}')

    # Get documents in ChromaDB  
    client = chromadb.PersistentClient(path='./backend/chroma_db')
    collection = client.get_collection('pdf_documents')
    results = collection.get(limit=200000, include=['metadatas'])

    db_docs = set()
    for meta in results['metadatas']:
        book = meta.get('book') or meta.get('filename', 'Unknown')
        if book != 'Unknown':
            db_docs.add(book)

    print(f'Documents in database: {len(db_docs)}')

    # Find missing documents
    missing = all_pdfs - db_docs
    print(f'\nMissing {len(missing)} documents:')
    for i, doc in enumerate(sorted(missing), 1):
        print(f'  {i}. {doc}')
    
    return missing

if __name__ == "__main__":
    missing = find_missing_documents()