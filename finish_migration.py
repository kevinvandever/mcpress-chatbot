#!/usr/bin/env python3
"""
Finish the pgvector migration - resume from where it stopped
Compatible with our fixed schema
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URLs (from migrate_to_pgvector_robust.py)
OLD_DB_URL = "postgresql://postgres:MHmKuNmWWbYhOujBeIFsfgbQFkNAJjHG@ballast.proxy.rlwy.net:41917/railway"
NEW_DB_URL = "postgresql://postgres:OxATCwPVTNVdadKbPNTGvUyrktrTObOh@shortline.proxy.rlwy.net:18459/railway"

# Embedding dimension
EMBEDDING_DIM = 384

# Progress tracking file
PROGRESS_FILE = "migration_progress.json"

def load_progress():
    """Load migration progress from file"""
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_migrated_id": 0, "total_migrated": 0}

def save_progress(last_id, total):
    """Save migration progress"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"last_migrated_id": last_id, "total_migrated": total}, f)
    logger.info(f"💾 Progress saved: ID {last_id}, Total {total:,}")

async def check_databases():
    """Check both databases"""
    logger.info("🔍 Checking databases...")

    # Old database
    old_conn = await asyncpg.connect(OLD_DB_URL, command_timeout=30)
    old_total = await old_conn.fetchval("SELECT COUNT(*) FROM documents")
    old_max_id = await old_conn.fetchval("SELECT MAX(id) FROM documents")
    await old_conn.close()

    # New database
    new_conn = await asyncpg.connect(NEW_DB_URL, command_timeout=30)
    new_total = await new_conn.fetchval("SELECT COUNT(*) FROM documents")
    new_with_emb = await new_conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
    has_pgvector = False
    try:
        await new_conn.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
        has_pgvector = True
    except:
        pass
    await new_conn.close()

    logger.info(f"📊 OLD database: {old_total:,} documents (max ID: {old_max_id:,})")
    logger.info(f"📊 NEW database: {new_total:,} documents ({new_with_emb:,} with embeddings)")
    logger.info(f"📊 pgvector enabled: {has_pgvector}")

    return old_total, old_max_id, new_total

async def migrate_batch(start_id, batch_size=500):
    """Migrate a single batch of documents"""
    old_conn = None
    new_conn = None
    migrated = 0

    try:
        # Connect with increased timeouts
        old_conn = await asyncpg.connect(OLD_DB_URL, command_timeout=120)
        new_conn = await asyncpg.connect(NEW_DB_URL, command_timeout=120)

        # Fetch batch from old database
        rows = await old_conn.fetch("""
            SELECT id, filename, content, page_number, chunk_index,
                   embedding, metadata, created_at
            FROM documents
            WHERE id > $1
            ORDER BY id
            LIMIT $2
        """, start_id, batch_size)

        if not rows:
            return 0, start_id

        logger.info(f"   Fetched {len(rows)} documents (IDs {rows[0]['id']} to {rows[-1]['id']})")

        # Insert batch into new database
        for row in rows:
            try:
                # Handle embedding (convert to pgvector format)
                embedding_data = None
                if row['embedding']:
                    # Old DB stored as JSONB, convert to pgvector format
                    if isinstance(row['embedding'], str):
                        embedding_list = json.loads(row['embedding'])
                    elif isinstance(row['embedding'], list):
                        embedding_list = row['embedding']
                    else:
                        # Already a list from JSONB
                        embedding_list = row['embedding']

                    # Format as PostgreSQL array string for pgvector
                    embedding_data = '[' + ','.join(map(str, embedding_list)) + ']'

                # Handle metadata (ensure it's JSON string)
                metadata_data = None
                if row['metadata']:
                    if isinstance(row['metadata'], str):
                        metadata_data = row['metadata']
                    else:
                        metadata_data = json.dumps(row['metadata'])

                # Insert with pgvector casting
                await new_conn.execute("""
                    INSERT INTO documents
                    (filename, content, page_number, chunk_index, embedding, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
                """,
                row['filename'],
                row['content'],
                row['page_number'],
                row['chunk_index'],
                embedding_data,
                metadata_data,
                row['created_at']
                )

                migrated += 1
                start_id = row['id']

            except Exception as e:
                logger.error(f"   ❌ Error migrating document ID {row['id']}: {e}")
                # Continue with next document
                continue

        return migrated, start_id

    except Exception as e:
        logger.error(f"   ❌ Batch failed: {e}")
        return 0, start_id

    finally:
        if old_conn:
            await old_conn.close()
        if new_conn:
            await new_conn.close()

