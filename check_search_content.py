#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check_search_content():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Check what different content types contain "data fabric"
    query = """
        SELECT metadata->>'type' as content_type, COUNT(*) as count,
               content
        FROM documents 
        WHERE to_tsvector('english', content) @@ plainto_tsquery('english', 'data fabric')
        GROUP BY metadata->>'type', content
        ORDER BY count DESC
        LIMIT 10
    """
    
    results = await conn.fetch(query)
    print(f'Found {len(results)} different pieces of content mentioning "data fabric":')
    
    for i, row in enumerate(results):
        print(f'\n{i+1}. Content Type: {row["content_type"]}')
        print(f'   Preview: {row["content"][:100]}...')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_search_content())