#!/usr/bin/env python3
"""
Check which books are currently in the database
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check_books():
    """Check what books are in the database"""
    import asyncpg

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set in environment")
        return

    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)

    try:
        # Get unique filenames
        rows = await conn.fetch("""
            SELECT DISTINCT filename
            FROM documents
            ORDER BY filename
        """)

        print(f"\n📚 Found {len(rows)} unique books in database:\n")
        print("="*60)

        for i, row in enumerate(rows, 1):
            filename = row['filename']
            # Get chunk count for this book
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM documents WHERE filename = $1",
                filename
            )
            print(f"{i:3d}. {filename:50s} ({count:,} chunks)")

        print("="*60)
        print(f"\nTotal books: {len(rows)}")
        print(f"Target: 115 books")
        print(f"Missing: {115 - len(rows)} books")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_books())
