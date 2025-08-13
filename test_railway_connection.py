#!/usr/bin/env python3
"""
Test Railway PostgreSQL connection and check current data
"""
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def test_railway_connection():
    """Test Railway connection and verify data"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set in environment")
        print("Please set your Railway DATABASE_URL in .env file")
        return
    
    try:
        print("🔍 Testing Railway connection...")
        print(f"Connection string: {DATABASE_URL[:30]}...")
        
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to Railway PostgreSQL!")
        
        # Check document count
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"📊 Total chunks: {doc_count:,}")
        
        # Check unique document count  
        unique_docs = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        print(f"📖 Unique documents: {unique_docs}")
        
        # Check if embeddings exist
        with_embeddings = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
        print(f"🧠 Chunks with embeddings: {with_embeddings:,}")
        
        # Show sample filenames
        sample_docs = await conn.fetch("SELECT DISTINCT filename FROM documents LIMIT 5")
        print("\n📚 Sample documents:")
        for row in sample_docs:
            print(f"   - {row['filename']}")
        
        await conn.close()
        
        print("\n✅ Railway database is ready for migration!")
        return True
        
    except Exception as e:
        print(f"❌ Railway connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_railway_connection())