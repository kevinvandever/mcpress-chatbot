#!/usr/bin/env python3
"""
Script to reprocess existing documents and update their metadata
including page counts and chunks
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv
import json

load_dotenv()

async def reprocess_documents():
    """Reprocess all documents to update page counts and metadata"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print("🔄 Connecting to database...")

    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")

        # First, let's analyze the embeddings table to get chunk counts per document
        print("\n📊 Analyzing embeddings table...")

        # Get chunk counts from embeddings grouped by book_id or filename
        chunks_data = await conn.fetch("""
            SELECT
                b.id as book_id,
                b.filename,
                b.title,
                COUNT(e.id) as chunk_count,
                MAX(CAST(e.metadata->>'page' AS INTEGER)) as max_page
            FROM books b
            LEFT JOIN embeddings e ON e.book_id = b.id OR
                (e.book_id IS NULL AND e.metadata->>'source' = b.filename)
            GROUP BY b.id, b.filename, b.title
            ORDER BY b.id
        """)

        if not chunks_data:
            # Try alternative approach - match by filename in metadata
            print("🔄 Trying alternative matching by filename...")
            chunks_data = await conn.fetch("""
                SELECT
                    b.id as book_id,
                    b.filename,
                    b.title,
                    (SELECT COUNT(*) FROM embeddings e
                     WHERE e.metadata->>'source' = b.filename
                        OR e.metadata->>'filename' = b.filename) as chunk_count
                FROM books b
                ORDER BY b.id
            """)

        print(f"📚 Found data for {len(chunks_data)} books")

        # Update each book with calculated metadata
        updated_count = 0
        for row in chunks_data:
            book_id = row['book_id']
            filename = row['filename']
            chunk_count = row['chunk_count'] or 0

            # Estimate pages based on chunks (typically 3-5 chunks per page)
            # or use max_page if available
            if 'max_page' in row and row['max_page']:
                estimated_pages = row['max_page']
            else:
                estimated_pages = max(1, chunk_count // 4) if chunk_count > 0 else 0

            print(f"\n📖 Processing: {filename}")
            print(f"   Book ID: {book_id}")
            print(f"   Chunks: {chunk_count}")
            print(f"   Estimated pages: {estimated_pages}")

            # Update the book record
            await conn.execute("""
                UPDATE books
                SET total_pages = $1
                WHERE id = $2
            """, estimated_pages, book_id)

            # Also update book_id in embeddings if not set
            if chunk_count > 0:
                await conn.execute("""
                    UPDATE embeddings
                    SET book_id = $1
                    WHERE (metadata->>'source' = $2 OR metadata->>'filename' = $2)
                    AND book_id IS NULL
                """, book_id, filename)

            updated_count += 1

        print(f"\n✅ Updated {updated_count} books with page counts")

        # Now let's check for documents in the old documents table that might have metadata
        print("\n🔍 Checking for additional metadata in documents table...")

        doc_metadata = await conn.fetch("""
            SELECT DISTINCT ON (filename)
                filename,
                metadata,
                COUNT(*) as chunk_count
            FROM documents
            WHERE metadata IS NOT NULL
            GROUP BY filename, metadata
        """)

        metadata_updated = 0
        for doc in doc_metadata:
            try:
                metadata = doc['metadata']
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                if metadata and isinstance(metadata, dict):
                    # Extract useful metadata
                    updates = []
                    params = []
                    param_count = 1

                    if 'author' in metadata and metadata['author']:
                        updates.append(f"author = ${param_count}")
                        params.append(metadata['author'])
                        param_count += 1

                    if 'category' in metadata and metadata['category']:
                        updates.append(f"category = ${param_count}")
                        params.append(metadata['category'])
                        param_count += 1

                    if 'title' in metadata and metadata['title']:
                        updates.append(f"title = ${param_count}")
                        params.append(metadata['title'])
                        param_count += 1

                    if updates:
                        params.append(doc['filename'])
                        query = f"UPDATE books SET {', '.join(updates)} WHERE filename = ${param_count}"
                        await conn.execute(query, *params)
                        metadata_updated += 1
                        print(f"   ✅ Updated metadata for {doc['filename']}")

            except Exception as e:
                print(f"   ⚠️ Could not update metadata for {doc['filename']}: {e}")

        if metadata_updated > 0:
            print(f"\n✅ Updated metadata for {metadata_updated} documents")

        # Final statistics
        print("\n📊 Final Statistics:")

        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_books,
                COUNT(CASE WHEN total_pages > 0 THEN 1 END) as books_with_pages,
                SUM(total_pages) as total_pages,
                COUNT(CASE WHEN author IS NOT NULL AND author != 'Unknown' THEN 1 END) as books_with_author,
                COUNT(CASE WHEN category IS NOT NULL AND category != 'General' THEN 1 END) as books_with_category
            FROM books
        """)

        embedding_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_embeddings,
                COUNT(DISTINCT book_id) as books_linked_to_embeddings
            FROM embeddings
            WHERE book_id IS NOT NULL
        """)

        print(f"  📚 Total books: {stats['total_books']}")
        print(f"  📄 Books with page counts: {stats['books_with_pages']}")
        print(f"  📑 Total pages: {stats['total_pages'] or 0}")
        print(f"  ✍️ Books with authors: {stats['books_with_author']}")
        print(f"  🏷️ Books with categories: {stats['books_with_category']}")
        print(f"  🔗 Total embeddings: {embedding_stats['total_embeddings']}")
        print(f"  🔗 Books linked to embeddings: {embedding_stats['books_linked_to_embeddings']}")

        await conn.close()
        print("\n🎉 Reprocessing completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return False


async def add_reprocess_endpoint():
    """Add a reprocess endpoint to admin_documents.py"""
    print("\n💡 To add reprocessing to the admin interface, add this endpoint to admin_documents.py:")
    print("""
@router.post("/reprocess-all")
async def reprocess_all_documents(
    current_admin = Depends(get_current_admin)
):
    '''Reprocess all documents to update page counts and metadata'''
    try:
        conn = await get_vector_store()._get_connection()
        try:
            # Get chunk counts from embeddings
            async with conn.cursor() as cursor:
                await cursor.execute('''
                    SELECT
                        b.id,
                        b.filename,
                        COUNT(e.id) as chunk_count
                    FROM books b
                    LEFT JOIN embeddings e ON e.book_id = b.id
                    GROUP BY b.id, b.filename
                ''')

                updated = 0
                async for row in cursor:
                    book_id, filename, chunk_count = row
                    estimated_pages = max(1, chunk_count // 4) if chunk_count > 0 else 0

                    await cursor.execute(
                        "UPDATE books SET total_pages = %s WHERE id = %s",
                        (estimated_pages, book_id)
                    )
                    updated += 1

                await conn.commit()

                return {
                    "status": "success",
                    "message": f"Reprocessed {updated} documents",
                    "updated": updated
                }
        finally:
            await conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
""")


if __name__ == "__main__":
    print("🚀 Starting document reprocessing...")
    print("=" * 60)

    success = asyncio.run(reprocess_documents())

    if success:
        asyncio.run(add_reprocess_endpoint())

    exit(0 if success else 1)