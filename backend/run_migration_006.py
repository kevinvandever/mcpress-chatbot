"""
Migration 006: Add total_pages column to books table.
Exposes a simple API endpoint to run the migration.
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(tags=["migrations"])

try:
    from auth_routes import get_current_user
except ImportError:
    from backend.auth_routes import get_current_user


@router.post("/api/migrations/006-add-total-pages")
async def run_migration_006(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Add total_pages column to books table if it doesn't exist."""
    try:
        try:
            from vector_store_postgres import PostgresVectorStore
        except ImportError:
            from backend.vector_store_postgres import PostgresVectorStore

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        import asyncpg
        conn = await asyncpg.connect(database_url)
        try:
            statements = [
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS total_pages INTEGER",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS document_type TEXT DEFAULT 'book'",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS tags TEXT[]",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS mc_press_url TEXT",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS article_url TEXT",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS year INTEGER",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS file_hash TEXT",
                "ALTER TABLE books ADD COLUMN IF NOT EXISTS subcategory TEXT",
            ]
            for stmt in statements:
                await conn.execute(stmt)

            # Add unique constraint on filename if not present
            has_unique = await conn.fetchval("""
                SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid = 'books'::regclass AND contype = 'u'
                AND array_to_string(conkey, ',') = (
                    SELECT attnum::text FROM pg_attribute
                    WHERE attrelid = 'books'::regclass AND attname = 'filename'
                )
            """)
            if has_unique == 0:
                # Remove duplicates first (keep lowest id)
                await conn.execute("""
                    DELETE FROM books a USING books b
                    WHERE a.id > b.id AND a.filename = b.filename
                """)
                await conn.execute("ALTER TABLE books ADD CONSTRAINT books_filename_unique UNIQUE (filename)")
                logger.info("✅ Added unique constraint on books.filename")

            # Fix document_type: numeric filenames are articles, not books
            updated = await conn.fetchval("""
                UPDATE books
                SET document_type = 'article'
                WHERE document_type = 'book'
                AND filename ~ '^[0-9]+\\.pdf$'
                RETURNING COUNT(*)
            """)
            if updated and updated > 0:
                logger.info(f"✅ Reclassified {updated} articles (numeric filenames) from 'book' to 'article'")

            logger.info("✅ Migration 006: all missing columns and constraints added to books table")
            return {"status": "success", "message": "All missing columns, unique constraint, and article reclassification applied"}
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Migration 006 failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
