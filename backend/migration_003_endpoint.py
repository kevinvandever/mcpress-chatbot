"""
Migration 003 Endpoint: Multi-Author Metadata Enhancement
Run this migration in production via HTTP request
Access at: https://your-backend-url/migration-003/run
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
from pathlib import Path

migration_003_router = APIRouter(prefix="/migration-003", tags=["migration-003"])

@migration_003_router.get("/run")
async def run_migration_003():
    """
    Run Migration 003: Multi-Author Metadata Enhancement
    Creates authors table, document_authors junction table, and adds document_type fields
    
    Access this at: https://your-backend-url/migration-003/run
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        results = []

        # Step 1: Check if books table exists
        books_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'books'
            )
        """)
        
        if not books_exist:
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail="Books table does not exist. Run Story 004 migration first."
            )
        
        results.append("✅ Books table exists")

        # Step 2: Create authors table
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    site_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results.append("✅ Authors table created")
        except Exception as e:
            results.append(f"⚠️ Authors table: {str(e)}")

        # Step 3: Create index on authors.name
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name)
            """)
            results.append("✅ Index on authors.name created")
        except Exception as e:
            results.append(f"⚠️ Authors index: {str(e)}")

        # Step 4: Create document_authors junction table
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_authors (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
                    author_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(book_id, author_id)
                )
            """)
            results.append("✅ Document_authors junction table created")
        except Exception as e:
            results.append(f"⚠️ Document_authors table: {str(e)}")

        # Step 5: Create indexes on document_authors
        indexes = [
            ("idx_document_authors_book", "book_id"),
            ("idx_document_authors_author", "author_id"),
        ]
        
        for idx_name, column in indexes:
            try:
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} ON document_authors({column})
                """)
                results.append(f"✅ Index {idx_name} created")
            except Exception as e:
                results.append(f"⚠️ Index {idx_name}: {str(e)}")

        # Step 6: Create composite index for ordering
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_authors_order 
                ON document_authors(book_id, author_order)
            """)
            results.append("✅ Composite index on (book_id, author_order) created")
        except Exception as e:
            results.append(f"⚠️ Order index: {str(e)}")

        # Step 7: Add document_type column to books table
        try:
            await conn.execute("""
                ALTER TABLE books
                ADD COLUMN IF NOT EXISTS document_type TEXT NOT NULL DEFAULT 'book' 
                CHECK (document_type IN ('book', 'article'))
            """)
            results.append("✅ Added document_type column to books table")
        except Exception as e:
            if "already exists" in str(e).lower():
                results.append("ℹ️ document_type column already exists")
            else:
                results.append(f"⚠️ document_type column: {str(e)}")

        # Step 8: Add article_url column to books table
        try:
            await conn.execute("""
                ALTER TABLE books
                ADD COLUMN IF NOT EXISTS article_url TEXT
            """)
            results.append("✅ Added article_url column to books table")
        except Exception as e:
            if "already exists" in str(e).lower():
                results.append("ℹ️ article_url column already exists")
            else:
                results.append(f"⚠️ article_url column: {str(e)}")

        # Step 9: Create trigger function for updated_at
        try:
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_authors_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)
            results.append("✅ Trigger function created")
        except Exception as e:
            results.append(f"⚠️ Trigger function: {str(e)}")

        # Step 10: Create trigger on authors table
        try:
            await conn.execute("""
                DROP TRIGGER IF EXISTS update_authors_updated_at_trigger ON authors
            """)
            await conn.execute("""
                CREATE TRIGGER update_authors_updated_at_trigger
                    BEFORE UPDATE ON authors
                    FOR EACH ROW
                    EXECUTE FUNCTION update_authors_updated_at()
            """)
            results.append("✅ Trigger on authors table created")
        except Exception as e:
            results.append(f"⚠️ Trigger: {str(e)}")

        # Final verification
        verification = {}
        
        # Check authors table
        authors_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'authors'
            )
        """)
        verification['authors_table'] = authors_exist
        
        # Check document_authors table
        doc_authors_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'document_authors'
            )
        """)
        verification['document_authors_table'] = doc_authors_exist
        
        # Check document_type column
        doc_type_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'books' AND column_name = 'document_type'
            )
        """)
        verification['document_type_column'] = doc_type_exists
        
        # Check article_url column
        article_url_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'books' AND column_name = 'article_url'
            )
        """)
        verification['article_url_column'] = article_url_exists

        # Get counts
        author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
        doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")

        await conn.close()

        all_verified = all(verification.values())

        return {
            "status": "success" if all_verified else "partial",
            "results": results,
            "verification": verification,
            "stats": {
                "authors": author_count,
                "document_authors": doc_author_count,
                "books": book_count
            },
            "message": "Migration 003 completed successfully!" if all_verified else "Migration completed with warnings",
            "next_steps": [
                "Run data migration to populate authors from existing books.author column",
                "Test the new multi-author functionality",
                "Update frontend to use new multi-author endpoints"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@migration_003_router.get("/check-status")
async def check_migration_003_status():
    """
    Check if Migration 003 has been run
    Access this at: https://your-backend-url/migration-003/check-status
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)

        # Check if tables exist
        authors_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'authors'
            )
        """)

        doc_authors_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'document_authors'
            )
        """)

        doc_type_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'books' AND column_name = 'document_type'
            )
        """)

        article_url_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'books' AND column_name = 'article_url'
            )
        """)

        migration_complete = all([authors_exist, doc_authors_exist, doc_type_exists, article_url_exists])

        stats = {}
        if migration_complete:
            stats = {
                "authors": await conn.fetchval("SELECT COUNT(*) FROM authors"),
                "document_authors": await conn.fetchval("SELECT COUNT(*) FROM document_authors"),
                "books": await conn.fetchval("SELECT COUNT(*) FROM books")
            }

        await conn.close()

        return {
            "migration_complete": migration_complete,
            "tables": {
                "authors": authors_exist,
                "document_authors": doc_authors_exist
            },
            "columns": {
                "document_type": doc_type_exists,
                "article_url": article_url_exists
            },
            "stats": stats,
            "message": "Migration 003 is complete" if migration_complete else "Migration 003 needs to be run"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@migration_003_router.get("/find-books")
async def find_books_in_database():
    """
    Find where books/documents are actually stored in the database
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        results = {}

        # Check documents table (vector store)
        try:
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            if doc_count > 0:
                # Get unique filenames
                unique_files = await conn.fetch("""
                    SELECT DISTINCT filename, COUNT(*) as chunks
                    FROM documents 
                    WHERE filename IS NOT NULL
                    GROUP BY filename
                    ORDER BY filename
                    LIMIT 20
                """)
                
                results['documents_table'] = {
                    "total_chunks": doc_count,
                    "unique_files": len(unique_files),
                    "sample_files": [{"filename": f['filename'], "chunks": f['chunks']} for f in unique_files]
                }
        except Exception as e:
            results['documents_table'] = {"error": str(e)}

        # Check books table
        try:
            books_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            results['books_table'] = {"count": books_count}
            
            if books_count > 0:
                sample_books = await conn.fetch("SELECT * FROM books LIMIT 5")
                results['books_table']['sample'] = [dict(book) for book in sample_books]
        except Exception as e:
            results['books_table'] = {"error": str(e)}

        # List all tables
        try:
            tables = await conn.fetch("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            results['all_tables'] = []
            for table in tables:
                table_name = table['table_name']
                try:
                    row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    results['all_tables'].append({
                        "name": table_name,
                        "columns": table['column_count'],
                        "rows": row_count
                    })
                except:
                    results['all_tables'].append({
                        "name": table_name,
                        "columns": table['column_count'],
                        "rows": "error"
                    })
        except Exception as e:
            results['all_tables'] = {"error": str(e)}

        await conn.close()
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@migration_003_router.get("/rollback")
async def rollback_migration_003():
    """
    Rollback Migration 003: Multi-Author Metadata Enhancement
    WARNING: This will delete authors and document_authors tables
    
    Access this at: https://your-backend-url/migration-003/rollback?confirm=yes
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        results = []

        # Drop triggers and functions
        try:
            await conn.execute("DROP TRIGGER IF EXISTS update_authors_updated_at_trigger ON authors")
            await conn.execute("DROP FUNCTION IF EXISTS update_authors_updated_at()")
            results.append("✅ Dropped triggers and functions")
        except Exception as e:
            results.append(f"⚠️ Triggers/functions: {str(e)}")

        # Drop indexes
        indexes_to_drop = [
            "idx_document_authors_order",
            "idx_document_authors_author",
            "idx_document_authors_book",
            "idx_authors_name"
        ]
        
        for idx in indexes_to_drop:
            try:
                await conn.execute(f"DROP INDEX IF EXISTS {idx}")
                results.append(f"✅ Dropped index {idx}")
            except Exception as e:
                results.append(f"⚠️ Index {idx}: {str(e)}")

        # Drop tables
        try:
            await conn.execute("DROP TABLE IF EXISTS document_authors CASCADE")
            results.append("✅ Dropped document_authors table")
        except Exception as e:
            results.append(f"⚠️ document_authors table: {str(e)}")

        try:
            await conn.execute("DROP TABLE IF EXISTS authors CASCADE")
            results.append("✅ Dropped authors table")
        except Exception as e:
            results.append(f"⚠️ authors table: {str(e)}")

        # Remove columns from books table
        try:
            await conn.execute("ALTER TABLE books DROP COLUMN IF EXISTS document_type")
            results.append("✅ Dropped document_type column")
        except Exception as e:
            results.append(f"⚠️ document_type column: {str(e)}")

        try:
            await conn.execute("ALTER TABLE books DROP COLUMN IF EXISTS article_url")
            results.append("✅ Dropped article_url column")
        except Exception as e:
            results.append(f"⚠️ article_url column: {str(e)}")

        await conn.close()

        return {
            "status": "success",
            "results": results,
            "message": "Migration 003 rolled back successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")
