#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def find_books_with_images_and_code():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Find books with images
    books_with_images = await conn.fetch("""
        SELECT filename, COUNT(*) as image_count
        FROM documents 
        WHERE metadata->>'type' = 'image'
        GROUP BY filename 
        ORDER BY image_count DESC
        LIMIT 3
    """)
    
    print('Books with most images:')
    for row in books_with_images:
        print(f'  {row["filename"]}: {row["image_count"]} images')
    
    # Find books with code
    books_with_code = await conn.fetch("""
        SELECT filename, COUNT(*) as code_count
        FROM documents 
        WHERE metadata->>'type' = 'code'
        GROUP BY filename 
        ORDER BY code_count DESC
        LIMIT 3
    """)
    
    print('\nBooks with most code blocks:')
    for row in books_with_code:
        print(f'  {row["filename"]}: {row["code_count"]} code blocks')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(find_books_with_images_and_code())