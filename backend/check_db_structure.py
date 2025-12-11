#!/usr/bin/env python3
"""
Check database structure to understand the schema
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_structure():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return

    conn = await asyncpg.connect(database_url)

    # Check embeddings table structure
    embeddings_cols = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'embeddings'
        ORDER BY ordinal_position
    """)

    print("📋 Embeddings table columns:")
    for col in embeddings_cols:
        print(f"  - {col['column_name']}: {col['data_type']}")

    # Check books table structure
    books_cols = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'books'
        ORDER BY ordinal_position
    """)

    print("\n📋 Books table columns:")
    for col in books_cols:
        print(f"  - {col['column_name']}: {col['data_type']}")

    # Check sample embeddings data
    sample = await conn.fetch("""
        SELECT * FROM embeddings LIMIT 1
    """)

    if sample:
        print("\n📄 Sample embedding record:")
        for key, value in dict(sample[0]).items():
            if key == 'embedding':
                print(f"  - {key}: <vector data>")
            else:
                print(f"  - {key}: {value}")

    # Check books count
    book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
    print(f"\n📚 Total books: {book_count}")

    # Check embeddings count
    embed_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
    print(f"🔗 Total embeddings: {embed_count}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_structure())