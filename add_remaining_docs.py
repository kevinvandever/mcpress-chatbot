#!/usr/bin/env python3
"""
Add the remaining 5 documents to complete the collection
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

async def add_remaining_documents():
    """Add the 5 remaining missing documents"""
    
    missing_files = [
        'Advanced Java EE Development for Rational Application Developer 7.5.pdf',
        'An Introduction to IBM Rational Application Developer.pdf',
        'IBM System i APIs at Work.pdf',
        'Programming Portlets.pdf',
        'The Modern RPG IV Language.pdf'
    ]
    
    print("🔄 Adding remaining 5 documents...")
    
    pdf_processor = PDFProcessorFull()
    category_mapper = get_category_mapper()
    
    os.environ['CHROMA_DB_PATH'] = './backend/chroma_db'
    vector_store = ChromaVectorStore()
    
    uploads_dir = Path("backend/uploads")
    
    successful = 0
    failed = 0
    
    for filename in missing_files:
        pdf_path = uploads_dir / filename
        if not pdf_path.exists():
            print(f"❌ File not found: {filename}")
            failed += 1
            continue
            
        print(f"\n📖 Processing: {filename}")
        
        try:
            # Process the PDF
            extracted_content = await pdf_processor.process_pdf(str(pdf_path))
            
            # Get metadata
            category = category_mapper.get_category(filename)
            author = extracted_content.get('author')
            
            # Ensure author is not None (ChromaDB requirement)
            if author is None or author == '' or author == 'None':
                author = 'Unknown Author'
                print(f"  ⚠️ Using fallback author: {author}")
            else:
                print(f"  ✅ Author: {author}")
            
            print(f"  📊 Extracted: {len(extracted_content['chunks'])} chunks, {len(extracted_content.get('images', []))} images, {len(extracted_content.get('code_blocks', []))} code blocks")
            print(f"  📝 Category: {category}")
            
            # Create metadata ensuring no None values
            metadata = {
                "filename": filename,
                "total_pages": extracted_content["total_pages"],
                "has_images": len(extracted_content.get("images", [])) > 0,
                "has_code": len(extracted_content.get("code_blocks", [])) > 0,
                "category": category or "Unknown",
                "title": filename.replace('.pdf', ''),
                "author": author  # Guaranteed not None
            }
            
            # Double-check metadata for None values
            for key, value in metadata.items():
                if value is None:
                    metadata[key] = "Unknown" if key == "author" else ""
                    print(f"  🔧 Fixed None value for {key}")
            
            # Store in ChromaDB
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata=metadata
            )
            
            print(f"  ✅ Successfully added to database!")
            successful += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            print(f"  📋 Full error: {traceback.format_exc()}")
            failed += 1

    print(f"\n🎉 Processing Complete!")
    print(f"✅ Successfully added: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total expected: 115")

if __name__ == "__main__":
    # Suppress tokenizer warnings
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    asyncio.run(add_remaining_documents())