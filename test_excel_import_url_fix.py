#!/usr/bin/env python3
"""
Test Excel Import Service URL normalization on Railway
This script tests that the URL normalization is working in the actual service
"""

import asyncio
import os
import sys

async def test_excel_import_url_normalization():
    """Test that Excel import service properly normalizes URLs"""
    
    try:
        # Import the service (this will only work on Railway with dependencies)
        from backend.excel_import_service import ExcelImportService
        from backend.author_service import AuthorService
        
        print("✓ Successfully imported ExcelImportService")
        
        # Create service instance
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return False
            
        author_service = AuthorService(database_url=database_url)
        excel_service = ExcelImportService(author_service, database_url=database_url)
        
        print("✓ Successfully created ExcelImportService instance")
        
        # Test URL normalization method directly
        test_urls = [
            "http://ww.mcpressonline.com/article",
            "https://ww.mcpressonline.com/article", 
            "ww.mcpressonline.com/article",
            "http://www.mcpressonline.com/article",  # Already correct
            "https://www.google.com"  # Different domain
        ]
        
        expected_results = [
            "http://www.mcpressonline.com/article",
            "https://www.mcpressonline.com/article",
            "www.mcpressonline.com/article", 
            "http://www.mcpressonline.com/article",
            "https://www.google.com"
        ]
        
        print("\nTesting URL normalization in ExcelImportService:")
        all_passed = True
        
        for i, (test_url, expected) in enumerate(zip(test_urls, expected_results), 1):
            result = excel_service._normalize_url(test_url)
            if result == expected:
                print(f"✓ Test {i}: '{test_url}' -> '{result}'")
            else:
                print(f"✗ Test {i}: '{test_url}' -> '{result}' (expected: '{expected}')")
                all_passed = False
        
        if all_passed:
            print("\n🎉 All URL normalization tests passed in ExcelImportService!")
            print("The service will now properly fix 'ww.mcpressonline.com' URLs during import.")
            return True
        else:
            print("\n❌ Some URL normalization tests failed!")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This test needs to be run on Railway where dependencies are available.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_excel_import_url_normalization())
    if result:
        print("\n✅ Task 2 implementation verified: URL normalization is working correctly!")
    else:
        print("\n❌ Task 2 verification failed!")
        sys.exit(1)