#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check_image_content():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Find an actual image chunk
    image_chunk = await conn.fetchrow("""
        SELECT filename, content, metadata 
        FROM documents 
        WHERE metadata->>'type' = 'image' 
        LIMIT 1
    """)
    
    if image_chunk:
        print(f'Image chunk from: {image_chunk["filename"]}')
        print(f'Content preview: {image_chunk["content"][:200]}...')
        metadata = json.loads(image_chunk['metadata'])
        print(f'Metadata: {metadata}')
    else:
        print('No image chunks found')
    
    # Find a code chunk
    code_chunk = await conn.fetchrow("""
        SELECT filename, content, metadata 
        FROM documents 
        WHERE metadata->>'type' = 'code' 
        LIMIT 1
    """)
    
    if code_chunk:
        print(f'\nCode chunk from: {code_chunk["filename"]}')
        print(f'Content preview: {code_chunk["content"][:200]}...')
        metadata = json.loads(code_chunk['metadata'])
        print(f'Metadata: {metadata}')
    else:
        print('No code chunks found')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_image_content())