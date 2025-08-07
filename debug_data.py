#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def debug_data():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Check page numbers
    pages = await conn.fetchrow('SELECT MIN(page_number) as min_page, MAX(page_number) as max_page, COUNT(*) as total FROM documents')
    print(f'Page numbers - Min: {pages["min_page"]}, Max: {pages["max_page"]}, Total docs: {pages["total"]}')
    
    # Check sample documents
    samples = await conn.fetch('SELECT filename, page_number, metadata FROM documents LIMIT 5')
    for sample in samples:
        metadata = json.loads(sample['metadata']) if sample['metadata'] else {}
        print(f'Sample: {sample["filename"][:50]}, Page: {sample["page_number"]}, Metadata keys: {list(metadata.keys())}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_data())