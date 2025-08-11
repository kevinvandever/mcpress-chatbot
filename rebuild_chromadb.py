#!/usr/bin/env python3
"""
Rebuild ChromaDB using the proven processing components
Uses the exact same PDF processing pipeline as the working system
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Import PROVEN WORKING COMPONENTS - same as main.py uses
from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper
from backend.vector_store_chroma import ChromaVectorStore

load_dotenv()

class ChromaDBRebuilder:
    def __init__(self):
        # Use YOUR EXACT SAME COMPONENTS that worked
        self.pdf_processor = PDFProcessorFull()
        self.category_mapper = get_category_mapper()
        
        # Use ChromaDB instead of PostgreSQL
        os.environ['CHROMA_DB_PATH'] = './backend/chroma_db'
        self.vector_store = ChromaVectorStore()
        
        self.uploads_dir = Path("backend/uploads")
        
    async def rebuild_database(self):
        """Rebuild ChromaDB using the EXACT SAME flow as your working system"""
        print("🚀 Rebuilding ChromaDB with PROVEN Components")
        print("=" * 50)
        
        # Get all PDF files
        pdf_files = list(self.uploads_dir.glob("*.pdf"))
        print(f"📚 Found {len(pdf_files)} PDF files")
        
        if not pdf_files:
            print("❌ No PDF files found!")
            return
        
        successful = 0
        failed = 0
        
        # Process each file using the PROVEN pipeline
        for i, pdf_path in enumerate(tqdm(pdf_files, desc="Processing PDFs")):
            try:
                print(f"\n📖 Processing {i+1}/{len(pdf_files)}: {pdf_path.name}")
                
                # STEP 1: Extract content using PROVEN processor
                # This handles text extraction, code detection, image processing, author extraction
                extracted_content = await self.pdf_processor.process_pdf(str(pdf_path))
                
                print(f"  📊 Extracted: {len(extracted_content['chunks'])} chunks, "
                      f"{len(extracted_content.get('images', []))} images, "
                      f"{len(extracted_content.get('code_blocks', []))} code blocks")
                
                # STEP 2: Get metadata using PROVEN mapper
                category = self.category_mapper.get_category(pdf_path.name)
                author = extracted_content.get('author', 'Unknown')
                
                print(f"  📝 Metadata: Category={category}, Author={author}")
                
                # STEP 3: Store using PROVEN method (same as main.py)
                await self.vector_store.add_documents(
                    documents=extracted_content["chunks"],
                    metadata={
                        "filename": pdf_path.name,
                        "total_pages": extracted_content["total_pages"],
                        "has_images": len(extracted_content.get("images", [])) > 0,
                        "has_code": len(extracted_content.get("code_blocks", [])) > 0,
                        "category": category,
                        "title": pdf_path.name.replace('.pdf', ''),
                        "author": author
                    }
                )
                
                print(f"  ✅ Successfully stored {len(extracted_content['chunks'])} chunks")
                successful += 1
                
            except Exception as e:
                print(f"  ❌ Error processing {pdf_path.name}: {e}")
                failed += 1
                continue
        
        print("\n" + "=" * 50)
        print(f"🎉 Rebuild Complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total processed: {successful + failed}")
        
        # Verify the rebuild
        print("\n🔍 Verifying rebuild...")
        try:
            documents = await self.vector_store.list_documents()
            doc_count = len(documents.get('documents', []))
            print(f"✅ Database now contains {doc_count} documents")
        except Exception as e:
            print(f"❌ Error verifying rebuild: {e}")

async def main():
    print("=" * 60)
    print("CHROMADB REBUILD SCRIPT")
    print("This will rebuild ChromaDB using the proven processing pipeline")
    print("Text extraction + Code detection + Image processing + Author extraction")
    print("=" * 60)
    
    rebuilder = ChromaDBRebuilder()
    await rebuilder.rebuild_database()

if __name__ == "__main__":
    asyncio.run(main())