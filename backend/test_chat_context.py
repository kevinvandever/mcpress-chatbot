from vector_store import VectorStore
from chat_handler import ChatHandler
import asyncio

async def test_chat_context():
    vector_store = VectorStore()
    chat_handler = ChatHandler(vector_store)
    
    # Test what context is being built
    results = await vector_store.search("what is a subfile", n_results=3)
    
    print("Search results:")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Content preview: {result['content'][:300]}...")
        print(f"Metadata: {result['metadata']}")
    
    print("\n" + "="*50)
    print("Context that would be sent to LLM:")
    context = chat_handler._build_context(results)
    print(context[:1000] + "..." if len(context) > 1000 else context)

if __name__ == "__main__":
    asyncio.run(test_chat_context())