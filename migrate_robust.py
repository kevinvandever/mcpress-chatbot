#!/usr/bin/env python3
"""
Robust migration with retry logic and smaller batches
"""
import os
import asyncio
import asyncpg
import json
import time
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = os.getenv('DATABASE_URL')
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')

async def connect_with_retry(url, max_retries=3):
    """Connect with retry logic"""
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(url)
            return conn
        except Exception as e:
            print(f"   Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                raise

async def migrate_robust():
    """Robust migration with retry and smaller batches"""
    
    print("🚀 Starting robust Railway to Supabase migration...")
    
    # Connect with retries
    print("🔍 Connecting to Railway...")
    railway_conn = await connect_with_retry(RAILWAY_URL)
    
    print("🔍 Connecting to Supabase...")  
    supabase_conn = await connect_with_retry(SUPABASE_URL)
    
    try:
        print("✅ Connected to both databases")
        
        # Create table in Supabase
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
        
        # Check if table already has data
        existing_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        if existing_count > 0:
            print(f"⚠️  Found {existing_count:,} existing records in Supabase")
            response = input("Do you want to clear and restart? (y/N): ")
            if response.lower() == 'y':
                await supabase_conn.execute("DELETE FROM documents")
                print("🧹 Cleared existing data")
            else:
                print("📊 Continuing with existing data...")
                return
        
        # Create indexes
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        await supabase_conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename)
        """)
        
        print("✅ Schema ready")
        
        # Get total count
        total_count = await railway_conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
        print(f"📊 Found {total_count:,} chunks with embeddings to migrate")
        
        # Use smaller batches for stability
        batch_size = 100
        migrated = 0
        
        for offset in range(0, total_count, batch_size):
            batch_num = offset // batch_size + 1
            total_batches = (total_count + batch_size - 1) // batch_size
            
            print(f"🔄 Processing batch {batch_num}/{total_batches} ({offset}-{min(offset + batch_size, total_count)})...")
            
            try:
                # Fetch batch from Railway
                rows = await railway_conn.fetch("""
                    SELECT filename, content, page_number, chunk_index, embedding, metadata, created_at
                    FROM documents 
                    WHERE embedding IS NOT NULL
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """, batch_size, offset)
                
                # Process each row
                for i, row in enumerate(rows):
                    try:
                        if row['embedding']:
                            # Parse embedding
                            if isinstance(row['embedding'], str):
                                embedding_list = json.loads(row['embedding'])
                            else:
                                embedding_list = row['embedding']
                            
                            # Convert to vector format
                            embedding_str = f"[{','.join(map(str, embedding_list))}]"
                            
                            # Insert
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
                            migrated += 1
                            
                    except Exception as e:
                        print(f"   ⚠️  Error processing row {i}: {e}")
                        continue
                
                # Progress update
                percent = (migrated / total_count) * 100
                print(f"   ✅ Batch complete. Total: {migrated:,}/{total_count:,} ({percent:.1f}%)")
                
                # Small delay to avoid overwhelming connections
                if batch_num % 10 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                print("   Continuing with next batch...")
                continue
        
        # Final verification
        supabase_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
        unique_docs = await supabase_conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        
        print(f"\n🎉 Migration Summary:")
        print(f"   Railway chunks: {total_count:,}")
        print(f"   Supabase chunks: {supabase_count:,}")
        print(f"   Unique documents: {unique_docs}")
        print(f"   Success rate: {(supabase_count/total_count)*100:.1f}%")
        
        if supabase_count > 0:
            print("✅ Migration successful!")
        else:
            print("❌ Migration failed - no data transferred")
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await railway_conn.close()
        await supabase_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_robust())