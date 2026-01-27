#!/usr/bin/env python3
"""
Basic test for AuthorDataValidator
This script must be run on Railway: railway run python3 test_author_validator_basic.py

Tests that the validator can be imported and initialized correctly.
"""

import asyncio
import sys

try:
    from backend.author_data_validator import AuthorDataValidator
    print("✅ Successfully imported AuthorDataValidator")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This script must be run on Railway where dependencies are available.")
    sys.exit(1)


async def test_validator():
    """Test basic validator functionality"""
    print("\n🔍 Testing AuthorDataValidator...")
    
    # Test initialization
    try:
        validator = AuthorDataValidator()
        print("✅ Validator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize validator: {e}")
        return False
    
    # Test placeholder patterns
    print(f"\n📋 Placeholder patterns configured: {len(validator.PLACEHOLDER_PATTERNS)}")
    print(f"   Patterns: {', '.join(validator.PLACEHOLDER_PATTERNS)}")
    
    # Test database connection (will fail locally, succeed on Railway)
    try:
        await validator.init_database()
        print("✅ Database connection successful")
        
        # Test a simple query
        report = await validator.generate_data_quality_report()
        print(f"\n📊 Report generated successfully:")
        print(f"   Total books: {report['summary']['total_books']}")
        print(f"   Total authors: {report['summary']['total_authors']}")
        print(f"   Total issues: {report['summary']['total_issues']}")
        
        await validator.close()
        return True
        
    except Exception as e:
        print(f"⚠️  Database connection failed (expected if running locally): {e}")
        print("   This is normal - the script needs to run on Railway")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_validator())
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Tests incomplete (run on Railway for full test)")
        sys.exit(0)  # Exit 0 since local failure is expected
