"""
Test Endpoint for DocumentAuthorService
Run DocumentAuthorService tests in production via HTTP request
Access at: https://your-backend-url/test-document-author-service/*
"""

from fastapi import APIRouter, HTTPException
import os
import random
import string
import asyncpg

# Import the services
try:
    from document_author_service import DocumentAuthorService
    from author_service import AuthorService
except ImportError:
    from backend.document_author_service import DocumentAuthorService
    from backend.author_service import AuthorService

document_author_service_test_router = APIRouter(
    prefix="/test-document-author-service",
    tags=["test-document-author-service"]
)


def generate_test_book_filename():
    """Generate a random test book filename"""
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"TEST_{random_suffix}.pdf"


def generate_test_author_name():
    """Generate a random test author name"""
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"TEST_{random_suffix}"


async def create_test_book(conn, filename: str, title: str) -> int:
    """Helper to create a test book"""
    # Insert minimal book record - only required fields
    book_id = await conn.fetchval("""
        INSERT INTO books (filename, title, document_type)
        VALUES ($1, $2, 'book')
        RETURNING id
    """, filename, title)
    return book_id


@document_author_service_test_router.get("/test-duplicate-prevention")
async def test_duplicate_prevention():
    """
    Test Property 3: No duplicate author associations
    Feature: multi-author-metadata-enhancement, Property 3: No duplicate author associations
    Validates: Requirements 1.4
    
    For any document and author, attempting to associate the same author with 
    the document multiple times should result in only one association record.
    """
    doc_service = DocumentAuthorService()
    author_service = AuthorService()
    await doc_service.init_database()
    await author_service.init_database()
    
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations
        for iteration in range(100):
            try:
                # Generate test data
                book_filename = generate_test_book_filename()
                author_name = generate_test_author_name()
                num_attempts = random.randint(2, 5)
                
                # Create test book and author
                book_id = await create_test_book(conn, book_filename, "Test Book")
                author_id = await author_service.get_or_create_author(author_name)
                
                # First attempt - should succeed
                await doc_service.add_author_to_document(book_id, author_id)
                
                # Subsequent attempts - should fail
                duplicate_prevented = True
                for attempt in range(1, num_attempts):
                    try:
                        await doc_service.add_author_to_document(book_id, author_id)
                        duplicate_prevented = False
                        break
                    except ValueError as e:
                        if "already associated" not in str(e):
                            duplicate_prevented = False
                            break
                
                if not duplicate_prevented:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Duplicate author association was not prevented"
                    })
                    # Clean up
                    await conn.execute("DELETE FROM books WHERE id = $1", book_id)
                    await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                    continue
                
                # Verify only one association exists
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM document_authors 
                    WHERE book_id = $1 AND author_id = $2
                """, book_id, author_id)
                
                if count != 1:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "expected_count": 1,
                        "actual_count": count,
                        "error": f"Expected 1 association, found {count}"
                    })
                else:
                    passed += 1
                
                # Clean up
                await conn.execute("DELETE FROM books WHERE id = $1", book_id)
                await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                
            except Exception as e:
                failed += 1
                test_results.append({
                    "iteration": iteration + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Final cleanup
        await conn.execute("DELETE FROM books WHERE filename LIKE 'TEST_%'")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        await conn.close()
        await doc_service.close()
        await author_service.close()
        
        success_rate = (passed / 100) * 100
        
        return {
            "test": "Property 3: No duplicate author associations",
            "validates": "Requirements 1.4",
            "total_iterations": 100,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate}%",
            "status": "PASSED" if failed == 0 else "FAILED",
            "failures": [r for r in test_results if r.get("status") in ["FAILED", "ERROR"]],
            "message": f"Property test {'PASSED' if failed == 0 else 'FAILED'}: {passed}/100 iterations successful"
        }
        
    except Exception as e:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@document_author_service_test_router.get("/test-last-author-validation")
async def test_last_author_validation():
    """
    Test Property 16: Require at least one author
    Feature: multi-author-metadata-enhancement, Property 16: Require at least one author
    Validates: Requirements 5.7
    
    For any document with exactly one author, attempting to remove that author 
    should be rejected.
    """
    doc_service = DocumentAuthorService()
    author_service = AuthorService()
    await doc_service.init_database()
    await author_service.init_database()
    
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations
        for iteration in range(100):
            try:
                # Generate test data
                book_filename = generate_test_book_filename()
                author_name = generate_test_author_name()
                
                # Create test book with one author
                book_id = await create_test_book(conn, book_filename, "Test Book")
                author_id = await author_service.get_or_create_author(author_name)
                await doc_service.add_author_to_document(book_id, author_id)
                
                # Verify we have exactly one author
                count_before = await doc_service.get_author_count_for_document(book_id)
                if count_before != 1:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": f"Expected 1 author, found {count_before}"
                    })
                    # Clean up
                    await conn.execute("DELETE FROM books WHERE id = $1", book_id)
                    await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                    continue
                
                # Attempt to remove the last author - should fail
                removal_prevented = False
                try:
                    await doc_service.remove_author_from_document(book_id, author_id)
                except ValueError as e:
                    if "Cannot remove last author" in str(e):
                        removal_prevented = True
                
                if not removal_prevented:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Last author removal was not prevented"
                    })
                    # Clean up
                    await conn.execute("DELETE FROM books WHERE id = $1", book_id)
                    await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                    continue
                
                # Verify the author is still associated
                count_after = await doc_service.get_author_count_for_document(book_id)
                if count_after != 1:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": f"Author was removed despite being the last one"
                    })
                else:
                    passed += 1
                
                # Clean up
                await conn.execute("DELETE FROM books WHERE id = $1", book_id)
                await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                
            except Exception as e:
                failed += 1
                test_results.append({
                    "iteration": iteration + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Final cleanup
        await conn.execute("DELETE FROM books WHERE filename LIKE 'TEST_%'")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        await conn.close()
        await doc_service.close()
        await author_service.close()
        
        success_rate = (passed / 100) * 100
        
        return {
            "test": "Property 16: Require at least one author",
            "validates": "Requirements 5.7",
            "total_iterations": 100,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate}%",
            "status": "PASSED" if failed == 0 else "FAILED",
            "failures": [r for r in test_results if r.get("status") in ["FAILED", "ERROR"]],
            "message": f"Property test {'PASSED' if failed == 0 else 'FAILED'}: {passed}/100 iterations successful"
        }
        
    except Exception as e:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@document_author_service_test_router.get("/test-cascade-deletion")
async def test_cascade_deletion():
    """
    Test Property 4: Cascade deletion preserves shared authors
    Feature: multi-author-metadata-enhancement, Property 4: Cascade deletion preserves shared authors
    Validates: Requirements 1.5
    
    For any author associated with multiple documents, when deleting one document,
    the author record should still exist and remain associated with the other documents.
    """
    doc_service = DocumentAuthorService()
    author_service = AuthorService()
    await doc_service.init_database()
    await author_service.init_database()
    
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations
        for iteration in range(100):
            try:
                # Generate test data
                book1_filename = generate_test_book_filename()
                book2_filename = f"ALT_{generate_test_book_filename()}"
                author_name = generate_test_author_name()
                
                # Create two test books
                book1_id = await create_test_book(conn, book1_filename, "Test Book 1")
                book2_id = await create_test_book(conn, book2_filename, "Test Book 2")
                
                # Create one author and associate with both books
                author_id = await author_service.get_or_create_author(author_name)
                await doc_service.add_author_to_document(book1_id, author_id)
                await doc_service.add_author_to_document(book2_id, author_id)
                
                # Verify author is associated with both documents
                docs_before = await doc_service.get_documents_by_author(author_id)
                if len(docs_before) != 2:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": f"Expected 2 documents, found {len(docs_before)}"
                    })
                    # Clean up
                    await conn.execute("DELETE FROM books WHERE id IN ($1, $2)", book1_id, book2_id)
                    await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                    continue
                
                # Delete one document
                await conn.execute("DELETE FROM books WHERE id = $1", book1_id)
                
                # Verify cascade deletion behavior
                verification = await doc_service.verify_cascade_deletion(author_id, book1_id)
                
                # Check all properties
                if not verification['author_still_exists']:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Author record was deleted"
                    })
                elif not verification['association_removed']:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Association with deleted document still exists"
                    })
                elif verification['remaining_document_count'] != 1:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "expected_remaining": 1,
                        "actual_remaining": verification['remaining_document_count'],
                        "error": f"Expected 1 remaining document, found {verification['remaining_document_count']}"
                    })
                else:
                    passed += 1
                
                # Clean up
                await conn.execute("DELETE FROM books WHERE id = $1", book2_id)
                await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                
            except Exception as e:
                failed += 1
                test_results.append({
                    "iteration": iteration + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Final cleanup
        await conn.execute("DELETE FROM books WHERE filename LIKE 'TEST_%'")
        await conn.execute("DELETE FROM books WHERE filename LIKE 'ALT_TEST_%'")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        await conn.close()
        await doc_service.close()
        await author_service.close()
        
        success_rate = (passed / 100) * 100
        
        return {
            "test": "Property 4: Cascade deletion preserves shared authors",
            "validates": "Requirements 1.5",
            "total_iterations": 100,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate}%",
            "status": "PASSED" if failed == 0 else "FAILED",
            "failures": [r for r in test_results if r.get("status") in ["FAILED", "ERROR"]],
            "message": f"Property test {'PASSED' if failed == 0 else 'FAILED'}: {passed}/100 iterations successful"
        }
        
    except Exception as e:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@document_author_service_test_router.get("/test-all")
async def test_all_properties():
    """
    Run all property tests for DocumentAuthorService
    """
    results = {}
    
    try:
        # Test 1: Duplicate prevention
        duplicate_result = await test_duplicate_prevention()
        results['property_3_duplicate_prevention'] = duplicate_result
        
        # Test 2: Last author validation
        last_author_result = await test_last_author_validation()
        results['property_16_last_author'] = last_author_result
        
        # Test 3: Cascade deletion
        cascade_result = await test_cascade_deletion()
        results['property_4_cascade_deletion'] = cascade_result
        
        # Overall status
        all_passed = all(
            r['status'] == 'PASSED' 
            for r in results.values()
        )
        
        return {
            "overall_status": "PASSED" if all_passed else "FAILED",
            "tests": results,
            "message": "All tests passed!" if all_passed else "Some tests failed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test suite failed: {str(e)}")


@document_author_service_test_router.get("/cleanup")
async def cleanup_test_data():
    """Clean up all test data"""
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        # Delete test books and their associations
        result1 = await conn.execute("DELETE FROM books WHERE filename LIKE 'TEST_%'")
        result2 = await conn.execute("DELETE FROM books WHERE filename LIKE 'ALT_TEST_%'")
        result3 = await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        deleted_books = int(result1.split()[-1]) if result1 else 0
        deleted_books += int(result2.split()[-1]) if result2 else 0
        deleted_authors = int(result3.split()[-1]) if result3 else 0
        
        await conn.close()
        
        return {
            "status": "success",
            "deleted_books": deleted_books,
            "deleted_authors": deleted_authors,
            "message": f"Cleaned up {deleted_books} test books and {deleted_authors} test authors"
        }
        
    except Exception as e:
        await conn.close()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
