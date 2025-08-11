#!/usr/bin/env python3
"""
Fix missing documents by re-processing them with fallback author values
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper
from backend.vector_store_chroma import ChromaVectorStore

async def fix_missing_documents():
    """Process the 6 missing documents with author fallback"""
    
    missing_files = [
        'IBM i5-iSeries Primer.pdf',
        'Programming Portlets.pdf',
        'An Introduction to IBM Rational Application Developer.pdf',
        'Identity Management- A Business Perspective.pdf',  # Check if missing
        'Identity Management.pdf',  # Check if missing
        'BYTE-ing Satire.pdf'  # Check if missing
    ]
    
    pdf_processor = PDFProcessorFull()
    category_mapper = get_category_mapper()
    
    os.environ['CHROMA_DB_PATH'] = './backend/chroma_db'
    vector_store = ChromaVectorStore()
    
    uploads_dir = Path("backend/uploads")
    
    for filename in missing_files:
        pdf_path = uploads_dir / filename
        if not pdf_path.exists():
            print(f"❌ File not found: {filename}")
            continue
            
        print(f"\n📖 Processing: {filename}")
        
        try:
            # Process the PDF
            extracted_content = await pdf_processor.process_pdf(str(pdf_path))
            
            # Get metadata
            category = category_mapper.get_category(filename)
            author = extracted_content.get('author')
            
            # Use fallback if author is None
            if author is None or author == '':
                author = 'Unknown Author'
                print(f"  ⚠️ Using fallback author: {author}")
            
            print(f"  📊 Extracted: {len(extracted_content['chunks'])} chunks")
            print(f"  📝 Metadata: Category={category}, Author={author}")
            
            # Store with non-None author
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata={
                    "filename": filename,
                    "total_pages": extracted_content["total_pages"],
                    "has_images": len(extracted_content.get("images", [])) > 0,
                    "has_code": len(extracted_content.get("code_blocks", [])) > 0,
                    "category": category,
                    "title": filename.replace('.pdf', ''),
                    "author": author  # Now guaranteed not None
                }
            )
            
            print(f"  ✅ Successfully added to database")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    print("Fixing missing documents with author fallback...")
    asyncio.run(fix_missing_documents())