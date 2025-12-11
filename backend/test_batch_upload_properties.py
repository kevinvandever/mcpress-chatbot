#!/usr/bin/env python3
"""
Property-based tests for batch upload multi-author functionality
Feature: multi-author-metadata-enhancement

Tests Properties 17, 18, 19 for batch upload author creation, parsing, and deduplication
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock
import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite

# Set up test environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

# Import services
from author_service import AuthorService
from document_author_service import DocumentAuthorService


class MockPDFProcessor:
    """Mock PDF processor for testing"""
    
    async def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Mock PDF processing that returns test data"""
        filename = Path(file_path).name
        
        # Extract author from filename for testing
        # Format: "title_by_author.pdf" or "title_by_author1_and_author2.pdf"
        if "_by_" in filename:
            parts = filename.replace(".pdf", "").split("_by_")
            title = parts[0].replace("_", " ")
            author_part = parts[1]
            
            # Parse multiple authors
            if "_and_" in author_part:
                authors = [a.replace("_", " ") for a in author_part.split("_and_")]
                author = "; ".join(authors)  # Use semicolon as separator
            else:
                author = author_part.replace("_", " ")
        else:
            title = filename.replace(".pdf", "").replace("_", " ")
            author = None  # No author metadata
        
        return {
            "chunks": [f"Content chunk 1 from {filename}", f"Content chunk 2 from {filename}"],
            "images": [],
            "code_blocks": [],
            "total_pages": 10,
            "author": author,
            "title": title
        }


class MockVectorStore:
    """Mock vector store for testing"""
    
    def __init__(self):
        self.documents = []
        self.metadata_store = {}
    
    async def add_documents(self, documents: List[str], metadata: Dict[str, Any]):
        """Mock adding documents to vector store"""
        doc_id = len(self.documents)
        self.documents.extend(documents)
        self.metadata_store[doc_id] = metadata
        return doc_id


class MockConnection:
    """Mock database connection for testing"""
    
    def __init__(self):
        self.authors = {}  # name -> id
        self.document_authors = {}  # (book_id, author_id) -> order
        self.books = {}  # id -> metadata
        self.next_author_id = 1
        self.next_book_id = 1
        self.operations = []
    
    async def fetchval(self, query: str, *args):
        """Mock fetchval for database operations"""
        self.operations.append(('fetchval', query, args))
        
        # Handle author creation/retrieval
        if "INSERT INTO authors" in query and "ON CONFLICT" in query:
            name = args[0]
            site_url = args[1] if len(args) > 1 else None
            
            if name in self.authors:
                return self.authors[name]
            else:
                author_id = self.next_author_id
                self.authors[name] = author_id
                self.next_author_id += 1
                return author_id
        
        # Handle book creation
        if "INSERT INTO books" in query:
            book_id = self.next_book_id
            self.next_book_id += 1
            return book_id
        
        # Handle existence checks
        if "SELECT EXISTS" in query:
            return True
        
        return None
    
    async def execute(self, query: str, *args):
        """Mock execute for database operations"""
        self.operations.append(('execute', query, args))
        
        # Handle document_authors insertion
        if "INSERT INTO document_authors" in query:
            book_id, author_id, order = args[0], args[1], args[2]
            self.document_authors[(book_id, author_id)] = order
        
        return "INSERT 0 1"
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class MockPool:
    """Mock connection pool"""
    
    def __init__(self):
        self.connection = MockConnection()
    
    def acquire(self):
        return self.connection


