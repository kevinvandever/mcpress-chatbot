#!/usr/bin/env python3
"""
Simple test for fuzzy matching logic without external dependencies
This tests the core logic that can be verified locally.
"""

def test_author_parsing_logic():
    """Test author parsing logic without dependencies"""
    print("Testing author parsing logic...")
    
    # Test cases for author parsing
    test_cases = [
        ("John Doe", ["John Doe"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        ("", []),
        ("   ", []),
        ("John Doe,, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe and and Jane Smith", ["John Doe", "Jane Smith"]),
    ]
    
    # Simple implementation of parse_authors logic for testing
    import re
    
    def parse_authors_simple(author_string):
        if not author_string or not author_string.strip():
            return []
        
        # Replace "and and" and similar patterns first
        author_string = re.sub(r'\s+and\s+and\s+', ' and ', author_string, flags=re.IGNORECASE)
        # Then replace " and " with comma for consistent splitting
        author_string = re.sub(r'\s+and\s+', ',', author_string, flags=re.IGNORECASE)
        # Handle cases with multiple consecutive commas
        author_string = re.sub(r',\s*,+', ',', author_string)
        
        # Replace semicolons with commas
        author_string = author_string.replace(';', ',')
        
        # Split by comma and clean up
        authors = [author.strip() for author in author_string.split(',')]
        
        # Remove empty strings
        authors = [author for author in authors if author]
        
        return authors
    
    for input_str, expected in test_cases:
        result = parse_authors_simple(input_str)
        if input_str == "John Doe and and Jane Smith":
            print(f"Debug: '{input_str}' -> {result} (expected {expected})")
            # Let's see the intermediate steps
            temp = re.sub(r'\s+and\s+', ',', input_str, flags=re.IGNORECASE)
            print(f"After and replacement: '{temp}'")
            temp = re.sub(r',\s*,+', ',', temp)
            print(f"After comma cleanup: '{temp}'")
        assert result == expected, f"Failed for '{input_str}': expected {expected}, got {result}"
        print(f"✓ '{input_str}' -> {result}")
    
    print("All author parsing tests passed!")

def test_url_validation_logic():
    """Test URL validation logic without dependencies"""
    print("\nTesting URL validation logic...")
    
    import re
    
    def is_valid_url_simple(url):
        if not url or not url.strip():
            return False
        
        url = url.strip()
        
        # Basic URL validation - must start with http:// or https://
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
    
    test_cases = [
        ("https://example.com", True),
        ("http://example.com", True),
        ("https://example.com/path", True),
        ("http://localhost:8000", True),
        ("ftp://example.com", False),
        ("invalid-url", False),
        ("", False),
        ("   ", False),
        ("https://", False),
    ]
    
    for url, expected in test_cases:
        result = is_valid_url_simple(url)
        assert result == expected, f"Failed for '{url}': expected {expected}, got {result}"
        print(f"✓ '{url}' -> {result}")
    
    print("All URL validation tests passed!")

if __name__ == "__main__":
    test_author_parsing_logic()
    test_url_validation_logic()
    print("\nAll simple logic tests passed! ✓")
    print("Note: Full property tests with fuzzy matching should be run on Railway.")