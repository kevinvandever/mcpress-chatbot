#!/usr/bin/env python3
"""
Basic functionality test for article metadata import
Tests the core article import functionality without property-based testing dependencies
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


async def test_article_import_basic():
    """Test basic article import functionality"""
    print("Testing article metadata import functionality...")
    
    # Initialize services
    author_service = AuthorService()
    excel_service = ExcelImportService(author_service)
    
    # Test 1: Article sheet filtering
    print("Test 1: Article sheet filtering")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_articles.xlsm"
        
        # Create Excel file with export_subset sheet
        with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
            # Add other sheets (should be ignored)
            df_other = pd.DataFrame({'col1': ['other_data']})
            df_other.to_excel(writer, sheet_name='other_sheet', index=False)
            
            # Add export_subset sheet with proper structure
            columns = [f'col_{i}' for i in range(12)]
            data = {col: [f'test_data_{col}'] for col in columns}
            data['col_7'] = ['yes']  # Feature article = yes
            
            df_export = pd.DataFrame(data)
            df_export.to_excel(writer, sheet_name='export_subset', index=False)
        
        # Test validation
        result = await excel_service.validate_excel_file(str(test_file), 'article')
        print(f"  Validation result: {result.valid}")
        if result.errors:
            print(f"  Errors: {[e.message for e in result.errors]}")
        
        assert result.valid, "Article file with export_subset sheet should be valid"
    
    # Test 2: Feature article filtering
    print("Test 2: Feature article filtering")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_feature_filter.xlsm"
        
        # Create Excel file with mixed feature article values
        with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
            columns = [f'col_{i}' for i in range(12)]
            data = {col: [f'data_{col}_{i}' for i in range(3)] for col in columns}
            data['col_0'] = ['article1', 'article2', 'article3']  # IDs
            data['col_7'] = ['yes', 'no', 'yes']  # Feature article values
            data['col_9'] = ['Author 1', 'Author 2', 'Author 3']  # Authors
            
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='export_subset', index=False)
        
        # Mock database and author service for testing
        class MockConnection:
            async def fetchval(self, query, *args):
                return 1  # Always find document
            
            async def execute(self, query, *args):
                pass
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockPool:
            def acquire(self):
                return MockConnection()
        
        async def mock_ensure_pool():
            pass
        
        async def mock_get_or_create(name, site_url=None):
            return 1
        
        # Apply mocks
        excel_service._ensure_pool = mock_ensure_pool
        excel_service.pool = MockPool()
        excel_service.author_service.get_or_create_author = mock_get_or_create
        
        # Test import
        result = await excel_service.import_article_metadata(str(test_file))
        print(f"  Articles processed: {result.articles_processed}")
        print(f"  Expected: 2 (only 'yes' values)")
        
        assert result.articles_processed == 2, "Should only process articles with feature_article='yes'"
    
    # Test 3: Author parsing
    print("Test 3: Author parsing")
    test_cases = [
        ("John Doe", ["John Doe"]),
        ("John Doe and Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
        ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
        ("", []),
        ("   ", [])
    ]
    
    for author_string, expected in test_cases:
        result = excel_service.parse_authors(author_string)
        print(f"  '{author_string}' -> {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    # Test 4: URL validation
    print("Test 4: URL validation")
    url_tests = [
        ("https://example.com", True),
        ("http://example.com", True),
        ("ftp://example.com", False),
        ("invalid-url", False),
        ("", False),
        ("   ", False)
    ]
    
    for url, expected in url_tests:
        result = excel_service._is_valid_url(url)
        print(f"  '{url}' -> {result}")
        assert result == expected, f"URL '{url}' validation should be {expected}"
    
    print("All basic tests passed!")


if __name__ == "__main__":
    asyncio.run(test_article_import_basic())