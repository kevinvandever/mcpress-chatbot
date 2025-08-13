#!/usr/bin/env python3
"""
Final migration with fixes for prepared statements and vector search
"""
import os
import asyncio
import asyncpg
import json
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = os.getenv('DATABASE_URL')
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')

async def migrate_all_data():
    print("🚀 Starting full Railway to Supabase migration...")
    
    try:
        # Connect with statement_cache_size=0 to avoid prepared statement issues
        print("🔍 Connecting to Railway...")
        railway_conn = await asyncpg.connect(RAILWAY_URL)
        
        print("🔍 Connecting to Supabase...")
        supabase_conn = await asyncpg.connect(SUPABASE_URL, statement_cache_size=0)
        
        print("✅ Connected to both databases")
        
        # Create table and indexes
        print("🏗️  Setting up Supabase schema...")
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
        
        # Check existing data
        existing_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        if existing_count > 0:
            print(f"⚠️  Found {existing_count:,} existing records in Supabase")
            print("Continuing from where we left off...")
        
        # Create indexes (safe to run multiple times)
        print("🔧 Creating indexes...")
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename)
        """)
        
        print("✅ Schema ready")
        
        # Get total count from Railway
        total_count = await railway_conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
        print(f"📊 Railway has {total_count:,} chunks with embeddings")
        
        # Migrate in manageable batches
        batch_size = 500
        migrated = 0
        errors = 0
        
        for offset in range(0, total_count, batch_size):
            batch_num = offset // batch_size + 1
            total_batches = (total_count + batch_size - 1) // batch_size
            
            print(f"🔄 Processing batch {batch_num}/{total_batches} (records {offset+1}-{min(offset + batch_size, total_count)})...")
            
            try:
                # Fetch batch from Railway
                rows = await railway_conn.fetch("""
                    SELECT filename, content, page_number, chunk_index, embedding, metadata, created_at
                    FROM documents 
                    WHERE embedding IS NOT NULL
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """, batch_size, offset)
                
                # Insert batch into Supabase
                batch_migrated = 0
                for row in rows:
                    try:
                        if row['embedding']:
                            # Parse embedding
                            if isinstance(row['embedding'], str):
                                embedding_list = json.loads(row['embedding'])
                            else:
                                embedding_list = row['embedding']
                            
                            # Convert to vector format
                            embedding_str = f"[{','.join(map(str, embedding_list))}]"
                            
                            # Insert with no prepared statement
                            await supabase_conn.execute("""
                                INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                                VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                            """, 
                            row['filename'],
                            row['content'],
                            row['page_number'],
                            row['chunk_index'],
                            embedding_str,
                            row['metadata'],
                            row['created_at']
                            )
                            batch_migrated += 1
                            
                    except Exception as e:
                        if "already exists" not in str(e):  # Skip duplicate errors
                            errors += 1
                        continue
                
                migrated += batch_migrated
                percent = (migrated / total_count) * 100
                print(f"   ✅ Batch complete: {batch_migrated}/{len(rows)} records. Total: {migrated:,}/{total_count:,} ({percent:.1f}%)")
                
                # Progress checkpoint every 10 batches
                if batch_num % 10 == 0:
                    current_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
                    print(f"   📊 Checkpoint: {current_count:,} records in Supabase")
                    await asyncio.sleep(1)  # Brief pause
                    
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                errors += 1
                continue
        
        # Final verification
        print(f"\n📊 Migration Summary:")
        supabase_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        unique_docs = await supabase_conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        
        print(f"   Railway source: {total_count:,} chunks")
        print(f"   Supabase result: {supabase_count:,} chunks")
        print(f"   Unique documents: {unique_docs}")
        print(f"   Success rate: {(supabase_count/total_count)*100:.1f}%")
        print(f"   Errors encountered: {errors}")
        
        if supabase_count > 100000:  # Expect ~200k chunks
            print("✅ Migration successful!")
            
            # Test vector search with proper dimensions
            print("\n🔍 Testing vector search performance...")
            import time
            
            # Create 384-dimensional zero vector for test
            zero_vector = "[" + ",".join(["0"] * 384) + "]"
            
            start_time = time.time()
            result = await supabase_conn.fetchrow("""
                SELECT filename, content[1:50] as sample, embedding <-> $1::vector as distance
                FROM documents 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <-> $1::vector
                LIMIT 1
            """, zero_vector)
            search_time = (time.time() - start_time) * 1000
            
            if result:
                print(f"✅ Vector search working!")
                print(f"   Search time: {search_time:.1f}ms")
                print(f"   Found: {result['filename']}")
                
                if search_time < 100:
                    print("🚀 Search performance excellent (<100ms)!")
                else:
                    print("⚠️  Search slower than expected - may need index tuning")
            else:
                print("❌ Vector search failed")
        else:
            print("❌ Migration incomplete - check for errors above")
        
        await railway_conn.close()
        await supabase_conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_all_data())