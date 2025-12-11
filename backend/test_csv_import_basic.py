#!/usr/bin/env python3
"""
Basic functionality test for CSV import multi-author functionality
Feature: multi-author-metadata-enhancement

Tests the updated CSV import functionality with multi-author support.
"""

import os
import asyncio
import tempfile
import csv
import io
from pathlib import Path


class MockConnection:
    """Mock database connection for testing"""
    
    def __init__(self):
        self.operations = []
        self.documents = {
            'test-book.pdf': {'id': 1, 'title': 'Test Book'},
            'another-book.pdf': {'id': 2, 'title': 'Another Book'}
        }
    
    async def cursor(self):
        return MockCursor(self)
    
    async def commit(self):
        self.operations.append(('COMMIT',))
    
    async def close(self):
        pass
    
    def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class MockCursor:
    """Mock database cursor for testing"""
    
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 0
    
    async def execute(self, query, params=None):
        self.connection.operations.append(('EXECUTE', query, params))
        
        # Mock document lookup
        if 'SELECT id FROM books WHERE filename' in query and params:
            filename = params[0]
            if filename in self.connection.documents:
                self._result = [self.connection.documents[filename]['id']]
                self.rowcount = 1
            else:
                self._result = []
                self.rowcount = 0
        else:
            self._result = []
            self.rowcount = 1
    
    async def fetchone(self):
        if hasattr(self, '_result') and self._result:
            return [self._result[0]]
        return None
    
    def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class MockVectorStore:
    """Mock vector store for testing"""
    
    def __init__(self):
        self.connection = MockConnection()
    
    async def _get_connection(self):
        return self.connection


class MockAuthorService:
    """Mock author service for testing"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url
        self.authors = {}
        self.next_id = 1
    
    async def init_database(self):
        pass
    
    async def get_or_create_author(self, name, site_url=None):
        """Mock get or create author"""
        # Find existing author by name
        for author_id, author in self.authors.items():
            if author['name'] == name:
                return author_id
        
        # Create new author
        author_id = self.next_id
        self.next_id += 1
        self.authors[author_id] = {
            'id': author_id,
            'name': name,
            'site_url': site_url
        }
        return author_id
    
    async def get_author_by_id(self, author_id):
        """Mock get author by ID"""
        return self.authors.get(author_id)
    
    async def update_author(self, author_id, name, site_url):
        """Mock update author"""
        if author_id in self.authors:
            self.authors[author_id]['name'] = name
            self.authors[author_id]['site_url'] = site_url


class MockDocumentAuthorService:
    """Mock document author service for testing"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url
        self.associations = {}  # doc_id -> [(author_id, order), ...]
    
    async def init_database(self):
        pass
    
    async def clear_document_authors(self, doc_id):
        """Mock clear document authors"""
        self.associations[doc_id] = []
    
    async def add_author_to_document(self, doc_id, author_id, order):
        """Mock add author to document"""
        if doc_id not in self.associations:
            self.associations[doc_id] = []
        self.associations[doc_id].append((author_id, order))


