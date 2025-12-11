#!/usr/bin/env python3
"""
Migrate chunks from documents table to embeddings table and update page counts
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv
import json

load_dotenv()

async def migrate_chunks():
    """Migrate chunks from documents to embeddings and update books"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print("🔄 Connecting to database...")

    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")

        # First check what's in the documents table
        print("\n📊 Analyzing documents table...")

        doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"📄 Found {doc_count} document chunks")

        if doc_count == 0:
            print("⚠️ No documents to migrate")
            await conn.close()
            return False

        # Check structure of documents table
        doc_cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)

        print("\n📋 Documents table structure:")
        for col in doc_cols:
            print(f"  - {col['column_name']}: {col['data_type']}")

        # Get sample document to understand structure
        sample = await conn.fetchrow("SELECT * FROM documents LIMIT 1")
        if sample:
            print("\n📄 Sample document record:")
            for key, value in dict(sample).items():
                if key == 'embedding':
                    print(f"  - {key}: <vector of length {len(value) if value else 0}>")
                elif key == 'metadata':
                    print(f"  - {key}: {json.dumps(value, indent=2) if value else None}")
                else:
                    print(f"  - {key}: {value}")

        # Process each book and migrate its chunks
        books = await conn.fetch("SELECT id, filename, title FROM books ORDER BY id")

        print(f"\n🔄 Processing {len(books)} books...")

        total_migrated = 0
        for book in books:
            book_id = book['id']
            filename = book['filename']
            title = book['title'] or filename

            print(f"\n📖 Processing: {filename} (ID: {book_id})")

            # Find chunks for this document in documents table
            # Try matching by filename in metadata or content
            chunks = await conn.fetch("""
                SELECT
                    id,
                    content,
                    embedding,
                    page_number,
                    chunk_index,
                    metadata,
                    created_at
                FROM documents
                WHERE filename = $1
                   OR (metadata->>'source' = $1)
                   OR (metadata->>'filename' = $1)
                ORDER BY
                    COALESCE(chunk_index, 0),
                    COALESCE(page_number, 0),
                    id
            """, filename)

            if not chunks:
                # Try without .pdf extension
                filename_no_ext = filename.replace('.pdf', '')
                chunks = await conn.fetch("""
                    SELECT
                        id,
                        content,
                        embedding,
                        page_number,
                        chunk_index,
                        metadata,
                        created_at
                    FROM documents
                    WHERE filename = $1
                       OR (metadata->>'source' = $1)
                       OR (metadata->>'filename' = $1)
                       OR content LIKE $2
                    ORDER BY
                        COALESCE(chunk_index, 0),
                        COALESCE(page_number, 0),
                        id
                    LIMIT 500
                """, filename_no_ext, f'%{title[:30]}%')

            if chunks:
                print(f"  Found {len(chunks)} chunks")

                # Migrate chunks to embeddings table
                migrated = 0
                max_page = 0

                for i, chunk in enumerate(chunks):
                    # Determine page number
                    page_num = chunk['page_number']
                    if page_num is None:
                        # Try to extract from metadata
                        if chunk['metadata'] and isinstance(chunk['metadata'], dict):
                            page_num = chunk['metadata'].get('page', i // 3 + 1)
                        else:
                            # Estimate: ~3 chunks per page
                            page_num = i // 3 + 1

                    max_page = max(max_page, page_num or 0)

                    try:
                        # Insert into embeddings table
                        await conn.execute("""
                            INSERT INTO embeddings
                                (book_id, chunk_index, content, embedding, page_number, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            ON CONFLICT DO NOTHING
                        """,
                            book_id,
                            i,
                            chunk['content'],
                            chunk['embedding'],
                            page_num,
                            chunk['created_at'] or book['processed_at']
                        )
                        migrated += 1
                    except Exception as e:
                        print(f"    ⚠️ Could not migrate chunk {i}: {e}")

                print(f"  ✅ Migrated {migrated} chunks")
                total_migrated += migrated

                # Update book with page count
                if max_page > 0:
                    await conn.execute("""
                        UPDATE books
                        SET total_pages = $1
                        WHERE id = $2
                    """, max_page, book_id)
                    print(f"  📄 Updated page count: {max_page}")

            else:
                print(f"  ⚠️ No chunks found for this document")

        print(f"\n✅ Total chunks migrated: {total_migrated}")

        # Update books without page counts based on chunk count
        print("\n🔄 Updating remaining page counts...")

        await conn.execute("""
            UPDATE books b
            SET total_pages = GREATEST(
                1,
                COALESCE(
                    (SELECT MAX(page_number) FROM embeddings WHERE book_id = b.id),
                    (SELECT COUNT(*) / 3 FROM embeddings WHERE book_id = b.id),
                    0
                )
            )
            WHERE total_pages IS NULL OR total_pages = 0
        """)

        # Final statistics
        print("\n📊 Final Statistics:")

        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_books,
                COUNT(CASE WHEN total_pages > 0 THEN 1 END) as books_with_pages,
                SUM(total_pages) as total_pages
            FROM books
        """)

        embedding_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_embeddings,
                COUNT(DISTINCT book_id) as books_with_embeddings
            FROM embeddings
        """)

        print(f"  📚 Total books: {stats['total_books']}")
        print(f"  📄 Books with page counts: {stats['books_with_pages']}")
        print(f"  📑 Total pages across all books: {stats['total_pages'] or 0}")
        print(f"  🔗 Total embeddings: {embedding_stats['total_embeddings']}")
        print(f"  📖 Books with embeddings: {embedding_stats['books_with_embeddings']}")

        await conn.close()
        print("\n🎉 Migration completed successfully!")

        print("\n💡 Note: The documents now have:")
        print("  - Proper IDs in the books table")
        print("  - Embeddings linked via book_id")
        print("  - Estimated page counts")
        print("\n📝 You should now be able to:")
        print("  - See document IDs in the admin interface")
        print("  - Export CSVs with complete data")
        print("  - Perform bulk operations")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    print("🚀 Starting chunk migration and reprocessing...")
    print("=" * 60)

    success = asyncio.run(migrate_chunks())
    exit(0 if success else 1)