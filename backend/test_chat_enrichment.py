"""
Unit Tests for Chat Handler Source Enrichment
Feature: chat-metadata-enrichment-fix

Tests the ChatHandler._enrich_source_metadata() method for:
- Successful enrichment with multiple authors (Task 2.1)
- Requirements: 1.4, 2.1, 2.2, 2.3
"""

import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Import the chat handler
try:
    from chat_handler import ChatHandler
except ImportError:
    from backend.chat_handler import ChatHandler


# =====================================================
# Test Fixtures
# =====================================================

@pytest.fixture
def mock_vector_store():
    """Create a mock vector store"""
    return MagicMock()


@pytest.fixture
def chat_handler(mock_vector_store):
    """Create a ChatHandler instance with mocked vector store"""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        handler = ChatHandler(mock_vector_store)
        return handler


# =====================================================
# Task 2.1: Unit Test for Successful Enrichment with Multiple Authors
# =====================================================

@pytest.mark.asyncio
async def test_enrich_source_metadata_with_multiple_authors(chat_handler):
    """
    Test successful enrichment with 3 authors in specific order
    
    Requirements tested:
    - 1.4: WHEN author records are found in the document_authors table 
           THEN the system SHALL join with the authors table to retrieve 
           author names and website URLs
    - 2.1: WHEN a source document has a document_type of "book" and an mc_press_url 
           THEN the system SHALL include the mc_press_url in the enriched metadata
    - 2.2: WHEN a source document has a document_type of "article" and an article_url 
           THEN the system SHALL include the article_url in the enriched metadata
    - 2.3: WHEN enriched metadata is returned to the frontend 
           THEN the system SHALL include the document_type field
    """
    # Arrange: Mock database connection and responses
    mock_conn = AsyncMock()
    
    # Mock book data response
    mock_book_data = {
        'id': 123,
        'filename': 'test-book.pdf',
        'title': 'Test Book Title',
        'legacy_author': 'Legacy Author Name',
        'mc_press_url': 'https://mcpress.com/test-book',
        'article_url': None,
        'document_type': 'book'
    }
    
    # Mock authors data response (3 authors in specific order)
    mock_authors = [
        {
            'id': 1,
            'name': 'Alice Johnson',
            'site_url': 'https://alice.example.com',
            'author_order': 0
        },
        {
            'id': 2,
            'name': 'Bob Smith',
            'site_url': 'https://bob.example.com',
            'author_order': 1
        },
        {
            'id': 3,
            'name': 'Charlie Davis',
            'site_url': None,
            'author_order': 2
        }
    ]
    
    # Configure mock connection
    mock_conn.fetchrow = AsyncMock(return_value=mock_book_data)
    mock_conn.fetch = AsyncMock(return_value=mock_authors)
    mock_conn.close = AsyncMock()
    
    # Mock asyncpg.connect to return our mock connection
    with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            # Act: Call the enrichment method
            result = await chat_handler._enrich_source_metadata('test-book.pdf')
    
    # Assert: Verify all required fields are present
    assert 'author' in result, "Missing 'author' field in enriched metadata"
    assert 'mc_press_url' in result, "Missing 'mc_press_url' field in enriched metadata"
    assert 'article_url' in result, "Missing 'article_url' field in enriched metadata"
    assert 'document_type' in result, "Missing 'document_type' field in enriched metadata"
    assert 'authors' in result, "Missing 'authors' array in enriched metadata"
    
    # Assert: Verify author field contains all author names
    assert result['author'] == 'Alice Johnson, Bob Smith, Charlie Davis', \
        f"Expected comma-separated author names, got: {result['author']}"
    
    # Assert: Verify mc_press_url is included
    assert result['mc_press_url'] == 'https://mcpress.com/test-book', \
        f"Expected mc_press_url to be included, got: {result['mc_press_url']}"
    
    # Assert: Verify article_url is None (book type)
    assert result['article_url'] is None, \
        f"Expected article_url to be None for book type, got: {result['article_url']}"
    
    # Assert: Verify document_type is 'book'
    assert result['document_type'] == 'book', \
        f"Expected document_type to be 'book', got: {result['document_type']}"
    
    # Assert: Verify authors array contains all 3 author objects
    assert len(result['authors']) == 3, \
        f"Expected 3 authors in array, got: {len(result['authors'])}"
    
    # Assert: Verify first author details
    assert result['authors'][0]['id'] == 1
    assert result['authors'][0]['name'] == 'Alice Johnson'
    assert result['authors'][0]['site_url'] == 'https://alice.example.com'
    assert result['authors'][0]['order'] == 0
    
    # Assert: Verify second author details
    assert result['authors'][1]['id'] == 2
    assert result['authors'][1]['name'] == 'Bob Smith'
    assert result['authors'][1]['site_url'] == 'https://bob.example.com'
    assert result['authors'][1]['order'] == 1
    
    # Assert: Verify third author details (no site_url)
    assert result['authors'][2]['id'] == 3
    assert result['authors'][2]['name'] == 'Charlie Davis'
    assert result['authors'][2]['site_url'] is None
    assert result['authors'][2]['order'] == 2
    
    # Assert: Verify database queries were called correctly
    mock_conn.fetchrow.assert_called_once()
    mock_conn.fetch.assert_called_once()
    
    # Verify the SQL query used book_id (not document_id)
    fetch_call_args = mock_conn.fetch.call_args
    sql_query = fetch_call_args[0][0]
    assert 'da.book_id' in sql_query, "SQL query should use 'da.book_id'"
    assert 'da.document_id' not in sql_query, "SQL query should NOT use 'da.document_id'"
    
    print("✅ Test passed: Enrichment with multiple authors works correctly")


