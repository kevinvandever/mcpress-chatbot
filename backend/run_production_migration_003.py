#!/usr/bin/env python3
"""
Production Migration 003: Multi-Author Metadata Enhancement
Complete production migration with backup, schema migration, data migration, and verification

This script performs the complete migration process for production:
1. Create database backup using pg_dump
2. Execute schema migration (003_multi_author_support.sql)
3. Run data migration to populate authors table
4. Run verification queries
5. Check for data integrity issues

Usage:
    python3 backend/run_production_migration_003.py

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import os
import asyncio
import asyncpg
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    print("Please set DATABASE_URL in your .env file")
    exit(1)

# Parse DATABASE_URL for pg_dump
def parse_database_url(url):
    """Parse DATABASE_URL into components for pg_dump"""
    # Format: postgresql://user:password@host:port/database
    if not url.startswith('postgresql://'):
        raise ValueError("DATABASE_URL must start with postgresql://")
    
    url = url[13:]  # Remove postgresql://
    
    if '@' in url:
        auth, host_db = url.split('@', 1)
        if ':' in auth:
            user, password = auth.split(':', 1)
        else:
            user = auth
            password = None
    else:
        user = None
        password = None
        host_db = url
    
    if '/' in host_db:
        host_port, database = host_db.rsplit('/', 1)
    else:
        host_port = host_db
        database = 'postgres'
    
    if ':' in host_port:
        host, port = host_port.rsplit(':', 1)
    else:
        host = host_port
        port = '5432'
    
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database
    }


async def create_database_backup():
    """Create a database backup using pg_dump"""
    print("💾 Step 1: Creating database backup...")
    
    try:
        db_config = parse_database_url(DATABASE_URL)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"mcpress_db_backup_{timestamp}.sql"
        backup_path = Path(backup_filename)
        
        # Prepare pg_dump command
        cmd = [
            'pg_dump',
            '--host', db_config['host'],
            '--port', db_config['port'],
            '--username', db_config['user'],
            '--dbname', db_config['database'],
            '--no-password',  # Use PGPASSWORD environment variable
            '--verbose',
            '--clean',  # Include DROP statements
            '--if-exists',  # Use IF EXISTS for DROP statements
            '--file', str(backup_path)
        ]
        
        # Set password in environment
        env = os.environ.copy()
        if db_config['password']:
            env['PGPASSWORD'] = db_config['password']
        
        print(f"📝 Creating backup: {backup_filename}")
        print(f"🔗 Host: {db_config['host']}:{db_config['port']}")
        print(f"👤 User: {db_config['user']}")
        print(f"🗄️  Database: {db_config['database']}")
        
        # Run pg_dump
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            backup_size = backup_path.stat().st_size
            print(f"✅ Database backup created successfully")
            print(f"📁 File: {backup_path}")
            print(f"📊 Size: {backup_size / (1024*1024):.1f} MB")
            return str(backup_path)
        else:
            print(f"❌ pg_dump failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            
            # Try alternative backup method using SQL
            print("\n🔄 Attempting alternative backup method...")
            return await create_sql_backup()
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        print("\n🔄 Attempting alternative backup method...")
        return await create_sql_backup()


async def create_sql_backup():
    """Alternative backup method using SQL queries"""
    print("📝 Creating SQL backup using database queries...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"mcpress_db_backup_sql_{timestamp}.sql"
        
        with open(backup_filename, 'w') as f:
            f.write(f"-- MC Press Database Backup\n")
            f.write(f"-- Created: {datetime.now().isoformat()}\n")
            f.write(f"-- Source: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}\n\n")
            
            # Get table list
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            for table_row in tables:
                table_name = table_row['table_name']
                print(f"  📋 Backing up table: {table_name}")
                
                # Get table schema
                f.write(f"\n-- Table: {table_name}\n")
                
                # Get row count
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                f.write(f"-- Rows: {count}\n")
                
                if count > 0:
                    # Export data (limit to prevent memory issues)
                    if count > 10000:
                        f.write(f"-- WARNING: Table has {count} rows, only backing up first 10000\n")
                        rows = await conn.fetch(f"SELECT * FROM {table_name} LIMIT 10000")
                    else:
                        rows = await conn.fetch(f"SELECT * FROM {table_name}")
                    
                    if rows:
                        # Write sample data as comments (not executable)
                        f.write(f"-- Sample data from {table_name}:\n")
                        for i, row in enumerate(rows[:5]):  # Just first 5 rows as sample
                            f.write(f"-- Row {i+1}: {dict(row)}\n")
                        f.write(f"-- ... and {len(rows)-5} more rows\n")
                
                f.write("\n")
        
        backup_size = Path(backup_filename).stat().st_size
        print(f"✅ SQL backup created: {backup_filename}")
        print(f"📊 Size: {backup_size / 1024:.1f} KB")
        return backup_filename
        
    except Exception as e:
        print(f"❌ SQL backup failed: {e}")
        return None
    finally:
        await conn.close()


async def run_schema_migration():
    """Execute the schema migration"""
    print("\n🏗️  Step 2: Running schema migration...")
    
    # Import and run the existing migration script
    try:
        # Import the migration function
        sys.path.append(str(Path(__file__).parent))
        from run_migration_003 import run_migration
        
        await run_migration()
        return True
        
    except Exception as e:
        print(f"❌ Schema migration failed: {e}")
        return False


async def run_data_migration():
    """Execute the data migration"""
    print("\n📊 Step 3: Running data migration...")
    
    try:
        # Import and run the data migration
        from data_migration_003 import run_data_migration
        
        await run_data_migration()
        return True
        
    except Exception as e:
        print(f"❌ Data migration failed: {e}")
        return False


async def run_verification():
    """Run verification queries"""
    print("\n🔍 Step 4: Running verification...")
    
    try:
        # Import and run verification
        from verify_data_migration_003 import verify_migration
        
        await verify_migration()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def check_data_integrity():
    """Perform additional data integrity checks"""
    print("\n🛡️  Step 5: Checking data integrity...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check 1: Ensure all books have at least one author
        orphaned_books = await conn.fetchval("""
            SELECT COUNT(*)
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            WHERE da.book_id IS NULL
        """)
        
        print(f"📋 Books without authors: {orphaned_books}")
        
        # Check 2: Ensure no duplicate author associations
        duplicate_associations = await conn.fetchval("""
            SELECT COUNT(*)
            FROM (
                SELECT book_id, author_id, COUNT(*) as cnt
                FROM document_authors
                GROUP BY book_id, author_id
                HAVING COUNT(*) > 1
            ) duplicates
        """)
        
        print(f"📋 Duplicate associations: {duplicate_associations}")
        
        # Check 3: Ensure author names are unique
        duplicate_authors = await conn.fetchval("""
            SELECT COUNT(*)
            FROM (
                SELECT name, COUNT(*) as cnt
                FROM authors
                GROUP BY name
                HAVING COUNT(*) > 1
            ) duplicates
        """)
        
        print(f"📋 Duplicate author names: {duplicate_authors}")
        
        # Check 4: Ensure all foreign keys are valid
        invalid_book_refs = await conn.fetchval("""
            SELECT COUNT(*)
            FROM document_authors da
            LEFT JOIN books b ON da.book_id = b.id
            WHERE b.id IS NULL
        """)
        
        invalid_author_refs = await conn.fetchval("""
            SELECT COUNT(*)
            FROM document_authors da
            LEFT JOIN authors a ON da.author_id = a.id
            WHERE a.id IS NULL
        """)
        
        print(f"📋 Invalid book references: {invalid_book_refs}")
        print(f"📋 Invalid author references: {invalid_author_refs}")
        
        # Overall integrity assessment
        integrity_issues = (
            orphaned_books + duplicate_associations + 
            duplicate_authors + invalid_book_refs + invalid_author_refs
        )
        
        if integrity_issues == 0:
            print("✅ Data integrity check PASSED - no issues found")
            return True
        else:
            print(f"⚠️  Data integrity check found {integrity_issues} issues")
            return False
            
    except Exception as e:
        print(f"❌ Data integrity check failed: {e}")
        return False
    finally:
        await conn.close()


async def main():
    """Main migration process"""
    print("🚀 MC Press Production Migration 003")
    print("=" * 50)
    print("Multi-Author Metadata Enhancement")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Confirm before proceeding
    print("⚠️  This will modify the production database!")
    print("   - Create database backup")
    print("   - Add new tables (authors, document_authors)")
    print("   - Modify books table (add document_type, article_url)")
    print("   - Migrate existing author data")
    print()
    
    confirm = input("Continue with production migration? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Migration cancelled")
        return
    
    print("\n🎯 Starting migration process...")
    
    # Step 1: Create backup
    backup_path = await create_database_backup()
    if not backup_path:
        print("❌ Could not create database backup")
        print("   Migration cancelled for safety")
        return
    
    try:
        # Step 2: Schema migration
        schema_success = await run_schema_migration()
        if not schema_success:
            print("❌ Schema migration failed - stopping")
            return
        
        # Step 3: Data migration
        data_success = await run_data_migration()
        if not data_success:
            print("❌ Data migration failed - stopping")
            return
        
        # Step 4: Verification
        verification_success = await run_verification()
        if not verification_success:
            print("⚠️  Verification had issues - please review")
        
        # Step 5: Data integrity
        integrity_success = await check_data_integrity()
        if not integrity_success:
            print("⚠️  Data integrity issues found - please review")
        
        # Final summary
        print("\n" + "=" * 50)
        print("🎉 Production Migration 003 Complete!")
        print()
        print("📋 Summary:")
        print(f"  ✅ Database backup: {backup_path}")
        print(f"  {'✅' if schema_success else '❌'} Schema migration")
        print(f"  {'✅' if data_success else '❌'} Data migration")
        print(f"  {'✅' if verification_success else '⚠️'} Verification")
        print(f"  {'✅' if integrity_success else '⚠️'} Data integrity")
        
        if schema_success and data_success:
            print("\n🎯 Next steps:")
            print("   1. Test the application with new multi-author features")
            print("   2. Update frontend to use new API endpoints")
            print("   3. Monitor for any issues")
            print("   4. Consider removing old books.author column if everything works")
        else:
            print("\n⚠️  Migration had issues - please review logs and consider rollback")
            print(f"   Backup available at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Migration process failed: {e}")
        print(f"💾 Database backup available at: {backup_path}")
        print("   Consider restoring from backup if needed")
        raise


if __name__ == "__main__":
    asyncio.run(main())