#!/usr/bin/env python3
"""
Migration script for Story 004 - Metadata Management System
Creates books table and metadata_history table if they don't exist,
and migrates data from documents table.
"""

import asyncio
import asyncpg
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def run_migration():
    """Run the complete migration for Story 004"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        logger.error("DATABASE_URL not set")
        return False

    try:
        logger.info("Connecting to database...")
        conn = await asyncpg.connect(database_url)

        # 1. Create books table
        logger.info("Creating books table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                title TEXT,
                author TEXT,
                category TEXT,
                subcategory TEXT,
                description TEXT,
                tags TEXT[],
                mc_press_url TEXT,
                year INTEGER,
                total_pages INTEGER,
                file_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Books table ready")

        # 2. Check if migration is needed
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        logger.info(f"Current books in table: {book_count}")

        if book_count == 0:
            logger.info("Migrating data from documents to books table...")

            # Get unique documents with their metadata
            unique_docs = await conn.fetch("""
                SELECT DISTINCT ON (filename)
                    filename,
                    metadata,
                    created_at,
                    MAX(page_number) OVER (PARTITION BY filename) as max_page
                FROM documents
                WHERE filename IS NOT NULL
                ORDER BY filename, created_at ASC
            """)

            logger.info(f"Found {len(unique_docs)} unique documents to migrate")

            migrated = 0
            for doc in unique_docs:
                try:
                    metadata = doc['metadata'] or {}

                    # Handle both string and dict metadata
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata) if metadata else {}
                        except:
                            metadata = {}

                    # Extract metadata with defaults
                    title = metadata.get('title', doc['filename'].replace('.pdf', ''))
                    author = metadata.get('author', 'Unknown')
                    category = metadata.get('category', 'General')

                    # Insert into books table
                    await conn.execute("""
                        INSERT INTO books (filename, title, author, category, total_pages, processed_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (filename) DO UPDATE SET
                            title = EXCLUDED.title,
                            author = EXCLUDED.author,
                            category = EXCLUDED.category,
                            total_pages = EXCLUDED.total_pages
                    """,
                        doc['filename'],
                        title,
                        author,
                        category,
                        doc['max_page'] or 0,
                        doc['created_at']
                    )
                    migrated += 1

                    if migrated % 10 == 0:
                        logger.info(f"Migrated {migrated} documents...")

                except Exception as e:
                    logger.warning(f"Failed to migrate {doc['filename']}: {e}")
                    continue

            logger.info(f"✅ Migrated {migrated} documents")

        # 3. Update page counts for documents that might have wrong counts
        logger.info("Updating page counts from chunk data...")
        chunk_stats = await conn.fetch("""
            SELECT filename,
                   COUNT(*) as chunk_count,
                   MAX(page_number) as max_page
            FROM documents
            GROUP BY filename
        """)

        updated = 0
        for stat in chunk_stats:
            # Calculate estimated pages
            max_page = stat['max_page'] if stat['max_page'] else None
            chunk_count = stat['chunk_count']

            # Use max_page if available, otherwise estimate from chunks
            # (assuming roughly 3 chunks per page)
            estimated_pages = max_page if max_page else max(1, chunk_count // 3)

            result = await conn.execute("""
                UPDATE books
                SET total_pages = $1
                WHERE filename = $2 AND (total_pages IS NULL OR total_pages = 0)
            """, estimated_pages, stat['filename'])

            if '1' in result:
                updated += 1

        logger.info(f"✅ Updated {updated} page counts")

        # 4. Create metadata_history table
        logger.info("Creating metadata_history table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata_history (
                id SERIAL PRIMARY KEY,
                book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Metadata history table created")

        # 5. Create indexes for performance
        logger.info("Creating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
            ON metadata_history(book_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
            ON metadata_history(changed_at)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_filename
            ON books(filename)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_category
            ON books(category)
        """)

        logger.info("✅ Indexes created")

        # 6. Get final statistics
        final_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_books,
                COUNT(DISTINCT category) as categories,
                AVG(total_pages) as avg_pages,
                MAX(total_pages) as max_pages
            FROM books
            WHERE total_pages > 0
        """)

        logger.info("=" * 60)
        logger.info("📚 MIGRATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total books: {final_stats['total_books']}")
        logger.info(f"Categories: {final_stats['categories']}")
        logger.info(f"Average pages: {int(final_stats['avg_pages'] or 0)}")
        logger.info(f"Max pages: {final_stats['max_pages']}")
        logger.info("=" * 60)

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)