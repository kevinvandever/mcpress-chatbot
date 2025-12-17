#!/usr/bin/env python3
"""
Railway Test Runner for Chat Handler Error Handling
Feature: chat-metadata-enrichment-fix, Task 3

Run this script on Railway to test error handling scenarios:
- Task 3.1: Missing DATABASE_URL
- Task 3.2: Database connection failure  
- Task 3.3: Book not found

Usage on Railway:
railway shell
python3 backend/run_test_error_handling.py
"""

import os
import sys
import asyncio

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def main():
    """Run the error handling tests on Railway"""
    print("🚀 Running Chat Handler Error Handling Tests on Railway")
    print("Feature: chat-metadata-enrichment-fix, Task 3")
    print("="*60)
    
    # Run pytest on the test file
    import subprocess
    
    try:
        # Run the specific error handling tests
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'backend/test_chat_enrichment.py::test_enrich_source_metadata_missing_database_url',
            'backend/test_chat_enrichment.py::test_enrich_source_metadata_connection_failure', 
            'backend/test_chat_enrichment.py::test_enrich_source_metadata_book_not_found',
            '-v', '-s', '--tb=short'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nTest exit code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ All error handling tests passed!")
        else:
            print("❌ Some tests failed. Check output above.")
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)