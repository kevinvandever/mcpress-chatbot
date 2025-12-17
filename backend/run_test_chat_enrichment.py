#!/usr/bin/env python3
"""
Script to run chat enrichment tests on Railway
Usage: python3 backend/run_test_chat_enrichment.py
"""

import subprocess
import sys

def run_tests():
    """Run the chat enrichment tests"""
    print("=" * 60)
    print("Running Chat Enrichment Tests")
    print("=" * 60)
    
    # Run pytest with the test file
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "backend/test_chat_enrichment.py",
        "-v",
        "-s",
        "--tb=short"
    ]
    
    print(f"\nExecuting: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
