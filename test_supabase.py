#!/usr/bin/env python3
"""
Test Supabase connection
"""
import asyncio
import asyncpg

import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')

async def test_connection():
    try:
        print("🔍 Testing Supabase connection...")
        print(f"Connection string: {SUPABASE_URL[:50]}...")
        
        conn = await asyncpg.connect(SUPABASE_URL)
        print("✅ Connected successfully!")
        
        # Test basic query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL version: {result[:50]}...")
        
        # Test pgvector
        try:
            result = await conn.fetchval("SELECT '[1,2,3]'::vector")
            print("✅ pgvector working!")
        except Exception as e:
            print(f"❌ pgvector test failed: {e}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please check:")
        print("1. Supabase project is running")
        print("2. Connection string is correct")
        print("3. Network connectivity")

if __name__ == "__main__":
    asyncio.run(test_connection())