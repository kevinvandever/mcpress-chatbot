"""
Simple migration endpoint to add to main.py temporarily
"""

from fastapi import HTTPException, Depends
from typing import Dict, Any

async def run_simple_migration(
    current_admin = None  # We'll check auth manually for now
) -> Dict[str, Any]:
    """Run database migration for metadata management"""
    try:
        import psycopg2
        import os
        from dotenv import load_dotenv

        load_dotenv()

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {"status": "error", "message": "DATABASE_URL not set"}

        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        results = []

        # Create metadata history table
        try:
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
            results.append("✅ Created metadata_history table")
        except Exception as e:
            results.append(f"⚠️ metadata_history: {str(e)}")

        # Create indexes
        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
                ON metadata_history(book_id)
            """)
            results.append("✅ Created index on book_id")
        except Exception as e:
            results.append(f"⚠️ Index book_id: {str(e)}")

        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
                ON metadata_history(changed_at)
            """)
            results.append("✅ Created index on changed_at")
        except Exception as e:
            results.append(f"⚠️ Index changed_at: {str(e)}")

        # Add missing columns to books table
        columns = [
            ('subcategory', 'TEXT'),
            ('description', 'TEXT'),
            ('tags', 'TEXT[]'),
            ('mc_press_url', 'TEXT'),
            ('year', 'INTEGER')
        ]

        for col_name, col_type in columns:
            try:
                cur.execute(f"ALTER TABLE books ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                results.append(f"✅ Added column {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    results.append(f"ℹ️ Column {col_name} already exists")
                else:
                    results.append(f"⚠️ Column {col_name}: {str(e)}")

        conn.commit()
        cur.close()
        conn.close()

        return {
            "status": "success",
            "message": "Migration completed",
            "details": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Migration failed: {str(e)}"
        }