async def test_csv_import_basic():
    """Test basic CSV import functionality"""
    print("🧪 Testing CSV Import Basic Functionality...")
    
    try:
        # Set up environment
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        
        # Import the function to test
        try:
            from admin_documents import import_documents_csv_updated
        except ImportError:
            from backend.admin_documents import import_documents_csv_updated
        
        # Create mock services
        vector_store = MockVectorStore()
        author_service = MockAuthorService()
        document_author_service = MockDocumentAuthorService()
        
        # Create test CSV content
        csv_content = """filename,title,authors,author_site_urls,category,document_type,mc_press_url,article_url
test-book.pdf,Updated Test Book,John Doe|Jane Smith,https://johndoe.com|https://janesmith.com,Programming,book,https://mcpress.com/test,
another-book.pdf,Another Updated Book,Alice Johnson,,Technical,article,,https://example.com/article"""
        
        # Test the import function
        result = await import_documents_csv_updated(
            csv_content,
            vector_store=vector_store,
            author_service=author_service,
            document_author_service=document_author_service
        )
        
        print(f"\n📊 CSV Import Results:")
        print(f"   - Documents updated: {result['updated']}")
        print(f"   - Authors created: {result['authors_created']}")
        print(f"   - Authors updated: {result['authors_updated']}")
        print(f"   - Errors: {result.get('errors', 'None')}")
        
        # Verify results
        assert result['updated'] == 2, f"Expected 2 documents updated, got {result['updated']}"
        assert result['authors_created'] >= 2, f"Expected at least 2 authors created, got {result['authors_created']}"
        
        # Verify authors were created
        assert len(author_service.authors) >= 2, f"Expected at least 2 authors in service, got {len(author_service.authors)}"
        
        # Verify author names
        author_names = [author['name'] for author in author_service.authors.values()]
        assert 'John Doe' in author_names, "John Doe should be created"
        assert 'Jane Smith' in author_names, "Jane Smith should be created"
        assert 'Alice Johnson' in author_names, "Alice Johnson should be created"
        
        # Verify document-author associations
        assert 1 in document_author_service.associations, "Document 1 should have author associations"
        assert 2 in document_author_service.associations, "Document 2 should have author associations"
        
        # Verify first document has 2 authors
        doc1_authors = document_author_service.associations[1]
        assert len(doc1_authors) == 2, f"Document 1 should have 2 authors, got {len(doc1_authors)}"
        
        # Verify second document has 1 author
        doc2_authors = document_author_service.associations[2]
        assert len(doc2_authors) == 1, f"Document 2 should have 1 author, got {len(doc2_authors)}"
        
        # Verify author URLs were handled correctly
        john_doe_id = None
        jane_smith_id = None
        for author_id, author in author_service.authors.items():
            if author['name'] == 'John Doe':
                john_doe_id = author_id
                assert author['site_url'] == 'https://johndoe.com', f"John Doe URL should be https://johndoe.com, got {author['site_url']}"
            elif author['name'] == 'Jane Smith':
                jane_smith_id = author_id
                assert author['site_url'] == 'https://janesmith.com', f"Jane Smith URL should be https://janesmith.com, got {author['site_url']}"
            elif author['name'] == 'Alice Johnson':
                assert author['site_url'] is None, f"Alice Johnson should have no URL, got {author['site_url']}"
        
        print(f"\n✅ CSV Import Basic Test Passed!")
        return True
        
    except Exception as e:
        print(f"❌ CSV Import Basic Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_csv_import_round_trip():
    """Test CSV export then import round trip"""
    print("🧪 Testing CSV Round Trip...")
    
    try:
        # This would test exporting then importing the same data
        # For now, just verify the import function handles the export format
        
        # Create CSV content in the export format
        csv_content = """id,filename,title,authors,author_site_urls,category,subcategory,year,tags,description,document_type,mc_press_url,article_url,total_pages,processed_at
1,test-book.pdf,Test Book,John Doe|Jane Smith,https://johndoe.com|https://janesmith.com,Programming,RPG,2024,"tag1,tag2",Test description,book,https://mcpress.com/test,,350,2024-01-01T00:00:00"""
        
        # Set up mocks
        vector_store = MockVectorStore()
        author_service = MockAuthorService()
        document_author_service = MockDocumentAuthorService()
        
        # Import the function
        try:
            from admin_documents import import_documents_csv_updated
        except ImportError:
            from backend.admin_documents import import_documents_csv_updated
        
        # Test import
        result = await import_documents_csv_updated(
            csv_content,
            vector_store=vector_store,
            author_service=author_service,
            document_author_service=document_author_service
        )
        
        # Verify round trip worked
        assert result['updated'] == 1, f"Expected 1 document updated, got {result['updated']}"
        assert result['authors_created'] == 2, f"Expected 2 authors created, got {result['authors_created']}"
        
        print(f"✅ CSV Round Trip Test Passed!")
        return True
        
    except Exception as e:
        print(f"❌ CSV Round Trip Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all basic tests"""
    print("🚀 Starting CSV Import Basic Tests...")
    
    success1 = await test_csv_import_basic()
    success2 = await test_csv_import_round_trip()
    
    if success1 and success2:
        print("\n🎉 All CSV Import Basic Tests Passed!")
    else:
        print("\n💥 Some CSV Import Basic Tests Failed!")
    
    return success1 and success2


if __name__ == "__main__":
    asyncio.run(main())