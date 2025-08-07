#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check_content_types():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Check what content types exist
    query = """
        SELECT DISTINCT metadata->>'type' as content_type, COUNT(*) as count 
        FROM documents 
        WHERE metadata->>'type' IS NOT NULL 
        GROUP BY metadata->>'type' 
        ORDER BY count DESC
    """
    types = await conn.fetch(query)
    print('Content types in database:')
    for row in types:
        print(f'  {row["content_type"]}: {row["count"]} chunks')
    
    # Check specific book
    book_types = await conn.fetch("""
        SELECT DISTINCT metadata->>'type' as content_type
        FROM documents 
        WHERE filename = '21st Century RPG- -Free, ILE, and MVC.pdf' AND metadata->>'type' IS NOT NULL
    """)
    print(f'\nContent types in "21st Century RPG":')
    for row in book_types:
        print(f'  {row["content_type"]}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_content_types())