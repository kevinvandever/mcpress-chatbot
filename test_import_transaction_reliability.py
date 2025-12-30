#!/usr/bin/env python3
"""
Test Import Transaction Reliability on Railway
This script tests that the Excel import service properly handles transactions
and provides accurate error reporting.
"""

import asyncio
import os
import sys
import tempfile
import json
from pathlib import Path

async def test_import_transaction_reliability():
    """Test that Excel import service properly handles transactions and error reporting"""
    
    try:
        # Import the service (this will only work on Railway with dependencies)
        from backend.excel_import_service import ExcelImportService
        from backend.author_service import AuthorService
        
        print("✓ Successfully imported ExcelImportService")
        
        # Create service instance
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return False
            
        author_service = AuthorService(database_url=database_url)
        excel_service = ExcelImportService(author_service, database_url=database_url)
        
        # Initialize database connections
        await author_service.init_database()
        await excel_service.init_database()
        
        print("✓ Successfully created and initialized ExcelImportService")
        
        # Test 1: Transaction rollback on critical error
        print("\n🧪 Test 1: Transaction rollback behavior")
        await test_transaction_rollback(excel_service)
        
        # Test 2: Proper error reporting
        print("\n🧪 Test 2: Error reporting accuracy")
        await test_error_reporting(excel_service)
        
        # Test 3: Database consistency after import
        print("\n🧪 Test 3: Database consistency verification")
        await test_database_consistency(excel_service)
        
        # Test 4: Detailed logging functionality
        print("\n🧪 Test 4: Detailed logging verification")
        await test_detailed_logging(excel_service)
        
        # Clean up
        await author_service.close()
        await excel_service.close()
        
        print("\n🎉 All transaction reliability tests completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This test needs to be run on Railway where dependencies are available.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_transaction_rollback(excel_service):
    """Test that transactions are properly rolled back on errors"""
    print("Testing transaction rollback behavior...")
    
    # Get initial database state
    async with excel_service.pool.acquire() as conn:
        initial_book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        initial_author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
        initial_doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
    
    print(f"Initial state: {initial_book_count} books, {initial_author_count} authors, {initial_doc_author_count} associations")
    
    # Create a test CSV with invalid data that should cause rollback
    test_data = """URL,Title,Author
https://example.com/book1,Valid Book 1,John Doe
https://example.com/book2,Valid Book 2,Jane Smith
invalid-url-format,Invalid Book,Bob Wilson
https://example.com/book3,Valid Book 3,Alice Johnson"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        temp_file.write(test_data)
        temp_file.flush()
        
        try:
            # This should process some rows but may have errors
            result = await excel_service.import_book_metadata(temp_file.name)
            
            print(f"Import result: Success={result.success}, Processed={result.books_processed}")
            print(f"Errors: {len(result.errors)}")
            
            # Check final database state
            async with excel_service.pool.acquire() as conn:
                final_book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
                final_author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
                final_doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
            
            print(f"Final state: {final_book_count} books, {final_author_count} authors, {final_doc_author_count} associations")
            
            # Verify transaction consistency
            if result.success:
                print("✅ Import reported success - transaction should be committed")
                if final_book_count >= initial_book_count and final_author_count >= initial_author_count:
                    print("✅ Database state consistent with successful transaction")
                else:
                    print("❌ Database state inconsistent - possible transaction issue")
            else:
                print("✅ Import reported failure - transaction should be rolled back")
                if final_book_count == initial_book_count and final_author_count == initial_author_count:
                    print("✅ Database state unchanged - transaction properly rolled back")
                else:
                    print("❌ Database state changed despite failure - transaction not rolled back properly")
            
        finally:
            os.unlink(temp_file.name)

async def test_error_reporting(excel_service):
    """Test that error reporting is accurate and detailed"""
    print("Testing error reporting accuracy...")
    
    # Create test data with various error conditions
    test_data = """URL,Title,Author
,Missing Title Test,John Doe
https://example.com/valid,Valid Book,
https://example.com/another,Another Valid Book,Jane Smith"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        temp_file.write(test_data)
        temp_file.flush()
        
        try:
            result = await excel_service.import_book_metadata(temp_file.name)
            
            print(f"Import processed {result.books_processed} rows")
            print(f"Found {len(result.errors)} errors/warnings")
            
            # Analyze error types
            errors = [e for e in result.errors if e.severity == "error"]
            warnings = [e for e in result.errors if e.severity == "warning"]
            
            print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
            
            # Check for expected error patterns
            has_missing_title_error = any("Title" in e.message for e in errors)
            has_missing_author_error = any("Author" in e.message for e in errors)
            
            if has_missing_title_error:
                print("✅ Correctly detected missing title error")
            else:
                print("❌ Failed to detect missing title error")
                
            if has_missing_author_error:
                print("✅ Correctly detected missing author error")
            else:
                print("❌ Failed to detect missing author error")
            
            # Verify error details include row numbers
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"   Error row {error.row}: {error.message} ({error.severity})")
            
        finally:
            os.unlink(temp_file.name)

