#!/usr/bin/env python3
"""
Isolated test for parse_authors function
Task 21: Update batch upload to support multi-author parsing
"""

from typing import List

def parse_authors(author_string: str) -> List[str]:
    """
    Parse multiple authors from a string with various delimiters.
    
    Supports:
    - Semicolon separation: "John Doe; Jane Smith"
    - Comma separation: "John Doe, Jane Smith"
    - "and" separation: "John Doe and Jane Smith"
    - Complex format: "John Doe, Jane Smith, and Bob Wilson"
    
    Args:
        author_string: String containing one or more author names
        
    Returns:
        List of individual author names (trimmed)
        
    Validates: Requirements 6.2
    """
    if not author_string:
        return []
    
    author_string = author_string.strip()
    if not author_string:
        return []
    
    # Handle semicolon separation first (highest priority)
    if ";" in author_string:
        return [author.strip() for author in author_string.split(";") if author.strip()]
    
    # Handle "and" separation with comma support
    if " and " in author_string:
        # Handle "A, B, and C" format
        if "," in author_string:
            parts = author_string.split(",")
            authors = []
            for i, part in enumerate(parts):
                part = part.strip()
                if i == len(parts) - 1 and part.startswith("and "):
                    part = part[4:]  # Remove "and "
                if part:
                    authors.append(part)
            return authors
        else:
            # Simple "A and B" format
            return [author.strip() for author in author_string.split(" and ") if author.strip()]
    
    # Handle edge case: string ends with " and" (incomplete)
    if author_string.endswith(" and"):
        return [author_string[:-4].strip()]
    
    # Handle comma separation
    if "," in author_string:
        return [author.strip() for author in author_string.split(",") if author.strip()]
    
    # Single author
    return [author_string.strip()]

def test_parse_authors():
    """Test the parse_authors function with various input formats"""
    
    print("🧪 Testing parse_authors function...")
    
    test_cases = [
        # Semicolon separation (highest priority)
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe; Jane Smith; Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # "and" separation with commas
        ("John Doe, Jane Smith, and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        
        # Comma separation
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith, Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # Single author
        ("John Doe", ["John Doe"]),
        
        # Edge cases
        ("", []),
        ("   ", []),
        ("John Doe;", ["John Doe"]),
        ("John Doe,", ["John Doe"]),
        ("John Doe and", ["John Doe"]),
        
        # Whitespace handling
        ("  John Doe  ;  Jane Smith  ", ["John Doe", "Jane Smith"]),
        ("John Doe , Jane Smith", ["John Doe", "Jane Smith"]),
    ]
    
    all_passed = True
    
    for i, (input_str, expected) in enumerate(test_cases, 1):
        try:
            result = parse_authors(input_str)
            if result == expected:
                print(f"✅ Test {i}: '{input_str}' -> {result}")
            else:
                print(f"❌ Test {i}: '{input_str}' -> Expected {expected}, got {result}")
                all_passed = False
        except Exception as e:
            print(f"❌ Test {i}: '{input_str}' -> Error: {e}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print("🚀 Testing parse_authors function for Task 21")
    print("=" * 50)
    
    if test_parse_authors():
        print("\n🎉 All parse_authors tests passed!")
        print("✅ Task 21 author parsing functionality is working correctly")
    else:
        print("\n💥 Some parse_authors tests failed!")
        print("❌ Task 21 author parsing needs fixes")