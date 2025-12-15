#!/usr/bin/env python3
"""
Pre-Migration Check 003: Multi-Author Metadata Enhancement
Verify environment and database state before running the migration

This script checks:
1. Database connectivity
2. Required tables exist
3. Data consistency
4. Backup tools availability
5. Migration dependencies

Usage:
    python3 backend/pre_migration_check_003.py
"""

import os
import asyncio
import asyncpg
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    exit(1)


async def check_database_connectivity():
    """Test database connection"""
    print("🔌 Checking database connectivity...")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Test basic query
        result = await conn.fetchval("SELECT 1")
        
        if result == 1:
            print("✅ Database connection successful")
            
            # Get database info
            db_version = await conn.fetchval("SELECT version()")
            print(f"   📊 Database: {db_version.split(',')[0]}")
            
            return True
        else:
            print("❌ Database connection test failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        try:
            await conn.close()
        except:
            pass


async def check_required_tables():
    """Check if required tables exist"""
    print("\n📋 Checking required tables...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check books table
        books_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'books'
            )
        """)
        
        print(f"  {'✅' if books_exists else '❌'} books table")
        
        if not books_exists:
            print("❌ books table is required for migration")
            return False
        
        # Check books table structure
        books_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'books'
            ORDER BY ordinal_position
        """)
        
        required_columns = ['id', 'filename', 'title']
        existing_columns = [col['column_name'] for col in books_columns]
        
        for req_col in required_columns:
            exists = req_col in existing_columns
            print(f"  {'✅' if exists else '❌'} books.{req_col} column")
            if not exists:
                print(f"❌ Required column books.{req_col} is missing")
                return False
        
        # Check if migration tables already exist
        authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'authors'
            )
        """)
        
        document_authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'document_authors'
            )
        """)
        
        if authors_exists or document_authors_exists:
            print(f"  ⚠️  Migration tables already exist:")
            print(f"     authors: {'yes' if authors_exists else 'no'}")
            print(f"     document_authors: {'yes' if document_authors_exists else 'no'}")
            print("     Migration may have already been run")
        
        return True
        
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False
    finally:
        await conn.close()


async def check_data_consistency():
    """Check current data for consistency issues"""
    print("\n🔍 Checking data consistency...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Count books
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        print(f"  📚 Total books: {book_count}")
        
        if book_count == 0:
            print("  ⚠️  No books found - migration will have nothing to migrate")
            return True
        
        # Check for books with author data
        books_with_author = await conn.fetchval("""
            SELECT COUNT(*) FROM books 
            WHERE author IS NOT NULL AND author != ''
        """)
        
        books_without_author = book_count - books_with_author
        
        print(f"  👤 Books with author: {books_with_author}")
        print(f"  ❓ Books without author: {books_without_author}")
        
        if books_without_author > 0:
            print(f"  ⚠️  {books_without_author} books have no author data")
            print("     These will need to be handled during migration")
        
        # Sample some author data
        sample_authors = await conn.fetch("""
            SELECT DISTINCT author
            FROM books 
            WHERE author IS NOT NULL AND author != ''
            LIMIT 10
        """)
        
        if sample_authors:
            print("  📝 Sample authors:")
            for author in sample_authors[:5]:
                print(f"     - {author['author']}")
            if len(sample_authors) > 5:
                print(f"     ... and {len(sample_authors) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Data consistency check failed: {e}")
        return False
    finally:
        await conn.close()


def check_backup_tools():
    """Check if backup tools are available"""
    print("\n💾 Checking backup tools...")
    
    # Check for pg_dump
    try:
        result = subprocess.run(['pg_dump', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✅ pg_dump available: {version}")
            return True
        else:
            print("  ❌ pg_dump not available")
            print("     Will use alternative SQL backup method")
            return False
    except FileNotFoundError:
        print("  ❌ pg_dump not found in PATH")
        print("     Will use alternative SQL backup method")
        return False


def check_migration_dependencies():
    """Check if migration script dependencies are available"""
    print("\n📦 Checking migration dependencies...")
    
    # Check Python modules
    required_modules = [
        'asyncpg',
        'pathlib',
        'datetime'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Missing required modules: {', '.join(missing_modules)}")
        print("   Install with: pip install " + " ".join(missing_modules))
        return False
    
    # Check migration files exist
    migration_files = [
        'backend/migrations/003_multi_author_support.sql',
        'backend/run_migration_003.py',
        'backend/data_migration_003.py',
        'backend/verify_data_migration_003.py'
    ]
    
    for file_path in migration_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            print(f"     Migration file missing: {file_path}")
            return False
    
    return True


async def main():
    """Run all pre-migration checks"""
    print("🔍 Pre-Migration Check 003: Multi-Author Metadata Enhancement")
    print("=" * 60)
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    checks = []
    
    # Run all checks
    checks.append(await check_database_connectivity())
    checks.append(await check_required_tables())
    checks.append(await check_data_consistency())
    checks.append(check_backup_tools())
    checks.append(check_migration_dependencies())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Pre-Migration Check Summary")
    print()
    
    passed_checks = sum(checks)
    total_checks = len(checks)
    
    check_names = [
        "Database connectivity",
        "Required tables",
        "Data consistency", 
        "Backup tools",
        "Migration dependencies"
    ]
    
    for i, (name, passed) in enumerate(zip(check_names, checks)):
        print(f"  {'✅' if passed else '❌'} {name}")
    
    print()
    
    if passed_checks == total_checks:
        print("🎉 All pre-migration checks PASSED!")
        print("   Ready to run production migration")
        print()
        print("📋 Next steps:")
        print("   1. Run: python3 backend/run_production_migration_003.py")
        print("   2. Monitor the migration process")
        print("   3. Verify results after completion")
    else:
        print(f"⚠️  {total_checks - passed_checks} pre-migration checks FAILED")
        print("   Please fix the issues before running migration")
        print()
        print("💡 Common fixes:")
        print("   - Install missing Python packages")
        print("   - Check database permissions")
        print("   - Verify migration files are present")
    
    return passed_checks == total_checks


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)