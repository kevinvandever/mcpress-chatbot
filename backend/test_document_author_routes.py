"""
Property-Based Tests for Document-Author Relationship API
Feature: multi-author-metadata-enhancement

Tests the document-author relationship endpoints using property-based testing
with Hypothesis to verify correctness properties across many inputs.
"""

import os
import asyncio
import pytest
import pytest_asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import List, Dict, Any
import asyncpg

# Import services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService


# =====================================================
# Test Fixtures and Setup
# =====================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def database_url():
    """Get database URL from environment"""
    url = os.getenv('DATABASE_URL')
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest_asyncio.fixture(scope="module")
async def author_service(database_url):
    """Create and initialize author service"""
    service = AuthorService(database_url)
    await service.init_database()
    yield service
    await service.close()


@pytest_asyncio.fixture(scope="module")
async def doc_author_service(database_url):
    """Create and initialize document-author service"""
    service = DocumentAuthorService(database_url)
    await service.init_database()
    yield service
    await service.close()


@pytest_asyncio.fixture
async def clean_test_data(database_url):
    """Clean up test data before and after each test"""
    # Setup: Clean before test
    conn = await asyncpg.connect(database_url)
    try:
        # Delete test documents and authors
        await conn.execute("""
            DELETE FROM books WHERE filename LIKE 'test_%'
        """)
        await conn.execute("""
            DELETE FROM authors WHERE name LIKE 'Test Author%'
        """)
    finally:
        await conn.close()
    
    yield
    
    # Teardown: Clean after test
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("""
            DELETE FROM books WHERE filename LIKE 'test_%'
        """)
        await conn.execute("""
            DELETE FROM authors WHERE name LIKE 'Test Author%'
        """)
    finally:
        await conn.close()


# =====================================================
# Helper Functions
# =====================================================

async def create_test_document(database_url: str, filename: str, title: str) -> int:
    """Create a test document and return its ID"""
    conn = await asyncpg.connect(database_url)
    try:
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, total_pages, processed_at)
            VALUES ($1, $2, 'book', 100, NOW())
            RETURNING id
        """, filename, title)
        return doc_id
    finally:
        await conn.close()


async def get_document_authors(database_url: str, doc_id: int) -> List[Dict[str, Any]]:
    """Get all authors for a document in order"""
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT a.id, a.name, a.site_url, da.author_order
            FROM authors a
            INNER JOIN document_authors da ON a.id = da.author_id
            WHERE da.book_id = $1
            ORDER BY da.author_order
        """, doc_id)
        
        return [
            {
                'id': row['id'],
                'name': row['name'],
                'site_url': row['site_url'],
                'order': row['author_order']
            }
            for row in rows
        ]
    finally:
        await conn.close()


async def get_document_type(database_url: str, doc_id: int) -> str:
    """Get document type"""
    conn = await asyncpg.connect(database_url)
    try:
        doc_type = await conn.fetchval("""
            SELECT document_type FROM books WHERE id = $1
        """, doc_id)
        return doc_type
    finally:
        await conn.close()


# =====================================================
# Hypothesis Strategies
# =====================================================

# Strategy for generating author names
author_names = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '),
    min_size=3,
    max_size=50
).map(lambda s: f"Test Author {s.strip()}")

# Strategy for generating lists of unique author names
author_name_lists = st.lists(
    author_names,
    min_size=1,
    max_size=5,
    unique=True
)


# =====================================================
# Property-Based Tests
# =====================================================

# Feature: multi-author-metadata-enhancement, Property 1: Multiple author association
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(author_names=author_name_lists)
async def test_property_multiple_author_association(
    author_names: List[str],
    author_service,
    doc_author_service,
    database_url,
    clean_test_data
):
    """
    Property 1: Multiple author association
    
    For any document and any list of authors, when associating those authors
    with the document, all authors should be retrievable from the document
    in the same order.
    
    **Validates: Requirements 1.1, 1.3**
    """
    # Create a test document
    doc_id = await create_test_document(
        database_url,
        f"test_doc_{hash(tuple(author_names))}.pdf",
        f"Test Document {hash(tuple(author_names))}"
    )
    
    try:
        # Create or get authors and associate them with the document
        author_ids = []
        for order, author_name in enumerate(author_names):
            author_id = await author_service.get_or_create_author(author_name)
            await doc_author_service.add_author_to_document(doc_id, author_id, order)
            author_ids.append(author_id)
        
        # Retrieve authors from the document
        retrieved_authors = await get_document_authors(database_url, doc_id)
        
        # Property: All authors should be retrievable in the same order
        assert len(retrieved_authors) == len(author_names), \
            f"Expected {len(author_names)} authors, got {len(retrieved_authors)}"
        
        for i, (expected_name, retrieved_author) in enumerate(zip(author_names, retrieved_authors)):
            assert retrieved_author['name'] == expected_name, \
                f"Author at position {i}: expected '{expected_name}', got '{retrieved_author['name']}'"
            assert retrieved_author['order'] == i, \
                f"Author order at position {i}: expected {i}, got {retrieved_author['order']}"
            assert retrieved_author['id'] == author_ids[i], \
                f"Author ID at position {i}: expected {author_ids[i]}, got {retrieved_author['id']}"
    
    finally:
        # Cleanup: Delete the test document
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
        finally:
            await conn.close()


