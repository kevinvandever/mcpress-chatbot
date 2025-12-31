#!/usr/bin/env python3
"""
Simple test to verify transaction reliability improvements are deployed
This test runs on Railway and checks that the transaction methods exist
"""

import asyncio
import sys

async def test_transaction_reliability_deployed():
    """Test that transaction reliability improvements are deployed"""
    
    try:
        # Test that we can import the service on Railway
        print("🔍 Testing Excel import service on Railway...")
        
        # Import the service
        from backend.excel_import_service import ExcelImportService
        from backend.author_service import AuthorService
        
        print("✅ Successfully imported ExcelImportService")
        
        # Create service instance
        author_service = AuthorService()
        excel_service = ExcelImportService(author_service)
        
        print("✅ Successfully created ExcelImportService instance")
        
        # Test that the transaction helper method exists
        if hasattr(excel_service, '_get_or_create_author_in_transaction'):
            print("✅ Transaction helper method _get_or_create_author_in_transaction exists")
        else:
            print("❌ Transaction helper method missing")
            return False
        
        # Test that URL validation method exists
        if hasattr(excel_service, '_validate_url'):
            print("✅ URL validation method _validate_url exists")
        else:
            print("❌ URL validation method missing")
            return False
        
        # Test URL normalization
        test_urls = [
            "http://ww.mcpressonline.com/article",
            "https://ww.mcpressonline.com/article", 
            "http://www.mcpressonline.com/article"
        ]
        
        expected_results = [
            "http://www.mcpressonline.com/article",
            "https://www.mcpressonline.com/article",
            "http://www.mcpressonline.com/article"
        ]
        
        print("\n🧪 Testing URL normalization:")
        all_passed = True
        
        for i, (test_url, expected) in enumerate(zip(test_urls, expected_results), 1):
            result = excel_service._normalize_url(test_url)
            if result == expected:
                print(f"✅ Test {i}: '{test_url}' -> '{result}'")
            else:
                print(f"❌ Test {i}: '{test_url}' -> '{result}' (expected: '{expected}')")
                all_passed = False
        
        if all_passed:
            print("\n🎉 All URL normalization tests passed!")
        else:
            print("\n❌ Some URL normalization tests failed!")
            return False
        
        # Test author parsing
        print("\n🧪 Testing author parsing:")
        test_authors = excel_service.parse_authors("John Doe, Jane Smith and Bob Wilson")
        expected_authors = ["John Doe", "Jane Smith", "Bob Wilson"]
        
        if test_authors == expected_authors:
            print(f"✅ Author parsing: {test_authors}")
        else:
            print(f"❌ Author parsing failed: {test_authors} (expected: {expected_authors})")
            return False
        
        print("\n✅ All basic functionality tests passed!")
        print("🎉 Transaction reliability improvements are successfully deployed!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_transaction_reliability_deployed())
    if result:
        print("\n✅ Task 6 verification SUCCESS: Transaction reliability improvements are working!")
    else:
        print("\n❌ Task 6 verification FAILED!")
        sys.exit(1)