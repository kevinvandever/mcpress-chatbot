"""
Property-Based Tests for Admin Documents Endpoints
Feature: multi-author-metadata-enhancement

Tests correctness properties for document type validation and URL fields.
"""

import pytest
import os
from hypothesis import given, strategies as st, settings
from typing import Optional

# Import services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService


# =====================================================
# Test Fixtures
# =====================================================

@pytest.fixture(scope="module")
def database_url():
    """Get database URL from environment"""
    url = os.getenv('DATABASE_URL')
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture(scope="module")
async def author_service(database_url):
    """Create author service instance"""
    service = AuthorService(database_url)
    await service.init_database()
    yield service
    await service.close()


@pytest.fixture(scope="module")
async def doc_author_service(database_url):
    """Create document-author service instance"""
    service = DocumentAuthorService(database_url)
    await service.init_database()
    yield service
    await service.close()


@pytest.fixture
async def test_document(database_url):
    """Create a test document for property tests"""
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Create a test document with valid document_type
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, total_pages)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, 'test_doc.pdf', 'Test Document', 'book', 100)
        
        yield doc_id
        
        # Cleanup
        await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
    finally:
        await conn.close()


# =====================================================
# Hypothesis Strategies
# =====================================================

# Valid document types
valid_document_types = st.sampled_from(['book', 'article'])

# Invalid document types (anything that's not 'book' or 'article')
invalid_document_types = st.text(min_size=1, max_size=50).filter(
    lambda x: x not in ['book', 'article']
)

# Valid URLs
valid_urls = st.sampled_from([
    'https://example.com',
    'http://test.org',
    'https://mcpress.com/books/123',
    'http://localhost:8000',
    'https://sub.domain.com/path?query=value'
])

# Optional URLs (can be None or valid URL)
optional_urls = st.one_of(st.none(), valid_urls)


# =====================================================
# Property 5: Document type validation
# Feature: multi-author-metadata-enhancement, Property 5: Document type validation
# Validates: Requirements 2.1
# =====================================================

@pytest.mark.asyncio
@settings(max_examples=100)
@given(doc_type=valid_document_types)
async def test_property_5_valid_document_types_accepted(
    doc_type: str,
    database_url
):
    """
    Property 5: Document type validation
    
    For any document creation attempt with a valid type ('book' or 'article'),
    the document should be created successfully.
    
    Validates: Requirements 2.1
    """
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Try to create a document with the given type
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, total_pages)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, f'test_{doc_type}.pdf', f'Test {doc_type}', doc_type, 100)
        
        # Verify it was created
        assert doc_id is not None
        
        # Verify the type was stored correctly
        stored_type = await conn.fetchval("""
            SELECT document_type FROM books WHERE id = $1
        """, doc_id)
        
        assert stored_type == doc_type
        
        # Cleanup
        await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
    finally:
        await conn.close()


@pytest.mark.asyncio
@settings(max_examples=100)
@given(doc_type=invalid_document_types)
async def test_property_5_invalid_document_types_rejected(
    doc_type: str,
    database_url
):
    """
    Property 5: Document type validation (negative test)
    
    For any document creation attempt with an invalid type (not 'book' or 'article'),
    the operation should be rejected with a constraint violation.
    
    Validates: Requirements 2.1
    """
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Try to create a document with an invalid type
        # This should raise a check constraint violation
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.fetchval("""
                INSERT INTO books (filename, title, document_type, total_pages)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, f'test_invalid.pdf', 'Test Invalid', doc_type, 100)
    finally:
        await conn.close()


# =====================================================
# Property 6: Type-specific URL fields
# Feature: multi-author-metadata-enhancement, Property 6: Type-specific URL fields
# Validates: Requirements 2.2, 2.3
# =====================================================

@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    book_url=optional_urls,
    article_url=optional_urls
)
async def test_property_6_book_type_stores_book_url(
    book_url: Optional[str],
    article_url: Optional[str],
    database_url
):
    """
    Property 6: Type-specific URL fields (book)
    
    For any document with type 'book', a book purchase URL (mc_press_url) can be stored,
    and an article URL can also be stored (though typically not used for books).
    
    Validates: Requirements 2.2
    """
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Create a book document with URLs
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, mc_press_url, article_url, total_pages)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, 'test_book.pdf', 'Test Book', 'book', book_url, article_url, 100)
        
        assert doc_id is not None
        
        # Verify URLs were stored correctly
        row = await conn.fetchrow("""
            SELECT document_type, mc_press_url, article_url FROM books WHERE id = $1
        """, doc_id)
        
        assert row['document_type'] == 'book'
        assert row['mc_press_url'] == book_url
        assert row['article_url'] == article_url
        
        # Cleanup
        await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
    finally:
        await conn.close()


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    book_url=optional_urls,
    article_url=optional_urls
)
async def test_property_6_article_type_stores_article_url(
    book_url: Optional[str],
    article_url: Optional[str],
    database_url
):
    """
    Property 6: Type-specific URL fields (article)
    
    For any document with type 'article', an article URL can be stored,
    and a book purchase URL can also be stored (though typically not used for articles).
    
    Validates: Requirements 2.3
    """
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Create an article document with URLs
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, mc_press_url, article_url, total_pages)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, 'test_article.pdf', 'Test Article', 'article', book_url, article_url, 100)
        
        assert doc_id is not None
        
        # Verify URLs were stored correctly
        row = await conn.fetchrow("""
            SELECT document_type, mc_press_url, article_url FROM books WHERE id = $1
        """, doc_id)
        
        assert row['document_type'] == 'article'
        assert row['mc_press_url'] == book_url
        assert row['article_url'] == article_url
        
        # Cleanup
        await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
    finally:
        await conn.close()


# =====================================================
# Additional Property Tests
# =====================================================

@pytest.mark.asyncio
@settings(max_examples=50)
@given(
    doc_type=valid_document_types,
    url1=optional_urls,
    url2=optional_urls
)
async def test_property_6_url_fields_independent_of_type(
    doc_type: str,
    url1: Optional[str],
    url2: Optional[str],
    database_url
):
    """
    Property 6: URL fields can be set regardless of document type
    
    For any document type and any combination of URLs, both URL fields
    should be stored correctly. The database doesn't enforce which URL
    field should be used for which type (that's application logic).
    
    Validates: Requirements 2.2, 2.3
    """
    import asyncpg
    
    conn = await asyncpg.connect(database_url)
    try:
        # Create document with both URLs
        doc_id = await conn.fetchval("""
            INSERT INTO books (filename, title, document_type, mc_press_url, article_url, total_pages)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, f'test_{doc_type}.pdf', f'Test {doc_type}', doc_type, url1, url2, 100)
        
        assert doc_id is not None
        
        # Verify all fields were stored correctly
        row = await conn.fetchrow("""
            SELECT document_type, mc_press_url, article_url FROM books WHERE id = $1
        """, doc_id)
        
        assert row['document_type'] == doc_type
        assert row['mc_press_url'] == url1
        assert row['article_url'] == url2
        
        # Cleanup
        await conn.execute("DELETE FROM books WHERE id = $1", doc_id)
    finally:
        await conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
