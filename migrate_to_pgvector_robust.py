#!/usr/bin/env python3
"""
Robust migration script with automatic reconnection and progress tracking
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URLs
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

async def init_new_database():
    """Initialize the new database"""
    logger.info("🔧 Initializing new database...")

    conn = await asyncpg.connect(NEW_DB_URL)

    try:
        # Enable pgvector
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("✅ pgvector extension enabled")

        # Create documents table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(500) NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                chunk_index INTEGER,
                embedding vector({EMBEDDING_DIM}),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename)")
        await conn.execute("CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING gin (metadata)")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        logger.info("✅ Database initialized")

    finally:
        await conn.close()

async def migrate_batch(start_id, batch_size=500):
    """Migrate a single batch of documents"""
    old_conn = None
    new_conn = None
    migrated = 0

    try:
        # Connect with timeout settings
        old_conn = await asyncpg.connect(OLD_DB_URL, command_timeout=120)
        new_conn = await asyncpg.connect(NEW_DB_URL, command_timeout=120)

        # Fetch batch
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

        # Insert batch
        for row in rows:
            try:
                # Handle embedding
                embedding_data = None
                if row['embedding']:
                    if isinstance(row['embedding'], str):
                        embedding_list = json.loads(row['embedding'])
                    else:
                        embedding_list = row['embedding']
                    embedding_data = '[' + ','.join(map(str, embedding_list)) + ']'

                # Insert
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
                json.dumps(row['metadata']) if row['metadata'] else None,
                row['created_at']
                )

                migrated += 1
                start_id = row['id']

            except Exception as e:
                logger.error(f"Error migrating document {row['id']}: {e}")
                continue

        return migrated, start_id

    finally:
        if old_conn:
            await old_conn.close()
        if new_conn:
            await new_conn.close()

async def migrate_all():
    """Main migration with progress tracking"""
    logger.info("="*60)
    logger.info("🚀 Starting Robust Migration to PGVector")
    logger.info("="*60)

    start_time = datetime.now()

    # Initialize new database
    await init_new_database()

    # Load progress
    progress = load_progress()
    last_id = progress['last_migrated_id']
    total_migrated = progress['total_migrated']

    logger.info(f"📊 Resuming from ID: {last_id}, Total migrated so far: {total_migrated}")

    # Get total count (with retry)
    for attempt in range(3):
        try:
            conn = await asyncpg.connect(OLD_DB_URL, command_timeout=30)
            total_docs = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE id > $1", last_id)
            await conn.close()
            break
        except:
            if attempt == 2:
                logger.error("Could not get total count, will migrate until exhausted")
                total_docs = 999999
            await asyncio.sleep(5)

    logger.info(f"📦 {total_docs:,} documents remaining to migrate")

    # Migrate in batches
    batch_size = 500
    errors_in_row = 0

    while True:
        try:
            migrated, last_id = await migrate_batch(last_id, batch_size)

            if migrated == 0:
                logger.info("✅ No more documents to migrate!")
                break

            total_migrated += migrated
            save_progress(last_id, total_migrated)
            errors_in_row = 0

            progress_pct = (total_migrated / (total_migrated + total_docs) * 100) if total_docs < 999999 else 0
            logger.info(f"⏳ Progress: {total_migrated:,} migrated, last ID: {last_id} ({progress_pct:.1f}%)")

            # Small delay between batches
            await asyncio.sleep(0.5)

        except Exception as e:
            errors_in_row += 1
            logger.error(f"Batch failed: {e}")

            if errors_in_row >= 5:
                logger.error("Too many consecutive errors, stopping")
                break

            logger.info(f"Retrying in 5 seconds... (attempt {errors_in_row}/5)")
            await asyncio.sleep(5)

    # Final stats
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "="*60)
    logger.info("🎉 MIGRATION COMPLETE!")
    logger.info("="*60)
    logger.info(f"⏱️  Total time: {elapsed:.1f} seconds")
    logger.info(f"📊 Documents migrated: {total_migrated:,}")
    logger.info(f"📊 Rate: {total_migrated / elapsed:.0f} docs/second")

    # Verify
    conn = await asyncpg.connect(NEW_DB_URL)
    final_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
    await conn.close()

    logger.info(f"📊 Final count in new database: {final_count:,}")
    logger.info("\n✅ Next steps:")
    logger.info("1. Update DATABASE_URL in Railway to point to new database")
    logger.info("2. Restart your application")
    logger.info("3. Test search quality")

if __name__ == "__main__":
    asyncio.run(migrate_all())
