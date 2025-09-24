"""
Simple migration endpoint for Story 004 that uses the existing vector store connection
"""

from fastapi import APIRouter, HTTPException
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

# Global reference to vector store (will be set by main.py)
_vector_store = None

def set_vector_store(vector_store):
    """Set the vector store instance to use for database operations"""
    global _vector_store
    _vector_store = vector_store
    logger.info("✅ Migration router initialized with vector store")

@router.get("/run-story4-migration-safe")
async def run_migration_safe():
    """Run Story 4 migration using existing connection pool"""
    if not _vector_store or not _vector_store.pool:
        return {"error": "Database not initialized"}

    try:
        results = []

        async with _vector_store.pool.acquire() as conn:
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
            results.append("Books table created")

            # 2. Check if migration needed
            book_count = await conn.fetchval("SELECT COUNT(*) FROM books")

            if book_count == 0:
                # Migrate from documents
                logger.info("Migrating documents to books...")

                # Get unique documents with metadata
                unique_docs = await conn.fetch("""
                    SELECT DISTINCT ON (filename)
                        filename,
                        metadata,
                        created_at
                    FROM documents
                    WHERE filename IS NOT NULL
                    ORDER BY filename, created_at ASC
                """)

                migrated = 0
                for doc in unique_docs:
                    try:
                        metadata = doc['metadata'] or {}
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata) if metadata else {}
                            except:
                                metadata = {}

                        title = metadata.get('title', doc['filename'].replace('.pdf', ''))
                        author = metadata.get('author', 'Unknown')
                        category = metadata.get('category', 'General')

                        await conn.execute("""
                            INSERT INTO books (filename, title, author, category, processed_at)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (filename) DO NOTHING
                        """,
                            doc['filename'],
                            title,
                            author,
                            category,
                            doc['created_at']
                        )
                        migrated += 1
                    except Exception as e:
                        logger.warning(f"Failed to migrate {doc['filename']}: {e}")
                        continue

                results.append(f"Migrated {migrated} documents to books table")
            else:
                results.append(f"Books table already has {book_count} entries")

            # 3. Update page counts
            logger.info("Updating page counts...")
            chunk_stats = await conn.fetch("""
                SELECT filename, COUNT(*) as chunks, MAX(page_number) as max_page
                FROM documents
                GROUP BY filename
            """)

            updated = 0
            for stat in chunk_stats:
                pages = stat['max_page'] if stat['max_page'] else max(1, stat['chunks'] // 3)
                result = await conn.execute("""
                    UPDATE books
                    SET total_pages = $1
                    WHERE filename = $2 AND (total_pages IS NULL OR total_pages = 0)
                """, pages, stat['filename'])

                if '1' in result:
                    updated += 1

            results.append(f"Updated {updated} page counts")

            # 4. Create metadata_history table
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
            results.append("Created metadata_history table")

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
                ON metadata_history(book_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_books_filename
                ON books(filename)
            """)
            results.append("Created indexes")

            # Get final stats
            final_books = await conn.fetchval("SELECT COUNT(*) FROM books")
            avg_pages = await conn.fetchval("SELECT AVG(total_pages) FROM books WHERE total_pages > 0")

            return {
                "success": True,
                "results": results,
                "total_books": final_books,
                "avg_pages": int(avg_pages or 0)
            }

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {"error": str(e), "results": results}