#!/usr/bin/env python3
"""
Run Data Migration 003: Populate Authors Table
Feature: multi-author-metadata-enhancement

This script executes the data migration to populate the authors table from existing books.author data.
It can be run locally or on Railway to migrate existing data to the new multi-author schema.

Usage:
    python backend/run_data_migration_003.py

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import os
import asyncio
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import the existing data migration module
try:
    from data_migration_003 import run_data_migration
except ImportError:
    print("❌ Could not import data_migration_003 module")
    print("   Make sure you're running this from the project root:")
    print("   python backend/run_data_migration_003.py")
    sys.exit(1)


def main():
    """
    Main entry point for running the data migration
    """
    print("🚀 MC Press Multi-Author Data Migration")
    print("=" * 50)
    print()
    print("This migration will:")
    print("  1. Extract unique authors from existing books.author column")
    print("  2. Create author records using AuthorService.get_or_create_author()")
    print("  3. Create document_authors associations for all existing books")
    print("  4. Verify all documents have at least one author after migration")
    print("  5. Log migration progress and any errors")
    print()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print()
        print("Please set DATABASE_URL in your environment:")
        print("  export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
        print()
        print("Or create a .env file with:")
        print("  DATABASE_URL=postgresql://user:pass@host:port/dbname")
        sys.exit(1)
    
    print(f"📊 Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    print()
    
    # Confirm before proceeding
    response = input("Continue with migration? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Migration cancelled")
        sys.exit(0)
    
    print()
    
    # Run the migration
    try:
        asyncio.run(run_data_migration())
        print()
        print("🎉 Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Verify the data looks correct")
        print("  2. Test the application with the new schema")
        print("  3. Update frontend to use new multi-author endpoints")
        
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("  1. Check that the database migration 003 has been run")
        print("  2. Verify DATABASE_URL is correct")
        print("  3. Ensure the database is accessible")
        print("  4. Check the logs above for specific errors")
        sys.exit(1)


if __name__ == "__main__":
    main()