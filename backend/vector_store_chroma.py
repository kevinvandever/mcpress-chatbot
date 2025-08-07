import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    def __init__(self):
        # Use environment variable for ChromaDB path, fallback to local
        chroma_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
        
        logger.info(f"Initializing ChromaDB at path: {chroma_path}")
        
        self.client = chromadb.PersistentClient(
            path=chroma_path, 
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection('pdf_documents')
            logger.info(f"Connected to existing ChromaDB collection")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB collection: {e}")
            raise
    
    async def search(self, query: str, n_results: int = 5, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        """Search for similar documents using ChromaDB vector similarity"""
        try:
            # Build where clause for filtering
            where_clause = {}
            if book_filter:
                where_clause['book'] = {'$in': book_filter}
            if type_filter:
                where_clause['type'] = {'$in': type_filter}
            
            # Perform similarity search
            search_params = {
                'query_texts': [query],
                'n_results': n_results,
                'include': ['metadatas', 'documents', 'distances']
            }
            
            if where_clause:
                search_params['where'] = where_clause
            
            results = self.collection.query(**search_params)
            
            # Format results to match expected interface
            formatted_results = []
            
            if results['documents'] and len(results['documents'][0]) > 0:
                for i in range(len(results['documents'][0])):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    
                    formatted_results.append({
                        'content': results['documents'][0][i],
                        'metadata': {
                            'filename': metadata.get('book', 'Unknown'),
                            'page': metadata.get('page', 'N/A'),
                            'type': metadata.get('type', 'text'),
                            'chunk_index': metadata.get('chunk_index'),
                            'mc_press_url': metadata.get('mc_press_url')
                        },
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            logger.info(f"ChromaDB search found {len(formatted_results)} results for query: '{query}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    async def list_documents(self) -> Dict[str, Any]:
        """List all documents in the ChromaDB collection"""
        try:
            # Get all documents without limit to count properly
            all_results = self.collection.get(
                include=['metadatas']
            )
            
            # Group by filename/book
            documents = {}
            total_chunks = 0
            
            for metadata in all_results['metadatas']:
                filename = metadata.get('book', 'Unknown')
                if filename not in documents:
                    documents[filename] = {
                        'chunk_count': 0,
                        'total_chunks': 0,
                        'has_images': False,
                        'has_code': False,
                        'uploaded_at': None,
                        'metadata': {},
                        'category': metadata.get('category', 'Unknown')
                    }
                
                documents[filename]['chunk_count'] += 1
                documents[filename]['total_chunks'] += 1
                total_chunks += 1
                
                # Track content types
                content_type = metadata.get('type', 'text')
                if content_type == 'image':
                    documents[filename]['has_images'] = True
                elif content_type == 'code':
                    documents[filename]['has_code'] = True
            
            logger.info(f"ChromaDB contains {len(documents)} documents with {total_chunks} total chunks")
            
            # Return in expected format for /documents endpoint
            return {
                'documents': documents,
                'total_documents': len(documents),
                'total_chunks': total_chunks
            }
            
        except Exception as e:
            logger.error(f"Error listing ChromaDB documents: {e}")
            return {'documents': {}, 'total_documents': 0, 'total_chunks': 0}
    
    async def delete_document(self, filename: str):
        """Delete document by filename"""
        try:
            # Get all IDs for this filename/book
            results = self.collection.get(
                where={'book': filename},
                include=['ids']
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for {filename}")
            else:
                logger.warning(f"No chunks found for {filename}")
                
        except Exception as e:
            logger.error(f"Error deleting document {filename}: {e}")
            raise