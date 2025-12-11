#!/usr/bin/env python3
"""
Basic functionality test for Excel API property tests (Task 12.1 and 12.2)
This script tests the core functionality without requiring full pytest/hypothesis setup.
"""

import asyncio
import os
import tempfile
import pandas as pd
from pathlib import Path

# Set up environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

try:
    from excel_import_service import ExcelImportService, ExcelValidationError, ValidationResult
    from author_service import AuthorService
    print("✅ Successfully imported Excel import modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    exit(1)


async def test_excel_error_reporting_basic():
    """
    Basic test for Property 35: Excel error reporting
    **Validates: Requirements 11.6**
    """
    print("🧪 Testing Excel error reporting (Property 35)...")
    
    try:
        # Set up service
        author_service = AuthorService()
        service = ExcelImportService(author_service)
        
        # Test 1: Valid file should have no errors
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "valid.xlsm"
            
            # Create valid Excel file
            df = pd.DataFrame({
                'URL': ['https://example.com'],
                'Title': ['Test Book'],
                'Author': ['Test Author']
            })
            df.to_excel(test_file, engine='openpyxl', index=False)
            
            result = await service.validate_excel_file(str(test_file), 'book')
            
            # Should have no errors for valid file
            error_count = len([e for e in result.errors if e.severity == "error"])
            print(f"   Valid file errors: {error_count} (expected: 0)")
            
            # Test 2: Invalid file should have errors with proper structure
            invalid_file = Path(temp_dir) / "invalid.txt"
            invalid_file.write_text("not an excel file")
            
            result = await service.validate_excel_file(str(invalid_file), 'book')
            
            # Should have errors
            assert len(result.errors) > 0, "Invalid file should have errors"
            
            # Each error should have required attributes
            for error in result.errors:
                assert hasattr(error, 'row'), "Error should have row attribute"
                assert hasattr(error, 'column'), "Error should have column attribute"
                assert hasattr(error, 'message'), "Error should have message attribute"
                assert hasattr(error, 'severity'), "Error should have severity attribute"
                assert error.severity in ['error', 'warning'], f"Invalid severity: {error.severity}"
            
            print(f"   Invalid file errors: {len(result.errors)} (expected: >0)")
            print(f"   Error structure: ✅ All errors have required attributes")
            
        print("✅ Excel error reporting test passed")
        return True
        
    except Exception as e:
        print(f"❌ Excel error reporting test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_excel_workflow_control_basic():
    """
    Basic test for Property 36: Excel workflow control
    **Validates: Requirements 11.7**
    """
    print("🧪 Testing Excel workflow control (Property 36)...")
    
    try:
        # Set up service
        author_service = AuthorService()
        service = ExcelImportService(author_service)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test 1: Valid file should allow proceeding
            valid_file = Path(temp_dir) / "valid.xlsm"
            df = pd.DataFrame({
                'URL': ['https://example.com'],
                'Title': ['Test Book'],
                'Author': ['Test Author']
            })
            df.to_excel(valid_file, engine='openpyxl', index=False)
            
            result = await service.validate_excel_file(str(valid_file), 'book')
            
            # Valid file should pass validation
            assert result.valid, "Valid file should pass validation"
            print(f"   Valid file validation: {'✅ PASS' if result.valid else '❌ FAIL'}")
            
            # Test 2: Invalid file should prevent proceeding
            invalid_file = Path(temp_dir) / "invalid.txt"
            invalid_file.write_text("not an excel file")
            
            result = await service.validate_excel_file(str(invalid_file), 'book')
            
            # Invalid file should fail validation
            assert not result.valid, "Invalid file should fail validation"
            assert len(result.errors) > 0, "Invalid file should have errors"
            print(f"   Invalid file validation: {'✅ FAIL (expected)' if not result.valid else '❌ PASS (unexpected)'}")
            
            # Test 3: Validation result should control workflow
            if result.valid:
                print("   Workflow: Can proceed with import")
            else:
                print("   Workflow: Cannot proceed - validation failed")
                print(f"   Error count: {len(result.errors)}")
            
        print("✅ Excel workflow control test passed")
        return True
        
    except Exception as e:
        print(f"❌ Excel workflow control test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_excel_api_integration():
    """Test basic Excel API integration"""
    print("🧪 Testing Excel API integration...")
    
    try:
        # Test service initialization
        author_service = AuthorService()
        service = ExcelImportService(author_service)
        
        # Test basic functionality
        authors = service.parse_authors("John Doe, Jane Smith and Bob Wilson")
        assert len(authors) == 3, f"Should parse 3 authors, got {len(authors)}"
        print(f"   Author parsing: ✅ Parsed {len(authors)} authors correctly")
        
        # Test URL validation
        valid_url = service._is_valid_url("https://example.com")
        invalid_url = service._is_valid_url("not-a-url")
        assert valid_url, "Should validate correct URL"
        assert not invalid_url, "Should reject invalid URL"
        print(f"   URL validation: ✅ Valid/invalid URLs handled correctly")
        
        print("✅ Excel API integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Excel API integration test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def main():
    """Run all basic tests"""
    print("🚀 Starting Excel API property tests (Task 12.1 and 12.2)")
    print("=" * 60)
    
    tests = [
        test_excel_error_reporting_basic,
        test_excel_workflow_control_basic,
        test_excel_api_integration
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Excel API property tests passed!")
        return True
    else:
        print("⚠️ Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)