class TestBatchUploadProperties:
    """Property-based tests for batch upload functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_pool = MockPool()
        self.author_service = AuthorService()
        self.author_service.pool = self.mock_pool
        
        self.doc_author_service = DocumentAuthorService()
        self.doc_author_service.pool = self.mock_pool
        
        self.pdf_processor = MockPDFProcessor()
        self.vector_store = MockVectorStore()

    # Feature: multi-author-metadata-enhancement, Property 17: Batch upload creates authors
    @given(
        filenames=st.lists(
            st.text(min_size=5, max_size=30).filter(lambda x: "_by_" in x and x.endswith(".pdf") == False),
            min_size=1, max_size=5
        ).map(lambda names: [f"{name}.pdf" for name in names])
    )
    @settings(max_examples=100)
    async def test_batch_upload_creates_authors(self, filenames: List[str]):
        """
        For any batch of documents with author metadata, all authors should be created or associated after the batch upload completes.
        **Validates: Requirements 6.1**
        """
        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            expected_authors = set()
            
            for filename in filenames:
                file_path = Path(temp_dir) / filename
                file_path.write_bytes(b"Mock PDF content")
                file_paths.append(str(file_path))
                
                # Extract expected authors from filename
                if "_by_" in filename:
                    author_part = filename.replace(".pdf", "").split("_by_")[1]
                    if "_and_" in author_part:
                        authors = [a.replace("_", " ") for a in author_part.split("_and_")]
                        expected_authors.update(authors)
                    else:
                        expected_authors.add(author_part.replace("_", " "))
            
            # Process batch upload
            await self._process_batch_upload(file_paths)
            
            # Verify all expected authors were created
            created_authors = set(self.mock_pool.connection.authors.keys())
            
            # Property: All authors from batch should be created
            for expected_author in expected_authors:
                assert expected_author in created_authors, f"Author '{expected_author}' was not created during batch upload"

    # Feature: multi-author-metadata-enhancement, Property 18: Parse multiple authors
    @given(
        author_strings=st.lists(
            st.one_of(
                st.just("John Doe"),
                st.just("John Doe; Jane Smith"),
                st.just("John Doe, Jane Smith"),
                st.just("John Doe and Jane Smith"),
                st.just("John Doe; Jane Smith; Bob Wilson"),
                st.just("John Doe, Jane Smith, and Bob Wilson")
            ),
            min_size=1, max_size=3
        )
    )
    @settings(max_examples=100)
    async def test_parse_multiple_authors(self, author_strings: List[str]):
        """
        For any author string with multiple authors separated by various delimiters, all individual authors should be correctly parsed.
        **Validates: Requirements 6.2**
        """
        for author_string in author_strings:
            parsed_authors = self._parse_authors(author_string)
            
            # Property: Parsing should extract all individual authors
            if ";" in author_string:
                expected_count = len([a.strip() for a in author_string.split(";")])
            elif " and " in author_string:
                # Handle "A, B, and C" format
                if "," in author_string:
                    parts = author_string.split(",")
                    expected_count = len(parts)
                else:
                    expected_count = len(author_string.split(" and "))
            elif "," in author_string:
                expected_count = len([a.strip() for a in author_string.split(",")])
            else:
                expected_count = 1
            
            assert len(parsed_authors) == expected_count, f"Expected {expected_count} authors from '{author_string}', got {len(parsed_authors)}: {parsed_authors}"
            
            # Property: No empty author names
            for author in parsed_authors:
                assert author.strip(), f"Empty author name found in parsed result: {parsed_authors}"

    # Feature: multi-author-metadata-enhancement, Property 19: Batch upload deduplicates authors
    @given(
        duplicate_authors=st.lists(
            st.sampled_from(["John Doe", "Jane Smith", "Bob Wilson"]),
            min_size=2, max_size=6
        )
    )
    @settings(max_examples=100)
    async def test_batch_upload_deduplicates_authors(self, duplicate_authors: List[str]):
        """
        For any batch upload containing documents with duplicate author names, only one author record per unique name should be created.
        **Validates: Requirements 6.5**
        """
        # Create filenames with duplicate authors
        filenames = [f"book{i}_by_{author.replace(' ', '_')}.pdf" for i, author in enumerate(duplicate_authors)]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            for filename in filenames:
                file_path = Path(temp_dir) / filename
                file_path.write_bytes(b"Mock PDF content")
                file_paths.append(str(file_path))
            
            # Process batch upload
            await self._process_batch_upload(file_paths)
            
            # Property: Only unique authors should be created
            unique_expected_authors = set(duplicate_authors)
            created_authors = set(self.mock_pool.connection.authors.keys())
            
            assert created_authors == unique_expected_authors, f"Expected unique authors {unique_expected_authors}, got {created_authors}"
            
            # Property: Each unique author should have exactly one ID
            author_ids = list(self.mock_pool.connection.authors.values())
            unique_ids = set(author_ids)
            assert len(unique_ids) == len(unique_expected_authors), f"Duplicate author IDs found: {author_ids}"

    async def _process_batch_upload(self, file_paths: List[str]):
        """Simulate batch upload processing"""
        for file_path in file_paths:
            # Process PDF to extract metadata
            extracted_content = await self.pdf_processor.process_pdf(file_path)
            
            # Parse authors if present
            author_metadata = extracted_content.get("author")
            if author_metadata:
                authors = self._parse_authors(author_metadata)
                
                # Create/get authors using AuthorService
                author_ids = []
                for author_name in authors:
                    author_id = await self.author_service.get_or_create_author(author_name.strip())
                    author_ids.append(author_id)
                
                # Create document record (mock)
                filename = Path(file_path).name
                book_id = await self.mock_pool.connection.fetchval("INSERT INTO books (filename) VALUES ($1) RETURNING id", filename)
                
                # Associate authors with document
                for order, author_id in enumerate(author_ids):
                    await self.doc_author_service.add_author_to_document(book_id, author_id, order)
                
                # Add to vector store
                await self.vector_store.add_documents(
                    extracted_content["chunks"],
                    {
                        "filename": filename,
                        "title": extracted_content.get("title", filename.replace(".pdf", "")),
                        "authors": authors,
                        "total_pages": extracted_content["total_pages"]
                    }
                )

    def _parse_authors(self, author_string: str) -> List[str]:
        """Parse multiple authors from a string with various delimiters"""
        if not author_string:
            return []
        
        # Handle semicolon separation first (highest priority)
        if ";" in author_string:
            return [author.strip() for author in author_string.split(";") if author.strip()]
        
        # Handle "and" separation
        if " and " in author_string:
            # Handle "A, B, and C" format
            if "," in author_string:
                parts = author_string.split(",")
                authors = []
                for i, part in enumerate(parts):
                    part = part.strip()
                    if i == len(parts) - 1 and part.startswith("and "):
                        part = part[4:]  # Remove "and "
                    authors.append(part)
                return [author for author in authors if author]
            else:
                return [author.strip() for author in author_string.split(" and ") if author.strip()]
        
        # Handle comma separation
        if "," in author_string:
            return [author.strip() for author in author_string.split(",") if author.strip()]
        
        # Single author
        return [author_string.strip()]


# Async test runner for pytest compatibility
def test_batch_upload_creates_authors():
    """Sync wrapper for async property test"""
    test_instance = TestBatchUploadProperties()
    test_instance.setup_method()
    
    # Run a simple test case
    filenames = ["book1_by_John_Doe.pdf", "book2_by_Jane_Smith.pdf"]
    asyncio.run(test_instance.test_batch_upload_creates_authors(filenames))


def test_parse_multiple_authors():
    """Sync wrapper for async property test"""
    test_instance = TestBatchUploadProperties()
    test_instance.setup_method()
    
    # Run a simple test case
    author_strings = ["John Doe; Jane Smith", "John Doe and Jane Smith"]
    asyncio.run(test_instance.test_parse_multiple_authors(author_strings))


def test_batch_upload_deduplicates_authors():
    """Sync wrapper for async property test"""
    test_instance = TestBatchUploadProperties()
    test_instance.setup_method()
    
    # Run a simple test case
    duplicate_authors = ["John Doe", "Jane Smith", "John Doe"]
    asyncio.run(test_instance.test_batch_upload_deduplicates_authors(duplicate_authors))


if __name__ == "__main__":
    print("Running batch upload property tests...")
    test_batch_upload_creates_authors()
    test_parse_multiple_authors()
    test_batch_upload_deduplicates_authors()
    print("All tests passed!")