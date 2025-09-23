#!/usr/bin/env python3
"""
Async migration script for metadata management using asyncpg
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    """Run database migrations for metadata management"""

    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print(f"🔄 Connecting to database...")

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)

        print("✅ Connected to database")
        print("🔄 Running metadata management migrations...")

        # Check if books table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'books'
            )
        """)

        if not table_exists:
            print("⚠️  'books' table does not exist - creating it...")

            # Create books table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    filename TEXT UNIQUE NOT NULL,
                    title TEXT,
                    author TEXT,
                    category TEXT,
                    subcategory TEXT,
                    description TEXT,
                    tags TEXT[],
                    mc_press_url TEXT,
                    year INTEGER,
                    total_pages INTEGER,
                    file_hash TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Created books table")

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_books_filename ON books(filename);
                CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
                CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
            """)
            print("✅ Created indexes on books table")
        else:
            print("✅ 'books' table already exists")

            # Add missing columns to existing books table
            columns_to_add = [
                ('subcategory', 'TEXT'),
                ('description', 'TEXT'),
                ('tags', 'TEXT[]'),
                ('mc_press_url', 'TEXT'),
                ('year', 'INTEGER')
            ]

            for column_name, column_type in columns_to_add:
                try:
                    await conn.execute(f"""
                        ALTER TABLE books
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"✅ Added column {column_name} to books table")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"ℹ️  Column {column_name} already exists")
                    else:
                        print(f"⚠️  Could not add column {column_name}: {str(e)}")

        # Create metadata history table
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
        print("✅ Created metadata_history table")

        # Create indexes for metadata_history
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
            ON metadata_history(book_id);

            CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
            ON metadata_history(changed_at);
        """)
        print("✅ Created indexes on metadata_history table")

        # Check if embeddings table exists and has book_id
        embeddings_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'embeddings'
            )
        """)

        if embeddings_exists:
            # Add book_id column to embeddings if it doesn't exist
            try:
                await conn.execute("""
                    ALTER TABLE embeddings
                    ADD COLUMN IF NOT EXISTS book_id INTEGER REFERENCES books(id) ON DELETE CASCADE
                """)
                print("✅ Added book_id column to embeddings table")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("ℹ️  Column book_id already exists in embeddings")
                else:
                    print(f"ℹ️  Embeddings table note: {str(e)}")

        # Migrate data from documents table to books table if needed
        documents_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'documents'
            )
        """)

        if documents_exists:
            print("\n🔄 Checking for data migration from documents to books...")

            # Check if books table is empty
            book_count = await conn.fetchval("SELECT COUNT(*) FROM books")

            if book_count == 0:
                print("📦 Migrating data from documents table to books table...")

                # Get unique documents
                unique_docs = await conn.fetch("""
                    SELECT DISTINCT ON (filename)
                        filename,
                        metadata,
                        created_at
                    FROM documents
                    ORDER BY filename, created_at ASC
                """)

                migrated = 0
                for doc in unique_docs:
                    try:
                        # Parse metadata
                        metadata = doc['metadata'] or {}
                        if isinstance(metadata, str):
                            import json
                            try:
                                metadata = json.loads(metadata)
                            except:
                                metadata = {}

                        # Insert into books table
                        await conn.execute("""
                            INSERT INTO books (filename, title, author, category, processed_at)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (filename) DO NOTHING
                        """,
                            doc['filename'],
                            metadata.get('title', doc['filename'].replace('.pdf', '')),
                            metadata.get('author', 'Unknown'),
                            metadata.get('category', 'General'),
                            doc['created_at']
                        )
                        migrated += 1
                    except Exception as e:
                        print(f"⚠️  Could not migrate {doc['filename']}: {str(e)}")

                print(f"✅ Migrated {migrated} documents to books table")
            else:
                print(f"ℹ️  Books table already has {book_count} records")

        # Verify migration
        print("\n📋 Verification:")

        # Check books table
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"  - Books table: {book_count} records")

        # Check columns
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)

        print("  - Books table columns:")
        for col in columns:
            print(f"    • {col['column_name']}: {col['data_type']}")

        # Check metadata_history
        history_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'metadata_history'
            )
        """)

        if history_exists:
            print("  - metadata_history table: ✅ Exists")

        await conn.close()
        print("\n🎉 Migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)