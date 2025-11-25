"""
Property-Based Tests for DocumentAuthorService
Feature: multi-author-metadata-enhancement

Tests the DocumentAuthorService implementation for:
- Duplicate prevention (Property 3)
- Last author validation (Property 16)
- Cascade deletion (Property 4)
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
    from document_author_service import DocumentAuthorService
    from author_service import AuthorService
except ImportError:
    from backend.document_author_service import DocumentAuthorService
    from backend.author_service import AuthorService

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


async def cleanup_test_data():
    """Clean up test data from all tables"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Delete test document-author associations
        await conn.execute("""
            DELETE FROM document_authors 
            WHERE book_id IN (SELECT id FROM books WHERE filename LIKE 'TEST_%')
        """)
        # Delete test books
        await conn.execute("DELETE FROM books WHERE filename LIKE 'TEST_%'")
        # Delete test authors
        await conn.execute("DELETE FROM authors WHERE name LIKE 'TEST_%'")
    except Exception as e:
        pass
    finally:
        await conn.close()


async def ensure_tables_exist():
    """Ensure the required tables exist for testing"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        tables = ['authors', 'document_authors', 'books']
        for table in tables:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """)
            if not exists:
                pytest.skip(f"{table} table does not exist - run migration first")
    except Exception as e:
        pytest.skip(f"Could not verify tables: {e}")
    finally:
        await conn.close()


async def create_test_book(conn, filename: str, title: str) -> int:
    """Helper to create a test book"""
    # Insert minimal book record - only required fields
    book_id = await conn.fetchval("""
        INSERT INTO books (filename, title, document_type)
        VALUES ($1, $2, 'book')
        RETURNING id
    """, filename, title)
    return book_id


async def create_test_author(author_service: AuthorService, name: str) -> int:
    """Helper to create a test author"""
    return await author_service.get_or_create_author(name)


# =====================================================
# Hypothesis Strategies
# =====================================================

# Strategy for generating test book filenames
book_filenames = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'),
    min_size=5,
    max_size=50
).map(lambda s: f"TEST_{s.strip()}.pdf")

# Strategy for generating test author names
author_names = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' .-'),
    min_size=1,
    max_size=100
).map(lambda s: f"TEST_{s.strip()}")


# =====================================================
# Property-Based Tests
# =====================================================

