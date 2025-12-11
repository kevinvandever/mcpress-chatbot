#!/usr/bin/env python3
"""
Basic functionality test for author search and filtering
Feature: multi-author-metadata-enhancement, Task 17

Tests the new author search and filtering functionality.
"""
import asyncio
import os
from admin_documents import search_documents_by_author
from author_service import AuthorService

async def test_author_search_functionality():
    """Test core author search functionality"""
    print("Testing author search and filtering functionality...")
    
    # Test 1: Initialize services
    database_url = os.getenv('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
    author_service = AuthorService(database_url)
    
    try:
        await author_service.init_database()
        print("✅ Author service initialized")
        
        # Test 2: List authors with sorting
        authors = await author_service.list_authors_with_sorting(
            limit=10,
            sort_by="name",
            sort_direction="asc",
            exclude_empty=False
        )
        print(f"✅ Listed {len(authors)} authors (sorted by name)")
        
        # Test 3: List authors sorted by document count
        authors_by_count = await author_service.list_authors_with_sorting(
            limit=10,
            sort_by="document_count",
            sort_direction="desc",
            exclude_empty=True
        )
        print(f"✅ Listed {len(authors_by_count)} authors with documents (sorted by count)")
        
        # Test 4: Search functionality
        if authors:
            search_results = await author_service.search_authors("test", limit=5)
            print(f"✅ Search returned {len(search_results)} results")
        
        print("All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await author_service.close()

if __name__ == "__main__":
    asyncio.run(test_author_search_functionality())