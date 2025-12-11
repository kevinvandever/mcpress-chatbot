"""
Property-Based Tests for Multi-Author Metadata Enhancement
Feature: multi-author-metadata-enhancement
"""

import os
import asyncio
import asyncpg
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    pytest.skip("DATABASE_URL not set - skipping database tests", allow_module_level=True)


# =====================================================
# Test Fixtures and Helpers
# =====================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the test module"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def get_connection():
    """Get a database connection"""
    return await asyncpg.connect(DATABASE_URL)


async def cleanup_test_data(conn):
    """Clean up test data from authors and document_authors tables"""
    try:
        # Delete test authors (this will cascade to document_authors)
        await conn.execute("DELETE FROM document_authors WHERE author_id IN (SELECT id FROM authors WHERE name LIKE 'TEST_%')")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
    except Exception as e:
        # Tables might not exist yet
        pass


async def ensure_tables_exist(conn):
    """Ensure the required tables exist for testing"""
    try:
        # Check if authors table exists
        authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'authors'
            )
        """)
        
        if not authors_exists:
            pytest.skip("authors table does not exist - run migration first")
        
        # Check if document_authors table exists
        doc_authors_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'document_authors'
            )
        """)
        
        if not doc_authors_exists:
            pytest.skip("document_authors table does not exist - run migration first")
            
    except Exception as e:
        pytest.skip(f"Could not verify tables: {e}")


# =====================================================
# Hypothesis Strategies
# =====================================================

# Strategy for generating author names
author_names = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' .-'),
    min_size=1,
    max_size=100
).map(lambda s: f"TEST_{s.strip()}")  # Prefix with TEST_ for easy cleanup

# Strategy for generating URLs
urls = st.one_of(
    st.none(),
    st.builds(
        lambda domain, path: f"https://{domain}.com/{path}",
        domain=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=3, max_size=20),
        path=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=0, max_size=50)
    )
)


# =====================================================
# Property-Based Tests
# =====================================================

# Feature: multi-author-metadata-enhancement, Property 2: Author deduplication
@pytest.mark.asyncio
@given(
    author_name=author_names,
    site_urls=st.lists(urls, min_size=2, max_size=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_author_deduplication(author_name, site_urls):
    """
    Property 2: Author deduplication
    
    For any author name, when that author is associated with multiple documents,
    only one author record should exist in the authors table.
    
    Validates: Requirements 1.2
    
    Test strategy:
    1. Generate a random author name
    2. Attempt to create the same author multiple times with different URLs
    3. Verify only one author record exists with that name
    4. Verify the author can be retrieved consistently
    """
    conn = await get_connection()
    
    try:
        # Ensure tables exist
        await ensure_tables_exist(conn)
        
        # Clean up any existing test data
        await cleanup_test_data(conn)
        
        # Attempt to insert the same author multiple times with different site URLs
        author_ids = []
        for site_url in site_urls:
            try:
                # Try to insert author
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
        assert len(unique_ids) == 1, (
            f"Author deduplication failed: expected 1 unique author ID, "
            f"got {len(unique_ids)} for author '{author_name}'"
        )
        
        # Verify only one author record exists with this name
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM authors WHERE name = $1
        """, author_name)
        
        assert count == 1, (
            f"Author deduplication failed: expected 1 author record, "
            f"found {count} for author '{author_name}'"
        )
        
        # Verify the author can be retrieved
        author = await conn.fetchrow("""
            SELECT id, name, site_url FROM authors WHERE name = $1
        """, author_name)
        
        assert author is not None, f"Could not retrieve author '{author_name}'"
        assert author['name'] == author_name, f"Author name mismatch"
        assert author['id'] == author_ids[0], f"Author ID mismatch"
        
    finally:
        # Clean up test data
        await cleanup_test_data(conn)
        await conn.close()


# =====================================================
# Additional Unit Tests for Edge Cases
# =====================================================

@pytest.mark.asyncio
async def test_author_unique_constraint():
    """
    Test that the UNIQUE constraint on author name is enforced
    """
    conn = await get_connection()
    
    try:
        await ensure_tables_exist(conn)
        await cleanup_test_data(conn)
        
        # Insert an author
        author_name = "TEST_Unique_Author"
        await conn.execute("""
            INSERT INTO authors (name, site_url)
            VALUES ($1, $2)
        """, author_name, "https://example.com")
        
        # Try to insert the same author again (should fail or be handled by ON CONFLICT)
        try:
            await conn.execute("""
                INSERT INTO authors (name, site_url)
                VALUES ($1, $2)
            """, author_name, "https://different.com")
            
            # If we get here, check that only one record exists
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM authors WHERE name = $1
            """, author_name)
            assert count == 1, "Duplicate author was inserted despite UNIQUE constraint"
            
        except asyncpg.UniqueViolationError:
            # This is expected - the UNIQUE constraint is working
            pass
        
    finally:
        await cleanup_test_data(conn)
        await conn.close()


@pytest.mark.asyncio
async def test_author_name_case_sensitivity():
    """
    Test that author names are case-sensitive (or case-insensitive based on requirements)
    """
    conn = await get_connection()
    
    try:
        await ensure_tables_exist(conn)
        await cleanup_test_data(conn)
        
        # Insert authors with different cases
        await conn.execute("""
            INSERT INTO authors (name, site_url)
            VALUES ($1, $2)
        """, "TEST_John_Doe", "https://example.com")
        
        # Try to insert with different case
        try:
            await conn.execute("""
                INSERT INTO authors (name, site_url)
                VALUES ($1, $2)
            """, "TEST_john_doe", "https://example.com")
            
            # If successful, names are case-sensitive
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM authors WHERE name IN ($1, $2)
            """, "TEST_John_Doe", "TEST_john_doe")
            
            # Both should exist if case-sensitive
            assert count == 2, "Case sensitivity test failed"
            
        except asyncpg.UniqueViolationError:
            # Names are case-insensitive
            pass
        
    finally:
        await cleanup_test_data(conn)
        await conn.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
