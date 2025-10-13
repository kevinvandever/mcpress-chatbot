#!/usr/bin/env python3
"""
Migration runner for Story-005 database schema
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def run_migration(migration_file: str):
    """Run a SQL migration file"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    # Read migration SQL
    migration_path = Path(__file__).parent / 'migrations' / migration_file
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False

    with open(migration_path, 'r') as f:
        migration_sql = f.read()

    print(f"🔄 Running migration: {migration_file}")
    print(f"📂 Path: {migration_path}")

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)

        # Execute migration
        await conn.execute(migration_sql)

        print(f"✅ Migration completed successfully!")

        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name IN ('processing_jobs', 'processing_events', 'storage_metrics')
        """)

        print(f"\n📋 Created tables:")
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
            print(f"   - {table['table_name']}: {count} rows")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

async def rollback_migration(rollback_file: str):
    """Rollback a migration"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    # Read rollback SQL
    rollback_path = Path(__file__).parent / 'migrations' / rollback_file
    if not rollback_path.exists():
        print(f"❌ Rollback file not found: {rollback_path}")
        return False

    with open(rollback_path, 'r') as f:
        rollback_sql = f.read()

    print(f"⚠️  Rolling back migration: {rollback_file}")
    print(f"📂 Path: {rollback_path}")

    # Confirm rollback
    response = input("Are you sure you want to rollback? This will delete data. (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Rollback cancelled")
        return False

    try:
        conn = await asyncpg.connect(database_url)
        await conn.execute(rollback_sql)

        print(f"✅ Rollback completed successfully!")
        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False

async def main():
    """Main migration runner"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run_migration.py migrate   # Run migration")
        print("  python run_migration.py rollback  # Rollback migration")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'migrate':
        success = await run_migration('001_processing_pipeline.sql')
        sys.exit(0 if success else 1)
    elif command == 'rollback':
        success = await rollback_migration('001_processing_pipeline_rollback.sql')
        sys.exit(0 if success else 1)
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'migrate' or 'rollback'")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