@pytest.mark.asyncio
async def test_enrich_source_metadata_article_with_url(chat_handler):
    """
    Test successful enrichment for article type with article_url
    
    Requirements tested:
    - 2.2: WHEN a source document has a document_type of "article" and an article_url 
           THEN the system SHALL include the article_url in the enriched metadata
    - 2.3: WHEN enriched metadata is returned to the frontend 
           THEN the system SHALL include the document_type field
    """
    # Arrange: Mock database connection and responses
    mock_conn = AsyncMock()
    
    # Mock article data response
    mock_book_data = {
        'id': 456,
        'filename': 'test-article.pdf',
        'title': 'Test Article Title',
        'legacy_author': 'Article Author',
        'mc_press_url': '',
        'article_url': 'https://mcpress.com/articles/test-article',
        'document_type': 'article'
    }
    
    # Mock single author for article
    mock_authors = [
        {
            'id': 10,
            'name': 'Article Author',
            'site_url': 'https://author.example.com',
            'author_order': 0
        }
    ]
    
    # Configure mock connection
    mock_conn.fetchrow = AsyncMock(return_value=mock_book_data)
    mock_conn.fetch = AsyncMock(return_value=mock_authors)
    mock_conn.close = AsyncMock()
    
    # Mock asyncpg.connect to return our mock connection
    with patch('asyncpg.connect', AsyncMock(return_value=mock_conn)):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            # Act: Call the enrichment method
            result = await chat_handler._enrich_source_metadata('test-article.pdf')
    
    # Assert: Verify article_url is included
    assert result['article_url'] == 'https://mcpress.com/articles/test-article', \
        f"Expected article_url to be included, got: {result['article_url']}"
    
    # Assert: Verify document_type is 'article'
    assert result['document_type'] == 'article', \
        f"Expected document_type to be 'article', got: {result['document_type']}"
    
    # Assert: Verify mc_press_url is empty for article
    assert result['mc_press_url'] == '', \
        f"Expected mc_press_url to be empty for article, got: {result['mc_press_url']}"
    
    print("✅ Test passed: Article enrichment with article_url works correctly")


# =====================================================
# Run tests
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
