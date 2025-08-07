#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check_actual_code():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Find actual code chunks
    code_chunks = await conn.fetch("""
        SELECT content, metadata 
        FROM documents 
        WHERE metadata->>'type' = 'code'
        LIMIT 5
    """)
    
    print(f'Found {len(code_chunks)} actual code chunks:')
    for i, row in enumerate(code_chunks):
        print(f'\n{i+1}. Content: {row["content"][:150]}...')
        metadata = json.loads(row['metadata'])
        print(f'   Metadata: {metadata}')
    
    # Also check what text chunks look like that contain "Code block from"
    text_with_code = await conn.fetch("""
        SELECT content, metadata 
        FROM documents 
        WHERE metadata->>'type' = 'text' AND content LIKE 'Code block from%'
        LIMIT 3
    """)
    
    print(f'\nFound {len(text_with_code)} text chunks that start with "Code block from":')
    for i, row in enumerate(text_with_code):
        print(f'\n{i+1}. Content: {row["content"][:150]}...')
        metadata = json.loads(row['metadata'])
        print(f'   Metadata type: {metadata.get("type")}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_actual_code())