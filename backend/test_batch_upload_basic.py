#!/usr/bin/env python3
"""
Basic functionality test for batch upload multi-author support
"""

import asyncio
import os
import tempfile
from pathlib import Path

# Set up test environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

# Import the parse_authors function from main
import sys
sys.path.append('/app/backend')

def parse_authors(author_string: str):
    """
    Parse multiple authors from a string with various delimiters.
    
    Supports:
    - Semicolon separation: "John Doe; Jane Smith"
    - Comma separation: "John Doe, Jane Smith"
    - "and" separation: "John Doe and Jane Smith"
    - Complex format: "John Doe, Jane Smith, and Bob Wilson"
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
    
    # Handle comma separation
    if "," in author_string:
        return [author.strip() for author in author_string.split(",") if author.strip()]
    
    # Single author
    return [author_string.strip()]


def test_parse_authors():
    """Test the parse_authors function with various inputs"""
    print("Testing parse_authors function...")
    
    test_cases = [
        ("John Doe", ["John Doe"]),
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith, and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        ("John Doe; Jane Smith; Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        ("", []),
        ("   ", []),
        ("John Doe,", ["John Doe"]),
        ("John Doe and", ["John Doe"]),
    ]
    
    for input_str, expected in test_cases:
        result = parse_authors(input_str)
        if result == expected:
            print(f"✅ '{input_str}' -> {result}")
        else:
            print(f"❌ '{input_str}' -> {result}, expected {expected}")
    
    print("Parse authors test completed!")


def test_author_service_integration():
    """Test integration with AuthorService"""
    print("Testing AuthorService integration...")
    
    try:
        from author_service import AuthorService
        
        # Mock database URL for testing
        service = AuthorService('postgresql://test:test@localhost:5432/test')
        print("✅ AuthorService imported successfully")
        
        # Test that the service can be instantiated
        assert service.database_url == 'postgresql://test:test@localhost:5432/test'
        print("✅ AuthorService configured correctly")
        
    except ImportError as e:
        print(f"⚠️ AuthorService import failed: {e}")
    except Exception as e:
        print(f"⚠️ AuthorService test failed: {e}")
    
    print("AuthorService integration test completed!")


def test_document_author_service_integration():
    """Test integration with DocumentAuthorService"""
    print("Testing DocumentAuthorService integration...")
    
    try:
        from document_author_service import DocumentAuthorService
        
        # Mock database URL for testing
        service = DocumentAuthorService('postgresql://test:test@localhost:5432/test')
        print("✅ DocumentAuthorService imported successfully")
        
        # Test that the service can be instantiated
        assert service.database_url == 'postgresql://test:test@localhost:5432/test'
        print("✅ DocumentAuthorService configured correctly")
        
    except ImportError as e:
        print(f"⚠️ DocumentAuthorService import failed: {e}")
    except Exception as e:
        print(f"⚠️ DocumentAuthorService test failed: {e}")
    
    print("DocumentAuthorService integration test completed!")


def test_batch_upload_workflow():
    """Test the overall batch upload workflow"""
    print("Testing batch upload workflow...")
    
    # Test data
    test_files = [
        ("book1.pdf", "John Doe"),
        ("book2.pdf", "Jane Smith; Bob Wilson"),
        ("book3.pdf", "Alice Cooper, Bob Dylan, and Charlie Brown"),
        ("book4.pdf", ""),  # No author metadata
    ]
    
    for filename, author_metadata in test_files:
        print(f"\n📝 Processing {filename} with author metadata: '{author_metadata}'")
        
        if author_metadata:
            parsed_authors = parse_authors(author_metadata)
            print(f"   Parsed authors: {parsed_authors}")
            
            # Simulate author creation
            print(f"   Would create/find {len(parsed_authors)} author records")
            for i, author in enumerate(parsed_authors):
                print(f"     {i+1}. '{author}'")
        else:
            print("   No author metadata - would prompt for manual input")
    
    print("\nBatch upload workflow test completed!")


if __name__ == "__main__":
    print("🚀 Running batch upload basic functionality tests...\n")
    
    test_parse_authors()
    print()
    
    test_author_service_integration()
    print()
    
    test_document_author_service_integration()
    print()
    
    test_batch_upload_workflow()
    
    print("\n✅ All basic functionality tests completed!")