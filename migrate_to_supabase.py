#!/usr/bin/env python3
"""
Migrate PDF documents from Railway PostgreSQL to Supabase PostgreSQL with pgvector
"""
import os
import asyncio
import asyncpg
import json
from dotenv import load_dotenv

load_dotenv()

# Connection strings
RAILWAY_URL = os.getenv('DATABASE_URL')  # Current Railway database
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')  # Supabase database

if not RAILWAY_URL:
    print("❌ RAILWAY DATABASE_URL not set in environment")
    exit(1)
    
if not SUPABASE_URL:
    print("❌ SUPABASE_DATABASE_URL not set in environment")
    print("Please set SUPABASE_DATABASE_URL in your .env file")
    print("Format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres")
    exit(1)

async def migrate_documents():
    """Migrate all documents from Railway to Supabase"""
    
    print("🔍 Connecting to databases...")
    
    # Connect to both databases
    railway_conn = await asyncpg.connect(RAILWAY_URL)
    supabase_conn = await asyncpg.connect(SUPABASE_URL)
    
    try:
        print("✅ Connected to both databases")
        
        # Create the documents table in Supabase with proper vector column
        print("🏗️  Creating documents table in Supabase...")
        await supabase_conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(500) NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                chunk_index INTEGER,
                embedding vector(384),  -- pgvector column for 384-dimensional embeddings
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vector index for fast similarity search
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        # Create other indexes
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename)
        """)
        
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING gin (metadata)
        """)
        
        print("✅ Table and indexes created")
        
        # Get total count from Railway
        total_count = await railway_conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"📊 Found {total_count:,} chunks to migrate")
        
        # Migrate in batches
        batch_size = 1000
        migrated = 0
        
        for offset in range(0, total_count, batch_size):
            print(f"🔄 Migrating batch {offset//batch_size + 1}/{(total_count + batch_size - 1)//batch_size}...")
            
            # Fetch batch from Railway
            rows = await railway_conn.fetch("""
                SELECT filename, content, page_number, chunk_index, embedding, metadata, created_at
                FROM documents 
                ORDER BY id
                LIMIT $1 OFFSET $2
            """, batch_size, offset)
            
            # Insert batch into Supabase
            for row in rows:
                # Parse embedding from JSON if needed
                if row['embedding']:
                    if isinstance(row['embedding'], str):
                        embedding_list = json.loads(row['embedding'])
                    else:
                        embedding_list = row['embedding']
                    
                    # Convert embedding list to pgvector format
                    embedding_str = f"[{','.join(map(str, embedding_list))}]"
                    
                    # Insert with proper vector format
                    await supabase_conn.execute("""
                        INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                    """, 
                    row['filename'],
                    row['content'],
                    row['page_number'],
                    row['chunk_index'],
                    embedding_str,  # pgvector string format
                    row['metadata'],
                    row['created_at']
                    )
                    migrated += 1
            
            print(f"✅ Migrated {migrated:,}/{total_count:,} chunks")
        
        # Verify migration
        supabase_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"\n🎉 Migration complete!")
        print(f"   Railway: {total_count:,} chunks")
        print(f"   Supabase: {supabase_count:,} chunks")
        
        if supabase_count == total_count:
            print("✅ All data migrated successfully!")
        else:
            print("⚠️  Counts don't match - please investigate")
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await railway_conn.close()
        await supabase_conn.close()

async def test_vector_search(supabase_url):
    """Test vector search functionality"""
    print("\n🧪 Testing vector search...")
    
    conn = await asyncpg.connect(supabase_url)
    
    try:
        # Test basic vector query with proper vector format
        result = await conn.fetchrow("""
            SELECT filename, content[1:100] as sample_content, embedding <-> $1::vector as distance
            FROM documents 
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> $1::vector
            LIMIT 1
        """, '[0,0,0]' + ',0' * 381)  # 384-dimensional zero vector
        
        if result:
            print("✅ Vector search working!")
            print(f"   Found: {result['filename']}")
        else:
            print("❌ No results found")
            
    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    print("🚀 Starting Railway to Supabase migration...")
    asyncio.run(migrate_documents())
    
    # Test vector search
    if SUPABASE_URL:
        asyncio.run(test_vector_search(SUPABASE_URL))