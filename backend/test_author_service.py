"""
Property-Based Tests for AuthorService
Feature: multi-author-metadata-enhancement

Tests the AuthorService implementation for:
- Author deduplication (Property 2)
- Get or create behavior (Property 14)
"""

import os
import asyncio
import asyncpg
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService

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


@pytest.fixture
async def author_service():
    """Create and initialize an AuthorService instance"""
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    yield service
    await service.close()


async def cleanup_test_data():
    """Clean up test data from authors and document_authors tables"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Delete test authors (this will cascade to document_authors)
        await conn.execute("DELETE FROM document_authors WHERE author_id IN (SELECT id FROM authors WHERE name LIKE 'TEST_%')")
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%')")
    except Exception as e:
        # Tables might not exist yet
        pass
    finally:
        await conn.close()


async def ensure_tables_exist():
    """Ensure the required tables exist for testing"""
    conn = await asyncpg.connect(DATABASE_URL)
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
    finally:
        await conn.close()


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
valid_urls = st.builds(
    lambda domain, path: f"https://{domain}.com/{path}",
    domain=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=3, max_size=20),
    path=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=0, max_size=50)
)

optional_urls = st.one_of(st.none(), valid_urls)


# =====================================================
# Property-Based Tests
# =====================================================

# Feature: multi-author-metadata-enhancement, Property 2: Author deduplication
@pytest.mark.asyncio
@given(
    author_name=author_names,
    site_urls=st.lists(optional_urls, min_size=2, max_size=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_author_deduplication_property(author_name, site_urls):
    """
    Property 2: Author deduplication
    
    For any author name, when that author is associated with multiple documents,
    only one author record should exist in the authors table.
    
    Validates: Requirements 1.2
    
    Test strategy:
    1. Generate a random author name
    2. Call get_or_create_author() multiple times with the same name but different URLs
    3. Verify all calls return the same author ID
    4. Verify only one author record exists with that name in the database
    """
    # Ensure tables exist
    await ensure_tables_exist()
    
    # Clean up any existing test data
    await cleanup_test_data()
    
    # Create service
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        # Call get_or_create_author multiple times with same name
        author_ids = []
        for site_url in site_urls:
            author_id = await service.get_or_create_author(author_name, site_url)
            author_ids.append(author_id)
        
        # Property: All author_ids should be the same (deduplication)
        unique_ids = set(author_ids)
        assert len(unique_ids) == 1, (
            f"Author deduplication failed: expected 1 unique author ID, "
            f"got {len(unique_ids)} for author '{author_name}'. IDs: {author_ids}"
        )
        
        # Verify only one author record exists with this name
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM authors WHERE name = $1
            """, author_name)
            
            assert count == 1, (
                f"Author deduplication failed: expected 1 author record, "
                f"found {count} for author '{author_name}'"
            )
            
            # Verify the author can be retrieved
            author = await service.get_author_by_id(author_ids[0])
            assert author is not None, f"Could not retrieve author '{author_name}'"
            assert author['name'] == author_name, f"Author name mismatch"
            assert author['id'] == author_ids[0], f"Author ID mismatch"
            
        finally:
            await conn.close()
        
    finally:
        await service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 14: Create or reuse author on add
