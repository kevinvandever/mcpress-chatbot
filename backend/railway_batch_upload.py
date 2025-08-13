#!/usr/bin/env python3
"""
Railway Batch Upload Script - Upload PDFs in controlled batches
Optimized based on connection pooling and timeout lessons learned
"""
import os
import sys
import asyncio
import asyncpg
import json
from pathlib import Path
from typing import List
import logging
import argparse

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
        
        # Upload chunks to database with timeout protection
        uploaded = 0
        chunk_timeout = 5  # 5 second timeout per chunk
        
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
                
                # Insert into database with timeout
                await asyncio.wait_for(
                    conn.execute("""
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
                    ),
                    timeout=chunk_timeout
                )
                
                uploaded += 1
                
                # Progress update every 50 chunks (more frequent)
                if uploaded % 50 == 0:
                    logger.info(f"    Uploaded {uploaded}/{len(chunks)} chunks...")
                    
            except asyncio.TimeoutError:
                logger.warning(f"    Chunk {i} timed out after {chunk_timeout}s, skipping...")
                continue
            except Exception as e:
                logger.error(f"    Error uploading chunk {i}: {e}")
                continue
        
        success_rate = (uploaded / len(chunks)) * 100 if chunks else 0
        logger.info(f"  ✅ Uploaded {uploaded}/{len(chunks)} chunks ({success_rate:.1f}%) for {pdf_name}")
        return uploaded > (len(chunks) * 0.5)  # Success if >50% chunks uploaded
        
    except Exception as e:
        logger.error(f"  ❌ Failed to process {pdf_name}: {e}")
        return False

async def batch_upload(batch_limit: int = None):
    """Main batch upload function with configurable limits"""
    logger.info("=" * 60)
    logger.info("Railway Batch PDF Upload Script")
    logger.info(f"Batch Limit: {batch_limit or 'No limit'}")
    logger.info("=" * 60)
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set!")
        return
    
    # Connect to database with optimized settings
    logger.info("Connecting to database...")
    conn = await asyncpg.connect(
        DATABASE_URL, 
        statement_cache_size=0,
        command_timeout=30,  # 30 second command timeout
        server_settings={
            'application_name': 'batch_upload',
            'tcp_keepalives_idle': '300',
            'tcp_keepalives_interval': '30',
            'tcp_keepalives_count': '3'
        }
    )
    
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
        
        # Apply batch limit
        if batch_limit and batch_limit < len(pdfs_to_upload):
            pdfs_to_upload = pdfs_to_upload[:batch_limit]
            logger.info(f"🎯 Batch mode: Processing only {batch_limit} PDFs")
        
        if not pdfs_to_upload:
            logger.info("✅ All PDFs already uploaded or batch complete!")
            return
        
        # Initialize processors
        processor = PDFProcessor()
        book_manager = BookManager()
        
        # Process PDFs with enhanced error handling
        successful = 0
        failed = []
        
        for i, pdf_path in enumerate(pdfs_to_upload, 1):
            logger.info(f"\n[{i}/{len(pdfs_to_upload)}] Processing {pdf_path.name}")
            
            try:
                success = await process_and_upload_pdf(pdf_path, conn, processor, book_manager)
                
                if success:
                    successful += 1
                    logger.info(f"  ✅ SUCCESS: {pdf_path.name}")
                else:
                    failed.append(pdf_path.name)
                    logger.info(f"  ❌ FAILED: {pdf_path.name}")
                
            except Exception as e:
                logger.error(f"  ❌ EXCEPTION: {pdf_path.name} - {e}")
                failed.append(pdf_path.name)
            
            # Progress summary every 5 PDFs (more frequent)
            if i % 5 == 0:
                logger.info(f"\nBatch Progress: {i}/{len(pdfs_to_upload)} processed, {successful} successful")
                
                # Check database status
                try:
                    total_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
                    total_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
                    logger.info(f"Database Status: {total_docs} documents, {total_chunks:,} chunks")
                except:
                    logger.warning("Could not query database status")
        
        # Final summary
        logger.info("=" * 60)
        logger.info("Batch Upload Complete!")
        logger.info(f"✅ Successful: {successful}/{len(pdfs_to_upload)}")
        logger.info(f"❌ Failed: {len(failed)}")
        
        if failed:
            logger.info("\nFailed uploads:")
            for name in failed[:10]:  # Show first 10 failures
                logger.info(f"  - {name}")
            if len(failed) > 10:
                logger.info(f"  ... and {len(failed) - 10} more")
        
        # Final database status
        try:
            final_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
            final_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
            
            logger.info(f"\nFinal Database Status:")
            logger.info(f"  Documents: {final_docs}")
            logger.info(f"  Total chunks: {final_chunks:,}")
        except Exception as e:
            logger.error(f"Could not get final database status: {e}")
        
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await conn.close()
            logger.info("Database connection closed")
        except:
            pass

def main():
    """Entry point with command line arguments"""
    parser = argparse.ArgumentParser(description='Railway Batch PDF Upload')
    parser.add_argument('--batch-size', type=int, default=15, 
                       help='Number of PDFs to upload in this batch (default: 15)')
    parser.add_argument('--no-limit', action='store_true',
                       help='Upload all remaining PDFs (ignore batch-size)')
    
    args = parser.parse_args()
    
    batch_limit = None if args.no_limit else args.batch_size
    
    # Run the batch upload
    asyncio.run(batch_upload(batch_limit))

if __name__ == "__main__":
    main()