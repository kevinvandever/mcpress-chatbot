#!/usr/bin/env python3
"""
Migration script to transfer data from old PostgreSQL to new PGVector database
Safely copies all documents, embeddings, and metadata
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

# Database URLs
OLD_DB_URL = "postgresql://postgres:MHmKuNmWWbYhOujBeIFsfgbQFkNAJjHG@ballast.proxy.rlwy.net:41917/railway"
NEW_DB_URL = "postgresql://postgres:OxATCwPVTNVdadKbPNTGvUyrktrTObOh@shortline.proxy.rlwy.net:18459/railway"

# Embedding dimension (all-MiniLM-L6-v2 uses 384)
EMBEDDING_DIM = 384

async def init_new_database(conn):
    """Initialize the new database with pgvector and tables"""
    logger.info("🔧 Initializing new database with pgvector extension...")

    # Enable pgvector extension
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    logger.info("✅ pgvector extension enabled")

    # Create documents table with vector column
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
    logger.info("✅ documents table created")

    # Create indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS documents_filename_idx
        ON documents (filename)
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS documents_metadata_idx
        ON documents USING gin (metadata)
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS documents_embedding_idx
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    logger.info("✅ Indexes created")

    # Create other tables if they exist in old DB
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES admin_users(id),
            token VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            author VARCHAR(500),
            filename VARCHAR(500),
            category VARCHAR(255),
            mc_press_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata_history (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(500) NOT NULL,
            old_title VARCHAR(500),
            new_title VARCHAR(500),
            old_author VARCHAR(500),
            new_author VARCHAR(500),
            old_category VARCHAR(255),
            new_category VARCHAR(255),
            changed_by VARCHAR(255),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            document_id INTEGER,
            embedding_vector vector({0}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """.format(EMBEDDING_DIM))

    logger.info("✅ All tables created")

async def get_table_stats(conn, db_name):
    """Get statistics about tables in database"""
    logger.info(f"\n📊 {db_name} Database Statistics:")

    tables = ['documents', 'admin_users', 'admin_sessions', 'books', 'metadata_history', 'embeddings']
    stats = {}

    for table in tables:
        try:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            stats[table] = count
            logger.info(f"  - {table}: {count:,} rows")
        except Exception as e:
            stats[table] = 0
            logger.debug(f"  - {table}: doesn't exist or error: {e}")

    return stats

async def migrate_documents(old_conn, new_conn):
    """Migrate documents with embeddings"""
    logger.info("\n🔄 Starting documents migration...")

    # Get total count
    total = await old_conn.fetchval("SELECT COUNT(*) FROM documents")
    logger.info(f"📦 Found {total:,} documents to migrate")

    if total == 0:
        logger.warning("⚠️ No documents found in old database!")
        return

    # Migrate in batches
    batch_size = 1000
    migrated = 0
    errors = 0

    for offset in range(0, total, batch_size):
        try:
            # Fetch batch from old database
            rows = await old_conn.fetch("""
                SELECT id, filename, content, page_number, chunk_index,
                       embedding, metadata, created_at
                FROM documents
                ORDER BY id
                LIMIT $1 OFFSET $2
            """, batch_size, offset)

            # Insert batch into new database
            for row in rows:
                try:
                    # Handle embedding conversion
                    embedding_data = None
                    if row['embedding']:
                        # Old DB might have JSONB embedding, convert to vector format
                        if isinstance(row['embedding'], str):
                            embedding_list = json.loads(row['embedding'])
                        else:
                            embedding_list = row['embedding']

                        # Format as PostgreSQL vector string
                        embedding_data = '[' + ','.join(map(str, embedding_list)) + ']'

                    # Insert into new database
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

                    if migrated % 100 == 0:
                        progress = (migrated / total) * 100
                        logger.info(f"  ⏳ Progress: {migrated:,}/{total:,} ({progress:.1f}%)")

                except Exception as e:
                    logger.error(f"  ❌ Error migrating document {row['id']}: {e}")
                    errors += 1
                    continue

        except Exception as e:
            logger.error(f"❌ Error fetching batch at offset {offset}: {e}")
            errors += batch_size
            continue

    logger.info(f"✅ Documents migration complete: {migrated:,} migrated, {errors} errors")

async def migrate_table(old_conn, new_conn, table_name, columns):
    """Generic table migration"""
    logger.info(f"\n🔄 Migrating {table_name}...")

    try:
        # Get total count
        total = await old_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

        if total == 0:
            logger.info(f"  ℹ️ No rows in {table_name}")
            return

        # Fetch all rows
        rows = await old_conn.fetch(f"SELECT * FROM {table_name}")

        # Insert into new database
        migrated = 0
        for row in rows:
            try:
                # Build insert query dynamically
                cols = ', '.join(columns)
                placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])

                values = [row[col] for col in columns]

                await new_conn.execute(
                    f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
                    *values
                )
                migrated += 1
            except Exception as e:
                logger.error(f"  ❌ Error migrating row: {e}")
                continue

        logger.info(f"✅ {table_name} migration complete: {migrated}/{total} rows")

    except Exception as e:
        logger.warning(f"  ⚠️ Could not migrate {table_name}: {e}")

async def migrate_all():
    """Main migration function"""
    logger.info("="*60)
    logger.info("🚀 Starting Migration to PGVector Database")
    logger.info("="*60)

    start_time = datetime.now()

    try:
        # Connect to both databases
        logger.info("\n📡 Connecting to databases...")
        old_conn = await asyncpg.connect(OLD_DB_URL)
        logger.info("✅ Connected to OLD database")

        new_conn = await asyncpg.connect(NEW_DB_URL)
        logger.info("✅ Connected to NEW database")

        # Get stats from old database
        old_stats = await get_table_stats(old_conn, "OLD")

        # Initialize new database
        await init_new_database(new_conn)

        # Migrate documents (main data)
        await migrate_documents(old_conn, new_conn)

        # Migrate other tables
        await migrate_table(old_conn, new_conn, 'admin_users',
                          ['email', 'password_hash', 'created_at'])

        await migrate_table(old_conn, new_conn, 'books',
                          ['title', 'author', 'filename', 'category', 'mc_press_url', 'created_at'])

        # Get final stats from new database
        new_stats = await get_table_stats(new_conn, "NEW")

        # Close connections
        await old_conn.close()
        await new_conn.close()

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "="*60)
        logger.info("🎉 MIGRATION COMPLETE!")
        logger.info("="*60)
        logger.info(f"⏱️  Total time: {elapsed:.1f} seconds")
        logger.info(f"📊 Documents migrated: {new_stats.get('documents', 0):,}")
        logger.info(f"📊 Users migrated: {new_stats.get('admin_users', 0):,}")
        logger.info(f"📊 Books migrated: {new_stats.get('books', 0):,}")
        logger.info("\n✅ New database is ready to use with pgvector!")
        logger.info("\n📝 Next steps:")
        logger.info("1. Update your app's DATABASE_URL to point to the new database")
        logger.info("2. Restart your application")
        logger.info("3. Test search quality")
        logger.info("4. Once confirmed working, you can delete the old database")

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(migrate_all())
