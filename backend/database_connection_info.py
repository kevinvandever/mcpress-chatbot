"""
Database Connection Info
Show exactly which database the Railway app is connected to
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os

db_info_router = APIRouter(prefix="/db-info", tags=["db-info"])

@db_info_router.get("/connection")
async def get_database_connection_info():
    """Show which database we're actually connected to"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        # Parse the URL to show connection details (without password)
        if database_url.startswith('postgresql://'):
            # Extract host info
            url_parts = database_url.replace('postgresql://', '').split('@')
            if len(url_parts) > 1:
                host_part = url_parts[1].split('/')[0]
                database_name = url_parts[1].split('/')[-1] if '/' in url_parts[1] else 'postgres'
            else:
                host_part = "unknown"
                database_name = "unknown"
        else:
            host_part = "unknown"
            database_name = "unknown"

        conn = await asyncpg.connect(database_url)
        
        # Get database info
        db_version = await conn.fetchval("SELECT version()")
        current_database = await conn.fetchval("SELECT current_database()")
        current_user = await conn.fetchval("SELECT current_user")
        
        # Check books table structure
        books_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)
        
        # Count records
        books_count = await conn.fetchval("SELECT COUNT(*) FROM books") if books_columns else 0
        
        # Check for migration 003 tables
        migration_tables = {}
        for table in ['authors', 'document_authors']:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            if exists:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                migration_tables[table] = {"exists": True, "count": count}
            else:
                migration_tables[table] = {"exists": False, "count": 0}
        
        await conn.close()
        
        return {
            "connection_info": {
                "host": host_part,
                "database": current_database,
                "user": current_user,
                "database_name_from_url": database_name
            },
            "database_version": db_version,
            "books_table": {
                "exists": len(books_columns) > 0,
                "column_count": len(books_columns),
                "record_count": books_count,
                "columns": [
                    {
                        "name": col['column_name'],
                        "type": col['data_type'],
                        "nullable": col['is_nullable'] == 'YES',
                        "default": col['column_default']
                    }
                    for col in books_columns
                ]
            },
            "migration_003_status": {
                "tables": migration_tables,
                "schema_migrated": all(table["exists"] for table in migration_tables.values()),
                "has_document_type_column": any(col['column_name'] == 'document_type' for col in books_columns),
                "has_article_url_column": any(col['column_name'] == 'article_url' for col in books_columns)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection info failed: {str(e)}")


@db_info_router.get("/supabase-check")
async def check_if_supabase():
    """Check if this is actually a Supabase database"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        
        # Check for Supabase-specific indicators
        supabase_indicators = {}
        
        # Check for supabase schema
        supabase_schema = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 'supabase'
            )
        """)
        supabase_indicators['supabase_schema'] = supabase_schema
        
        # Check for auth schema (Supabase auth)
        auth_schema = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 'auth'
            )
        """)
        supabase_indicators['auth_schema'] = auth_schema
        
        # Check for pgvector extension
        pgvector_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM pg_extension 
                WHERE extname = 'vector'
            )
        """)
        supabase_indicators['pgvector_extension'] = pgvector_exists
        
        # Check host from connection
        is_supabase_host = 'supabase.co' in database_url
        supabase_indicators['supabase_host'] = is_supabase_host
        
        await conn.close()
        
        return {
            "is_supabase": is_supabase_host and (supabase_schema or auth_schema),
            "indicators": supabase_indicators,
            "database_url_host": database_url.split('@')[1].split('/')[0] if '@' in database_url else "unknown"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase check failed: {str(e)}")