# Feature: multi-author-metadata-enhancement, Property 1: Multiple author association
@pytest.mark.asyncio
@given(
    book_filename=book_filenames,
    author_names_list=st.lists(
        author_names,
        min_size=1,
        max_size=10,
        unique=True  # Ensure all author names are unique
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_multiple_author_association(book_filename, author_names_list):
    """
    Property 1: Multiple author association
    
    For any document and any list of authors, when associating those authors with 
    the document, all authors should be retrievable from the document in the same order.
    
    Validates: Requirements 1.1, 1.3
    
    Test strategy:
    1. Generate a random list of unique author names
    2. Create a test document
    3. Create authors and associate them with the document in order
    4. Retrieve the authors for the document
    5. Verify all authors are present
    6. Verify the order matches the original order
    """
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create test book
        book_id = await create_test_book(conn, book_filename, "Test Book")
        
        # Create authors and associate them with the document in order
        expected_author_ids = []
        for order, author_name in enumerate(author_names_list):
            author_id = await create_test_author(author_service, author_name)
            await doc_service.add_author_to_document(book_id, author_id, order)
            expected_author_ids.append(author_id)
        
        # Retrieve authors for the document
        retrieved_authors = await author_service.get_authors_for_document(book_id)
        
        # Property: All authors should be retrievable
        assert len(retrieved_authors) == len(author_names_list), (
            f"Expected {len(author_names_list)} authors, "
            f"but retrieved {len(retrieved_authors)}"
        )
        
        # Property: Authors should be in the same order
        retrieved_author_ids = [author['id'] for author in retrieved_authors]
        assert retrieved_author_ids == expected_author_ids, (
            f"Author order mismatch: expected {expected_author_ids}, "
            f"got {retrieved_author_ids}"
        )
        
        # Verify each author's order field matches
        for i, author in enumerate(retrieved_authors):
            assert author['order'] == i, (
                f"Author at position {i} has incorrect order field: "
                f"expected {i}, got {author['order']}"
            )
        
        # Verify author names match
        retrieved_names = [author['name'] for author in retrieved_authors]
        assert retrieved_names == author_names_list, (
            f"Author names mismatch: expected {author_names_list}, "
            f"got {retrieved_names}"
        )
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 3: No duplicate author associations
@pytest.mark.asyncio
@given(
    book_filename=book_filenames,
    author_name=author_names,
    num_attempts=st.integers(min_value=2, max_value=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_no_duplicate_author_associations(book_filename, author_name, num_attempts):
    """
    Property 3: No duplicate author associations
    
    For any document and author, attempting to associate the same author with 
    the document multiple times should result in only one association record.
    
    Validates: Requirements 1.4
    
    Test strategy:
    1. Create a test document and author
    2. Attempt to add the same author to the document multiple times
    3. Verify only the first attempt succeeds
    4. Verify subsequent attempts raise ValueError
    5. Verify only one association exists in database
    """
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create test book and author
        book_id = await create_test_book(conn, book_filename, "Test Book")
        author_id = await create_test_author(author_service, author_name)
        
        # First attempt - should succeed
        await doc_service.add_author_to_document(book_id, author_id)
        
        # Subsequent attempts - should fail with ValueError
        for attempt in range(1, num_attempts):
            with pytest.raises(ValueError, match="already associated"):
                await doc_service.add_author_to_document(book_id, author_id)
        
        # Property: Only one association should exist
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM document_authors 
            WHERE book_id = $1 AND author_id = $2
        """, book_id, author_id)
        
        assert count == 1, (
            f"Duplicate prevention failed: expected 1 association, "
            f"found {count} for book {book_id} and author {author_id}"
        )
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 16: Require at least one author
@pytest.mark.asyncio
@given(
    book_filename=book_filenames,
    author_name=author_names
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_require_at_least_one_author(book_filename, author_name):
    """
    Property 16: Require at least one author
    
    For any document with exactly one author, attempting to remove that author 
    should be rejected.
    
    Validates: Requirements 5.7
    
    Test strategy:
    1. Create a test document with one author
    2. Attempt to remove the only author
    3. Verify the removal is rejected with ValueError
    4. Verify the author association still exists
    """
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create test book with one author
        book_id = await create_test_book(conn, book_filename, "Test Book")
        author_id = await create_test_author(author_service, author_name)
        await doc_service.add_author_to_document(book_id, author_id)
        
        # Verify we have exactly one author
        count_before = await doc_service.get_author_count_for_document(book_id)
        assert count_before == 1, "Should have exactly one author"
        
        # Property: Attempting to remove the last author should fail
        with pytest.raises(ValueError, match="Cannot remove last author"):
            await doc_service.remove_author_from_document(book_id, author_id)
        
        # Verify the author is still associated
        count_after = await doc_service.get_author_count_for_document(book_id)
        assert count_after == 1, (
            f"Last author validation failed: author was removed despite being the last one"
        )
        
        # Verify the association still exists
        association_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM document_authors 
                WHERE book_id = $1 AND author_id = $2
            )
        """, book_id, author_id)
        
        assert association_exists, "Author association should still exist"
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


# Feature: multi-author-metadata-enhancement, Property 4: Cascade deletion preserves shared authors
@pytest.mark.asyncio
@given(
    book1_filename=book_filenames,
    book2_filename=book_filenames,
    author_name=author_names
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_cascade_deletion_preserves_shared_authors(book1_filename, book2_filename, author_name):
    """
    Property 4: Cascade deletion preserves shared authors
    
    For any author associated with multiple documents, when deleting one document,
    the author record should still exist and remain associated with the other documents.
    
    Validates: Requirements 1.5
    
    Test strategy:
    1. Create two test documents
    2. Create one author and associate with both documents
    3. Delete one document
    4. Verify the author record still exists
    5. Verify the author is still associated with the remaining document
    6. Verify the association with the deleted document is removed
    """
    # Ensure filenames are different
    if book1_filename == book2_filename:
        book2_filename = f"ALT_{book2_filename}"
    
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create two test books
        book1_id = await create_test_book(conn, book1_filename, "Test Book 1")
        book2_id = await create_test_book(conn, book2_filename, "Test Book 2")
        
        # Create one author and associate with both books
        author_id = await create_test_author(author_service, author_name)
        await doc_service.add_author_to_document(book1_id, author_id)
        await doc_service.add_author_to_document(book2_id, author_id)
        
        # Verify author is associated with both documents
        docs_before = await doc_service.get_documents_by_author(author_id)
        assert len(docs_before) == 2, "Author should be associated with 2 documents"
        
        # Delete one document (CASCADE should remove the association)
        await conn.execute("DELETE FROM books WHERE id = $1", book1_id)
        
        # Verify cascade deletion behavior
        verification = await doc_service.verify_cascade_deletion(author_id, book1_id)
        
        # Property: Author record should still exist
        assert verification['author_still_exists'], (
            "Author record should still exist after deleting one document"
        )
        
        # Property: Association with deleted document should be removed
        assert verification['association_removed'], (
            "Association with deleted document should be removed"
        )
        
        # Property: Author should still be associated with remaining document
        assert verification['remaining_document_count'] == 1, (
            f"Author should have 1 remaining document, "
            f"found {verification['remaining_document_count']}"
        )
        
        # Verify we can still retrieve the remaining document
        docs_after = await doc_service.get_documents_by_author(author_id)
        assert len(docs_after) == 1, "Author should be associated with 1 document"
        assert docs_after[0]['id'] == book2_id, "Should be associated with book2"
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


# =====================================================
# Additional Unit Tests
# =====================================================

@pytest.mark.asyncio
async def test_add_author_to_nonexistent_document():
    """Test that adding author to non-existent document fails"""
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    try:
        # Create an author
        author_id = await create_test_author(author_service, "TEST_Author")
        
        # Try to add to non-existent document
        with pytest.raises(ValueError, match="Document.*not found"):
            await doc_service.add_author_to_document(999999, author_id)
            
    finally:
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_reorder_authors():
    """Test reordering authors for a document"""
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create a book with 3 authors
        book_id = await create_test_book(conn, "TEST_reorder.pdf", "Test Book")
        author1_id = await create_test_author(author_service, "TEST_Author_1")
        author2_id = await create_test_author(author_service, "TEST_Author_2")
        author3_id = await create_test_author(author_service, "TEST_Author_3")
        
        await doc_service.add_author_to_document(book_id, author1_id, 0)
        await doc_service.add_author_to_document(book_id, author2_id, 1)
        await doc_service.add_author_to_document(book_id, author3_id, 2)
        
        # Reorder: 3, 1, 2
        new_order = [author3_id, author1_id, author2_id]
        await doc_service.reorder_authors(book_id, new_order)
        
        # Verify new order
        rows = await conn.fetch("""
            SELECT author_id, author_order 
            FROM document_authors 
            WHERE book_id = $1 
            ORDER BY author_order
        """, book_id)
        
        assert len(rows) == 3
        assert rows[0]['author_id'] == author3_id and rows[0]['author_order'] == 0
        assert rows[1]['author_id'] == author1_id and rows[1]['author_order'] == 1
        assert rows[2]['author_id'] == author2_id and rows[2]['author_order'] == 2
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_get_documents_by_author():
    """Test finding documents by author"""
    await ensure_tables_exist()
    await cleanup_test_data()
    
    doc_service = DocumentAuthorService(DATABASE_URL)
    author_service = AuthorService(DATABASE_URL)
    await doc_service.init_database()
    await author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create an author and 3 books
        author_id = await create_test_author(author_service, "TEST_Prolific_Author")
        book1_id = await create_test_book(conn, "TEST_book1.pdf", "Book 1")
        book2_id = await create_test_book(conn, "TEST_book2.pdf", "Book 2")
        book3_id = await create_test_book(conn, "TEST_book3.pdf", "Book 3")
        
        # Associate author with all books
        await doc_service.add_author_to_document(book1_id, author_id)
        await doc_service.add_author_to_document(book2_id, author_id)
        await doc_service.add_author_to_document(book3_id, author_id)
        
        # Get documents by author
        docs = await doc_service.get_documents_by_author(author_id)
        
        assert len(docs) == 3, f"Expected 3 documents, got {len(docs)}"
        doc_ids = [d['id'] for d in docs]
        assert book1_id in doc_ids
        assert book2_id in doc_ids
        assert book3_id in doc_ids
        
    finally:
        await conn.close()
        await doc_service.close()
        await author_service.close()
        await cleanup_test_data()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
