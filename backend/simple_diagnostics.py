"""
Simple diagnostic endpoints that don't depend on complex initialization
"""

import os
import asyncpg
import asyncio
from fastapi import APIRouter

router = APIRouter()

@router.get("/diag/simple-db-test")
async def simple_db_test():
    """Direct database test with timeout"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        return {"error": "DATABASE_URL not set"}

    try:
        # Very short timeout to avoid hanging
        conn = await asyncio.wait_for(
            asyncpg.connect(
                database_url,
                server_settings={'jit': 'off'},  # Disable JIT
                command_timeout=5
            ),
            timeout=3.0
        )

        # Simple query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        return {
            "status": "success",
            "database_connected": True,
            "test_result": result
        }
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "error": "Database connection timed out after 3 seconds",
            "suggestion": "Check Railway PostgreSQL addon status"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/diag/pool-status")
async def pool_status():
    """Check if connection pool exists"""
    from main import vector_store

    if not vector_store:
        return {"error": "Vector store not initialized"}

    if not hasattr(vector_store, 'pool'):
        return {"error": "Vector store has no pool attribute"}

    if not vector_store.pool:
        return {"error": "Connection pool is None"}

    try:
        # Get pool statistics
        return {
            "pool_exists": True,
            "pool_size": vector_store.pool.get_size(),
            "pool_free_size": vector_store.pool.get_free_size(),
            "pool_min_size": vector_store.pool.get_min_size(),
            "pool_max_size": vector_store.pool.get_max_size()
        }
    except Exception as e:
        return {
            "pool_exists": True,
            "error": f"Could not get pool stats: {str(e)}"
        }

@router.get("/diag/test-query")
async def test_query():
    """Test a simple query using the pool"""
    from main import vector_store

    if not vector_store or not vector_store.pool:
        return {"error": "Pool not available"}

    try:
        async with vector_store.pool.acquire() as conn:
            # Check documents table
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")

            # Check if books table exists
            books_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'books'
                )
            """)

            books_count = 0
            if books_exists:
                books_count = await conn.fetchval("SELECT COUNT(*) FROM books")

            return {
                "status": "success",
                "documents_count": doc_count,
                "books_table_exists": books_exists,
                "books_count": books_count
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }