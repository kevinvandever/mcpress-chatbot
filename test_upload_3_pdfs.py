#!/usr/bin/env python3
"""
Test upload of just 3 PDFs to validate the process
"""
import os
import sys
import asyncio
import asyncpg
import json
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/Users/kevinvandever/kev-dev/pdf-chatbot/backend')

# Simple imports for testing
load_dotenv()

SUPABASE_URL = os.getenv('DATABASE_URL')
PDF_DIR = "/Users/kevinvandever/kev-dev/pdf-chatbot/backend/uploads"

async def test_upload_simple():
    """Test uploading 3 PDFs with minimal processing"""
    
    print("🧪 Testing upload of 3 PDFs to Supabase...")
    
    # Select 3 small PDFs for testing
    test_pdfs = [
        "5 Keys to Business Analytics Program Success.pdf",
        "BYTE-ing Satire.pdf", 
        "From Idea to Print.pdf"
    ]
    
    try:
        # Connect to Supabase
        conn = await asyncpg.connect(SUPABASE_URL, statement_cache_size=0)
        print("✅ Connected to Supabase")
        
        # Check current status
        current_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        current_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"📊 Current: {current_docs} docs, {current_chunks:,} chunks")
        
        for pdf_name in test_pdfs:
            pdf_path = os.path.join(PDF_DIR, pdf_name)
            
            if not os.path.exists(pdf_path):
                print(f"❌ File not found: {pdf_name}")
                continue
            
            print(f"📄 Testing: {pdf_name}")
            
            # Very simple approach - just create a few dummy chunks to test database insertion
            try:
                for i in range(3):  # Just 3 test chunks per PDF
                    # Create a simple embedding (zeros for testing)
                    embedding_str = "[" + ",".join(["0.1"] * 384) + "]"
                    
                    # Simple metadata
                    metadata = {
                        'author': 'Test Author',
                        'category': 'Test',
                        'title': pdf_name.replace('.pdf', '')
                    }
                    
                    # Insert test chunk
                    await conn.execute("""
                        INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5::vector, $6, NOW())
                    """, 
                    pdf_name,
                    f"Test content for {pdf_name} chunk {i+1}",
                    1,
                    i,
                    embedding_str,
                    json.dumps(metadata)
                    )
                
                print(f"   ✅ Added 3 test chunks")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        # Check final status
        final_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        final_chunks = await conn.fetchval("SELECT COUNT(*) FROM documents")
        
        print(f"\n📊 Final: {final_docs} docs, {final_chunks:,} chunks")
        print(f"✅ Added {final_docs - current_docs} new documents")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_upload_simple())