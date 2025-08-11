#!/usr/bin/env python3
"""
Script to reprocess all PDFs with updated code detection patterns.
This will clear the existing vector store and reprocess all PDFs in the uploads folder.
"""

import os
import sys
import asyncio
from pathlib import Path
import chromadb
from dotenv import load_dotenv

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_processor import PDFProcessor
from vector_store_chroma import ChromaVectorStore
from category_mapper import get_category_mapper

load_dotenv()

async def reprocess_all_pdfs():
    """Reprocess all PDFs in the uploads folder"""
    
    print("🔄 Starting PDF reprocessing with updated code detection...")
    
    # Initialize components
    pdf_processor = PDFProcessor()
    
    # Clear existing ChromaDB collection
    print("🗑️  Clearing existing vector store...")
    persist_directory = "./chroma_db"
    client = chromadb.PersistentClient(path=persist_directory)
    
    try:
        # Delete the existing collection if it exists
        client.delete_collection("pdf_documents")
        print("✅ Deleted existing collection")
    except Exception as e:
        print(f"ℹ️  No existing collection to delete: {e}")
    
    # Recreate vector store
    vector_store = ChromaVectorStore()
    print("✅ Created new vector store")
    
    # Get category mapper
    category_mapper = get_category_mapper()
    
    # Find all PDFs in uploads folder
    uploads_dir = Path("./uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads folder")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n📖 Processing {i}/{len(pdf_files)}: {pdf_path.name}")
        
        try:
            # Extract content with updated code detection
            extracted_content = await pdf_processor.process_pdf(str(pdf_path))
            
            # Count code blocks by language
            code_languages = {}
            for chunk in extracted_content.get('chunks', []):
                if chunk.get('metadata', {}).get('type') == 'code':
                    lang = chunk.get('metadata', {}).get('language', 'unknown')
                    code_languages[lang] = code_languages.get(lang, 0) + 1
            
            if code_languages:
                print(f"  📊 Code blocks found: {code_languages}")
            
            # Get metadata
            metadata = category_mapper.get_metadata(pdf_path.name)
            
            # Store in vector store
            await vector_store.add_document(
                extracted_content, 
                pdf_path.name,
                metadata
            )
            
            print(f"  ✅ Successfully processed and stored")
            
        except Exception as e:
            print(f"  ❌ Error processing {pdf_path.name}: {e}")
            continue
    
    print("\n✨ Reprocessing complete!")
    print("🎯 The vector store has been updated with improved RPG/DDS code detection")

if __name__ == "__main__":
    print("=" * 60)
    print("PDF REPROCESSING SCRIPT")
    print("This will clear and rebuild the vector store with updated code detection")
    print("=" * 60)
    
    response = input("\n⚠️  This will DELETE all existing data. Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        asyncio.run(reprocess_all_pdfs())
    else:
        print("❌ Reprocessing cancelled")