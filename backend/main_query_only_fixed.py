"""
Fixed Query-Only Backend for Railway Deployment
Works with the actual documents table structure
"""

import os
import warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from dotenv import load_dotenv
import asyncpg

load_dotenv()

app = FastAPI(title="MC Press Chatbot Query API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for maximum compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = 5

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Dict]] = []
    stream: bool = False

class BookInfo(BaseModel):
    filename: str
    title: str
    author: str
    category: str
    total_chunks: int
    total_pages: int
    has_images: bool = False
    has_code: bool = False

class SearchResult(BaseModel):
    content: str
    filename: str
    page: int
    metadata: Dict

class QueryOnlyBackend:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.pool = None
        
    async def init(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
    
    async def text_search(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[SearchResult]:
        """Search using PostgreSQL text search (no embeddings)"""
        async with self.pool.acquire() as conn:
            # Use text search since we don't have vector embeddings
            if category:
                results = await conn.fetch("""
                    SELECT 
                        content,
                        filename,
                        page_number,
                        metadata,
                        ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank
                    FROM documents
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                        AND metadata->>'category' = $2
                    ORDER BY rank DESC
                    LIMIT $3
                """, query, category, limit)
            else:
                results = await conn.fetch("""
                    SELECT 
                        content,
                        filename,
                        page_number,
                        metadata,
                        ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank
                    FROM documents
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC
                    LIMIT $2
                """, query, limit)
            
            return [
                SearchResult(
                    content=r['content'],
                    filename=r['filename'],
                    page=r['page_number'],
                    metadata=json.loads(r['metadata']) if r['metadata'] else {}
                )
                for r in results
            ]
    
    async def get_books_info(self) -> List[BookInfo]:
        """Get information about all books in the database"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    filename,
                    COUNT(*) as chunk_count,
                    MAX(page_number) as max_page,
                    (array_agg(metadata))[1] as sample_metadata
                FROM documents
                GROUP BY filename
                ORDER BY filename
            """)
            
            books = []
            for r in results:
                # Get first chunk's metadata for this book
                first_chunk = await conn.fetchrow("""
                    SELECT metadata 
                    FROM documents 
                    WHERE filename = $1 
                    LIMIT 1
                """, r['filename'])
                
                metadata = json.loads(first_chunk['metadata']) if first_chunk and first_chunk['metadata'] else {}
                
                # Fix page count issue - if max_page is 0, estimate from chunk count
                # Most books have ~2-4 chunks per page, so divide by 3 as reasonable estimate
                estimated_pages = max(1, r['chunk_count'] // 3) if (r['max_page'] or 0) == 0 else r['max_page']
                
                # Check for images and code in this book
                content_types = await conn.fetch("""
                    SELECT DISTINCT metadata->>'type' as content_type
                    FROM documents 
                    WHERE filename = $1 AND metadata->>'type' IS NOT NULL
                """, r['filename'])
                
                types = [row['content_type'] for row in content_types if row['content_type']]
                has_images = 'image' in types
                has_code = 'code' in types
                
                # Ensure no None values
                books.append(BookInfo(
                    filename=r['filename'],
                    title=metadata.get('title') or r['filename'].replace('.pdf', ''),
                    author=metadata.get('author') or 'Unknown',
                    category=metadata.get('category') or 'General',
                    total_chunks=r['chunk_count'],
                    total_pages=estimated_pages,
                    has_images=has_images,
                    has_code=has_code
                ))
            
            return books
    
    async def get_categories(self) -> List[str]:
        """Get all available categories"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT DISTINCT metadata->>'category' as category
                FROM documents
                WHERE metadata->>'category' IS NOT NULL
                ORDER BY metadata->>'category'
            """)
            return [r['category'] for r in results if r['category']]

# Initialize backend
backend = QueryOnlyBackend()

@app.on_event("startup")
async def startup_event():
    """Initialize backend on startup"""
    await backend.init()
    
    # Test database connection
    try:
        async with backend.pool.acquire() as conn:
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            file_count = await conn.fetchval("SELECT COUNT(DISTINCT filename) FROM documents")
            print(f"✅ Database connected: {file_count} books, {doc_count} document chunks")
    except Exception as e:
        print(f"❌ Database connection error: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "MC Press Chatbot Query API v3",
        "mode": "query-only",
        "info": "This is a read-only API. Books are pre-processed."
    }

@app.get("/api/books")
async def get_books():
    """Get list of all available books"""
    try:
        books = await backend.get_books_info()
        return {
            "total": len(books),
            "books": [book.dict() for book in books]
        }
    except Exception as e:
        print(f"Error in /api/books: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/categories")
async def get_categories():
    """Get all available categories"""
    try:
        categories = await backend.get_categories()
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search(request: QueryRequest):
    """Search for similar content"""
    try:
        results = await backend.text_search(
            query=request.query,
            category=request.category,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": [r.dict() for r in results],
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_get(q: str, n_results: int = 5, filename: str = None, content_types: str = None):
    """Search endpoint for GET requests (legacy compatibility)"""
    try:
        results = await backend.text_search(
            query=q,
            category=None,
            limit=n_results
        )
        
        # Convert to legacy format
        legacy_results = []
        for r in results:
            legacy_results.append({
                "content": r.content,
                "metadata": {
                    "filename": r.filename,
                    "page_number": r.page,
                    **r.metadata
                },
                "distance": 0.5  # Mock distance for compatibility
            })
        
        return {"query": q, "results": legacy_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with context from search results"""
    try:
        # First, search for relevant content
        search_results = await backend.text_search(
            query=request.message,
            limit=3
        )
        
        # Build context from search results
        context = "\n\n".join([
            f"From '{r.filename}' (page {r.page}):\n{r.content}"
            for r in search_results
        ])
        
        # For demo, return a structured response with the context
        response = {
            "response": f"Based on the MC Press books, here's relevant information about '{request.message}':",
            "context": context,
            "sources": [
                {
                    "filename": r.filename,
                    "page": r.page,
                    "metadata": r.metadata
                }
                for r in search_results
            ]
        }
        
        if request.stream:
            # Simulate streaming response
            async def generate():
                for word in response["response"].split():
                    yield json.dumps({"chunk": word + " "}) + "\n"
                    await asyncio.sleep(0.05)
                yield json.dumps({"context": context, "sources": response["sources"]}) + "\n"
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documents/{filename}/metadata")
async def update_document_metadata(filename: str):
    """Update document metadata - READ-ONLY mode returns success"""
    # Since this is a read-only backend, we'll return success without making changes
    return {
        "status": "success",
        "message": f"Metadata update requested for {filename} (read-only mode)",
        "note": "This is a query-only backend. Updates are not persisted."
    }

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        async with backend.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT filename) as total_books,
                    COUNT(DISTINCT metadata->>'category') as total_categories,
                    COUNT(DISTINCT metadata->>'author') as total_authors,
                    COUNT(*) as total_chunks,
                    MAX(page_number) as max_pages
                FROM documents
            """)
            
            # Fix stats to show estimated pages instead of 0
            total_chunks = stats['total_chunks'] or 0
            estimated_total_pages = max(1, total_chunks // 3) if total_chunks > 0 else 0
            
            return {
                "books": stats['total_books'] or 0,
                "categories": stats['total_categories'] or 0,
                "authors": stats['total_authors'] or 0,
                "chunks": total_chunks,
                "pages": estimated_total_pages  # Return estimated pages instead of 0
            }
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)