@pytest.mark.asyncio
@given(
    author_name=author_names,
    first_url=optional_urls,
    second_url=optional_urls
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_get_or_create_behavior_property(author_name, first_url, second_url):
    """
    Property 14: Create or reuse author on add
    
    For any author name, when adding it to a document, if the author exists
    it should be reused, otherwise a new author record should be created.
    
    Validates: Requirements 5.3, 5.4
    
    Test strategy:
    1. Generate a random author name
    2. Call get_or_create_author() first time - should create new author
    3. Call get_or_create_author() second time with same name - should reuse existing
    4. Verify both calls return the same author ID
    5. Verify only one author record exists
    """
    # Ensure tables exist
    await ensure_tables_exist()
    
    # Clean up any existing test data
    await cleanup_test_data()
    
    # Create service
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        # First call - should create new author
        first_id = await service.get_or_create_author(author_name, first_url)
        assert first_id is not None, "First call should return an author ID"
        
        # Verify author was created
        author = await service.get_author_by_id(first_id)
        assert author is not None, "Author should exist after creation"
        assert author['name'] == author_name, "Author name should match"
        
        # Second call with same name - should reuse existing author
        second_id = await service.get_or_create_author(author_name, second_url)
        assert second_id is not None, "Second call should return an author ID"
        
        # Property: Both IDs should be the same (reuse existing)
        assert first_id == second_id, (
            f"get_or_create_author should reuse existing author: "
            f"first_id={first_id}, second_id={second_id}"
        )
        
        # Verify only one author record exists
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM authors WHERE name = $1
            """, author_name)
            
            assert count == 1, (
                f"Expected 1 author record, found {count} for author '{author_name}'"
            )
        finally:
            await conn.close()
        
    finally:
        await service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 15: Author updates propagate
@pytest.mark.asyncio
@given(
    author_name=author_names,
    initial_url=optional_urls,
    updated_name=author_names,
    updated_url=optional_urls,
    num_documents=st.integers(min_value=1, max_value=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_author_updates_propagate_property(author_name, initial_url, updated_name, updated_url, num_documents):
    """
    Property 15: Author updates propagate
    
    For any author associated with multiple documents, when updating the author's
    information, all documents should reflect the updated information.
    
    Validates: Requirements 5.6
    
    Test strategy:
    1. Create an author with initial information
    2. Associate the author with multiple documents
    3. Update the author's name and/or URL
    4. Retrieve the author information from each document
    5. Verify all documents reflect the updated author information
    """
    # Ensure tables exist
    await ensure_tables_exist()
    
    # Clean up any existing test data
    await cleanup_test_data()
    
    # Create services
    author_service = AuthorService(DATABASE_URL)
    await author_service.init_database()
    
    doc_author_service = DocumentAuthorService(DATABASE_URL)
    await doc_author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Step 1: Create an author with initial information
        author_id = await author_service.get_or_create_author(author_name, initial_url)
        
        # Step 2: Create test documents and associate them with the author
        document_ids = []
        for i in range(num_documents):
            # Create a test document in the books table
            doc_id = await conn.fetchval("""
                INSERT INTO books (filename, title, total_pages, processed_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                RETURNING id
            """, f"TEST_doc_{i}.pdf", f"TEST Document {i}", 100)
            document_ids.append(doc_id)
            
            # Associate the author with the document
            await doc_author_service.add_author_to_document(doc_id, author_id, order=0)
        
        # Verify initial state
        initial_author = await author_service.get_author_by_id(author_id)
        assert initial_author['name'] == author_name
        assert initial_author['site_url'] == initial_url
        
        # Step 3: Update the author's information
        await author_service.update_author(author_id, name=updated_name, site_url=updated_url)
        
        # Step 4 & 5: Retrieve author information from each document and verify updates
        for doc_id in document_ids:
            # Get authors for this document
            authors = await author_service.get_authors_for_document(doc_id)
            
            # Property: The document should have the author with updated information
            assert len(authors) >= 1, f"Document {doc_id} should have at least one author"
            
            # Find our test author in the list
            test_author = None
            for author in authors:
                if author['id'] == author_id:
                    test_author = author
                    break
            
            assert test_author is not None, (
                f"Author {author_id} should be associated with document {doc_id}"
            )
            
            # Verify the author information is updated
            assert test_author['name'] == updated_name, (
                f"Author name should be updated to '{updated_name}' for document {doc_id}, "
                f"but got '{test_author['name']}'"
            )
            assert test_author['site_url'] == updated_url, (
                f"Author site_url should be updated to '{updated_url}' for document {doc_id}, "
                f"but got '{test_author['site_url']}'"
            )
        
        # Also verify by retrieving the author directly
        updated_author = await author_service.get_author_by_id(author_id)
        assert updated_author['name'] == updated_name, (
            f"Author name should be updated to '{updated_name}'"
        )
        assert updated_author['site_url'] == updated_url, (
            f"Author site_url should be updated to '{updated_url}'"
        )
        
        # Verify document count is correct
        assert updated_author['document_count'] == num_documents, (
            f"Author should be associated with {num_documents} documents, "
            f"but document_count is {updated_author['document_count']}"
        )
        
    finally:
        # Clean up test documents
        for doc_id in document_ids:
            try:
                await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
            except:
                pass
        
        await conn.close()
        await author_service.close()
        await doc_author_service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 10: URL validation
@pytest.mark.asyncio
@given(
    author_name=author_names,
    url=st.one_of(
        # Valid URLs
        st.builds(
            lambda scheme, domain, tld, path: f"{scheme}://{domain}.{tld}{path}",
            scheme=st.sampled_from(['http', 'https']),
            domain=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'), min_size=1, max_size=63).filter(lambda s: s and not s.startswith('-') and not s.endswith('-')),
            tld=st.sampled_from(['com', 'org', 'net', 'edu', 'io', 'co', 'uk', 'de']),
            path=st.one_of(
                st.just(''),
                st.builds(lambda p: f"/{p}", p=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='/-_'), min_size=0, max_size=50))
            )
        ),
        # Invalid URLs - various malformed formats
        st.text(alphabet=st.characters(blacklist_characters=':/'), min_size=1, max_size=50),  # No protocol
        st.builds(lambda s: f"ftp://{s}.com", s=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=3, max_size=20)),  # Wrong protocol
        st.builds(lambda s: f"http://{s}", s=st.text(alphabet='!@#$%^&*()', min_size=1, max_size=10)),  # Invalid characters
        st.just(''),  # Empty string
        st.just('   '),  # Whitespace only
        st.just('not-a-url'),  # Plain text
        st.just('www.example.com'),  # Missing protocol
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_url_validation_property(author_name, url):
    """
    Property 10: URL validation
    
    For any author site URL provided, invalid URL formats should be rejected
    while valid URLs are accepted.
    
    Validates: Requirements 3.2
    
    Test strategy:
    1. Generate random valid and invalid URLs
    2. Attempt to create author with each URL
    3. Valid URLs (http:// or https://) should be accepted
    4. Invalid URLs should raise ValueError
    """
    # Ensure tables exist
    await ensure_tables_exist()
    
    # Clean up any existing test data
    await cleanup_test_data()
    
    # Create service
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        # Determine if URL is valid based on our validation rules
        is_valid = False
        if url and url.strip():
            url_stripped = url.strip()
            # Valid URLs must start with http:// or https:// and have proper format
            if url_stripped.startswith(('http://', 'https://')):
                # Check for basic domain structure
                import re
                url_pattern = re.compile(
                    r'^https?://'
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
                    r'localhost|'
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                    r'(?::\d+)?'
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                is_valid = bool(url_pattern.match(url_stripped))
        
        # Test the property
        if is_valid:
            # Valid URL should be accepted
            author_id = await service.get_or_create_author(author_name, url)
            assert author_id is not None, f"Valid URL should be accepted: {url}"
            
            # Verify the author was created with the URL
            author = await service.get_author_by_id(author_id)
            assert author is not None
            assert author['site_url'] == url.strip()
        else:
            # Invalid URL should raise ValueError
            with pytest.raises(ValueError, match="Invalid URL format"):
                await service.get_or_create_author(author_name, url)
    
    finally:
        await service.close()
        await cleanup_test_data()


# =====================================================
# Additional Unit Tests
# =====================================================

@pytest.mark.asyncio
async def test_author_service_initialization():
    """Test that AuthorService initializes correctly"""
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    assert service.pool is not None, "Database pool should be initialized"
    
    await service.close()
    assert service.pool is None, "Database pool should be closed"


@pytest.mark.asyncio
async def test_get_or_create_author_empty_name():
    """Test that empty author names are rejected"""
    await ensure_tables_exist()
    
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        with pytest.raises(ValueError, match="Author name cannot be empty"):
            await service.get_or_create_author("")
        
        with pytest.raises(ValueError, match="Author name cannot be empty"):
            await service.get_or_create_author("   ")
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_update_author():
    """Test updating author information"""
    await ensure_tables_exist()
    await cleanup_test_data()
    
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        # Create an author
        author_id = await service.get_or_create_author("TEST_Update_Author", "https://example.com")
        
        # Update the author
        await service.update_author(author_id, name="TEST_Updated_Name", site_url="https://updated.com")
        
        # Verify update
        author = await service.get_author_by_id(author_id)
        assert author['name'] == "TEST_Updated_Name"
        assert author['site_url'] == "https://updated.com"
        
    finally:
        await service.close()
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_search_authors():
    """Test author search functionality"""
    await ensure_tables_exist()
    await cleanup_test_data()
    
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        # Create some test authors
        await service.get_or_create_author("TEST_John_Doe", "https://john.com")
        await service.get_or_create_author("TEST_Jane_Doe", "https://jane.com")
        await service.get_or_create_author("TEST_Bob_Smith", "https://bob.com")
        
        # Search for "Doe"
        results = await service.search_authors("Doe")
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        
        names = [r['name'] for r in results]
        assert "TEST_John_Doe" in names
        assert "TEST_Jane_Doe" in names
        
        # Search for "Smith"
        results = await service.search_authors("Smith")
        assert len(results) == 1
        assert results[0]['name'] == "TEST_Bob_Smith"
        
    finally:
        await service.close()
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_invalid_url():
    """Test that invalid URLs are rejected"""
    await ensure_tables_exist()
    
    service = AuthorService(DATABASE_URL)
    await service.init_database()
    
    try:
        with pytest.raises(ValueError, match="Invalid URL format"):
            await service.get_or_create_author("TEST_Invalid_URL", "not-a-url")
        
        with pytest.raises(ValueError, match="Invalid URL format"):
            await service.get_or_create_author("TEST_Invalid_URL", "ftp://example.com")
    finally:
        await service.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
