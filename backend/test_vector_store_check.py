import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
client = chromadb.PersistentClient(path='./chroma_db', settings=Settings(anonymized_telemetry=False))

try:
    collection = client.get_collection('pdf_documents')
    
    # Get a batch of documents from the collection for Subfiles book
    # Use different approach - get by IDs pattern
    all_results = collection.get(
        where={'book': 'Subfiles in Free-Format RPG.pdf'},
        limit=1000,
        include=['metadatas', 'documents']
    )
    
    # Count by type
    type_counts = {}
    text_chunks_data = []
    
    for i, metadata in enumerate(all_results['metadatas']):
        chunk_type = metadata.get('type', 'unknown')
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        if chunk_type == 'text' and i < len(all_results['documents']):
            text_chunks_data.append({
                'metadata': metadata,
                'content': all_results['documents'][i]
            })
    
    print(f'Total Subfiles chunks in vector store: {len(all_results["metadatas"])}')
    print(f'Chunks by type: {type_counts}')
    
    if text_chunks_data:
        print(f'\nText chunks found: {len(text_chunks_data)}')
        print('\nFirst 3 text chunks:')
        for i, chunk_data in enumerate(text_chunks_data[:3]):
            print(f'\n--- Chunk {i} ---')
            print(f'Chunk index: {chunk_data["metadata"].get("chunk_index", "N/A")}')
            print(f'Page: {chunk_data["metadata"].get("page", "N/A")}')
            print(f'Total length: {chunk_data["metadata"].get("total_length", "N/A")}')
            print(f'Meaningful length: {chunk_data["metadata"].get("meaningful_length", "N/A")}')
            print(f'Content preview: {chunk_data["content"][:150]}...')
    else:
        print('\nNo text chunks found in vector store!')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()