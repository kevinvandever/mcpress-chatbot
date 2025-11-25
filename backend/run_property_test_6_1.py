#!/usr/bin/env python3
"""
Script to run Property Test 6.1 on Railway
Feature: multi-author-metadata-enhancement
Property 1: Multiple author association

This script should be run on Railway where DATABASE_URL is available.

Usage:
    python backend/run_property_test_6_1.py
"""

import subprocess
import sys

def main():
    """Run the property test for task 6.1"""
    print("=" * 70)
    print("Running Property Test 6.1: Multiple Author Association")
    print("Feature: multi-author-metadata-enhancement")
    print("Property 1: Multiple author association")
    print("Validates: Requirements 1.1, 1.3")
    print("=" * 70)
    print()
    
    # Run the specific test
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/test_document_author_service.py::test_multiple_author_association",
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
        print("✓ Property Test 6.1 PASSED")
    else:
        print("✗ Property Test 6.1 FAILED")
    print("=" * 70)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
