#!/usr/bin/env python3
"""
Check the actual books table schema on Railway.
This script must be run on Railway: railway run python3 check_books_schema.py
"""

import asyncio
import asyncpg
import os
import sys

async def check_books_schema():
    """Check what columns actually exist in the books table"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print('❌ No DATABASE_URL found')
            return
        
        print('🔍 Checking books table schema...')
        conn = await asyncpg.connect(database_url)
        
        # Check if books table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'books'
            )
        """)
        
        if not table_exists:
            print('❌ Books table does not exist')
            await conn.close()
            return
        
        print('✅ Books table exists')
        
        # Get actual column information
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)
        
        print('\n📋 Books table columns:')
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        # Get sample data
        sample = await conn.fetchrow("SELECT * FROM books LIMIT 1")
        if sample:
            print('\n📄 Sample book record:')
            for key, value in sample.items():
                print(f"  {key}: {value}")
        else:
            print('\n⚠️  No books found in table')
        
        # Count total books
        count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f'\n📊 Total books: {count}')
        
        await conn.close()
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_books_schema())