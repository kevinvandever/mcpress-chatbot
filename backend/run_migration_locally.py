#!/usr/bin/env python3
"""
Run the metadata migration locally using Railway's DATABASE_URL
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        print("Get it from Railway dashboard and add to .env:")
        print("DATABASE_URL=postgresql://...")
        return

    print(f"🔄 Connecting to database...")

    try:
        conn = await asyncpg.connect(database_url)

        print("✅ Connected to database")

        results = []

        # Create metadata_history table
        try:
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
            results.append("✅ Created metadata_history table")
        except Exception as e:
            results.append(f"⚠️ metadata_history: {str(e)}")

        # Add indexes
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
                ON metadata_history(book_id)
            """)
            results.append("✅ Created index on book_id")
        except Exception as e:
            results.append(f"⚠️ Index book_id: {str(e)}")

        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
                ON metadata_history(changed_at)
            """)
            results.append("✅ Created index on changed_at")
        except Exception as e:
            results.append(f"⚠️ Index changed_at: {str(e)}")

        # Add missing columns
        columns = [
            ('subcategory', 'TEXT'),
            ('description', 'TEXT'),
            ('tags', 'TEXT[]'),
            ('mc_press_url', 'TEXT'),
            ('year', 'INTEGER')
        ]

        for col_name, col_type in columns:
            try:
                await conn.execute(f"""
                    ALTER TABLE books
                    ADD COLUMN {col_name} {col_type}
                """)
                results.append(f"✅ Added column {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    results.append(f"ℹ️ Column {col_name} already exists")
                else:
                    results.append(f"❌ Column {col_name}: {str(e)}")

        await conn.close()

        print("\n📋 Migration Results:")
        for result in results:
            print(f"  {result}")

        print("\n🎉 Migration completed!")

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\nMake sure you have the correct DATABASE_URL from Railway")

if __name__ == "__main__":
    asyncio.run(run_migration())