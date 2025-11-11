"""
Database migration for conversation export tracking (Story-012)
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def run_migration():
    """Create conversation_exports table"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not configured")
        return False

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url, timeout=10)
        print("✅ Connected to database")

        # Create conversation_exports table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_exports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                format TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size INTEGER,
                options JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        print("✅ Created conversation_exports table")

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exports_user
            ON conversation_exports(user_id, created_at DESC)
        """)
        print("✅ Created idx_exports_user index")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exports_conversation
            ON conversation_exports(conversation_id)
        """)
        print("✅ Created idx_exports_conversation index")

        # Verify table
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'conversation_exports'
        """)

        await conn.close()

        if count > 0:
            print("✅ Migration completed successfully")
            return True
        else:
            print("❌ Migration failed - table not created")
            return False

    except asyncpg.exceptions.UndefinedTableError as e:
        print(f"⚠️ conversations table doesn't exist yet: {e}")
        print("ℹ️ Skipping foreign key constraint - will work without it")

        # Retry without foreign key constraint
        try:
            conn = await asyncpg.connect(database_url, timeout=10)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_exports (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    options JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exports_user
                ON conversation_exports(user_id, created_at DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exports_conversation
                ON conversation_exports(conversation_id)
            """)

            await conn.close()
            print("✅ Migration completed (without foreign key)")
            return True

        except Exception as e2:
            print(f"❌ Migration failed: {e2}")
            return False

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    print("🔄 Running Story-012 export migration...")
    result = asyncio.run(run_migration())
    if result:
        print("✅ Story-012 database schema ready")
    else:
        print("❌ Story-012 migration failed")
