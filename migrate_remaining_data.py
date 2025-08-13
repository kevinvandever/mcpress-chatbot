#!/usr/bin/env python3
"""
Migrate remaining data from Railway to Supabase with connection retry and resume capability
"""
import os
import asyncio
import asyncpg
import json
import time
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = os.getenv('RAILWAY_DATABASE_URL')
SUPABASE_URL = os.getenv('DATABASE_URL')  # Now points to Supabase

async def connect_with_retry(url, max_retries=5):
    """Connect with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(url, statement_cache_size=0)
            return conn
        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"   Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"   Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

async def get_migration_status(supabase_conn):
    """Check current migration status"""
    count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")
    unique_docs = await supabase_conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
    return count, unique_docs

async def migrate_remaining_data():
    """Continue migration from where we left off"""
    
    print("🚀 Resuming Railway to Supabase migration...")
    
    try:
        print("🔍 Connecting to databases...")
        
        # Connect to Railway (source)
        print("   Connecting to Railway...")
        railway_conn = await connect_with_retry(RAILWAY_URL)
        print("   ✅ Railway connected")
        
        # Connect to Supabase (destination)
        print("   Connecting to Supabase...")
        supabase_conn = await connect_with_retry(SUPABASE_URL)
        print("   ✅ Supabase connected")
        
        # Check current status
        current_count, current_docs = await get_migration_status(supabase_conn)
        print(f"📊 Current Supabase status: {current_count:,} chunks from {current_docs} documents")
        
        # Get total from Railway
        total_railway = await railway_conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
        total_docs_railway = await railway_conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents WHERE embedding IS NOT NULL")
        print(f"📊 Railway source: {total_railway:,} chunks from {total_docs_railway} documents")
        
        remaining = total_railway - current_count
        print(f"📊 Remaining to migrate: {remaining:,} chunks")
        
        if remaining <= 0:
            print("✅ Migration already complete!")
            return
        
        # Use smaller batches and session-based approach
        batch_size = 200
        session_size = 10  # Reconnect every 10 batches
        
        migrated_this_session = 0
        batch_count = 0
        
        # Start from where we left off (skip already migrated)
        offset = current_count
        
        while offset < total_railway:
            batch_count += 1
            
            # Reconnect every session_size batches to prevent timeouts
            if batch_count % session_size == 1:
                print(f"🔄 Starting new session (batch {batch_count})...")
                try:
                    await railway_conn.close()
                    await supabase_conn.close()
                except:
                    pass
                
                railway_conn = await connect_with_retry(RAILWAY_URL)
                supabase_conn = await connect_with_retry(SUPABASE_URL)
                print("   ✅ Reconnected to both databases")
            
            batch_num = batch_count
            progress = (offset / total_railway) * 100
            
            print(f"🔄 Batch {batch_num}: records {offset+1}-{min(offset + batch_size, total_railway)} ({progress:.1f}% complete)")
            
            try:
                # Fetch batch from Railway with ORDER BY for consistency
                rows = await railway_conn.fetch("""
                    SELECT filename, content, page_number, chunk_index, embedding, metadata, created_at
                    FROM documents 
                    WHERE embedding IS NOT NULL
                    ORDER BY filename, chunk_index
                    LIMIT $1 OFFSET $2
                """, batch_size, offset)
                
                if not rows:
                    print("   No more records to process")
                    break
                
                # Process each record
                batch_success = 0
                for row in rows:
                    try:
                        if row['embedding']:
                            # Parse and format embedding
                            if isinstance(row['embedding'], str):
                                embedding_list = json.loads(row['embedding'])
                            else:
                                embedding_list = row['embedding']
                            
                            embedding_str = f"[{','.join(map(str, embedding_list))}]"
                            
                            # Insert into Supabase
                            await supabase_conn.execute("""
                                INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                                VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                                ON CONFLICT DO NOTHING
                            """, 
                            row['filename'], row['content'], row['page_number'], 
                            row['chunk_index'], embedding_str, row['metadata'], row['created_at'])
                            
                            batch_success += 1
                            migrated_this_session += 1
                            
                    except Exception as e:
                        if "duplicate" not in str(e).lower():
                            print(f"     ⚠️  Record error: {e}")
                        continue
                
                offset += len(rows)
                
                print(f"   ✅ Batch complete: {batch_success}/{len(rows)} records. Session total: {migrated_this_session:,}")
                
                # Progress update every 20 batches
                if batch_count % 20 == 0:
                    current_total, current_docs = await get_migration_status(supabase_conn)
                    print(f"   📊 Checkpoint: {current_total:,} total records from {current_docs} documents")
                    
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Batch {batch_num} failed: {e}")
                if "connection" in str(e).lower():
                    print("   Connection lost, will reconnect next session")
                    batch_count = session_size  # Force reconnect
                continue
        
        # Final verification
        print(f"\n🎉 Migration Session Complete!")
        final_count, final_docs = await get_migration_status(supabase_conn)
        
        print(f"📊 Final Status:")
        print(f"   Railway source: {total_railway:,} chunks from {total_docs_railway} documents")
        print(f"   Supabase result: {final_count:,} chunks from {final_docs} documents")
        print(f"   Success rate: {(final_count/total_railway)*100:.1f}%")
        print(f"   This session: +{migrated_this_session:,} records")
        
        if final_docs >= total_docs_railway * 0.9:  # 90% of documents
            print("✅ Migration successful!")
        else:
            print("⚠️  Some documents may not have fully migrated - check for errors")
        
        await railway_conn.close()
        await supabase_conn.close()
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_remaining_data())