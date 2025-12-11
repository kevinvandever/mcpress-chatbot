#!/usr/bin/env python3
"""
Basic functionality test for CSV export multi-author functionality
Feature: multi-author-metadata-enhancement

Tests the updated CSV export functionality with multi-author support.
"""

import os
import io
import csv
import asyncio
from typing import List, Dict, Any


class MockConnection:
    """Mock database connection for testing"""
    
    def __init__(self, test_data: List[tuple]):
        self.test_data = test_data
    
    async def close(self):
        """Mock connection close"""
        pass
    
    def cursor(self):
        """Mock cursor context manager"""
        return MockCursor(self.test_data)


class MockCursor:
    """Mock database cursor for testing"""
    
    def __init__(self, test_data: List[tuple]):
        self.test_data = test_data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def execute(self, query: str, *args):
        """Mock cursor execute"""
        pass
    
    async def fetchall(self):
        """Mock cursor fetchall"""
        return self.test_data


class MockVectorStore:
    """Mock vector store for testing"""
    
    def __init__(self, test_data: List[tuple]):
        self.test_data = test_data
    
    async def _get_connection(self):
        return MockConnection(self.test_data)


class MockAuthorService:
    """Mock author service for testing"""
    
    def __init__(self):
        # Mock author data
        self.authors_data = {
            1: [
                {'id': 1, 'name': 'John Doe', 'site_url': 'https://johndoe.com', 'order': 0},
                {'id': 2, 'name': 'Jane Smith', 'site_url': 'https://janesmith.com', 'order': 1}
            ],
            2: [
                {'id': 3, 'name': 'Bob Wilson', 'site_url': None, 'order': 0}
            ],
            3: [
                {'id': 4, 'name': 'Alice Brown', 'site_url': 'https://alicebrown.com', 'order': 0}
            ]
        }
    
    async def get_authors_for_document(self, book_id: int) -> List[Dict[str, Any]]:
        """Mock getting authors for a document"""
        return self.authors_data.get(book_id, [])


async def test_csv_export_basic():
    """Test basic CSV export functionality"""
    print("🧪 Testing CSV Export Basic Functionality...")
    
    # Set up environment
    os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
    
    # Mock database data (matching the query structure in admin_documents.py)
    test_data = [
        # (id, filename, title, category, subcategory, year, tags, description, mc_press_url, total_pages, processed_at, document_type, article_url)
        (1, 'book1.pdf', 'RPG Programming Guide', 'Programming', 'RPG', 2024, ['programming', 'rpg'], 'A guide to RPG programming', 'https://mcpress.com/rpg-guide', 350, None, 'book', ''),
        (2, 'article1.pdf', 'SQL Tips and Tricks', 'Database', 'SQL', 2023, ['database', 'sql'], 'Useful SQL tips', '', 25, None, 'article', 'https://example.com/sql-tips'),
        (3, 'book2.pdf', 'ILE Concepts', 'Programming', 'ILE', 2024, ['programming', 'ile'], 'Understanding ILE', 'https://mcpress.com/ile-concepts', 280, None, 'book', '')
    ]
    
    # Create mock services
    mock_vector_store = MockVectorStore(test_data)
    mock_author_service = MockAuthorService()
    
    try:
        # Import the function we're testing
        from admin_documents import export_documents_csv_updated
        
        # Call the export function
        response = await export_documents_csv_updated(
            vector_store=mock_vector_store,
            author_service=mock_author_service
        )
        
        # Parse the CSV response
        csv_content = response.body.decode('utf-8')
        print(f"📄 CSV Content Preview (first 500 chars):\n{csv_content[:500]}...")
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        csv_rows = list(csv_reader)
        
        print(f"\n📊 CSV Export Results:")
        print(f"   - Total documents: {len(csv_rows)}")
        print(f"   - CSV headers: {csv_reader.fieldnames}")
        
        # Verify expected fields are present
        expected_fields = ['id', 'filename', 'title', 'authors', 'author_site_urls', 'document_type', 'mc_press_url', 'article_url']
        missing_fields = [field for field in expected_fields if field not in csv_reader.fieldnames]
        
        if missing_fields:
            print(f"   ❌ Missing fields: {missing_fields}")
            return False
        else:
            print(f"   ✅ All required fields present")
        
        # Check each document
        for i, row in enumerate(csv_rows):
            doc_id = int(row['id'])
            print(f"\n📋 Document {doc_id}:")
            print(f"   - Title: {row['title']}")
            print(f"   - Authors: {row['authors']}")
            print(f"   - Author URLs: {row['author_site_urls']}")
            print(f"   - Document Type: {row['document_type']}")
            print(f"   - MC Press URL: {row['mc_press_url']}")
            print(f"   - Article URL: {row['article_url']}")
            
            # Verify multi-author formatting
            if doc_id == 1:  # Should have 2 authors
                expected_authors = "John Doe|Jane Smith"
                expected_urls = "https://johndoe.com|https://janesmith.com"
                
                if row['authors'] == expected_authors:
                    print(f"   ✅ Authors correctly formatted")
                else:
                    print(f"   ❌ Authors incorrect: expected '{expected_authors}', got '{row['authors']}'")
                    return False
                
                if row['author_site_urls'] == expected_urls:
                    print(f"   ✅ Author URLs correctly formatted")
                else:
                    print(f"   ❌ Author URLs incorrect: expected '{expected_urls}', got '{row['author_site_urls']}'")
                    return False
            
            elif doc_id == 2:  # Should have 1 author with no URL
                expected_authors = "Bob Wilson"
                expected_urls = ""
                
                if row['authors'] == expected_authors:
                    print(f"   ✅ Single author correctly formatted")
                else:
                    print(f"   ❌ Single author incorrect: expected '{expected_authors}', got '{row['authors']}'")
                    return False
                
                if row['author_site_urls'] == expected_urls:
                    print(f"   ✅ Empty author URL correctly handled")
                else:
                    print(f"   ❌ Author URL incorrect: expected '{expected_urls}', got '{row['author_site_urls']}'")
                    return False
        
        print(f"\n✅ CSV Export Basic Test Passed!")
        return True
        
    except Exception as e:
        print(f"❌ CSV Export Basic Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all basic tests"""
    print("🚀 Starting CSV Export Basic Tests...")
    
    success = await test_csv_export_basic()
    
    if success:
        print("\n🎉 All CSV Export Basic Tests Passed!")
    else:
        print("\n💥 Some CSV Export Basic Tests Failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())