async def finish_migration():
    """Finish the migration from where it stopped"""
    logger.info("="*60)
    logger.info("🚀 Resuming PGVector Migration")
    logger.info("="*60)
    print()

    start_time = datetime.now()

    # Check databases
    old_total, old_max_id, new_total = await check_databases()
    print()

    # Load progress
    progress = load_progress()
    last_id = progress['last_migrated_id']
    total_migrated = progress['total_migrated']

    logger.info(f"📍 Resuming from ID: {last_id:,}")
    logger.info(f"📍 Already migrated: {total_migrated:,} documents")
    print()

    # Calculate remaining
    remaining = old_total - new_total
    logger.info(f"📦 Estimated remaining: {remaining:,} documents")
    logger.info(f"📦 Completion: {(new_total/old_total*100):.1f}%")
    print()

    # Confirm
    response = input("Continue migration? (y/n): ").lower()
    if response != 'y':
        logger.info("❌ Migration cancelled")
        return

    print()
    logger.info("="*60)
    logger.info("🔄 Starting migration batches...")
    logger.info("="*60)
    print()

    # Migrate in batches
    batch_size = 500
    batch_num = 0
    errors_in_row = 0

    while True:
        try:
            batch_num += 1
            logger.info(f"📦 Batch {batch_num} (from ID {last_id:,})...")

            migrated, last_id = await migrate_batch(last_id, batch_size)

            if migrated == 0:
                logger.info("✅ No more documents to migrate!")
                break

            total_migrated += migrated
            save_progress(last_id, total_migrated)
            errors_in_row = 0

            # Calculate progress
            current_total = new_total + (total_migrated - progress['total_migrated'])
            progress_pct = (current_total / old_total * 100)

            logger.info(f"   ✅ Migrated {migrated} documents")
            logger.info(f"   📊 Total progress: {current_total:,}/{old_total:,} ({progress_pct:.1f}%)")
            print()

            # Small delay between batches
            await asyncio.sleep(0.5)

        except Exception as e:
            errors_in_row += 1
            logger.error(f"❌ Batch {batch_num} failed: {e}")

            if errors_in_row >= 5:
                logger.error("❌ Too many consecutive errors, stopping")
                break

            logger.info(f"⏳ Retrying in 5 seconds... (attempt {errors_in_row}/5)")
            await asyncio.sleep(5)

    # Final stats
    elapsed = (datetime.now() - start_time).total_seconds()
    print()
    logger.info("="*60)
    logger.info("🎉 MIGRATION COMPLETE!")
    logger.info("="*60)
    logger.info(f"⏱️  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    logger.info(f"📊 Documents migrated in this session: {total_migrated - progress['total_migrated']:,}")
    logger.info(f"📊 Total documents migrated: {total_migrated:,}")

    if elapsed > 0:
        rate = (total_migrated - progress['total_migrated']) / elapsed
        logger.info(f"📊 Migration rate: {rate:.0f} docs/second")

    # Final verification
    print()
    logger.info("🔍 Verifying final state...")
    conn = await asyncpg.connect(NEW_DB_URL)
    final_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
    final_with_emb = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL")
    await conn.close()

    logger.info(f"📊 Final count in new database: {final_count:,}")
    logger.info(f"📊 Documents with embeddings: {final_with_emb:,} ({final_with_emb/final_count*100:.1f}%)")

    completion_pct = (final_count / old_total * 100)
    logger.info(f"📊 Migration completion: {completion_pct:.1f}%")

    print()
    if completion_pct >= 99.9:
        logger.info("✅ Migration is essentially complete!")
        logger.info("✅ Any remaining documents are likely deleted or corrupted in old DB")
    elif completion_pct < 96:
        logger.warning("⚠️  Migration incomplete. Check errors above and retry.")
    else:
        logger.info("✅ Migration mostly complete. Remaining docs may be optional.")

    print()
    logger.info("📝 Next steps:")
    logger.info("1. Verify search quality with test_pgvector_chatbot.py")
    logger.info("2. Generate embeddings for documents that don't have them")
    logger.info("3. Test with real queries")
    logger.info("4. Once verified, can delete old database to save costs")

if __name__ == "__main__":
    try:
        asyncio.run(finish_migration())
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrupted by user")
        print("💾 Progress has been saved - you can resume later")
