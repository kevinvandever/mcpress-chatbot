#!/usr/bin/env python3
"""
Process books using PROVEN components from the original working system
Directly writes to PostgreSQL without going through API endpoints
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
import hashlib
from tqdm import tqdm
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Import YOUR PROVEN WORKING COMPONENTS - same as main.py uses
from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper
from backend.vector_store import VectorStore

load_dotenv()

class ProvenProcessor:
    def __init__(self):
        # Use YOUR EXACT SAME COMPONENTS that worked
        self.pdf_processor = PDFProcessorFull()
        self.category_mapper = get_category_mapper()
        self.vector_store = VectorStore()
        
        self.uploads_dir = Path("backend/uploads")
        self.processed_log = Path("proven_processing_log.json")
        self.processed_books = self.load_processed_log()
        
    def load_processed_log(self) -> Dict:
        """Load log of already processed books"""
        if self.processed_log.exists():
            with open(self.processed_log, 'r') as f:
                return json.load(f)
        return {"processed": [], "failed": [], "timestamp": None}
    
    def save_processed_log(self):
        """Save processing log"""
        self.processed_books["timestamp"] = datetime.now().isoformat()
        with open(self.processed_log, 'w') as f:
            json.dump(self.processed_books, f, indent=2)
    
    async def process_all_books(self):
        """Process all books using the EXACT SAME flow as your working system"""
        print("🚀 Processing Books with PROVEN Components")
        print("=" * 50)
        
        # Initialize the vector store (same as main.py startup)
        await self.vector_store.init_database()
        print("✅ Database initialized")
        
        # Get all PDF files
        pdf_files = list(self.uploads_dir.glob("*.pdf"))
        print(f"📚 Found {len(pdf_files)} PDF files")
        
        # Filter already processed
        if self.processed_books['processed']:
            already_processed = set(self.processed_books['processed'])
            pdf_files = [f for f in pdf_files if f.name not in already_processed]
            print(f"📋 Skipping {len(already_processed)} already processed files")
            print(f"📖 {len(pdf_files)} files to process")
        
        if not pdf_files:
            print("✅ All files already processed!")
            return
        
        # Process each PDF using YOUR EXACT SAME FLOW
        for pdf_file in pdf_files:
            try:
                print(f"\n📚 Processing: {pdf_file.name}")
                
                # Step 1: Process PDF with YOUR PDFProcessorFull
                pdf_data = await self.pdf_processor.process_pdf(str(pdf_file))
                
                # Step 2: Extract title from pdf_data (not filename)
                # Use filename as title if not in metadata
                title = pdf_file.stem  # Default to filename without extension
                
                # Step 3: Get category using YOUR category mapper 
                # The mapper expects (filename, content) after our fix, but content is optional
                category = self.category_mapper.get_category(pdf_file.name, "")
                
                # Step 4: Store using YOUR vector store's add_documents method
                # Format chunks for the vector store
                documents = []
                for i, chunk in enumerate(pdf_data.get('chunks', [])):
                    documents.append({
                        'content': chunk.get('text', chunk.get('content', '')),
                        'page_number': chunk.get('page', 0),
                        'chunk_index': i,
                        'metadata': {
                            'title': title,
                            'author': pdf_data.get('author', 'Unknown'),
                            'category': category,
                            'type': chunk.get('type', 'text')
                        }
                    })
                
                # Store using the vector store's actual method
                if documents:
                    await self.vector_store.add_documents(
                        documents,
                        metadata={
                            'filename': pdf_file.name,
                            'title': title,
                            'author': pdf_data.get('author', 'Unknown'),
                            'category': category,
                            'total_pages': pdf_data.get('total_pages', 0),
                            'has_images': len(pdf_data.get('images', [])) > 0,
                            'has_code': len(pdf_data.get('code_blocks', [])) > 0
                        }
                    )
                    result = True
                else:
                    result = False
                
                if result:
                    print(f"   ✅ Successfully stored {len(pdf_data.get('chunks', []))} chunks")
                    self.processed_books['processed'].append(pdf_file.name)
                else:
                    print(f"   ❌ Failed to store in database")
                    self.processed_books['failed'].append({
                        'filename': pdf_file.name,
                        'error': 'Database storage failed'
                    })
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                self.processed_books['failed'].append({
                    'filename': pdf_file.name,
                    'error': str(e)
                })
            
            # Save progress after each book
            self.save_processed_log()
        
        # Final report
        print("\n" + "="*50)
        print("📊 Processing Complete!")
        print(f"✅ Successfully processed: {len(self.processed_books['processed'])} books")
        print(f"❌ Failed: {len(self.processed_books['failed'])} books")
        
        if self.processed_books['failed']:
            print("\nFailed books:")
            for failure in self.processed_books['failed']:
                print(f"  - {failure['filename']}: {failure['error']}")

async def main():
    processor = ProvenProcessor()
    await processor.process_all_books()

if __name__ == "__main__":
    asyncio.run(main())