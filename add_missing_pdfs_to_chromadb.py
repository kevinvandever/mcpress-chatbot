#!/usr/bin/env python3
"""
Add the 2 missing PDF files to the existing ChromaDB collection
"""

import os
import sys
import chromadb
from chromadb.config import Settings
from pathlib import Path
import asyncio
from typing import List, Dict, Any
import json
import hashlib

# Add backend to path
sys.path.append('backend')

from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper

class ChromaDBUploader:
    def __init__(self):
        self.pdf_processor = PDFProcessorFull()
        self.category_mapper = get_category_mapper()
        
        # Connect to existing ChromaDB
        print("Connecting to ChromaDB...")
        self.client = chromadb.PersistentClient(
            path='./backend/chroma_db', 
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_collection('pdf_documents')
        print(f"Connected to ChromaDB collection: {self.collection.name}")
        
    async def process_pdf(self, pdf_path: str):
        """Process a single PDF and add to ChromaDB"""
        filename = Path(pdf_path).name
        print(f"\\nProcessing: {filename}")
        
        # Check if already exists
        existing = self.collection.get(
            where={'book': filename},
            limit=1
        )
        
        if existing['documents']:
            print(f"  ⚠️  {filename} already exists in ChromaDB - skipping")
            return
        
        try:
            # Process the PDF using your proven processor
            print("  📄 Extracting content...")
            result = await self.pdf_processor.process_pdf(pdf_path)
            chunks = result.get('chunks', [])
            print(f"  📊 Extracted {len(chunks)} chunks")
            
            if not chunks:
                print(f"  ❌ No content extracted from {filename}")
                return
            
            # Prepare for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            category = self.category_mapper.get_category(filename)
            
            for i, chunk in enumerate(chunks):
                # Create unique ID
                content_hash = hashlib.md5(f"{filename}_{i}_{chunk.get('content', '')[:100]}".encode()).hexdigest()
                chunk_id = f"{filename}_{i}_{content_hash[:8]}"
                
                # Prepare document content
                content = chunk.get('content', '')
                if not content.strip():
                    continue
                    
                documents.append(content)
                ids.append(chunk_id)
                
                # Prepare metadata to match existing structure
                metadata = {
                    'book': filename,
                    'chunk_index': i,
                    'page': chunk.get('page', 1),
                    'type': chunk.get('type', 'text'),
                    'category': category,
                    'total_length': len(content),
                    'meaningful_length': len(content.strip())
                }
                
                # Add any additional metadata from the chunk
                if chunk.get('metadata'):
                    metadata.update(chunk['metadata'])
                
                metadatas.append(metadata)
            
            if documents:
                print(f"  📝 Adding {len(documents)} chunks to ChromaDB...")
                
                # Add to ChromaDB collection
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                print(f"  ✅ Successfully added {filename} ({len(documents)} chunks)")
            else:
                print(f"  ⚠️  No valid content chunks found in {filename}")
                
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()

async def main():
    uploader = ChromaDBUploader()
    
    # The 2 missing files
    missing_files = [
        "backend/uploads/mcpressonline.com-From Legacy to Modern_ Upgrading Your BI Strategy with LANSA BI for IBM i.pdf",
        "backend/uploads/mcpressonline.com-Organizing for Data Governance.pdf"
    ]
    
    print(f"Adding {len(missing_files)} missing PDFs to ChromaDB:")
    for pdf_path in missing_files:
        if Path(pdf_path).exists():
            await uploader.process_pdf(pdf_path)
        else:
            print(f"❌ File not found: {pdf_path}")
    
    # Verify final count
    print("\\n📊 Final ChromaDB Status:")
    all_results = uploader.collection.get(include=['metadatas'])
    books = set()
    for metadata in all_results['metadatas']:
        books.add(metadata.get('book', 'Unknown'))
    
    print(f"Total books in ChromaDB: {len(books)}")
    print(f"Total chunks: {len(all_results['metadatas'])}")

if __name__ == "__main__":
    asyncio.run(main())