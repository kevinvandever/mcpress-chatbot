import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
client = chromadb.PersistentClient(path='./chroma_db', settings=Settings(anonymized_telemetry=False))

try:
    collection = client.get_collection('pdf_documents')
    
    # Test search queries
    test_queries = [
        "subfile",
        "RPG programming",
        "display file",
        "SFLCTL",
        "free format"
    ]
    
    for query in test_queries:
        print(f'\n=== Searching for: "{query}" ===')
        
        # Search with filter for Subfiles book
        results = collection.query(
            query_texts=[query],
            n_results=5,
            where={'book': 'Subfiles in Free-Format RPG.pdf'},
            include=['metadatas', 'documents', 'distances']
        )
        
        if results['documents'][0]:
            print(f'Found {len(results["documents"][0])} results')
            
            # Analyze result types
            result_types = {}
            for metadata in results['metadatas'][0]:
                result_type = metadata.get('type', 'unknown')
                result_types[result_type] = result_types.get(result_type, 0) + 1
            
            print(f'Result types: {result_types}')
            
            # Show first result
            if len(results['documents'][0]) > 0:
                print(f'\nTop result:')
                print(f'Type: {results["metadatas"][0][0].get("type")}')
                print(f'Distance: {results["distances"][0][0]:.4f}')
                print(f'Content preview: {results["documents"][0][0][:200]}...')
        else:
            print('No results found')
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()