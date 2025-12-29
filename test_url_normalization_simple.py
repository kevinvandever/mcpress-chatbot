#!/usr/bin/env python3
"""
Simple test for URL normalization logic without dependencies
"""

import re

def normalize_url(url: str) -> str:
    """
    Normalize URL format, specifically fixing "ww.mcpressonline.com" to "www.mcpressonline.com"
    
    Args:
        url: URL string to normalize
        
    Returns:
        Normalized URL string
    """
    if not url or not url.strip():
        return url
    
    url = url.strip()
    
    # Fix common typo: "ww.mcpressonline.com" -> "www.mcpressonline.com"
    url = re.sub(r'://ww\.mcpressonline\.com', '://www.mcpressonline.com', url, flags=re.IGNORECASE)
    
    # Also handle cases without protocol
    url = re.sub(r'^ww\.mcpressonline\.com', 'www.mcpressonline.com', url, flags=re.IGNORECASE)
    
    return url

def test_url_normalization():
    """Test URL normalization fixes common formatting issues"""
    
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
        result = normalize_url(input_url)
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

if __name__ == "__main__":
    success = test_url_normalization()
    
    if success:
        print("\n🎉 All tests passed! URL normalization logic is working correctly.")
        exit(0)
    else:
        print("\n❌ Some tests failed!")
        exit(1)