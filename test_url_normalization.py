#!/usr/bin/env python3
"""
Test URL normalization functionality in Excel Import Service
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.excel_import_service import ExcelImportService
from backend.author_service import AuthorService

def test_url_normalization():
    """Test URL normalization fixes common formatting issues"""
    
    # Create service instance (we don't need database for this test)
    author_service = AuthorService(database_url="dummy://url")
    service = ExcelImportService(author_service, database_url="dummy://url")
    
    # Test cases for URL normalization
    test_cases = [
        # Basic case: ww -> www
        ("http://ww.mcpressonline.com/article", "http://www.mcpressonline.com/article"),
        ("https://ww.mcpressonline.com/article", "https://www.mcpressonline.com/article"),
        
        # Case insensitive
        ("http://WW.MCPRESSONLINE.COM/article", "http://www.mcpressonline.com/article"),
        ("https://Ww.McPressOnline.Com/article", "https://www.mcpressonline.com/article"),
        
        # Without protocol
        ("ww.mcpressonline.com/article", "www.mcpressonline.com/article"),
        ("WW.MCPRESSONLINE.COM/article", "www.mcpressonline.com/article"),
        
        # Already correct URLs should remain unchanged
        ("http://www.mcpressonline.com/article", "http://www.mcpressonline.com/article"),
        ("https://www.mcpressonline.com/article", "https://www.mcpressonline.com/article"),
        
        # Other domains should remain unchanged
        ("http://ww.example.com/article", "http://ww.example.com/article"),
        ("https://www.google.com", "https://www.google.com"),
        
        # Empty/None cases
        ("", ""),
        ("   ", "   "),
        
        # Edge cases
        ("http://ww.mcpressonline.com", "http://www.mcpressonline.com"),
        ("https://ww.mcpressonline.com/", "https://www.mcpressonline.com/"),
        ("ww.mcpressonline.com", "www.mcpressonline.com"),
    ]
    
    print("Testing URL normalization...")
    all_passed = True
    
    for i, (input_url, expected_url) in enumerate(test_cases, 1):
        result = service._normalize_url(input_url)
        if result == expected_url:
            print(f"✓ Test {i}: '{input_url}' -> '{result}'")
        else:
            print(f"✗ Test {i}: '{input_url}' -> '{result}' (expected: '{expected_url}')")
            all_passed = False
    
    if all_passed:
        print("\n✓ All URL normalization tests passed!")
        return True
    else:
        print("\n✗ Some URL normalization tests failed!")
        return False

def test_url_validation():
    """Test URL validation works with normalized URLs"""
    
    # Create service instance
    author_service = AuthorService(database_url="dummy://url")
    service = ExcelImportService(author_service, database_url="dummy://url")
    
    # Test cases for URL validation after normalization
    test_cases = [
        # These should be valid after normalization
        ("http://ww.mcpressonline.com/article", True),
        ("https://ww.mcpressonline.com/article", True),
        
        # These should be invalid
        ("ww.mcpressonline.com/article", False),  # No protocol
        ("not-a-url", False),
        ("", False),
        ("   ", False),
    ]
    
    print("\nTesting URL validation with normalization...")
    all_passed = True
    
    for i, (input_url, should_be_valid) in enumerate(test_cases, 1):
        normalized_url = service._normalize_url(input_url)
        is_valid = service._is_valid_url(normalized_url)
        
        if is_valid == should_be_valid:
            print(f"✓ Test {i}: '{input_url}' -> '{normalized_url}' -> valid={is_valid}")
        else:
            print(f"✗ Test {i}: '{input_url}' -> '{normalized_url}' -> valid={is_valid} (expected: {should_be_valid})")
            all_passed = False
    
    if all_passed:
        print("\n✓ All URL validation tests passed!")
        return True
    else:
        print("\n✗ Some URL validation tests failed!")
        return False

if __name__ == "__main__":
    success1 = test_url_normalization()
    success2 = test_url_validation()
    
    if success1 and success2:
        print("\n🎉 All tests passed! URL normalization is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)