# Feature: multi-author-metadata-enhancement, Property 7: Document type in responses
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    doc_type=st.sampled_from(['book', 'article']),
    author_name=author_names
)
async def test_property_document_type_in_responses(
    doc_type: str,
    author_name: str,
    author_service,
    doc_author_service,
    database_url,
    clean_test_data
):
    """
    Property 7: Document type in responses
    
    For any document retrieval, the response should include the document_type field.
    
    **Validates: Requirements 2.4**
    """
    # Create a test document with specific type
    conn = await asyncpg.connect(database_url)
    try:
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, total_pages, processed_at)
            VALUES ($1, $2, $3, 100, NOW())
            RETURNING id
        """, f"test_doc_{hash(author_name)}.pdf", f"Test Document {hash(author_name)}", doc_type)
    finally:
        await conn.close()
    
    try:
        # Add an author to the document
        author_id = await author_service.get_or_create_author(author_name)
        await doc_author_service.add_author_to_document(doc_id, author_id, 0)
        
        # Retrieve the document type
        retrieved_type = await get_document_type(database_url, doc_id)
        
        # Property: Document type should be present and match what was set
        assert retrieved_type is not None, "Document type should not be None"
        assert retrieved_type == doc_type, \
            f"Expected document type '{doc_type}', got '{retrieved_type}'"
    
    finally:
        # Cleanup: Delete the test document
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
        finally:
            await conn.close()


# =====================================================
# Additional Edge Case Tests
# =====================================================

@pytest.mark.asyncio
async def test_duplicate_author_prevention(
    author_service,
    doc_author_service,
    database_url,
    clean_test_data
):
    """
    Test that adding the same author twice to a document is prevented.
    
    This validates the duplicate prevention requirement.
    """
    # Create a test document
    doc_id = await create_test_document(
        database_url,
        "test_duplicate.pdf",
        "Test Duplicate Prevention"
    )
    
    try:
        # Create an author
        author_id = await author_service.get_or_create_author("Test Author Duplicate")
        
        # Add author to document (should succeed)
        await doc_author_service.add_author_to_document(doc_id, author_id, 0)
        
        # Try to add the same author again (should fail)
        with pytest.raises(ValueError, match="already associated"):
            await doc_author_service.add_author_to_document(doc_id, author_id, 1)
        
        # Verify only one association exists
        authors = await get_document_authors(database_url, doc_id)
        assert len(authors) == 1, f"Expected 1 author, got {len(authors)}"
    
    finally:
        # Cleanup
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_last_author_removal_prevention(
    author_service,
    doc_author_service,
    database_url,
    clean_test_data
):
    """
    Test that removing the last author from a document is prevented.
    
    This validates the requirement that documents must have at least one author.
    """
    # Create a test document
    doc_id = await create_test_document(
        database_url,
        "test_last_author.pdf",
        "Test Last Author Prevention"
    )
    
    try:
        # Create an author and add to document
        author_id = await author_service.get_or_create_author("Test Author Last")
        await doc_author_service.add_author_to_document(doc_id, author_id, 0)
        
        # Try to remove the only author (should fail)
        with pytest.raises(ValueError, match="at least one author"):
            await doc_author_service.remove_author_from_document(doc_id, author_id)
        
        # Verify author still exists
        authors = await get_document_authors(database_url, doc_id)
        assert len(authors) == 1, f"Expected 1 author, got {len(authors)}"
    
    finally:
        # Cleanup
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
        finally:
            await conn.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
