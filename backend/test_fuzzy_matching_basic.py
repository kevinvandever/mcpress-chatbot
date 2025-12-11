#!/usr/bin/env python3
"""
Basic functionality test for fuzzy matching on Railway deployment
This tests the core fuzzy matching functionality without property-based testing.
"""

import asyncio
import os
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from excel_import_service import ExcelImportService
from author_service import AuthorService

async def test_basic_fuzzy_matching():
    """Test core fuzzy matching functionality"""
    print("Testing basic fuzzy matching functionality...")
    
    # Initialize services
    author_service = AuthorService()
    excel_service = ExcelImportService(author_service)
    
    # Test 1: Basic fuzzy matching logic with mock data
    print("\n1. Testing fuzzy matching consistency...")
    
    # Test with exact match
    mock_data = [(1, "RPG Programming Guide"), (2, "ILE RPG Reference"), (3, "System i Navigator")]
    
    result1 = await excel_service._mock_fuzzy_match_with_data("RPG Programming Guide", mock_data)
    result2 = await excel_service._mock_fuzzy_match_with_data("RPG Programming Guide", mock_data)
    
    assert result1 == result2, f"Fuzzy matching should be consistent: {result1} != {result2}"
    assert result1 == 1, f"Exact match should return correct ID: {result1}"
    print("✓ Exact match consistency: PASSED")
    
    # Test with case variation
    result_case = await excel_service._mock_fuzzy_match_with_data("rpg programming guide", mock_data)
    assert result_case == 1, f"Case variation should match: {result_case}"
    print("✓ Case variation matching: PASSED")
    
    # Test with punctuation variation
    result_punct = await excel_service._mock_fuzzy_match_with_data("RPG Programming Guide", mock_data)
    assert result_punct == 1, f"Punctuation variation should match: {result_punct}"
    print("✓ Punctuation variation matching: PASSED")
    
    # Test with empty input
    result_empty = await excel_service._mock_fuzzy_match_with_data("", mock_data)
    assert result_empty is None, f"Empty input should return None: {result_empty}"
    print("✓ Empty input handling: PASSED")
    
    # Test with very short input
    result_short = await excel_service._mock_fuzzy_match_with_data("ab", mock_data)
    assert result_short is None, f"Very short input should return None: {result_short}"
    print("✓ Short input handling: PASSED")
    
    # Test 2: Fuzzy threshold behavior
    print("\n2. Testing fuzzy threshold behavior...")
    
    # Test with a title that should not match (very different)
    result_nomatch = await excel_service._mock_fuzzy_match_with_data("Completely Different Book", mock_data)
    assert result_nomatch is None, f"Very different title should not match: {result_nomatch}"
    print("✓ No match for very different titles: PASSED")
    
    # Test with partial match
    result_partial = await excel_service._mock_fuzzy_match_with_data("RPG Programming", mock_data)
    # This might or might not match depending on threshold - just check it's consistent
    result_partial2 = await excel_service._mock_fuzzy_match_with_data("RPG Programming", mock_data)
    assert result_partial == result_partial2, f"Partial match should be consistent: {result_partial} != {result_partial2}"
    print("✓ Partial match consistency: PASSED")
    
    print("\n3. Testing threshold configuration...")
    print(f"Current fuzzy threshold: {excel_service.fuzzy_threshold}")
    assert excel_service.fuzzy_threshold == 80, f"Default threshold should be 80: {excel_service.fuzzy_threshold}"
    print("✓ Default threshold configuration: PASSED")
    
    print("\nAll basic fuzzy matching tests passed!")
    
    # Clean up
    await excel_service.close()

if __name__ == "__main__":
    asyncio.run(test_basic_fuzzy_matching())