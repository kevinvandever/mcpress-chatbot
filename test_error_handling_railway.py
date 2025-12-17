#!/usr/bin/env python3
"""
Railway Test Script for Chat Handler Error Handling
Feature: chat-metadata-enrichment-fix, Task 3

Tests error handling and graceful degradation scenarios:
- Task 3.1: Missing DATABASE_URL
- Task 3.2: Database connection failure  
- Task 3.3: Book not found

This script is designed to run on Railway where the actual database and environment exist.
Run with: python3 test_error_handling_railway.py
"""

import os
import asyncio
import logging
import sys
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any
import io

# Configure logging to capture all levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("🚀 Starting Chat Handler Error Handling Tests")
print("Feature: chat-metadata-enrichment-fix, Task 3")
print("="*60)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Try to import required modules
try:
    # Import required modules for testing
    import openai
    import tiktoken
    import asyncpg
    
    print("✅ Successfully imported required modules")
    
    # Import config
    try:
        from config import OPENAI_CONFIG, SEARCH_CONFIG, RESPONSE_CONFIG
        print("✅ Successfully imported config")
    except ImportError as e:
        print(f"⚠️ Could not import config: {e}")
        # Create mock config
        OPENAI_CONFIG = {"model": "gpt-4o-mini", "stream": True, "temperature": 0.5, "max_tokens": 3000}
        SEARCH_CONFIG = {"initial_search_results": 30, "max_sources": 12, "relevance_threshold": 0.55}
        RESPONSE_CONFIG = {"max_conversation_history": 10}
        print("✅ Using mock config")
    
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("This script needs to run on Railway where dependencies are installed")
    exit(1)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.tests.append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        for test in self.tests:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"{status}: {test['name']}")
            if test['message']:
                print(f"    {test['message']}")
        print(f"\nTotal: {len(self.tests)} tests, {self.passed} passed, {self.failed} failed")
        print("="*60)


async def test_missing_database_url():
    """
    Task 3.1: Test graceful degradation when DATABASE_URL is not set
    Requirements: 4.1
    """
    print("\n🧪 Testing Task 3.1: Missing DATABASE_URL")
    
    try:
        # Create a mock vector store
        mock_vector_store = AsyncMock()
        
        # Create chat handler with mocked OPENAI_API_KEY
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            chat_handler = ChatHandler(mock_vector_store)
        
        # Remove DATABASE_URL from environment
        original_db_url = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        
        # Capture logs
        import io
        import sys
        from contextlib import redirect_stderr
        
        log_capture = io.StringIO()
        
        # Set up a custom log handler to capture logs
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.WARNING)
        chat_logger = logging.getLogger('backend.chat_handler')
        chat_logger.addHandler(log_handler)
        
        try:
            # Call the enrichment method
            result = await chat_handler._enrich_source_metadata('test-book.pdf')
            
            # Check result
            if result == {}:
                print("✅ Returned empty dict as expected")
                
                # Check logs
                log_output = log_capture.getvalue()
                if 'DATABASE_URL not available' in log_output:
                    print("✅ Warning logged as expected")
                    return True, "Missing DATABASE_URL handled correctly"
                else:
                    print("❌ Expected warning log not found")
                    print(f"Log output: {log_output}")
                    return False, "Warning log not found"
            else:
                print(f"❌ Expected empty dict, got: {result}")
                return False, f"Expected empty dict, got: {result}"
                
        finally:
            # Restore DATABASE_URL
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            chat_logger.removeHandler(log_handler)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Exception: {e}"


