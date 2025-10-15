#!/usr/bin/env python3
"""
Migration Runner for Story-006: Code Upload System
Run this script to execute the database migration on Railway PostgreSQL
"""

import asyncio
import asyncpg
import os
from pathlib import Path

# Use public DATABASE_URL for local connections
# Railway provides DATABASE_PUBLIC_URL for external access
DATABASE_URL = os.getenv(
    'DATABASE_PUBLIC_URL',  # Public URL for local connections
    os.getenv('DATABASE_URL', '')  # Fallback to internal (won't work locally)
)

async def run_migration():
    print("=" * 60)
    print("🚀 Story-006: Code Upload System Migration")
    print("=" * 60)

    # Read migration script
    migration_file = Path(__file__).parent / 'migrations' / '002_code_upload_system.sql'
    print(f"📄 Reading migration from: {migration_file}")

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print(f"📊 Migration script size: {len(migration_sql)} characters")

    # Show which database we're connecting to (hide password)
    db_host = DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'
    print(f"🔌 Connecting to database: {db_host}...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")

        print("🏗️  Executing migration...")
        # Execute the entire migration script
        result = await conn.execute(migration_sql)
        print(f"✅ Migration executed!")

        # Verify tables were created
        print("\n📊 Verifying migration results...")

        # Check tables
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('code_uploads', 'upload_sessions', 'user_quotas')
            ORDER BY table_name
        """)
        print(f"\n✅ Tables created ({len(tables)}):")
        for table in tables:
            print(f"   - {table['table_name']}")

        # Check indexes
        indexes = await conn.fetch("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN ('code_uploads', 'upload_sessions', 'user_quotas')
            ORDER BY indexname
        """)
        print(f"\n✅ Indexes created ({len(indexes)}):")
        for idx in indexes:
            print(f"   - {idx['indexname']}")

        # Check functions
        functions = await conn.fetch("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_name IN (
                'cleanup_expired_code_files',
                'reset_daily_quotas',
                'purge_old_deleted_files',
                'get_user_quota_status'
            )
            ORDER BY routine_name
        """)
        print(f"\n✅ Functions created ({len(functions)}):")
        for func in functions:
            print(f"   - {func['routine_name']}()")

        # Check view
        views = await conn.fetch("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            AND table_name = 'code_upload_stats'
        """)
        print(f"\n✅ Views created ({len(views)}):")
        for view in views:
            print(f"   - {view['table_name']}")

        await conn.close()

        print("\n" + "=" * 60)
        print("🎉 Migration 002 completed successfully!")
        print("=" * 60)
        return True

    except asyncpg.exceptions.DuplicateTableError as e:
        print(f"⚠️  Tables may already exist: {e}")
        print("🔍 Checking existing schema...")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
