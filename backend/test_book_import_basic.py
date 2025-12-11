#!/usr/bin/env python3
"""
Basic functionality test for book import properties
This script tests the core functionality without requiring pytest or hypothesis
"""

import asyncio
import tempfile
import os
from pathlib import Path
import pandas as pd

# Set up environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

from excel_import_service import ExcelImportService
from author_service import AuthorService


async def test_book_url_update_basic():
    """Test basic book URL update functionality"""
    print("Testing book URL update...")
    
    # Set up service
    author_service = AuthorService()
    service = ExcelImportService(author_service)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.xlsm"
        
        # Create test Excel data
        data = {
            'URL': ['https://mcpress.com/book1', 'http://example.com/book2', ''],
            'Title': ['Test Book 1', 'Test Book 2', 'Test Book 3'],
            'Author': ['Test Author 1', 'Test Author 2', 'Test Author 3']
        }
        df = pd.DataFrame(data)
        df.to_excel(test_file, engine='openpyxl', index=False)
        
        # Mock fuzzy matching to simulate book existence
        updated_books = []
        
        async def mock_fuzzy_match(title):
            return 1  # Always find a book
        
        service.fuzzy_match_title = mock_fuzzy_match
        
        # Mock database operations
        async def mock_ensure_pool():
            pass
        
        class MockConnection:
            async def execute(self, query, *args):
                if "UPDATE books SET mc_press_url" in query:
                    updated_books.append((args[0], args[1]))  # (url, book_id)
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockPool:
            def acquire(self):
                return MockConnection()
        
        service._ensure_pool = mock_ensure_pool
        service.pool = MockPool()
        
        # Mock author service
        async def mock_get_or_create(name, site_url=None):
            return 1
        
        service.author_service.get_or_create_author = mock_get_or_create
        
        # Test import
        result = await service.import_book_metadata(str(test_file))
        
        # Verify results
        print(f"Books processed: {result.books_processed}")
        print(f"Books matched: {result.books_matched}")
        print(f"Books updated: {result.books_updated}")
        print(f"Updated books: {updated_books}")
        
        # Check that valid URLs were used for updates
        valid_urls = ['https://mcpress.com/book1', 'http://example.com/book2']
        assert len(updated_books) == 2, f"Expected 2 updates, got {len(updated_books)}"
        
        for url, book_id in updated_books:
            assert url in valid_urls, f"URL {url} should be in valid URLs"
            assert book_id == 1, f"Book ID should be 1, got {book_id}"
        
        print("✓ Book URL update test passed")


async def test_book_author_parsing_basic():
    """Test basic book author parsing functionality"""
    print("Testing book author parsing...")
    
    # Set up service
    author_service = AuthorService()
    service = ExcelImportService(author_service)
    
    # Test various author string formats
    test_cases = [
        ("John Doe", ["John Doe"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith and Bob Wilson", ["John Doe", "Jane Smith", "Bob Wilson"]),
        ("  John Doe  ,  Jane Smith  ", ["John Doe", "Jane Smith"]),
        ("", []),
        ("   ", [])
    ]
    
    for author_string, expected in test_cases:
        result = service.parse_authors(author_string)
        print(f"Input: '{author_string}' -> Output: {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✓ Book author parsing test passed")


async def test_book_import_reporting_basic():
    """Test basic book import reporting functionality"""
    print("Testing book import reporting...")
    
    # Set up service
    author_service = AuthorService()
    service = ExcelImportService(author_service)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.xlsm"
        
        # Create test data with some errors
        data = {
            'URL': ['https://example.com/book1', '', 'https://example.com/book3'],
            'Title': ['Test Book 1', '', 'Test Book 3'],  # Empty title = error
            'Author': ['Test Author 1', 'Test Author 2', 'Test Author 3']
        }
        df = pd.DataFrame(data)
        df.to_excel(test_file, engine='openpyxl', index=False)
        
        # Mock fuzzy matching - only match valid books
        async def mock_fuzzy_match(title):
            if title.strip():
                return 1
            return None
        
        service.fuzzy_match_title = mock_fuzzy_match
        
        # Mock database operations
        update_count = 0
        
        async def mock_ensure_pool():
            pass
        
        class MockConnection:
            async def execute(self, query, *args):
                nonlocal update_count
                if "UPDATE books SET mc_press_url" in query:
                    update_count += 1
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockPool:
            def acquire(self):
                return MockConnection()
        
        service._ensure_pool = mock_ensure_pool
        service.pool = MockPool()
        
        # Mock author service
        async def mock_get_or_create(name, site_url=None):
            return 1
        
        service.author_service.get_or_create_author = mock_get_or_create
        
        # Test import
        result = await service.import_book_metadata(str(test_file))
        
        # Verify reporting
        print(f"Books processed: {result.books_processed}")
        print(f"Books matched: {result.books_matched}")
        print(f"Books updated: {result.books_updated}")
        print(f"Errors: {len(result.errors)}")
        print(f"Processing time: {result.processing_time}")
        print(f"Success: {result.success}")
        
        # Check reporting accuracy
        assert result.books_processed == 3, f"Should process 3 books, got {result.books_processed}"
        assert result.books_matched == 2, f"Should match 2 books, got {result.books_matched}"  # Only valid titles
        assert result.books_updated == 2, f"Should update 2 books, got {result.books_updated}"  # Only valid URLs
        assert len(result.errors) >= 1, f"Should have at least 1 error, got {len(result.errors)}"
        assert result.processing_time > 0, f"Should have positive processing time"
        assert result.success is True, f"Should be successful"
        
        print("✓ Book import reporting test passed")


async def main():
    """Run all basic tests"""
    print("Running basic book import functionality tests...")
    print("=" * 50)
    
    try:
        await test_book_url_update_basic()
        await test_book_author_parsing_basic()
        await test_book_import_reporting_basic()
        
        print("=" * 50)
        print("✓ All basic tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())