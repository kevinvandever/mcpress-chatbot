#!/usr/bin/env python3
"""Reprocess a single PDF to update vector store with improved code detection"""

import asyncio
import sys
import os
from pathlib import Path
from pdf_processor import PDFProcessor
from vector_store_chroma import ChromaVectorStore
from category_mapper import get_category_mapper
from dotenv import load_dotenv

load_dotenv()

# Don't override the path - let it use the default from vector_store_chroma.py
# which will be ./backend/chroma_db when running from project root
# or ./chroma_db when running from backend directory

async def reprocess_single_pdf(pdf_name: str):
    """Reprocess a single PDF"""
    
    pdf_path = Path(f"./uploads/{pdf_name}")
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📖 Processing: {pdf_name}")
    
    # Initialize components
    pdf_processor = PDFProcessor()
    vector_store = ChromaVectorStore()
    category_mapper = get_category_mapper()
    
    try:
        # First, delete existing documents for this PDF
        print("🗑️  Removing old entries...")
        # ChromaDB doesn't have a direct way to delete by filename, 
        # so we'll need to search and delete
        
        # Process with new detection
        print("🔄 Processing with updated code detection...")
        extracted_content = await pdf_processor.process_pdf(str(pdf_path))
        
        # Count code blocks
        languages = {}
        for chunk in extracted_content['chunks']:
            if chunk['metadata'].get('type') == 'code':
                lang = chunk['metadata'].get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            print(f"📊 Code blocks detected:")
            for lang, count in sorted(languages.items()):
                print(f"   {lang}: {count}")
        
        # Get category
        category = category_mapper.get_category(pdf_name)
        
        # Create metadata
        metadata = {
            'filename': pdf_name,
            'category': category,
            'author': 'Unknown'  # Would need author extraction
        }
        
        # Store in vector store
        print("💾 Storing in vector database...")
        await vector_store.add_documents(
            extracted_content['chunks'],
            metadata
        )
        
        print(f"✅ Successfully reprocessed {pdf_name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_name = sys.argv[1]
    else:
        pdf_name = "Subfiles in Free-Format RPG.pdf"
    
    print("=" * 60)
    print(f"REPROCESSING: {pdf_name}")
    print("=" * 60)
    
    asyncio.run(reprocess_single_pdf(pdf_name))