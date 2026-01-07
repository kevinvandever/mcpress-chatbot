#!/usr/bin/env python3
"""
Check actual table structure on Railway to understand column mismatches
This script must be run on Railway: railway run python3 check_table_columns_railway.py
"""

import asyncio
import asyncpg
import os
import sys

async def check_table_structure():
    """Check the actual structure of tables on Railway"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return 1
    
    print("🔍 CHECKING TABLE STRUCTURE ON RAILWAY")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # List all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        print(f"\n📋 TABLES FOUND ({len(tables)}):")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Check specific tables we care about
        tables_to_check = ['books', 'authors', 'document_authors', 'documents']
        
        for table_name in tables_to_check:
            print(f"\n🔍 TABLE: {table_name}")
            print("-" * 40)
            
            # Check if table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """, table_name)
            
            if not exists:
                print(f"❌ Table '{table_name}' does not exist")
                continue
                
            # Get column information
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            print(f"✅ Table '{table_name}' exists with {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   - {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            # Get row count
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                print(f"   📊 Row count: {count}")
            except Exception as e:
                print(f"   ❌ Error counting rows: {e}")
        
        # Check for foreign key relationships
        print(f"\n🔗 FOREIGN KEY RELATIONSHIPS:")
        print("-" * 40)
        
        fks = await conn.fetch("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name
        """)
        
        if fks:
            for fk in fks:
                print(f"   {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        else:
            print("   No foreign key relationships found")
        
        await conn.close()
        print(f"\n✅ Database inspection complete")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Main function"""
    try:
        return asyncio.run(check_table_structure())
    except Exception as e:
        print(f"❌ Failed to run: {e}")
        print("This script must be run on Railway where DATABASE_URL is available.")
        print("Use: railway run python3 check_table_columns_railway.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())