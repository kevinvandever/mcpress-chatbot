"""
Test Endpoint for Migration 003: Multi-Author Metadata Enhancement
Run property-based tests in production via HTTP request
Access at: https://your-backend-url/test-003/run-property-tests
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
import random
import string

test_003_router = APIRouter(prefix="/test-003", tags=["test-003"])

async def get_connection():
    """Get a database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return await asyncpg.connect(database_url)


async def cleanup_test_data(conn):
    """Clean up test data from authors and document_authors tables"""
    try:
        await conn.execute("DELETE FROM document_authors WHERE author_id IN (SELECT id FROM authors WHERE name LIKE 'TEST_%')")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%')")
    except Exception as e:
        # Tables might not exist yet
        pass


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


@test_003_router.get("/run-property-tests")
async def run_property_tests():
    """
    Run property-based tests for author deduplication
    Feature: multi-author-metadata-enhancement, Property 2: Author deduplication
    Validates: Requirements 1.2
    
    Access this at: https://your-backend-url/test-003/run-property-tests
    """
    conn = await get_connection()
    
    try:
        # Check if tables exist
        authors_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'authors'
            )
        """)
        
        if not authors_exist:
            await conn.close()
            raise HTTPException(
                status_code=400,
                detail="Authors table does not exist. Run migration first."
            )
        
        # Clean up any existing test data
        await cleanup_test_data(conn)
        
        test_results = []
        passed = 0
        failed = 0
        
        # Run 100 iterations of the property test
        for iteration in range(100):
            try:
                # Generate test data
                author_name = generate_test_author_name()
                num_attempts = random.randint(2, 5)
                site_urls = [generate_test_url() for _ in range(num_attempts)]
                
                # Attempt to insert the same author multiple times with different URLs
                author_ids = []
                for site_url in site_urls:
                    try:
                        # Try to insert author with ON CONFLICT handling
                        author_id = await conn.fetchval("""
                            INSERT INTO authors (name, site_url)
                            VALUES ($1, $2)
                            ON CONFLICT (name) DO UPDATE
                            SET site_url = EXCLUDED.site_url
                            RETURNING id
                        """, author_name, site_url)
                        author_ids.append(author_id)
                    except Exception as e:
                        # If insert fails, try to get existing author
                        author_id = await conn.fetchval("""
                            SELECT id FROM authors WHERE name = $1
                        """, author_name)
                        if author_id:
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
                        "error": f"Author deduplication failed: expected 1 unique author ID, got {len(unique_ids)}"
                    })
                    continue
                
                # Verify only one author record exists with this name
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
                        "error": f"Author deduplication failed: expected 1 author record, found {count}"
                    })
                    continue
                
                # Verify the author can be retrieved
                author = await conn.fetchrow("""
                    SELECT id, name, site_url FROM authors WHERE name = $1
                """, author_name)
                
                if author is None:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "author_name": author_name,
                        "error": f"Could not retrieve author '{author_name}'"
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
                
                if author['id'] != author_ids[0]:
                    failed += 1
                    test_results.append({
                        "iteration": iteration + 1,
                        "status": "FAILED",
                        "author_name": author_name,
                        "error": "Author ID mismatch"
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
        await cleanup_test_data(conn)
        await conn.close()
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        await conn.close()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@test_003_router.get("/test-unique-constraint")
async def test_unique_constraint():
    """
    Test that the UNIQUE constraint on author name is enforced
    Access this at: https://your-backend-url/test-003/test-unique-constraint
    """
    conn = await get_connection()
    
    try:
        await cleanup_test_data(conn)
        
        # Insert an author
        author_name = "TEST_Unique_Constraint_Author"
        await conn.execute("""
            INSERT INTO authors (name, site_url)
            VALUES ($1, $2)
        """, author_name, "https://example.com")
        
        # Try to insert the same author again
        constraint_enforced = False
        try:
            await conn.execute("""
                INSERT INTO authors (name, site_url)
                VALUES ($1, $2)
            """, author_name, "https://different.com")
            
            # If we get here, check that only one record exists
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM authors WHERE name = $1
            """, author_name)
            
            if count == 1:
                constraint_enforced = True
                message = "UNIQUE constraint working: duplicate prevented by application logic"
            else:
                message = f"UNIQUE constraint FAILED: {count} records exist for same author"
            
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                constraint_enforced = True
                message = "UNIQUE constraint working: database rejected duplicate"
            else:
                message = f"Unexpected error: {str(e)}"
        
        # Clean up
        await conn.execute("DELETE FROM authors WHERE name = $1", author_name)
        await conn.close()
        
        return {
            "test": "UNIQUE constraint on author name",
            "status": "PASSED" if constraint_enforced else "FAILED",
            "message": message
        }
        
    except Exception as e:
        await conn.close()
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@test_003_router.get("/cleanup")
async def cleanup_all_test_data():
    """
    Clean up all test data
    Access this at: https://your-backend-url/test-003/cleanup
    """
    conn = await get_connection()
    
    try:
        # Delete all test authors
        result = await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
        deleted = int(result.split()[-1]) if result else 0
        
        await conn.close()
        
        return {
            "status": "success",
            "deleted_authors": deleted,
            "message": f"Cleaned up {deleted} test authors"
        }
        
    except Exception as e:
        await conn.close()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
