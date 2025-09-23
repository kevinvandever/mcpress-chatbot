#!/usr/bin/env python3
"""
Migration script to add metadata management tables and columns
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    """Run database migrations for metadata management"""

    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print("🔄 Running metadata management migrations...")

        # Create metadata history table
        cur.execute("""
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
        print("✅ Created metadata_history table")

        # Add indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
            ON metadata_history(book_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
            ON metadata_history(changed_at)
        """)
        print("✅ Created indexes on metadata_history")

        # Add missing columns to books table
        columns_to_add = [
            ('subcategory', 'TEXT'),
            ('description', 'TEXT'),
            ('tags', 'TEXT[]'),
            ('mc_press_url', 'TEXT'),
            ('year', 'INTEGER')
        ]

        for column_name, column_type in columns_to_add:
            try:
                cur.execute(f"""
                    ALTER TABLE books
                    ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                """)
                print(f"✅ Added column {column_name} to books table")
            except psycopg2.errors.DuplicateColumn:
                print(f"ℹ️ Column {column_name} already exists")
            except Exception as e:
                print(f"⚠️ Could not add column {column_name}: {str(e)}")

        # Verify migration
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)

        print("\n📋 Current books table structure:")
        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]}")

        # Check if metadata_history exists
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'metadata_history'
        """)

        if cur.fetchone()[0] > 0:
            print("\n✅ metadata_history table verified")

        cur.close()
        conn.close()

        print("\n🎉 Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)