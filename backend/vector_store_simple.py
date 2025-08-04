import os
import asyncio
from typing import List, Dict, Any, Optional
import asyncpg
import json

class VectorStore:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.pool = None
    
    async def init_pool(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
    
    async def init_database(self):
        """Initialize database with basic tables (no vector extension for now)"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            # Create simple documents table without vector extension
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
            
            # Create simple text search index
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_content_idx 
                ON documents USING gin(to_tsvector('english', content))
            """)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.pool is not None
    
    async def search(self, query: str, n_results: int = 5, book_filter: List[str] = None, type_filter: List[str] = None) -> List[Dict[str, Any]]:
        """Search for documents using PostgreSQL full-text search"""
        await self.init_pool()
        
        async with self.pool.acquire() as conn:
            # Use PostgreSQL full-text search instead of vector similarity
            rows = await conn.fetch("""
                SELECT filename, content, page_number, metadata,
                       ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank
                FROM documents
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
            """, query, n_results)
            
            results = []
            for row in rows:
                results.append({
                    'document': row['content'],
                    'metadata': {
                        'filename': row['filename'],
                        'page_number': row['page_number'],
                        **(json.loads(row['metadata']) if row['metadata'] else {})
                    },
                    'distance': 1.0 - float(row['rank'])  # Convert rank to distance-like score
                })
            
            return results
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the database"""
        await self.init_pool()
        
        async with self.pool.acquire() as conn:
            for doc in documents:
                await conn.execute("""
                    INSERT INTO documents (filename, content, page_number, chunk_index, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, 
                doc['filename'],
                doc['content'],
                doc.get('page_number', 0),
                doc.get('chunk_index', 0),
                json.dumps(doc.get('metadata', {}))
                )
    
    async def list_documents(self) -> Dict[str, Any]:
        """List all documents in the database"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT filename, COUNT(*) as chunk_count, 
                       MIN(created_at) as uploaded_at
                FROM documents 
                GROUP BY filename
                ORDER BY MIN(created_at) DESC
            """)
            
            documents = {}
            for row in rows:
                documents[row['filename']] = {
                    'chunk_count': row['chunk_count'],
                    'uploaded_at': row['uploaded_at'].isoformat() if row['uploaded_at'] else None,
                    'metadata': {}
                }
            
            return {
                'documents': documents,
                'total_documents': len(documents),
                'total_chunks': sum(doc['chunk_count'] for doc in documents.values())
            }
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()