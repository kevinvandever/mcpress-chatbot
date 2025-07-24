import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import os
from sentence_transformers import SentenceTransformer
import asyncio

class VectorStore:
    def __init__(self):
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
    def is_connected(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except:
            return False
    
    async def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any]):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._add_documents_sync, documents, metadata)
    
    def _add_documents_sync(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any]):
        texts = [doc["content"] for doc in documents]
        ids = [doc["id"] for doc in documents]
        metadatas = []
        
        for doc in documents:
            doc_metadata = doc.get("metadata", {})
            doc_metadata.update(metadata)
            metadatas.append(doc_metadata)
        
        # ChromaDB has a max batch size limit (~5500). Split large batches.
        max_batch_size = 5000
        total_docs = len(documents)
        
        print(f"Adding {total_docs} documents to vector store")
        
        for i in range(0, total_docs, max_batch_size):
            end_idx = min(i + max_batch_size, total_docs)
            batch_texts = texts[i:end_idx]
            batch_ids = ids[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            
            print(f"Processing batch {i//max_batch_size + 1}: documents {i+1}-{end_idx} of {total_docs}")
            
            # Generate embeddings for this batch
            batch_embeddings = self.embedder.encode(batch_texts).tolist()
            
            # Add this batch to the collection
            self.collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=batch_metadatas
            )
            
            print(f"Successfully added batch {i//max_batch_size + 1} ({end_idx - i} documents)")
        
        print(f"Completed adding all {total_docs} documents to vector store")
    
    async def search(self, query: str, n_results: int = 5, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, n_results, book_filter, type_filter)
    
    def _search_sync(self, query: str, n_results: int, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        query_embedding = self.embedder.encode([query]).tolist()
        
        # Build where clause for filtering
        where_conditions = {}
        
        if book_filter:
            where_conditions["filename"] = {"$in": book_filter}
            
        if type_filter:
            where_conditions["type"] = {"$in": type_filter}
        
        where_clause = where_conditions if where_conditions else None
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_clause
        )
        
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        
        return formatted_results
    
    async def list_documents(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_documents_sync)
    
    def _list_documents_sync(self) -> Dict[str, Any]:
        all_docs = self.collection.get()
        
        documents_by_file = {}
        for i, metadata in enumerate(all_docs["metadatas"]):
            filename = metadata.get("filename", "unknown")
            if filename not in documents_by_file:
                documents_by_file[filename] = {
                    "filename": filename,
                    "total_chunks": 0,
                    "has_images": metadata.get("has_images", False),
                    "has_code": metadata.get("has_code", False),
                    "total_pages": metadata.get("total_pages", 0),
                    "category": metadata.get("category", "technical"),
                    "author": metadata.get("author")
                }
            documents_by_file[filename]["total_chunks"] += 1
        
        return {
            "total_documents": len(documents_by_file),
            "documents": list(documents_by_file.values())
        }
    
    async def delete_document(self, filename: str):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_document_sync, filename)
    
    def _delete_document_sync(self, filename: str):
        import os
        import urllib.parse
        
        all_docs = self.collection.get()
        ids_to_delete = []
        
        for i, metadata in enumerate(all_docs["metadatas"]):
            if metadata.get("filename") == filename:
                ids_to_delete.append(all_docs["ids"][i])
        
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            
            # Also remove the physical file
            upload_dir = "uploads"
            if os.path.exists(upload_dir):
                # Try both the original filename and URL-encoded version
                file_paths = [
                    os.path.join(upload_dir, filename),
                    os.path.join(upload_dir, urllib.parse.quote(filename, safe=''))
                ]
                
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed physical file: {file_path}")
                        
        print(f"Deleted {len(ids_to_delete)} chunks for document: {filename}")
    
    def reset_database(self):
        """Completely reset the database by deleting the collection and recreating it"""
        try:
            self.client.delete_collection("pdf_documents")
            print("Deleted collection pdf_documents")
        except Exception as e:
            print(f"Error deleting collection: {e}")
        
        # Recreate the collection
        self.collection = self.client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )
        print("Recreated collection pdf_documents")