import os
import re
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean text by replacing common PDF ligatures only"""
    if not text:
        return text
    
    # Just fix the ligatures that were causing display issues
    replacements = {
        'ﬁ': 'fi',
        'ﬂ': 'fl',
        'ﬀ': 'ff',
        'ﬃ': 'ffi',
        'ﬄ': 'ffl',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

class ChromaVectorStore:
    def __init__(self):
        # Use environment variable for ChromaDB path, fallback to local
        chroma_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
        
        logger.info(f"Initializing ChromaDB at path: {chroma_path}")
        
        # Check if ChromaDB directory exists
        if not os.path.exists(chroma_path):
            logger.warning(f"ChromaDB path {chroma_path} does not exist - creating empty database")
            os.makedirs(chroma_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=chroma_path, 
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection('pdf_documents')
            logger.info(f"✅ Connected to existing ChromaDB collection with data")
        except Exception as e:
            logger.warning(f"⚠️ ChromaDB collection 'pdf_documents' not found, creating empty one: {e}")
            # Create empty collection if it doesn't exist
            self.collection = self.client.create_collection('pdf_documents')
            logger.info("📝 Created empty ChromaDB collection - no documents available yet")
    
    async def search(self, query: str, n_results: int = 5, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        """Search for similar documents using ChromaDB vector similarity"""
        try:
            # Build where clause for filtering
            where_clause = {}
            if book_filter:
                where_clause['book'] = {'$in': book_filter}
            if type_filter:
                where_clause['type'] = {'$in': type_filter}
            
            # Get more results initially to allow for better filtering/ranking
            search_n_results = max(n_results * 3, 20)  # Get 3x more results
            
            # Perform similarity search
            search_params = {
                'query_texts': [query],
                'n_results': search_n_results,
                'include': ['metadatas', 'documents', 'distances']
            }
            
            if where_clause:
                search_params['where'] = where_clause
            
            results = self.collection.query(**search_params)
            
            # Format and rank results to prefer text over images
            formatted_results = []
            
            if results['documents'] and len(results['documents'][0]) > 0:
                for i in range(len(results['documents'][0])):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    content_type = metadata.get('type', 'text')
                    distance = results['distances'][0][i] if results['distances'] else 0.0
                    
                    # Apply type-based penalty to prioritize text content
                    adjusted_distance = distance
                    if content_type == 'image':
                        adjusted_distance += 0.3  # Strong penalty for images
                    elif content_type == 'code':
                        adjusted_distance -= 0.1  # Bonus for code
                    
                    # Clean the text content
                    cleaned_content = clean_text(results['documents'][0][i])
                    
                    formatted_results.append({
                        'content': cleaned_content,
                        'metadata': {
                            'filename': metadata.get('book', 'Unknown'),
                            'page': metadata.get('page', 'N/A'),
                            'type': content_type,
                            'chunk_index': metadata.get('chunk_index'),
                            'mc_press_url': metadata.get('mc_press_url')
                        },
                        'distance': distance,  # Original distance
                        'adjusted_distance': adjusted_distance  # For sorting
                    })
            
            # Simple sort by adjusted distance and return requested number
            formatted_results.sort(key=lambda x: x['adjusted_distance'])
            final_results = formatted_results[:n_results]
            
            # Remove the adjusted_distance field
            for result in final_results:
                result.pop('adjusted_distance', None)
            
            logger.info(f"ChromaDB search found {len(final_results)} results for query: '{query}' (from {len(formatted_results)} total)")
            return final_results
            
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
                # Try both 'book' and 'filename' for compatibility
                filename = metadata.get('book') or metadata.get('filename', 'Unknown')
                if filename not in documents:
                    documents[filename] = {
                        'chunk_count': 0,
                        'total_chunks': 0,
                        'has_images': False,
                        'has_code': False,
                        'uploaded_at': None,
                        'metadata': {},
                        'category': metadata.get('category', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'total_pages': metadata.get('total_pages', 100)
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
            
            # Convert to array format that frontend expects
            documents_array = []
            for filename, doc_info in documents.items():
                documents_array.append({
                    'filename': filename,
                    'total_chunks': doc_info['total_chunks'],
                    'chunk_count': doc_info['chunk_count'],
                    'has_images': doc_info['has_images'],
                    'has_code': doc_info['has_code'],
                    'category': doc_info['category'],
                    'uploaded_at': None,  # ChromaDB doesn't track upload time
                    'metadata': doc_info['metadata'],
                    'total_pages': doc_info['total_pages'],
                    'author': doc_info['author']
                })
            
            # Return in format frontend expects
            return {'documents': documents_array}
            
        except Exception as e:
            logger.error(f"Error listing ChromaDB documents: {e}")
            return {'documents': []}
    
    async def add_documents(self, documents: List[Dict], metadata: Dict[str, Any]):
        """Add documents to ChromaDB collection with batch size handling"""
        try:
            # ChromaDB has a batch size limit, split large documents into smaller batches
            BATCH_SIZE = 5000  # Safe batch size under the limit
            total_documents = len(documents)
            
            if total_documents > BATCH_SIZE:
                logger.info(f"📦 Large document detected ({total_documents} chunks), processing in batches of {BATCH_SIZE}")
                
                # Process in batches
                for batch_start in range(0, total_documents, BATCH_SIZE):
                    batch_end = min(batch_start + BATCH_SIZE, total_documents)
                    batch_docs = documents[batch_start:batch_end]
                    
                    logger.info(f"   Processing batch {batch_start//BATCH_SIZE + 1}: chunks {batch_start} to {batch_end-1}")
                    await self._add_batch(batch_docs, metadata, batch_start)
                
                logger.info(f"✅ Added all {total_documents} chunks to ChromaDB for {metadata.get('filename', 'unknown')} in {(total_documents + BATCH_SIZE - 1) // BATCH_SIZE} batches")
            else:
                # Small document, add all at once
                await self._add_batch(documents, metadata, 0)
                logger.info(f"✅ Added {total_documents} chunks to ChromaDB for {metadata.get('filename', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error adding documents to ChromaDB: {e}")
            raise e
    
    async def _add_batch(self, documents: List[Dict], metadata: Dict[str, Any], batch_offset: int = 0):
        """Add a batch of documents to ChromaDB"""
        # Prepare data for ChromaDB
        ids = []
        docs = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            # Create unique ID for each chunk (include batch offset)
            doc_id = f"{metadata['filename']}_{batch_offset + i}"
            ids.append(doc_id)
            
            # Get the document content
            content = doc.get('content', '') if isinstance(doc, dict) else str(doc)
            docs.append(content)
            
            # Create metadata for this chunk
            chunk_metadata = metadata.copy()
            if isinstance(doc, dict):
                chunk_metadata.update(doc.get('metadata', {}))
            
            # Fix None values in metadata (ChromaDB can't store None)
            for key, value in chunk_metadata.items():
                if value is None:
                    chunk_metadata[key] = 'Unknown' if key == 'author' else ''
            
            metadatas.append(chunk_metadata)
        
        # Add to ChromaDB collection
        self.collection.add(
            documents=docs,
            metadatas=metadatas,
            ids=ids
        )

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