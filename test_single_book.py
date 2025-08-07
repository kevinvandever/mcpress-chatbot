#!/usr/bin/env python3
"""
Test processing a single book to verify connection handling
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Import proven components
from backend.pdf_processor_full import PDFProcessorFull
from backend.category_mapper import get_category_mapper
from backend.vector_store import VectorStore

load_dotenv()

async def test_single_book():
    print("🧪 Testing single book processing...")
    
    # Initialize components
    pdf_processor = PDFProcessorFull()
    category_mapper = get_category_mapper()
    vector_store = VectorStore()
    
    # Initialize database
    print("🔄 Initializing database...")
    await vector_store.init_database()
    print("✅ Database initialized")
    
    # Get first PDF
    uploads_dir = Path("backend/uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found!")
        return
    
    test_file = pdf_files[0]  # Just test the first one
    print(f"📚 Testing with: {test_file.name}")
    
    try:
        # Process PDF
        print("🔄 Processing PDF...")
        pdf_data = await pdf_processor.process_pdf(str(test_file))
        print(f"✅ PDF processed: {len(pdf_data.get('chunks', []))} chunks")
        
        # Get metadata
        title = test_file.stem
        category = category_mapper.get_category(test_file.name, "")
        print(f"📝 Title: {title}, Category: {category}")
        
        # Format documents
        documents = []
        for i, chunk in enumerate(pdf_data.get('chunks', [])[:10]):  # Only test first 10 chunks
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
        
        print(f"📊 Prepared {len(documents)} documents for storage")
        
        # Store with retry
        print("🔄 Storing in database...")
        for attempt in range(3):
            try:
                await vector_store.add_documents(
                    documents,
                    metadata={
                        'filename': test_file.name,
                        'title': title,
                        'author': pdf_data.get('author', 'Unknown'),
                        'category': category,
                        'total_pages': pdf_data.get('total_pages', 0),
                        'has_images': len(pdf_data.get('images', [])) > 0,
                        'has_code': len(pdf_data.get('code_blocks', [])) > 0
                    }
                )
                print("✅ Successfully stored in database!")
                break
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    print("🔄 Retrying in 3 seconds...")
                    await asyncio.sleep(3)
                    # Reinitialize connection
                    if vector_store.pool:
                        await vector_store.pool.close()
                        vector_store.pool = None
                    await vector_store.init_database()
                else:
                    print("❌ All attempts failed!")
                    return
        
        # Verify storage
        print("🔍 Verifying storage...")
        count = await vector_store.get_document_count()
        print(f"✅ Database now contains {count} document chunks")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        if vector_store.pool:
            await vector_store.pool.close()

if __name__ == "__main__":
    asyncio.run(test_single_book())