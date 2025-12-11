#!/usr/bin/env python3
"""
Basic test script for ExcelImportService functionality
This can be run on Railway to verify the service works correctly.
"""

import os
import tempfile
import asyncio
from pathlib import Path
import pandas as pd

from excel_import_service import ExcelImportService
from author_service import AuthorService


async def test_basic_functionality():
    """Test basic ExcelImportService functionality"""
    print("Testing ExcelImportService basic functionality...")
    
    # Set up services
    author_service = AuthorService()
    excel_service = ExcelImportService(author_service)
    
    # Test 1: Author parsing
    print("\n1. Testing author parsing...")
    test_cases = [
        "John Doe",
        "John Doe and Jane Smith",
        "John Doe, Jane Smith",
        "John Doe, Jane Smith and Bob Wilson",
        "",
        "   ",
    ]
    
    for test_case in test_cases:
        result = excel_service.parse_authors(test_case)
        print(f"  '{test_case}' -> {result}")
    
    # Test 2: URL validation
    print("\n2. Testing URL validation...")
    test_urls = [
        "https://example.com",
        "http://example.com",
        "invalid-url",
        "",
        "ftp://example.com"
    ]
    
    for url in test_urls:
        is_valid = excel_service._is_valid_url(url)
        print(f"  '{url}' -> {is_valid}")
    
    # Test 3: Excel file validation
    print("\n3. Testing Excel file validation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a valid book Excel file
        test_file = Path(temp_dir) / "test_book.xlsm"
        df = pd.DataFrame({
            'URL': ['https://example.com', 'https://example2.com'],
            'Title': ['Test Book 1', 'Test Book 2'],
            'Author': ['John Doe', 'Jane Smith and Bob Wilson']
        })
        df.to_excel(test_file, engine='openpyxl', index=False)
        
        # Test validation
        result = await excel_service.validate_excel_file(str(test_file), 'book')
        print(f"  Book file validation: valid={result.valid}, errors={len(result.errors)}")
        for error in result.errors:
            print(f"    Error: {error.message}")
        
        print(f"  Preview rows: {len(result.preview_rows)}")
        for i, row in enumerate(result.preview_rows):
            print(f"    Row {row['row']}: {row['status']} - {row['data']}")
    
    # Test 4: Article Excel file validation
    print("\n4. Testing article Excel file validation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_article.xlsm"
        
        # Create article file with export_subset sheet
        with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
            # Create enough columns for article format
            columns = [f'col_{i}' for i in range(12)]
            data = {col: [f'data_{col}_{i}' for i in range(3)] for col in columns}
            # Set specific columns for article data
            data['col_0'] = ['article1', 'article2', 'article3']  # ID column
            data['col_7'] = ['yes', 'no', 'yes']  # Feature article column
            data['col_9'] = ['Author 1', 'Author 2', 'Author 3']  # Author column
            data['col_10'] = ['https://article1.com', 'https://article2.com', '']  # Article URL
            data['col_11'] = ['https://author1.com', '', 'https://author3.com']  # Author URL
            
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='export_subset', index=False)
        
        # Test validation
        result = await excel_service.validate_excel_file(str(test_file), 'article')
        print(f"  Article file validation: valid={result.valid}, errors={len(result.errors)}")
        for error in result.errors:
            print(f"    Error: {error.message}")
        
        print(f"  Preview rows: {len(result.preview_rows)}")
        for i, row in enumerate(result.preview_rows):
            print(f"    Row {row['row']}: {row['status']} - {row['data']}")
    
    print("\nBasic functionality test completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())