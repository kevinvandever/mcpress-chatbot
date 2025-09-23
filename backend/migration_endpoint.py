"""
Simple migration endpoint to run in production
Add this to your main.py temporarily
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os

migration_router = APIRouter(prefix="/migration", tags=["migration"])

@migration_router.get("/run-story-004")
async def run_story_004_migration():
    """
    Run Story 004 migration - creates books table and migrates data
    Access this at: https://your-backend-url/migration/run-story-004
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)

        results = []

        # Step 1: Ensure books table exists with all columns
        try:
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
            results.append("✅ Books table created/verified")
        except Exception as e:
            results.append(f"⚠️ Books table: {str(e)}")

        # Step 2: Add missing columns if needed
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
                results.append(f"✅ Added column {column_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    results.append(f"ℹ️ Column {column_name} already exists")
                else:
                    results.append(f"⚠️ Column {column_name}: {str(e)}")

        # Step 3: Create metadata_history table
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
            results.append("✅ Metadata history table created")
        except Exception as e:
            results.append(f"⚠️ Metadata history: {str(e)}")

        # Step 4: Migrate data from documents to books if needed
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")

        if book_count == 0:
            # Migrate from documents table
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
                    metadata = doc['metadata'] or {}
                    if isinstance(metadata, str):
                        import json
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}

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
                    results.append(f"⚠️ Could not migrate {doc['filename']}: {str(e)}")

            results.append(f"✅ Migrated {migrated} documents to books table")
        else:
            results.append(f"ℹ️ Books table already has {book_count} records")

        # Step 5: Update page counts based on chunks
        chunk_stats = await conn.fetch("""
            SELECT
                filename,
                COUNT(*) as chunk_count,
                MAX(page_number) as max_page
            FROM documents
            GROUP BY filename
        """)

        updated = 0
        for stat in chunk_stats:
            filename = stat['filename']
            chunk_count = stat['chunk_count']
            max_page = stat['max_page']

            # Calculate page count
            if max_page and max_page > 0:
                estimated_pages = max_page
            else:
                estimated_pages = max(1, chunk_count // 3)

            result = await conn.execute("""
                UPDATE books
                SET total_pages = $1
                WHERE filename = $2
            """, estimated_pages, filename)

            if result.split()[-1] == '1':
                updated += 1

        results.append(f"✅ Updated page counts for {updated} books")

        # Step 6: Add book_id to embeddings if table exists
        try:
            await conn.execute("""
                ALTER TABLE embeddings
                ADD COLUMN IF NOT EXISTS book_id INTEGER REFERENCES books(id) ON DELETE CASCADE
            """)
            results.append("✅ Added book_id to embeddings table")
        except Exception as e:
            if "does not exist" in str(e).lower():
                results.append("ℹ️ Embeddings table does not exist (will be created when needed)")
            else:
                results.append(f"ℹ️ Embeddings: {str(e)}")

        # Final stats
        final_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_books,
                COUNT(CASE WHEN total_pages > 0 THEN 1 END) as books_with_pages,
                AVG(total_pages) as avg_pages
            FROM books
        """)

        await conn.close()

        return {
            "status": "success",
            "results": results,
            "stats": {
                "total_books": final_stats['total_books'],
                "books_with_pages": final_stats['books_with_pages'],
                "avg_pages_per_book": int(final_stats['avg_pages'] or 0)
            },
            "message": "Migration completed successfully! Documents now have IDs and page counts."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@migration_router.get("/check-status")
async def check_migration_status():
    """Check if migration has been run"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)

        # Check if books table exists and has data
        books_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'books'
            )
        """)

        if not books_exist:
            await conn.close()
            return {
                "migration_needed": True,
                "message": "Books table does not exist. Run migration."
            }

        # Get stats
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_books,
                COUNT(CASE WHEN total_pages > 0 THEN 1 END) as books_with_pages
            FROM books
        """)

        doc_count = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")

        await conn.close()

        return {
            "migration_needed": stats['total_books'] == 0,
            "books_table_exists": True,
            "books_count": stats['total_books'],
            "books_with_pages": stats['books_with_pages'],
            "documents_count": doc_count,
            "message": "Migration already completed" if stats['total_books'] > 0 else "Migration needed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")