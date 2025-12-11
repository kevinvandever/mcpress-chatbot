#!/usr/bin/env python3
"""
Script to run Property Test 10.1 on Railway
Feature: multi-author-metadata-enhancement
Property 37: Book title fuzzy matching

This script should be run on Railway where DATABASE_URL is available.

Usage:
    python backend/run_property_test_10_1.py
"""

import subprocess
import sys

def main():
    """Run the property test for task 10.1"""
    print("=" * 70)
    print("Running Property Test 10.1: Book Title Fuzzy Matching")
    print("Feature: multi-author-metadata-enhancement")
    print("Property 37: Book title fuzzy matching")
    print("Validates: Requirements 9.2")
    print("=" * 70)
    print()
    
    # Run the specific test
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/test_excel_import_properties.py::TestFuzzyMatching::test_book_title_fuzzy_matching",
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    
    print()
    print("=" * 70)
    if result.returncode == 0:
        print("✓ Property Test 10.1 PASSED")
    else:
        print("✗ Property Test 10.1 FAILED")
    print("=" * 70)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())