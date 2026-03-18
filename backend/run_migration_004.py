"""
Migration Runner: 004 Customer Password Authentication
Feature: chatmaster-password-auth

API endpoint to execute migration 004 (customer_passwords and password_reset_tokens tables).
Safe to run multiple times (idempotent - uses CREATE TABLE IF NOT EXISTS).
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


@router.post("/run-migration-004")
async def run_migration_004():
    """
    Run database migration 004: Customer Password Authentication tables.

    ONE-TIME USE: Creates customer_passwords and password_reset_tokens tables.
    Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    pool = None
    try:
        pool = await _get_pool()

        # Check if tables already exist
        async with pool.acquire() as conn:
            existing_tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('customer_passwords', 'password_reset_tokens')
            """)

            if len(existing_tables) == 2:
                table_counts = {}
                for table in existing_tables:
                    count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {table['table_name']}"
                    )
                    table_counts[table['table_name']] = count

                return {
                    "status": "skipped",
                    "message": "Migration already completed - all tables exist",
                    "tables": [row['table_name'] for row in existing_tables],
                    "row_counts": table_counts,
                }

        # Read migration SQL
        migration_file = Path(__file__).parent / "migrations" / "004_customer_password_auth.sql"

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

        # Verify tables created
        async with pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('customer_passwords', 'password_reset_tokens')
            """)

            table_counts = {}
            for table in tables:
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table['table_name']}"
                )
                table_counts[table['table_name']] = count

        return {
            "status": "success",
            "message": "Migration 004 completed successfully",
            "tables_created": list(table_counts.keys()),
            "row_counts": table_counts,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Migration 004 failed: {str(e)}"
        )
    finally:
        if pool:
            await pool.close()
