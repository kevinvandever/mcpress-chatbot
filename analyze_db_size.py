#!/usr/bin/env python3
"""
Direct database analysis for size optimization
"""

import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def analyze_database():
    """Analyze database size and content"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found. Set it in .env file")
        return

    print("🔍 Connecting to Railway PostgreSQL...")
    conn = await asyncpg.connect(database_url, command_timeout=60)

    try:
        # Total documents
        total_docs = await conn.fetchval('SELECT COUNT(*) FROM documents')
        print(f"\n📊 Total document chunks: {total_docs:,}")

        # Docs with embeddings
        with_embeddings = await conn.fetchval('SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL')
        print(f"📊 Chunks with embeddings: {with_embeddings:,} ({with_embeddings/total_docs*100:.1f}%)")

        # Database size
        db_size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        print(f"\n💾 Total database size: {db_size}")

        # Table size breakdown
        table_size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_total_relation_size('documents'))
        """)
        print(f"💾 Documents table size: {table_size}")

        # Check for duplicate content
        print(f"\n🔍 Analyzing duplicate content...")
        duplicates = await conn.fetch("""
            SELECT content, COUNT(*) as count
            FROM documents
            GROUP BY content
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)

        if duplicates:
            total_duplicate_chunks = sum(row['count'] - 1 for row in duplicates)
            print(f"⚠️  Found duplicate content patterns")
            print(f"Top duplicates:")
            for row in duplicates[:5]:
                content_preview = row['content'][:60].replace('\n', ' ')
                print(f"  - {row['count']} copies: \"{content_preview}...\"")
        else:
            print("✅ No exact duplicate content found")

        # Analyze filename patterns
        print(f"\n📚 Analyzing file distribution...")
        file_stats = await conn.fetch("""
            SELECT filename, COUNT(*) as chunks
            FROM documents
            GROUP BY filename
            ORDER BY chunks DESC
            LIMIT 10
        """)

        print(f"\nTop 10 files by chunk count:")
        for row in file_stats:
            print(f"  {row['filename']}: {row['chunks']:,} chunks")

        # Estimate compression potential
        print(f"\n💡 Size Reduction Opportunities:")

        # 1. Remove embeddings (keep in separate table or service)
        embedding_size = await conn.fetchval("""
            SELECT pg_size_pretty(
                SUM(pg_column_size(embedding))
            )
            FROM documents
            WHERE embedding IS NOT NULL
        """)
        print(f"  1. Embeddings alone: ~{embedding_size}")

        # 2. Short/low-value chunks
        short_chunks = await conn.fetchval("""
            SELECT COUNT(*)
            FROM documents
            WHERE LENGTH(content) < 100
        """)
        print(f"  2. Very short chunks (<100 chars): {short_chunks:,}")

        # 3. Avg content length
        avg_length = await conn.fetchval("""
            SELECT AVG(LENGTH(content))::int
            FROM documents
        """)
        print(f"  3. Average chunk size: {avg_length} characters")

    finally:
        await conn.close()
        print(f"\n✅ Analysis complete")

if __name__ == "__main__":
    asyncio.run(analyze_database())
