#!/usr/bin/env python3
"""
Test script to verify batch upload multi-author parsing functionality
Task 21: Update batch upload to support multi-author parsing
"""

import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_parse_authors():
    """Test the parse_authors function with various input formats"""
    
    # Import the function from main.py
    from main import parse_authors
    
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
    
    if all_passed:
        print("\n🎉 All parse_authors tests passed!")
        return True
    else:
        print("\n💥 Some parse_authors tests failed!")
        return False

def test_batch_upload_requirements():
    """Test that batch upload meets all task requirements"""
    
    print("\n📋 Checking Task 21 requirements implementation...")
    
    requirements = [
        "Parse multiple authors from PDF metadata (separated by semicolon, comma, or 'and')",
        "Call AuthorService.get_or_create_author() for each parsed author", 
        "Create document_authors associations in correct order",
        "Set document_type based on file metadata or default to 'book'",
        "Handle missing author metadata with default or prompt"
    ]
    
    # Check if the implementation exists in main.py
    try:
        with open('backend/main.py', 'r') as f:
            content = f.read()
        
        checks = [
            ("parse_authors function", "def parse_authors(" in content),
            ("AuthorService usage", "author_service.get_or_create_author" in content),
            ("DocumentAuthorService usage", "doc_author_service.add_author_to_document" in content),
            ("Document type handling", "document_type" in content),
            ("Missing author handling", "Unknown Author" in content or "needs_author" in content),
            ("Batch upload endpoint", "@app.post(\"/batch-upload\")" in content),
            ("Multi-author parsing in batch", "parse_authors(" in content and "process_single_pdf" in content)
        ]
        
        all_implemented = True
        for check_name, check_result in checks:
            if check_result:
                print(f"✅ {check_name}: Implemented")
            else:
                print(f"❌ {check_name}: Not found")
                all_implemented = False
        
        if all_implemented:
            print("\n🎉 All Task 21 requirements appear to be implemented!")
            return True
        else:
            print("\n💥 Some Task 21 requirements are missing!")
            return False
            
    except Exception as e:
        print(f"❌ Error checking implementation: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Task 21: Batch Upload Multi-Author Parsing")
    print("=" * 60)
    
    # Test parse_authors function
    parse_test_passed = test_parse_authors()
    
    # Test requirements implementation
    requirements_test_passed = test_batch_upload_requirements()
    
    print("\n" + "=" * 60)
    if parse_test_passed and requirements_test_passed:
        print("🎉 Task 21 implementation verification: PASSED")
        sys.exit(0)
    else:
        print("💥 Task 21 implementation verification: FAILED")
        sys.exit(1)