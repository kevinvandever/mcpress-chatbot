#!/usr/bin/env python3
"""
Simple script to run the complete author corrections SQL on Railway
Usage: python3 run_sql_on_railway.py
"""

import os
import sys

def main():
    print("=" * 60)
    print("COMPLETE AUTHOR CORRECTIONS - RAILWAY EXECUTION")
    print("=" * 60)
    
    # Check if we have the SQL file
    if not os.path.exists('complete_author_audit_corrections.sql'):
        print("❌ ERROR: complete_author_audit_corrections.sql not found")
        print("Make sure you're in the correct directory")
        return 1
    
    # Check if we have DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not found")
        print("This script must be run on Railway or with DATABASE_URL set")
        return 1
    
    print("✅ Found SQL file and DATABASE_URL")
    print("🚀 Starting execution...")
    
    # Import and run the async function
    try:
        import asyncio
        from execute_complete_author_corrections import execute_sql_corrections
        
        success = asyncio.run(execute_sql_corrections())
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Author corrections completed!")
            print("=" * 60)
            print("Next steps:")
            print("1. Test the chat interface with queries like:")
            print("   - 'Complete CL programming'")
            print("   - 'Subfiles RPG'") 
            print("   - 'Control Language Programming'")
            print("2. Verify authors show correctly (not 'annegrubb' or 'admin')")
            print("3. Check that multi-author books show all authors")
            return 0
        else:
            print("\n❌ Execution failed - check errors above")
            return 1
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)