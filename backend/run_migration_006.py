"""
Migration Runner: 006 Temporal Metadata for RPG Era Awareness
Feature: temporal-rag-anti-hallucination

API endpoint to execute migration 006 (publication_year and rpg_era columns on books table).
Safe to run multiple times (idempotent - uses ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
"""

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

try:
    import asyncpg
except ImportError:
    pass

router = APIRouter()


async def _get_pool():
    """Create a temporary connection pool for migration execution."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return await asyncpg.create_pool(database_url, min_size=1, max_size=2)


@router.post("/run-migration-006")
async def run_migration_006():
    """
    Run database migration 006: Temporal Metadata columns on books table.

    Adds publication_year (INTEGER) and rpg_era (VARCHAR(20)) columns to the books table.
    Creates an index on rpg_era for efficient filtering.
    Safe to run multiple times (uses ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
    """
    pool = None
    try:
        pool = await _get_pool()

        # Check if columns already exist
        async with pool.acquire() as conn:
            existing_columns = await conn.fetch("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'books'
                  AND column_name IN ('publication_year', 'rpg_era')
            """)

            if len(existing_columns) == 2:
                return {
                    "status": "skipped",
                    "message": "Migration already completed - columns already exist",
                    "columns": [row['column_name'] for row in existing_columns],
                }

        # Read migration SQL
        migration_file = Path(__file__).parent / "migrations" / "006_temporal_metadata.sql"

        if not migration_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Migration file not found: {migration_file}",
            )

        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Execute migration
        async with pool.acquire() as conn:
            await conn.execute(migration_sql)

        # Verify columns were created
        async with pool.acquire() as conn:
            columns = await conn.fetch("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'books'
                  AND column_name IN ('publication_year', 'rpg_era')
            """)

            column_info = {
                row['column_name']: {
                    "data_type": row['data_type'],
                    "default": row['column_default'],
                }
                for row in columns
            }

        return {
            "status": "success",
            "message": "Migration 006 completed successfully",
            "columns_added": list(column_info.keys()),
            "column_details": column_info,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Migration 006 failed: {str(e)}"
        )
    finally:
        if pool:
            await pool.close()
