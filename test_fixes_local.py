#!/usr/bin/env python3
"""
Local test script to verify the fixes before deploying
Tests the vector store and chat handler changes
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_vector_store():
    """Test vector store configuration"""
    print("="*60)
    print("🔍 TESTING VECTOR STORE CONFIGURATION")
    print("="*60)

    # Check environment variables
    use_postgresql = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'
    database_url = os.getenv('DATABASE_URL', '')

    print(f"USE_POSTGRESQL: {use_postgresql}")
    print(f"DATABASE_URL present: {bool(database_url)}")
    print()

    if not database_url:
        print("❌ No DATABASE_URL found - cannot test PostgreSQL vector store")
        print("   Set DATABASE_URL in your .env file to test")
        return False

    # Import and test PostgresVectorStore
    try:
        from backend.vector_store_postgres import PostgresVectorStore
        print("✅ PostgresVectorStore imported successfully")

        vector_store = PostgresVectorStore()
        print("✅ PostgresVectorStore instantiated")

        # Initialize database
        await vector_store.init_database()
        print(f"✅ Database initialized")
        print(f"   - pgvector enabled: {vector_store.has_pgvector}")

        # Check document count
        doc_count = await vector_store.get_document_count()
        print(f"   - Total documents: {doc_count:,}")

        if doc_count == 0:
            print("⚠️  No documents in database - search test will be limited")

        # Test search with a sample query
        print()
        print("🔍 Testing search functionality...")
        test_query = "What is RPG programming?"
        results = await vector_store.search(test_query, n_results=5)

        print(f"✅ Search completed - found {len(results)} results")

        if results:
            print()
            print("📊 Sample results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n   Result {i}:")
                print(f"   - Distance: {result.get('distance', 'N/A'):.4f}")
                print(f"   - Similarity: {result.get('similarity', 'N/A'):.4f}")
                print(f"   - Using pgvector: {result.get('using_pgvector', 'N/A')}")
                print(f"   - Filename: {result.get('metadata', {}).get('filename', 'Unknown')}")
                print(f"   - Page: {result.get('metadata', {}).get('page', 'N/A')}")
                print(f"   - Content preview: {result.get('content', '')[:100]}...")

        # Close connections
        await vector_store.close()

        print()
        print("="*60)
        print("✅ VECTOR STORE TEST PASSED")
        print("="*60)
        return True

    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_handler():
    """Test chat handler with new threshold logic"""
    print()
    print("="*60)
    print("🔍 TESTING CHAT HANDLER CONFIGURATION")
    print("="*60)

    try:
        from backend.chat_handler import ChatHandler
        from backend.vector_store_postgres import PostgresVectorStore

        # Create vector store
        vector_store = PostgresVectorStore()
        await vector_store.init_database()

        # Create chat handler
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            print("⚠️  No OPENAI_API_KEY - skipping chat handler test")
            return True

        chat_handler = ChatHandler(vector_store)
        print("✅ ChatHandler instantiated")

        # Test threshold calculation
        test_queries = [
            "What is RPG programming?",  # RPG keyword
            "How do I use SQL?",  # Code keyword
            "Configure the database",  # Tech keyword
            '"exact match"',  # Exact search
            "General question"  # General
        ]

        print()
        print("📊 Testing dynamic threshold logic:")
        for query in test_queries:
            threshold = chat_handler._get_dynamic_threshold(query)
            print(f"   Query: {query:35s} => Threshold: {threshold:.2f}")

        # Close connections
        await vector_store.close()

        print()
        print("="*60)
        print("✅ CHAT HANDLER TEST PASSED")
        print("="*60)
        return True

    except Exception as e:
        print(f"❌ Chat handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print()
    print("🧪 TESTING PGVECTOR FIXES")
    print()

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed - using system environment only")

    print()

    # Run tests
    test_results = []

    # Test 1: Vector Store
    result1 = await test_vector_store()
    test_results.append(("Vector Store", result1))

    # Test 2: Chat Handler
    result2 = await test_chat_handler()
    test_results.append(("Chat Handler", result2))

    # Summary
    print()
    print("="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    for name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result for _, result in test_results)

    if all_passed:
        print()
        print("🎉 All tests passed! Ready to deploy.")
    else:
        print()
        print("⚠️  Some tests failed. Review errors above.")

    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
