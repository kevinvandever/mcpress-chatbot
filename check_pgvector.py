#!/usr/bin/env python3
"""
Check if pgvector can be enabled on Railway PostgreSQL
"""
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_pgvector():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check available extensions
        print("📋 Checking available PostgreSQL extensions...")
        extensions = await conn.fetch("""
            SELECT name, default_version, installed_version 
            FROM pg_available_extensions 
            WHERE name LIKE '%vector%' OR name LIKE '%embed%'
            ORDER BY name;
        """)
        
        if extensions:
            print("✅ Found vector-related extensions:")
            for ext in extensions:
                print(f"  - {ext['name']}: {ext['default_version']} (installed: {ext['installed_version']})")
        else:
            print("❌ No vector extensions available in this PostgreSQL instance")
        
        # Try to create extension
        print("\n🔧 Attempting to create vector extension...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("✅ pgvector extension created successfully!")
        except Exception as e:
            print(f"❌ Cannot create pgvector: {e}")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(check_pgvector())