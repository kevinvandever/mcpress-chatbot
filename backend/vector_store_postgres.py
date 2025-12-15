"""
Modern PostgreSQL Vector Store with pgvector extension
Provides semantic similarity search equivalent to ChromaDB
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import asyncpg
import json
import logging

logger = logging.getLogger(__name__)

# Lazy imports for embeddings
sentence_transformers = None
numpy = None

def ensure_embedding_dependencies():
    """Import embedding dependencies on demand"""
    global sentence_transformers, numpy
    
    if sentence_transformers is None:
        try:
            import sentence_transformers
            import numpy as np
            numpy = np
        except ImportError:
            raise ImportError(
                "sentence-transformers and numpy are required for vector search. "
                "Install with: pip install sentence-transformers numpy"
            )

class PostgresVectorStore:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self._embedding_model = None
        self.pool = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
    
    @property
    def embedding_model(self):
        """Lazy load the embedding model"""
        if self._embedding_model is None:
            ensure_embedding_dependencies()
            logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
            self._embedding_model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully!")
        return self._embedding_model
    
    async def init_database(self):
        """Initialize database with or without pgvector extension"""
        # Skip if already initialized
        if self.pool:
            logger.info("Database pool already initialized, skipping...")
            return

        self.pool = await asyncpg.create_pool(
            self.database_url,
            statement_cache_size=0,  # Fix for pgbouncer compatibility
            min_size=1,
            max_size=10,
            command_timeout=60  # Increased from 10 to 60 seconds for large table queries
        )
        
        self.has_pgvector = False
        
        async with self.pool.acquire() as conn:
            # Try to enable pgvector extension
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                self.has_pgvector = True
                logger.info("✅ pgvector extension enabled - using vector similarity")
            except Exception as e:
                logger.warning(f"⚠️ pgvector not available: {e}")
                logger.info("🔄 Using pure PostgreSQL with embedding similarity calculation")
                self.has_pgvector = False
            
            # Create documents table (with or without vector column)
            if self.has_pgvector:
                # Use vector column with pgvector
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(500) NOT NULL,
                        content TEXT NOT NULL,
                        page_number INTEGER,
                        chunk_index INTEGER,
                        embedding vector({self.embedding_dim}),
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Migration: Add embedding column if it doesn't exist (pgvector version)
                try:
                    await conn.execute(f"""
                        ALTER TABLE documents 
                        ADD COLUMN IF NOT EXISTS embedding vector({self.embedding_dim})
                    """)
                    logger.info("🔄 Migration: Added vector embedding column to existing table")
                except Exception as e:
                    logger.info(f"📋 Migration: vector embedding column already exists or migration not needed: {e}")
                
                # Create vector index for fast similarity search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                    ON documents USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
            else:
                # Use JSON column for embeddings without pgvector
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(500) NOT NULL,
                        content TEXT NOT NULL,
                        page_number INTEGER,
                        chunk_index INTEGER,
                        embedding JSONB,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Migration: Add embedding column if it doesn't exist
                try:
                    await conn.execute("""
                        ALTER TABLE documents 
                        ADD COLUMN IF NOT EXISTS embedding JSONB
                    """)
                    logger.info("🔄 Migration: Added embedding column to existing table")
                except Exception as e:
                    logger.info(f"📋 Migration: embedding column already exists or migration not needed: {e}")
                
                # Create index on embedding for better performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                    ON documents USING gin (embedding)
                """)
            
            # Create metadata indexes for filtering
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_filename_idx 
                ON documents (filename)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS documents_metadata_idx 
                ON documents USING gin (metadata)
            """)
            
            logger.info("✅ PostgreSQL vector database initialized")
    
    def _generate_embeddings(self, texts: List[str]):
        """Generate embeddings for a list of texts"""
        if not texts:
            return numpy.array([])
        
        # Generate embeddings using the model
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        return embeddings
    
    async def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """Add documents with embeddings to the database"""
        if not documents:
            return

        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()
        
        # Extract texts for embedding
        texts = [doc['content'] for doc in documents]
        logger.info(f"Generating embeddings for {len(texts)} documents...")
        
        # Generate embeddings
        embeddings = self._generate_embeddings(texts)
        
        # Get filename from metadata or first document
        filename = (metadata or {}).get('filename', 'unknown.pdf')
        if not filename and documents:
            filename = documents[0].get('filename', 'unknown.pdf')
        
        async with self.pool.acquire() as conn:
            # Insert documents with embeddings
            for i, doc in enumerate(documents):
                # For pgvector, we need to format the embedding as a string representation
                # of an array that PostgreSQL can cast to vector type
                if self.has_pgvector:
                    # Format as PostgreSQL array string: '[0.1, 0.2, ...]'
                    embedding_list = embeddings[i].tolist()
                    embedding_data = '[' + ','.join(map(str, embedding_list)) + ']'
                else:
                    # For JSONB column, JSON-encode the embedding
                    embedding_data = json.dumps(embeddings[i].tolist())
                
                # Combine document metadata with passed metadata
                doc_metadata = doc.get('metadata', {})
                if metadata:
                    doc_metadata.update(metadata)
                
                # Use proper type casting for pgvector
                if self.has_pgvector:
                    await conn.execute("""
                        INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata)
                        VALUES ($1, $2, $3, $4, $5::vector, $6)
                    """, 
                    filename,
                    doc['content'],
                    doc.get('page_number', 0),
                    doc.get('chunk_index', 0),
                    embedding_data,
                    json.dumps(doc_metadata)
                    )
                else:
                    await conn.execute("""
                        INSERT INTO documents (filename, content, page_number, chunk_index, embedding, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, 
                    filename,
                    doc['content'],
                    doc.get('page_number', 0),
                    doc.get('chunk_index', 0),
                    embedding_data,
                    json.dumps(doc_metadata)
                    )
        
        logger.info(f"✅ Added {len(documents)} documents with embeddings to PostgreSQL")
    
    async def search(self, query: str, n_results: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()

        # Generate query embedding
        query_embedding = self._generate_embeddings([query])[0]

        async with self.pool.acquire() as conn:
            if self.has_pgvector:
                # Use pgvector for efficient similarity search
                # Format query embedding as PostgreSQL array string
                query_vector = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                logger.info(f"🔍 Using pgvector to search ALL {await self.get_document_count():,} documents")
                rows = await conn.fetch("""
                    SELECT
                        filename, content, page_number, chunk_index, metadata,
                        1 - (embedding <=> $1::vector) as similarity,
                        (embedding <=> $1::vector) as distance
                    FROM documents
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                """, query_vector, n_results)
            else:
                # Calculate similarity in Python without pgvector
                # WARNING: Without pgvector, this loads ALL documents into memory
                # This is inefficient but ensures we search the full corpus
                logger.warning("⚠️ pgvector not available - using fallback Python similarity calculation")
                rows = await conn.fetch("""
                    SELECT filename, content, page_number, chunk_index, metadata, embedding
                    FROM documents
                    WHERE embedding IS NOT NULL
                """)

                logger.info(f"🔍 Calculating similarity for {len(rows):,} documents in Python")

                # Calculate cosine similarity for each document
                similarities = []
                for row in rows:
                    if row['embedding']:
                        # JSONB returns the embedding as already parsed JSON (list)
                        # But we need to handle both cases for safety
                        if isinstance(row['embedding'], str):
                            doc_embedding = numpy.array(json.loads(row['embedding']))
                        else:
                            doc_embedding = numpy.array(row['embedding'])
                        similarity = numpy.dot(query_embedding, doc_embedding) / (
                            numpy.linalg.norm(query_embedding) * numpy.linalg.norm(doc_embedding)
                        )
                        similarities.append((row, similarity, 1.0 - similarity))

                # Sort by similarity and take top results
                similarities.sort(key=lambda x: x[1], reverse=True)
                rows = [(row[0], row[1], row[2]) for row in similarities[:n_results]]
            
            results = []
            for item in rows:
                if self.has_pgvector:
                    # pgvector results have similarity/distance already calculated
                    row = item
                    # FIXED: Handle metadata - could be dict (JSONB), string (JSON), or None
                    # This prevents AttributeError: 'str' object has no attribute 'update'
                    try:
                        if row['metadata'] is None:
                            metadata = {}
                        elif isinstance(row['metadata'], dict):
                            metadata = row['metadata'].copy()  # Create a copy to avoid mutations
                        elif isinstance(row['metadata'], str):
                            try:
                                parsed = json.loads(row['metadata'])
                                # Ensure parsed result is a dict
                                metadata = parsed if isinstance(parsed, dict) else {}
                            except (json.JSONDecodeError, ValueError):
                                logger.warning(f"Failed to parse metadata JSON: {row['metadata'][:100]}")
                                metadata = {}
                        else:
                            logger.warning(f"Unexpected metadata type: {type(row['metadata'])}")
                            metadata = {}
                    except Exception as e:
                        logger.error(f"Error processing metadata: {e}")
                        metadata = {}

                    metadata.update({
                        'filename': row['filename'],
                        'page': row['page_number'] or 'N/A',
                        'page_number': row['page_number'],
                        'chunk_index': row['chunk_index']
                    })

                    # pgvector uses cosine DISTANCE (0=identical, 2=opposite)
                    # We store BOTH distance and similarity for compatibility
                    results.append({
                        'content': row['content'],
                        'metadata': metadata,
                        'distance': float(row['distance']),  # pgvector cosine distance (0-2)
                        'similarity': float(row['similarity']),  # converted to similarity (0-1)
                        'using_pgvector': True  # Flag to indicate pgvector was used
                    })
                else:
                    # Manual similarity calculation results (fallback without pgvector)
                    row, similarity, distance = item
                    # FIXED: Handle metadata - could be dict (JSONB), string (JSON), or None
                    # This prevents AttributeError: 'str' object has no attribute 'update'
                    try:
                        if row['metadata'] is None:
                            metadata = {}
                        elif isinstance(row['metadata'], dict):
                            metadata = row['metadata'].copy()  # Create a copy to avoid mutations
                        elif isinstance(row['metadata'], str):
                            try:
                                parsed = json.loads(row['metadata'])
                                # Ensure parsed result is a dict
                                metadata = parsed if isinstance(parsed, dict) else {}
                            except (json.JSONDecodeError, ValueError):
                                logger.warning(f"Failed to parse metadata JSON: {row['metadata'][:100]}")
                                metadata = {}
                        else:
                            logger.warning(f"Unexpected metadata type: {type(row['metadata'])}")
                            metadata = {}
                    except Exception as e:
                        logger.error(f"Error processing metadata: {e}")
                        metadata = {}

                    metadata.update({
                        'filename': row['filename'],
                        'page': row['page_number'] or 'N/A',
                        'page_number': row['page_number'],
                        'chunk_index': row['chunk_index']
                    })

                    # Fallback mode: similarity is already 0-1, distance is 1-similarity
                    results.append({
                        'content': row['content'],
                        'metadata': metadata,
                        'distance': float(distance),  # 1 - similarity
                        'similarity': float(similarity),  # cosine similarity (0-1)
                        'using_pgvector': False  # Flag to indicate fallback mode
                    })
        
        logger.info(f"Found {len(results)} similar documents for query")
        return results
    
    async def list_documents(self) -> Dict[str, Any]:
        """List all documents from books table with multi-author support"""
        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()
        
        async with self.pool.acquire() as conn:
            # Check if books table exists (for backward compatibility)
            books_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'books'
                )
            """)
            
            if books_exists:
                # Use new books table with multi-author support
                rows = await conn.fetch("""
                    WITH book_authors AS (
                        SELECT 
                            b.id,
                            b.filename,
                            b.title,
                            b.category,
                            b.document_type,
                            b.mc_press_url,
                            b.article_url,
                            b.total_pages,
                            b.processed_at,
                            COALESCE(
                                STRING_AGG(a.name, '; ' ORDER BY da.author_order),
                                'Unknown'
                            ) as authors,
                            COUNT(d.id) as chunk_count
                        FROM books b
                        LEFT JOIN document_authors da ON b.id = da.book_id
                        LEFT JOIN authors a ON da.author_id = a.id
                        LEFT JOIN documents d ON b.filename = d.filename
                        GROUP BY b.id, b.filename, b.title, b.category, 
                                 b.document_type, b.mc_press_url, b.article_url, 
                                 b.total_pages, b.processed_at
                        ORDER BY b.processed_at DESC
                    )
                    SELECT * FROM book_authors
                """)
                
                documents = []
                for row in rows:
                    documents.append({
                        'id': row['id'],
                        'filename': row['filename'],
                        'title': row['title'] or row['filename'].replace('.pdf', ''),
                        'author': row['authors'],  # Legacy field for compatibility
                        'authors': row['authors'].split('; ') if row['authors'] and row['authors'] != 'Unknown' else ['Unknown'],
                        'category': row['category'] or 'Uncategorized',
                        'document_type': row['document_type'] or 'book',
                        'mc_press_url': row['mc_press_url'],
                        'article_url': row['article_url'],
                        'total_pages': row['total_pages'] or 'N/A',
                        'chunk_count': row['chunk_count'] or 0,
                        'uploaded_at': row['processed_at'].isoformat() if row['processed_at'] else None
                    })
            else:
                # Fallback to old documents table aggregation
                rows = await conn.fetch("""
                    WITH doc_stats AS (
                        SELECT filename,
                               COUNT(*) as chunk_count,
                               MAX(page_number) as total_pages,
                               MIN(created_at) as uploaded_at
                        FROM documents
                        GROUP BY filename
                    ),
                    latest_metadata AS (
                        SELECT DISTINCT ON (filename)
                               filename,
                               metadata
                        FROM documents
                        ORDER BY filename, id DESC
                    )
                    SELECT ds.filename,
                           ds.chunk_count,
                           ds.total_pages,
                           ds.uploaded_at,
                           lm.metadata
                    FROM doc_stats ds
                    JOIN latest_metadata lm ON ds.filename = lm.filename
                    ORDER BY ds.uploaded_at DESC
                """)
                
                documents = []
                for row in rows:
                    # Handle metadata - could be dict, string, or None
                    metadata = row['metadata']
                    if metadata is None:
                        metadata = {}
                    elif isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    elif not isinstance(metadata, dict):
                        metadata = {}

                    author = metadata.get('author', 'Unknown') if isinstance(metadata, dict) else 'Unknown'
                    documents.append({
                        'filename': row['filename'],
                        'chunk_count': row['chunk_count'],
                        'total_pages': row['total_pages'] or 'N/A',
                        'uploaded_at': row['uploaded_at'].isoformat() if row['uploaded_at'] else None,
                        'author': author,  # Legacy field for compatibility
                        'authors': [author],  # Multi-author format
                        'category': metadata.get('category', 'Uncategorized') if isinstance(metadata, dict) else 'Uncategorized',
                        'title': metadata.get('title', row['filename'].replace('.pdf', '')) if isinstance(metadata, dict) else row['filename'].replace('.pdf', ''),
                        'mc_press_url': metadata.get('mc_press_url') if isinstance(metadata, dict) else None,
                        'document_type': 'book'  # Default for legacy data
                    })
        
        result = {'documents': documents}
        logger.info(f"📋 list_documents returning: {type(result)} with {len(documents)} documents from {'books' if books_exists else 'documents'} table")
        return result
    
    async def delete_by_filename(self, filename: str):
        """Delete all chunks for a specific filename"""
        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()

        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM documents WHERE filename = $1", filename)
            deleted_count = int(result.split()[-1])
            logger.info(f"Deleted {deleted_count} chunks for {filename}")

    async def update_document_metadata(self, filename: str, title: str, author: str, category: str = None, mc_press_url: str = None):
        """Update document metadata for all chunks of a specific filename"""
        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()

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
            logger.info(f"Updated metadata for {filename}: {metadata}")

    async def get_document_count(self) -> int:
        """Get total number of document chunks"""
        # Only init if pool doesn't exist
        if not self.pool:
            await self.init_database()
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            return count or 0
    
    def is_connected(self) -> bool:
        """Check if database pool is available"""
        return self.pool is not None
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            self.pool = None