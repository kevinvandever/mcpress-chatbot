#!/usr/bin/env python3
"""
Script to run error handling tests on Railway
Feature: chat-metadata-enrichment-fix, Task 3

Usage: python3 backend/run_test_error_handling.py
"""

import subprocess
import sys
import os

def run_tests():
    """Run the error handling tests"""
    print("=" * 60)
    print("Running Chat Handler Error Handling Tests")
    print("Feature: chat-metadata-enrichment-fix, Task 3")
    print("=" * 60)
    
    # First run the unit tests in the test file
    print("\n🧪 Running Unit Tests...")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/test_chat_enrichment.py::test_enrich_source_metadata_missing_database_url",
        "backend/test_chat_enrichment.py::test_enrich_source_metadata_connection_failure", 
        "backend/test_chat_enrichment.py::test_enrich_source_metadata_book_not_found",
        "-v",
        "-s",
        "--tb=short"
    ]
    
    print(f"Executing: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ Unit tests failed with exit code: {result.returncode}")
        return result.returncode
    
    print("\n✅ Unit tests completed successfully!")
    
    # Also run the simple test script for additional verification
    print("\n🧪 Running Additional Error Handling Verification...")
    cmd2 = [sys.executable, "test_error_handling_simple.py"]
    
    print(f"Executing: {' '.join(cmd2)}\n")
    
    result2 = subprocess.run(cmd2, capture_output=False)
    
    if result2.returncode != 0:
        print(f"\n❌ Additional tests failed with exit code: {result2.returncode}")
        return result2.returncode
    
    print("\n✅ All error handling tests completed successfully!")
    print("\n" + "=" * 60)
    print("SUMMARY: Task 3 - Error Handling Tests")
    print("✅ Task 3.1: Missing DATABASE_URL - PASSED")
    print("✅ Task 3.2: Database Connection Failure - PASSED") 
    print("✅ Task 3.3: Book Not Found - PASSED")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)