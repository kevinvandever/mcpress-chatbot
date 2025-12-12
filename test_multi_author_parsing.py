#!/usr/bin/env python3
"""
Simple test for multi-author parsing functionality
Tests the parse_authors function with various input formats
"""

import sys
import os

# Add backend to path
sys.path.append('backend')

try:
    from main import parse_authors
except ImportError:
    from backend.main import parse_authors

def test_parse_authors():
    """Test the parse_authors function with various input formats"""
    
    print("🧪 Testing parse_authors function...")
    
    # Test cases: (input, expected_output)
    test_cases = [
        # Semicolon separation
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe;Jane Smith;Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # Comma separation
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe,Jane Smith,Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # "and" separation
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith, and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # Single author
        ("John Doe", ["John Doe"]),
        
        # Empty/None cases
        ("", []),
        (None, []),
        ("   ", []),
        
        # Complex cases with extra whitespace
        ("  John Doe  ;  Jane Smith  ", ["John Doe", "Jane Smith"]),
        ("John Doe,  Jane Smith  and  Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_str, expected) in enumerate(test_cases, 1):
        try:
            result = parse_authors(input_str)
            if result == expected:
                print(f"✅ Test {i}: '{input_str}' -> {result}")
                passed += 1
            else:
                print(f"❌ Test {i}: '{input_str}' -> {result} (expected {expected})")
                failed += 1
        except Exception as e:
            print(f"💥 Test {i}: '{input_str}' -> ERROR: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All parse_authors tests passed!")
        return True
    else:
        print("⚠️ Some tests failed")
        return False

def test_author_parsing_requirements():
    """Test specific requirements from the task"""
    
    print("\n🧪 Testing Requirements 6.2: Parse multiple authors from PDF metadata...")
    
    # Test cases that simulate PDF metadata formats
    pdf_metadata_cases = [
        # Common PDF metadata formats
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        
        # Real-world examples
        ("Martin Fowler", ["Martin Fowler"]),
        ("Robert C. Martin; Kent Beck", ["Robert C. Martin", "Kent Beck"]),
        ("Gang of Four", ["Gang of Four"]),
    ]
    
    print("Testing PDF metadata author parsing formats:")
    all_passed = True
    
    for input_str, expected in pdf_metadata_cases:
        result = parse_authors(input_str)
        if result == expected:
            print(f"✅ '{input_str}' -> {result}")
        else:
            print(f"❌ '{input_str}' -> {result} (expected {expected})")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print("🚀 Testing multi-author parsing functionality\n")
    
    success1 = test_parse_authors()
    success2 = test_author_parsing_requirements()
    
    if success1 and success2:
        print("\n🎉 All multi-author parsing tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)