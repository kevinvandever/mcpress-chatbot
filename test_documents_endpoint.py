#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import json

load_dotenv()

async def check_documents():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set!")
        return
    
    print(f"Connecting to database...")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check if documents table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'documents'
            )
        """)
        
        if not exists:
            print("Documents table does not exist!")
            await conn.close()
            return
        
        # Count documents
        count = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
        print(f"Found {count} unique documents in database")
        
        # Get list of documents
        rows = await conn.fetch("""
            SELECT filename, COUNT(*) as chunk_count
            FROM documents 
            GROUP BY filename
            ORDER BY filename
            LIMIT 10
        """)
        
        if rows:
            print("\nFirst 10 documents:")
            for row in rows:
                print(f"  - {row['filename']}: {row['chunk_count']} chunks")
        else:
            print("No documents found in database!")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_documents())