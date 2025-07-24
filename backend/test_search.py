from vector_store import VectorStore
import asyncio

async def test_search():
    vector_store = VectorStore()
    
    # Test if we can search the uploaded document
    results = await vector_store.search("chapter", n_results=3)
    
    print("Search results for 'chapter':")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"ID: {result['id']}")
        print(f"Distance: {result['distance']}")
        print(f"Content preview: {result['content'][:200]}...")
        print(f"Metadata: {result['metadata']}")

if __name__ == "__main__":
    asyncio.run(test_search())