#!/usr/bin/env python3
"""
Upload PDFs directly to Supabase PostgreSQL with pgvector
"""
import os
import sys
import asyncio
import asyncpg
import json
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.append('/Users/kevinvandever/kev-dev/pdf-chatbot/backend')

from pdf_processor import PDFProcessor
from book_manager import BookManager

load_dotenv()

SUPABASE_URL = os.getenv('DATABASE_URL')
PDF_DIR = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"
CURRENT_DOC = "Advanced, Integrated RPG.pdf"

async def upload_pdf_to_supabase(pdf_path, conn):
    """Process and upload a single PDF to Supabase"""
    
    pdf_name = Path(pdf_path).name
    print(f"📄 Processing: {pdf_name}")
    
    try:
        # Initialize processors
        book_manager = BookManager()
        processor = PDFProcessor()
        
        # Extract metadata
        metadata = book_manager.get_book_metadata(pdf_name)
        author = metadata.get('author', 'Unknown')
        category = metadata.get('category', 'General')
        title = metadata.get('title', pdf_name.replace('.pdf', ''))
        
        print(f"   📋 Metadata: {author} | {category}")
        
        # Process PDF and generate chunks with embeddings
        print(f"   🔄 Processing PDF content...")
        
        # Use simplified processing for speed
        chunks = processor.process_pdf_simple(pdf_path)
        
        if not chunks:
            print(f"   ❌ No content extracted")
            return False
        
        print(f"   📊 Generated {len(chunks)} chunks")
        
        # Insert chunks into Supabase
        uploaded_chunks = 0
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding for chunk
                embedding = processor.generate_embedding(chunk['content'])
                if not embedding:
                    continue
                
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                # Create metadata JSON
                chunk_metadata = {
                    'author': author,
                    'category': category,
                    'title': title
                }
                
                # Insert into Supabase
                await conn.execute("""
                    INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5::vector, $6, NOW())
                """, 
                pdf_name,
                chunk['content'],
                chunk.get('page_number', 1),
                i,
                embedding_str,
                json.dumps(chunk_metadata)
                )
                
                uploaded_chunks += 1
                
                # Progress indicator
                if uploaded_chunks % 50 == 0:
                    print(f"     ⏳ Uploaded {uploaded_chunks}/{len(chunks)} chunks...")
                    
            except Exception as e:
                print(f"     ⚠️  Chunk {i} failed: {e}")
                continue
        
        print(f"   ✅ Uploaded {uploaded_chunks}/{len(chunks)} chunks")
        return uploaded_chunks > 0
        
    except Exception as e:
        print(f"   ❌ Processing failed: {e}")
        return False

async def upload_missing_pdfs():
    """Upload all missing PDFs to Supabase"""
    
    print("🚀 Starting direct PDF upload to Supabase...")
    
    # Get list of PDFs to upload
    pdf_files = [f for f in Path(PDF_DIR).glob("*.pdf") if f.name != CURRENT_DOC]
    
    print(f"📚 Found {len(pdf_files)} PDFs to upload")
    
    try:
        # Connect to Supabase
        print("🔍 Connecting to Supabase...")
        conn = await asyncpg.connect(SUPABASE_URL, statement_cache_size=0)
        print("✅ Connected to Supabase")
        
        # Upload PDFs in batches
        batch_size = 5  # Process 5 PDFs at a time
        successful_uploads = 0
        failed_uploads = []
        
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(pdf_files) + batch_size - 1) // batch_size
            
            print(f"\n🔄 Batch {batch_num}/{total_batches}: Processing {len(batch)} PDFs...")
            
            for pdf_path in batch:
                success = await upload_pdf_to_supabase(pdf_path, conn)
                if success:
                    successful_uploads += 1
                else:
                    failed_uploads.append(pdf_path.name)
            
            # Progress update
            progress = (successful_uploads / len(pdf_files)) * 100
            print(f"📊 Progress: {successful_uploads}/{len(pdf_files)} completed ({progress:.1f}%)")
            
            # Check current database status
            if batch_num % 10 == 0:
                total_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
                total_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
                print(f"   📈 Database status: {total_docs} documents, {total_chunks:,} chunks")
        
        # Final summary
        print(f"\n🎉 Upload Complete!")
        print(f"   ✅ Successful: {successful_uploads}/{len(pdf_files)} PDFs")
        print(f"   ❌ Failed: {len(failed_uploads)} PDFs")
        
        if failed_uploads:
            print("   Failed files:")
            for filename in failed_uploads[:10]:  # Show first 10
                print(f"     - {filename}")
        
        # Final database check
        final_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        final_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
        
        print(f"\n📊 Final Database Status:")
        print(f"   Documents: {final_docs}")
        print(f"   Total chunks: {final_chunks:,}")
        
        if final_docs >= 100:  # Expecting ~115 documents
            print("✅ Upload successful! Most documents uploaded.")
        else:
            print("⚠️  Some uploads may have failed - check errors above")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(upload_missing_pdfs())