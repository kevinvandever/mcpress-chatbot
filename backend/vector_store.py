import os
import asyncio
from typing import List, Dict, Any, Optional
import asyncpg
import json
import subprocess
import sys

# Lazy imports for heavy dependencies
numpy = None
SentenceTransformer = None

def ensure_dependencies():
    """Install heavy dependencies at runtime if needed"""
    global numpy, SentenceTransformer
    
    if numpy is None:
        try:
            import numpy as np
            numpy = np
        except ImportError:
            print("Installing required ML packages... This is a one-time setup.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                 "sentence-transformers", "numpy", "pandas", "pdfplumber"])
            import numpy as np
            numpy = np
    
    if SentenceTransformer is None:
        from sentence_transformers import SentenceTransformer as ST
        SentenceTransformer = ST

class VectorStore:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self._embedding_model = None
        self.pool = None
    
    @property
    def embedding_model(self):
        """Lazy load the embedding model on first use"""
        if self._embedding_model is None:
            ensure_dependencies()  # Install packages if needed
            print("Loading embedding model for the first time... This may take a minute.")
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded successfully!")
        return self._embedding_model
    
    async def init_pool(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
    
    async def init_database(self):
        """Initialize database with pgvector extension and tables"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    embedding vector(384),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for vector similarity search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                ON documents USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents with embeddings to the database"""
        await self.init_pool()
        
        # Generate embeddings
        texts = [doc['content'] for doc in documents]
        embeddings = self.embedding_model.encode(texts)
        
        async with self.pool.acquire() as conn:
            for doc, embedding in zip(documents, embeddings):
                await conn.execute("""
                    INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5::vector, $6)
                """, 
                doc['filename'],
                doc['content'],
                doc.get('page_number', 0),
                doc.get('chunk_index', 0),
                embedding.tolist(),  # Convert numpy array to list
                json.dumps(doc.get('metadata', {}))
                )
    
    async def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        await self.init_pool()
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0]
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT filename, content, page_number, metadata,
                       embedding <=> $1::vector as distance
                FROM documents
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, query_embedding.tolist(), k)
            
            results = []
            for row in rows:
                results.append({
                    'filename': row['filename'],
                    'content': row['content'],
                    'page_number': row['page_number'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'distance': float(row['distance'])
                })
            
            return results
    
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM documents")
            return result
    
    async def delete_by_filename(self, filename: str):
        """Delete all chunks for a specific filename"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM documents WHERE filename = $1", filename)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.pool is not None
    
    async def search(self, query: str, n_results: int = 5, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        """Search for similar documents - compatibility method"""
        results = await self.similarity_search(query, n_results)
        
        # Convert format to match original interface
        formatted_results = []
        for result in results:
            formatted_results.append({
                'document': result['content'],
                'metadata': {
                    'filename': result['filename'],
                    'page_number': result['page_number'],
                    **result['metadata']
                },
                'distance': result['distance']
            })
        
        return formatted_results
    
    async def list_documents(self) -> Dict[str, Any]:
        """List all documents in the database"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT filename, COUNT(*) as chunk_count, 
                       MIN(created_at) as uploaded_at,
                       jsonb_object_agg(
                           COALESCE(metadata->>'key', 'metadata'), 
                           metadata
                       ) as metadata
                FROM documents 
                GROUP BY filename
                ORDER BY MIN(created_at) DESC
            """)
            
            documents = {}
            for row in rows:
                documents[row['filename']] = {
                    'chunk_count': row['chunk_count'],
                    'uploaded_at': row['uploaded_at'].isoformat() if row['uploaded_at'] else None,
                    'metadata': row['metadata'] or {}
                }
            
            return {
                'documents': documents,
                'total_documents': len(documents),
                'total_chunks': sum(doc['chunk_count'] for doc in documents.values())
            }
    
    async def delete_document(self, filename: str):
        """Delete document by filename"""
        await self.delete_by_filename(filename)
    
    async def update_document_metadata(self, filename: str, title: str, author: str, category: str = None, mc_press_url: str = None):
        """Update document metadata"""
        await self.init_pool()
        metadata = {
            'title': title,
            'author': author,
            'category': category,
            'mc_press_url': mc_press_url
        }
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE documents 
                SET metadata = $2::jsonb
                WHERE filename = $1
            """, filename, json.dumps(metadata))
    
    def reset_database(self):
        """Reset/clear the database"""
        # This would be dangerous in production, so we'll just pass for now
        pass
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()