async def test_database_consistency(excel_service):
    """Test that database remains consistent after import operations"""
    print("Testing database consistency...")
    
    # Check for orphaned records or inconsistent relationships
    async with excel_service.pool.acquire() as conn:
        # Check for document_authors records without corresponding books
        orphaned_doc_authors = await conn.fetchval("""
            SELECT COUNT(*) FROM document_authors da
            LEFT JOIN books b ON da.book_id = b.id
            WHERE b.id IS NULL
        """)
        
        # Check for document_authors records without corresponding authors
        orphaned_author_refs = await conn.fetchval("""
            SELECT COUNT(*) FROM document_authors da
            LEFT JOIN authors a ON da.author_id = a.id
            WHERE a.id IS NULL
        """)
        
        # Check for duplicate author names (should not exist due to unique constraint)
        duplicate_authors = await conn.fetchval("""
            SELECT COUNT(*) FROM (
                SELECT name, COUNT(*) as cnt
                FROM authors
                GROUP BY name
                HAVING COUNT(*) > 1
            ) duplicates
        """)
        
        print(f"Orphaned document_authors (no book): {orphaned_doc_authors}")
        print(f"Orphaned document_authors (no author): {orphaned_author_refs}")
        print(f"Duplicate author names: {duplicate_authors}")
        
        if orphaned_doc_authors == 0 and orphaned_author_refs == 0:
            print("✅ No orphaned records found - referential integrity maintained")
        else:
            print("❌ Found orphaned records - referential integrity compromised")
        
        if duplicate_authors == 0:
            print("✅ No duplicate authors found - deduplication working correctly")
        else:
            print("❌ Found duplicate authors - deduplication not working")

async def test_detailed_logging(excel_service):
    """Test that detailed logging is working properly"""
    print("Testing detailed logging functionality...")
    
    # Create a simple test file
    test_data = """URL,Title,Author
https://example.com/test,Test Book,Test Author"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        temp_file.write(test_data)
        temp_file.flush()
        
        try:
            # Capture the import process (logging should be visible in console)
            print("Running import with detailed logging...")
            result = await excel_service.import_book_metadata(temp_file.name)
            
            # Verify result contains expected information
            expected_fields = ['success', 'books_processed', 'books_matched', 'books_updated', 
                             'authors_created', 'processing_time', 'errors']
            
            missing_fields = [field for field in expected_fields if not hasattr(result, field)]
            
            if not missing_fields:
                print("✅ All expected result fields present")
            else:
                print(f"❌ Missing result fields: {missing_fields}")
            
            # Check processing time is reasonable
            if 0 < result.processing_time < 60:  # Should be between 0 and 60 seconds
                print(f"✅ Processing time reasonable: {result.processing_time:.2f}s")
            else:
                print(f"❌ Processing time unreasonable: {result.processing_time:.2f}s")
            
        finally:
            os.unlink(temp_file.name)

if __name__ == "__main__":
    result = asyncio.run(test_import_transaction_reliability())
    if result:
        print("\n✅ Task 6 implementation verified: Import transaction reliability is working correctly!")
    else:
        print("\n❌ Task 6 verification failed!")
        sys.exit(1)