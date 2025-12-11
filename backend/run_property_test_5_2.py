#!/usr/bin/env python3
"""
Script to run Property Test 5.2: Author updates propagate
This should be run on Railway where DATABASE_URL is available.
"""

import sys
import subprocess

def main():
    """Run the specific property test"""
    print("=" * 60)
    print("Running Property Test 5.2: Author updates propagate")
    print("=" * 60)
    print()
    
    # Run the specific test
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "backend/test_author_service.py::test_author_updates_propagate_property",
        "-v", "--tb=short", "-s"
    ], cwd="/app" if sys.platform == "linux" else ".")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
