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
            # Enable pgvector extension (skip if not available)
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            except Exception as e:
                print(f"pgvector not available, using text search instead: {e}")
            
            # Create documents table (without vector column if pgvector not available)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create text search index instead of vector index
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_content_idx 
                ON documents USING gin(to_tsvector('english', content))
            """)
    
    async def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """Add documents to the database"""
        await self.init_pool()
        
        async with self.pool.acquire() as conn:
            # Get filename from metadata parameter, fallback to first document if available
            filename = (metadata or {}).get('filename', 'unknown.pdf')
            if not filename and documents:
                filename = documents[0].get('filename', 'unknown.pdf')
            
            for doc in documents:
                await conn.execute("""
                    INSERT INTO documents (filename, content, page_number, chunk_index, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, 
                filename,  # Use filename from metadata parameter
                doc['content'],
                doc.get('page_number', 0),
                doc.get('chunk_index', 0),
                json.dumps(doc.get('metadata', {}))
                )
    
    async def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using text search with mixed content types"""
        await self.init_pool()
        
        async with self.pool.acquire() as conn:
            # Search with content type diversity - get more results while maintaining variety
            rows = await conn.fetch("""
                WITH ranked_results AS (
                    SELECT filename, content, page_number, metadata,
                           ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank,
                           metadata->>'type' as content_type,
                           ROW_NUMBER() OVER (PARTITION BY metadata->>'type' ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) DESC) as type_rank
                    FROM documents
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                ),
                diverse_results AS (
                    SELECT filename, content, page_number, metadata, rank
                    FROM ranked_results
                    WHERE type_rank <= GREATEST(3, $2::int / 3)  -- At least 3 per type, or limit/3
                ),
                top_results AS (
                    SELECT filename, content, page_number, metadata, rank
                    FROM ranked_results
                    ORDER BY rank DESC
                    LIMIT $2
                )
                SELECT * FROM diverse_results
                UNION
                SELECT * FROM top_results
                ORDER BY rank DESC
                LIMIT $2
            """, query, k)
            
            results = []
            for row in rows:
                results.append({
                    'filename': row['filename'],
                    'content': row['content'],
                    'page_number': row['page_number'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'distance': 1.0 - float(row['rank'])  # Convert rank to distance-like score
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
                'content': result['content'],  # Changed from 'document' to 'content'
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
            
            documents = []
            for row in rows:
                # Parse metadata if it's a JSON string
                metadata = row['metadata'] or '{}'
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Get proper category from category mapper
                try:
                    from category_mapper import get_category_mapper
                except ImportError:
                    from backend.category_mapper import get_category_mapper
                category_mapper = get_category_mapper()
                category = category_mapper.get_category(row['filename'])
                
                documents.append({
                    'filename': row['filename'],
                    'total_chunks': row['chunk_count'],  # Frontend expects total_chunks
                    'chunk_count': row['chunk_count'],   # Keep for compatibility
                    'uploaded_at': row['uploaded_at'].isoformat() if row['uploaded_at'] else None,
                    'metadata': metadata,
                    # Add fields expected by frontend
                    'has_images': True,  # Assume true for now
                    'has_code': True,    # Assume true for now  
                    'total_pages': metadata.get('metadata', {}).get('page', 100),  # Get from metadata
                    'category': category,  # Use real category from CSV
                    'author': metadata.get('metadata', {}).get('author', 'Unknown')
                })
            
            # Return array directly - frontend expects this format
            return documents
    
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