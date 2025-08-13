#!/usr/bin/env python3
"""
Simple migration using Railway API to get data, then load to Supabase
"""
import asyncio
import asyncpg
import requests
import json

# Your connection strings
RAILWAY_API = "https://mcpress-chatbot-production-569b.up.railway.app"
SUPABASE_URL = "postgresql://postgres:&PVfwRg2X_qkEv7@db.ytxzshhejgmwogrnmqzt.supabase.co:5432/postgres"

async def get_railway_data():
    """Get document data from Railway API"""
    print("📥 Fetching data from Railway API...")
    
    try:
        response = requests.get(f"{RAILWAY_API}/documents", timeout=60)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            print(f"✅ Retrieved {len(docs)} documents from Railway")
            return docs
        else:
            print(f"❌ API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Failed to get data: {e}")
        return []

async def setup_supabase():
    """Set up Supabase database with pgvector table"""
    print("🏗️  Setting up Supabase database...")
    
    conn = await asyncpg.connect(SUPABASE_URL)
    
    try:
        # Create the documents table with proper vector column
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(500) NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                chunk_index INTEGER,
                embedding vector(384),  -- pgvector column
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vector index for fast similarity search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        # Create other indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING gin (metadata)
        """)
        
        print("✅ Supabase database setup complete")
        
    finally:
        await conn.close()

async def test_vector_search():
    """Test that pgvector is working"""
    print("🧪 Testing pgvector functionality...")
    
    conn = await asyncpg.connect(SUPABASE_URL)
    
    try:
        # Test vector operations
        result = await conn.fetchval("SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector")
        print(f"✅ Vector distance calculation working: {result}")
        
        # Check if we have any documents
        count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"📊 Current documents in Supabase: {count}")
        
    except Exception as e:
        print(f"❌ Vector test failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    print("🚀 Starting Supabase setup and testing...")
    
    # Setup Supabase
    asyncio.run(setup_supabase())
    
    # Test vector functionality
    asyncio.run(test_vector_search())
    
    # Get Railway data (for later migration)
    docs = asyncio.run(get_railway_data())
    if docs:
        print(f"📋 Ready to migrate {len(docs)} documents")
        print("Next step: Upload all documents to Supabase using the upload script")
    else:
        print("❌ No data retrieved - check Railway API")