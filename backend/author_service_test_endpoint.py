"""
Test Endpoint for AuthorService
Run AuthorService tests in production via HTTP request
Access at: https://your-backend-url/test-author-service/*
"""

from fastapi import APIRouter, HTTPException
import os
import random
import string

# Import the service
try:
    from author_service import AuthorService
except ImportError:
    from backend.author_service import AuthorService

author_service_test_router = APIRouter(prefix="/test-author-service", tags=["test-author-service"])


def generate_test_author_name():
    """Generate a random test author name"""
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"TEST_{random_suffix}"


def generate_test_url():
    """Generate a random test URL"""
    if random.choice([True, False]):
        return None
    domain = ''.join(random.choices(string.ascii_lowercase, k=10))
    path = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
    return f"https://{domain}.com/{path}"


@author_service_test_router.get("/test-deduplication")
async def test_author_deduplication():
    """
    Test Property 2: Author deduplication
    Feature: multi-author-metadata-enhancement, Property 2: Author deduplication
    Validates: Requirements 1.2
    
    For any author name, when that author is associated with multiple documents,
    only one author record should exist in the authors table.
    """
    service = AuthorService()
    await service.init_database()
    
    try:
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations
        for iteration in range(100):
            try:
                # Generate test data
                author_name = generate_test_author_name()
                num_attempts = random.randint(2, 5)
                site_urls = [generate_test_url() for _ in range(num_attempts)]
                
                # Call get_or_create_author multiple times with same name
                author_ids = []
                for site_url in site_urls:
                    author_id = await service.get_or_create_author(author_name, site_url)
                    author_ids.append(author_id)
                
                # Property: All author_ids should be the same (deduplication)
                unique_ids = set(author_ids)
                if len(unique_ids) != 1:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "author_name": author_name,
                        "expected_unique_ids": 1,
                        "actual_unique_ids": len(unique_ids),
                        "author_ids": author_ids,
                        "error": f"Author deduplication failed: expected 1 unique author ID, got {len(unique_ids)}"
                    })
                    continue
                
                # Verify only one author record exists with this name
                async with service.pool.acquire() as conn:
                    count = await conn.fetchval("""
                        SELECT COUNT(*) FROM authors WHERE name = $1
                    """, author_name)
                    
                    if count != 1:
                        failed += 1
                        test_results.append({
                            "iteration": iteration + 1,
                            "status": "FAILED",
                            "author_name": author_name,
                            "expected_count": 1,
                            "actual_count": count,
                            "error": f"Expected 1 author record, found {count}"
                        })
                        continue
                    
                    # Verify the author can be retrieved
                    author = await service.get_author_by_id(author_ids[0])
                    if author is None:
                        failed += 1
                        test_results.append({
                            "iteration": iteration + 1,
                            "status": "FAILED",
                            "author_name": author_name,
                            "error": f"Could not retrieve author"
                        })
                        continue
                    
                    if author['name'] != author_name:
                        failed += 1
                        test_results.append({
                            "iteration": iteration + 1,
                            "status": "FAILED",
                            "author_name": author_name,
                            "error": "Author name mismatch"
                        })
                        continue
                    
                    # Test passed
                    passed += 1
                    
                    # Clean up this test's data
                    await conn.execute("DELETE FROM authors WHERE name = $1", author_name)
                
            except Exception as e:
                failed += 1
                test_results.append({
                    "iteration": iteration + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Clean up all test data
        async with service.pool.acquire() as conn:
            await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        await service.close()
        
        success_rate = (passed / 100) * 100
        
        return {
            "test": "Property 2: Author deduplication",
            "validates": "Requirements 1.2",
            "total_iterations": 100,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate}%",
            "status": "PASSED" if failed == 0 else "FAILED",
            "failures": [r for r in test_results if r.get("status") in ["FAILED", "ERROR"]],
            "message": f"Property test {'PASSED' if failed == 0 else 'FAILED'}: {passed}/100 iterations successful"
        }
        
    except Exception as e:
        await service.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@author_service_test_router.get("/test-get-or-create")
async def test_get_or_create_behavior():
    """
    Test Property 14: Create or reuse author on add
    Feature: multi-author-metadata-enhancement, Property 14: Create or reuse author on add
    Validates: Requirements 5.3, 5.4
    
    For any author name, when adding it to a document, if the author exists
    it should be reused, otherwise a new author record should be created.
    """
    service = AuthorService()
    await service.init_database()
    
    try:
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations
        for iteration in range(100):
            try:
                # Generate test data
                author_name = generate_test_author_name()
                first_url = generate_test_url()
                second_url = generate_test_url()
                
                # First call - should create new author
                first_id = await service.get_or_create_author(author_name, first_url)
                if first_id is None:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "First call should return an author ID"
                    })
                    continue
                
                # Verify author was created
                author = await service.get_author_by_id(first_id)
                if author is None:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Author should exist after creation"
                    })
                    continue
                
                if author['name'] != author_name:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Author name should match"
                    })
                    continue
                
                # Second call with same name - should reuse existing author
                second_id = await service.get_or_create_author(author_name, second_url)
                if second_id is None:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "error": "Second call should return an author ID"
                    })
                    continue
                
                # Property: Both IDs should be the same (reuse existing)
                if first_id != second_id:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "author_name": author_name,
                        "first_id": first_id,
                        "second_id": second_id,
                        "error": f"get_or_create_author should reuse existing author"
                    })
                    continue
                
                # Verify only one author record exists
                async with service.pool.acquire() as conn:
                    count = await conn.fetchval("""
                        SELECT COUNT(*) FROM authors WHERE name = $1
                    """, author_name)
                    
                    if count != 1:
                        failed += 1
                        test_results.append({
                            "iteration": iteration + 1,
                            "status": "FAILED",
                            "author_name": author_name,
                            "expected_count": 1,
                            "actual_count": count,
                            "error": f"Expected 1 author record, found {count}"
                        })
                        continue
                    
                    # Test passed
                    passed += 1
                    
                    # Clean up this test's data
                    await conn.execute("DELETE FROM authors WHERE name = $1", author_name)
                
            except Exception as e:
                failed += 1
                test_results.append({
                    "iteration": iteration + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Clean up all test data
        async with service.pool.acquire() as conn:
            await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        
        await service.close()
        
        success_rate = (passed / 100) * 100
        
        return {
            "test": "Property 14: Create or reuse author on add",
            "validates": "Requirements 5.3, 5.4",
            "total_iterations": 100,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate}%",
            "status": "PASSED" if failed == 0 else "FAILED",
            "failures": [r for r in test_results if r.get("status") in ["FAILED", "ERROR"]],
            "message": f"Property test {'PASSED' if failed == 0 else 'FAILED'}: {passed}/100 iterations successful"
        }
        
    except Exception as e:
        await service.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@author_service_test_router.get("/test-all")
async def test_all_properties():
    """
    Run all property tests for AuthorService
    """
    results = {}
    
    try:
        # Test 1: Author deduplication
        dedup_result = await test_author_deduplication()
        results['property_2_deduplication'] = dedup_result
        
        # Test 2: Get or create behavior
        get_or_create_result = await test_get_or_create_behavior()
        results['property_14_get_or_create'] = get_or_create_result
        
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


@author_service_test_router.get("/test-unit-tests")
async def test_unit_tests():
    """
    Run unit tests for AuthorService
    """
    service = AuthorService()
    await service.init_database()
    
    results = []
    
    try:
        # Test 1: Empty author name should be rejected
        try:
            await service.get_or_create_author("")
            results.append({
                "test": "Empty author name rejection",
                "status": "FAILED",
                "error": "Should have raised ValueError"
            })
        except ValueError as e:
            if "cannot be empty" in str(e):
                results.append({
                    "test": "Empty author name rejection",
                    "status": "PASSED"
                })
            else:
                results.append({
                    "test": "Empty author name rejection",
                    "status": "FAILED",
                    "error": f"Wrong error message: {str(e)}"
                })
        
        # Test 2: Update author
        try:
            author_id = await service.get_or_create_author("TEST_Update_Author", "https://example.com")
            await service.update_author(author_id, name="TEST_Updated_Name", site_url="https://updated.com")
            author = await service.get_author_by_id(author_id)
            
            if author['name'] == "TEST_Updated_Name" and author['site_url'] == "https://updated.com":
                results.append({
                    "test": "Update author",
                    "status": "PASSED"
                })
            else:
                results.append({
                    "test": "Update author",
                    "status": "FAILED",
                    "error": f"Update failed: name={author['name']}, url={author['site_url']}"
                })
            
            # Clean up
            async with service.pool.acquire() as conn:
                await conn.execute("DELETE FROM authors WHERE id = $1", author_id)
                
        except Exception as e:
            results.append({
                "test": "Update author",
                "status": "FAILED",
                "error": str(e)
            })
        
        # Test 3: Search authors
        try:
            # Create test authors
            await service.get_or_create_author("TEST_John_Doe", "https://john.com")
            await service.get_or_create_author("TEST_Jane_Doe", "https://jane.com")
            await service.get_or_create_author("TEST_Bob_Smith", "https://bob.com")
            
            # Search for "Doe"
            search_results = await service.search_authors("Doe")
            names = [r['name'] for r in search_results]
            
            if len(search_results) == 2 and "TEST_John_Doe" in names and "TEST_Jane_Doe" in names:
                results.append({
                    "test": "Search authors",
                    "status": "PASSED"
                })
            else:
                results.append({
                    "test": "Search authors",
                    "status": "FAILED",
                    "error": f"Expected 2 results with John and Jane, got: {names}"
                })
            
            # Clean up
            async with service.pool.acquire() as conn:
                await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
                
        except Exception as e:
            results.append({
                "test": "Search authors",
                "status": "FAILED",
                "error": str(e)
            })
        
        # Test 4: Invalid URL
        try:
            await service.get_or_create_author("TEST_Invalid_URL", "not-a-url")
            results.append({
                "test": "Invalid URL rejection",
                "status": "FAILED",
                "error": "Should have raised ValueError"
            })
        except ValueError as e:
            if "Invalid URL format" in str(e):
                results.append({
                    "test": "Invalid URL rejection",
                    "status": "PASSED"
                })
            else:
                results.append({
                    "test": "Invalid URL rejection",
                    "status": "FAILED",
                    "error": f"Wrong error message: {str(e)}"
                })
        
        await service.close()
        
        passed = sum(1 for r in results if r['status'] == 'PASSED')
        total = len(results)
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "status": "PASSED" if passed == total else "FAILED",
            "results": results
        }
        
    except Exception as e:
        await service.close()
        raise HTTPException(status_code=500, detail=f"Unit tests failed: {str(e)}")


@author_service_test_router.get("/cleanup")
async def cleanup_test_data():
    """Clean up all test data"""
    service = AuthorService()
    await service.init_database()
    
    try:
        async with service.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
            deleted = int(result.split()[-1]) if result else 0
        
        await service.close()
        
        return {
            "status": "success",
            "deleted_authors": deleted,
            "message": f"Cleaned up {deleted} test authors"
        }
        
    except Exception as e:
        await service.close()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
