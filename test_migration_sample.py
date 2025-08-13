#!/usr/bin/env python3
"""
Test migration with just a small sample (10 records)
"""
import os
import asyncio
import asyncpg
import json
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = os.getenv('DATABASE_URL')
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')

async def test_small_migration():
    print("🧪 Testing sample migration (10 records)...")
    
    try:
        print("🔍 Connecting to Railway...")
        railway_conn = await asyncpg.connect(RAILWAY_URL)
        print("✅ Railway connected")
        
        print("🔍 Connecting to Supabase...")
        supabase_conn = await asyncpg.connect(SUPABASE_URL)
        print("✅ Supabase connected")
        
        # Create table in Supabase
        print("🏗️  Creating table...")
        await supabase_conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(500) NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                chunk_index INTEGER,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table created")
        
        # Clear any existing test data
        await supabase_conn.execute("DELETE FROM documents")
        print("🧹 Cleared existing data")
        
        # Get 10 sample records from Railway
        print("📥 Fetching sample data...")
        rows = await railway_conn.fetch("""
            SELECT filename, content, page_number, chunk_index, embedding, metadata, created_at
            FROM documents 
            WHERE embedding IS NOT NULL
            ORDER BY id
            LIMIT 10
        """)
        print(f"✅ Fetched {len(rows)} records")
        
        # Migrate each record
        migrated = 0
        for i, row in enumerate(rows):
            print(f"🔄 Processing record {i+1}/10: {row['filename'][:30]}...")
            
            try:
                if row['embedding']:
                    # Parse embedding
                    if isinstance(row['embedding'], str):
                        embedding_list = json.loads(row['embedding'])
                    else:
                        embedding_list = row['embedding']
                    
                    print(f"   Embedding dims: {len(embedding_list)}")
                    
                    # Convert to vector format
                    embedding_str = f"[{','.join(map(str, embedding_list))}]"
                    
                    # Insert into Supabase
                    await supabase_conn.execute("""
                        INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                    """, 
                    row['filename'],
                    row['content'][:100] + "...",  # Truncate content for test
                    row['page_number'],
                    row['chunk_index'],
                    embedding_str,
                    row['metadata'],
                    row['created_at']
                    )
                    migrated += 1
                    print(f"   ✅ Inserted successfully")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        print(f"\n📊 Test Results:")
        print(f"   Records processed: {len(rows)}")
        print(f"   Successfully migrated: {migrated}")
        
        # Verify data
        supabase_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"   Records in Supabase: {supabase_count}")
        
        if supabase_count > 0:
            print("✅ Sample migration successful!")
            
            # Test vector search
            print("\n🔍 Testing vector search...")
            result = await supabase_conn.fetchrow("""
                SELECT filename, embedding <-> '[0,0,0]' as distance
                FROM documents 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <-> '[0,0,0]'
                LIMIT 1
            """)
            
            if result:
                print(f"✅ Vector search working! Found: {result['filename']}")
            else:
                print("❌ Vector search failed")
        else:
            print("❌ No data migrated")
        
        await railway_conn.close()
        await supabase_conn.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_small_migration())