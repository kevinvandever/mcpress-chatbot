#!/usr/bin/env python3
"""Check what's actually in the local database"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check_database():
    database_url = os.getenv('DATABASE_URL')
    print(f"Connecting to: {database_url[:50]}...")
    
    conn = await asyncpg.connect(database_url)
    
    try:
        # Count total documents
        count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        print(f"Total document chunks: {count}")
        
        # Count unique filenames
        unique_files = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        print(f"Unique books: {unique_files}")
        
        # Get sample of filenames
        files = await conn.fetch("SELECT DISTINCT filename FROM documents LIMIT 10")
        print("\nSample books in database:")
        for row in files:
            print(f"  - {row['filename']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_database())