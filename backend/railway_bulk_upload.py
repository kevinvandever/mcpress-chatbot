#!/usr/bin/env python3
"""
Railway Bulk Upload Script - Runs directly on Railway to upload all PDFs
This script will be deployed to Railway where it has direct access to Supabase
"""
import os
import sys
import asyncio
import asyncpg
import json
from pathlib import Path
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the PDF processor and book manager
from pdf_processor import PDFProcessor
from book_manager import BookManager

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/app/backend/uploads')

async def get_uploaded_files(conn) -> List[str]:
    """Get list of already uploaded files"""
    try:
        rows = await conn.fetch("SELECT DISTINCT filename FROM documents")
        return [row['filename'] for row in rows]
    except Exception as e:
        logger.error(f"Error getting uploaded files: {e}")
        return []

async def process_and_upload_pdf(pdf_path: Path, conn, processor: PDFProcessor, book_manager: BookManager) -> bool:
    """Process a single PDF and upload to Supabase"""
    pdf_name = pdf_path.name
    
    try:
        logger.info(f"Processing: {pdf_name}")
        
        # Get metadata
        metadata = book_manager.get_book_metadata(pdf_name)
        author = metadata.get('author', 'Unknown')
        category = metadata.get('category', 'General')
        title = metadata.get('title', pdf_name.replace('.pdf', ''))
        
        logger.info(f"  Metadata: Author={author}, Category={category}")
        
        # Process PDF - use simple processing for speed
        chunks = processor.process_pdf_simple(str(pdf_path))
        
        if not chunks:
            logger.warning(f"  No content extracted from {pdf_name}")
            return False
        
        logger.info(f"  Generated {len(chunks)} chunks")
        
        # Upload chunks to database
        uploaded = 0
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding = processor.generate_embedding(chunk['content'])
                if not embedding or len(embedding) != 384:
                    continue
                
                # Convert to pgvector format
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                # Prepare metadata
                chunk_metadata = {
                    'author': author,
                    'category': category,
                    'title': title,
                    'total_pages': chunk.get('total_pages', 1)
                }
                
                # Insert into database
                await conn.execute("""
                    INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5::vector, $6, NOW())
                    ON CONFLICT DO NOTHING
                """, 
                pdf_name,
                chunk['content'],
                chunk.get('page_number', 1),
                i,
                embedding_str,
                json.dumps(chunk_metadata)
                )
                
                uploaded += 1
                
                # Progress update
                if uploaded % 100 == 0:
                    logger.info(f"    Uploaded {uploaded}/{len(chunks)} chunks...")
                    
            except Exception as e:
                logger.error(f"    Error uploading chunk {i}: {e}")
                continue
        
        logger.info(f"  ✅ Uploaded {uploaded}/{len(chunks)} chunks for {pdf_name}")
        return uploaded > 0
        
    except Exception as e:
        logger.error(f"  ❌ Failed to process {pdf_name}: {e}")
        return False

async def bulk_upload():
    """Main bulk upload function"""
    logger.info("=" * 60)
    logger.info("Railway Bulk PDF Upload Script")
    logger.info("=" * 60)
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set!")
        return
    
    # Connect to database
    logger.info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
    
    try:
        # Get already uploaded files
        uploaded_files = await get_uploaded_files(conn)
        logger.info(f"Found {len(uploaded_files)} already uploaded files")
        
        # Get list of PDFs to upload
        pdf_dir = Path(UPLOAD_DIR)
        if not pdf_dir.exists():
            logger.error(f"Upload directory not found: {UPLOAD_DIR}")
            return
        
        all_pdfs = sorted(pdf_dir.glob("*.pdf"))
        logger.info(f"Found {len(all_pdfs)} total PDFs in {UPLOAD_DIR}")
        
        # Filter out already uploaded
        pdfs_to_upload = [p for p in all_pdfs if p.name not in uploaded_files]
        logger.info(f"Need to upload {len(pdfs_to_upload)} new PDFs")
        
        if not pdfs_to_upload:
            logger.info("✅ All PDFs already uploaded!")
            return
        
        # Initialize processors
        processor = PDFProcessor()
        book_manager = BookManager()
        
        # Process PDFs
        successful = 0
        failed = []
        
        for i, pdf_path in enumerate(pdfs_to_upload, 1):
            logger.info(f"\n[{i}/{len(pdfs_to_upload)}] Processing {pdf_path.name}")
            
            success = await process_and_upload_pdf(pdf_path, conn, processor, book_manager)
            
            if success:
                successful += 1
            else:
                failed.append(pdf_path.name)
            
            # Progress summary every 10 PDFs
            if i % 10 == 0:
                logger.info(f"\nProgress: {i}/{len(pdfs_to_upload)} processed, {successful} successful")
                
                # Check database status
                total_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
                total_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
                logger.info(f"Database: {total_docs} documents, {total_chunks:,} chunks")
        
        # Final summary
        logger.info("=" * 60)
        logger.info("Upload Complete!")
        logger.info(f"✅ Successful: {successful}/{len(pdfs_to_upload)}")
        logger.info(f"❌ Failed: {len(failed)}")
        
        if failed:
            logger.info("\nFailed uploads:")
            for name in failed[:20]:
                logger.info(f"  - {name}")
        
        # Final database status
        final_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        final_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
        
        logger.info(f"\nFinal Database Status:")
        logger.info(f"  Documents: {final_docs}")
        logger.info(f"  Total chunks: {final_chunks:,}")
        
    except Exception as e:
        logger.error(f"Bulk upload failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    # Run the bulk upload
    asyncio.run(bulk_upload())