async def test_connection_failure():
    """
    Task 3.2: Test graceful degradation when database connection fails
    Requirements: 4.2
    """
    print("\n🧪 Testing Task 3.2: Database Connection Failure")
    
    try:
        # Create a mock vector store
        mock_vector_store = AsyncMock()
        
        # Create chat handler
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key', 'DATABASE_URL': 'postgresql://fake'}):
            chat_handler = ChatHandler(mock_vector_store)
        
        # Set up log capture
        import io
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.ERROR)
        chat_logger = logging.getLogger('backend.chat_handler')
        chat_logger.addHandler(log_handler)
        
        try:
            # Mock asyncpg.connect to raise ConnectionError
            import asyncpg
            with patch('asyncpg.connect', AsyncMock(side_effect=ConnectionError("Database connection failed"))):
                # Call the enrichment method
                result = await chat_handler._enrich_source_metadata('test-book.pdf')
            
            # Check result
            if result == {}:
                print("✅ Returned empty dict as expected")
                
                # Check logs
                log_output = log_capture.getvalue()
                if 'Error enriching source metadata' in log_output and 'Traceback' in log_output:
                    print("✅ Error logged with traceback as expected")
                    return True, "Connection failure handled correctly"
                else:
                    print("❌ Expected error log with traceback not found")
                    print(f"Log output: {log_output}")
                    return False, "Error log with traceback not found"
            else:
                print(f"❌ Expected empty dict, got: {result}")
                return False, f"Expected empty dict, got: {result}"
                
        finally:
            chat_logger.removeHandler(log_handler)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Exception: {e}"


async def test_book_not_found():
    """
    Task 3.3: Test graceful degradation when book is not found
    Requirements: 4.3
    """
    print("\n🧪 Testing Task 3.3: Book Not Found")
    
    try:
        # Create a mock vector store
        mock_vector_store = AsyncMock()
        
        # Create chat handler
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key', 'DATABASE_URL': 'postgresql://fake'}):
            chat_handler = ChatHandler(mock_vector_store)
        
        # Set up log capture
        import io
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.INFO)
        chat_logger = logging.getLogger('backend.chat_handler')
        chat_logger.addHandler(log_handler)
        
        try:
            # Mock database connection that returns no book
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)  # No book found
            mock_conn.close = AsyncMock()
            
            import asyncpg
            with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
                # Call the enrichment method
                result = await chat_handler._enrich_source_metadata('nonexistent-book.pdf')
            
            # Check result
            if result == {}:
                print("✅ Returned empty dict as expected")
                
                # Check logs
                log_output = log_capture.getvalue()
                if 'No book found for filename' in log_output:
                    print("✅ Info log about book not found as expected")
                    
                    # Verify connection was closed
                    mock_conn.close.assert_called_once()
                    print("✅ Database connection closed as expected")
                    
                    return True, "Book not found handled correctly"
                else:
                    print("❌ Expected info log about book not found")
                    print(f"Log output: {log_output}")
                    return False, "Info log about book not found missing"
            else:
                print(f"❌ Expected empty dict, got: {result}")
                return False, f"Expected empty dict, got: {result}"
                
        finally:
            chat_logger.removeHandler(log_handler)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Exception: {e}"


async def main():
    """Run all error handling tests"""
    print("🚀 Starting Chat Handler Error Handling Tests on Railway")
    print("Feature: chat-metadata-enrichment-fix, Task 3")
    print("="*60)
    
    results = TestResults()
    
    # Test 3.1: Missing DATABASE_URL
    try:
        passed, message = await test_missing_database_url()
        results.add_result("Task 3.1: Missing DATABASE_URL", passed, message)
    except Exception as e:
        results.add_result("Task 3.1: Missing DATABASE_URL", False, f"Exception: {e}")
    
    # Test 3.2: Connection failure
    try:
        passed, message = await test_connection_failure()
        results.add_result("Task 3.2: Database Connection Failure", passed, message)
    except Exception as e:
        results.add_result("Task 3.2: Database Connection Failure", False, f"Exception: {e}")
    
    # Test 3.3: Book not found
    try:
        passed, message = await test_book_not_found()
        results.add_result("Task 3.3: Book Not Found", passed, message)
    except Exception as e:
        results.add_result("Task 3.3: Book Not Found", False, f"Exception: {e}")
    
    # Print summary
    results.print_summary()
    
    # Return exit code
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)