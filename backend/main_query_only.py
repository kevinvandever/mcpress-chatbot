"""
Simplified Query-Only Backend for Railway Deployment
No PDF processing - just vector search and chat
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
from sentence_transformers import SentenceTransformer
import numpy as np

load_dotenv()

app = FastAPI(title="MC Press Chatbot Query API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",
        os.getenv("CORS_ORIGIN", "*")
    ],
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
    title: str
    author: str
    category: str
    total_pages: int

class SearchResult(BaseModel):
    content: str
    book_title: str
    author: str
    page: int
    relevance: float

class QueryOnlyBackend:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.embedding_model = None
        self.pool = None
        
    async def init(self):
        """Initialize connection pool and model"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        
        if not self.embedding_model:
            print("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Model loaded successfully!")
    
    async def search_similar(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[SearchResult]:
        """Search for similar content in the vector database"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        async with self.pool.acquire() as conn:
            # Build query with optional category filter
            if category:
                results = await conn.fetch("""
                    SELECT 
                        e.content,
                        e.page_number,
                        b.title,
                        b.author,
                        b.category,
                        1 - (e.embedding <=> $1::vector) as similarity
                    FROM embeddings e
                    JOIN books b ON e.book_id = b.id
                    WHERE b.category = $2
                    ORDER BY e.embedding <=> $1::vector
                    LIMIT $3
                """, query_embedding, category, limit)
            else:
                results = await conn.fetch("""
                    SELECT 
                        e.content,
                        e.page_number,
                        b.title,
                        b.author,
                        b.category,
                        1 - (e.embedding <=> $1::vector) as similarity
                    FROM embeddings e
                    JOIN books b ON e.book_id = b.id
                    ORDER BY e.embedding <=> $1::vector
                    LIMIT $2
                """, query_embedding, limit)
            
            return [
                SearchResult(
                    content=r['content'],
                    book_title=r['title'],
                    author=r['author'],
                    page=r['page_number'],
                    relevance=float(r['similarity'])
                )
                for r in results
            ]
    
    async def get_books_info(self) -> List[BookInfo]:
        """Get information about all books in the database"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT DISTINCT title, author, category, total_pages
                FROM books
                ORDER BY title
            """)
            
            return [
                BookInfo(
                    title=r['title'],
                    author=r['author'] or 'Unknown',
                    category=r['category'] or 'General',
                    total_pages=r['total_pages'] or 0
                )
                for r in results
            ]
    
    async def get_categories(self) -> List[str]:
        """Get all available categories"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT DISTINCT category 
                FROM books 
                WHERE category IS NOT NULL
                ORDER BY category
            """)
            return [r['category'] for r in results]

# Initialize backend
backend = QueryOnlyBackend()

@app.on_event("startup")
async def startup_event():
    """Initialize backend on startup"""
    await backend.init()
    
    # Test database connection
    try:
        async with backend.pool.acquire() as conn:
            book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
            embedding_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
            print(f"✅ Database connected: {book_count} books, {embedding_count} embeddings")
    except Exception as e:
        print(f"❌ Database connection error: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "MC Press Chatbot Query API v2",
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
        results = await backend.search_similar(
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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with context from search results"""
    try:
        # First, search for relevant content
        search_results = await backend.search_similar(
            query=request.message,
            limit=3
        )
        
        # Build context from search results
        context = "\n\n".join([
            f"From '{r.book_title}' by {r.author} (page {r.page}):\n{r.content}"
            for r in search_results
        ])
        
        # For demo, return a structured response with the context
        # In production, you'd call an LLM here
        response = {
            "response": f"Based on the MC Press books, here's relevant information about '{request.message}':",
            "context": context,
            "sources": [
                {
                    "title": r.book_title,
                    "author": r.author,
                    "page": r.page
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

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        async with backend.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT id) as total_books,
                    COUNT(DISTINCT category) as total_categories,
                    COUNT(DISTINCT author) as total_authors,
                    (SELECT COUNT(*) FROM embeddings) as total_chunks,
                    SUM(total_pages) as total_pages
                FROM books
            """)
            
            return {
                "books": stats['total_books'],
                "categories": stats['total_categories'],
                "authors": stats['total_authors'],
                "chunks": stats['total_chunks'],
                "pages": stats['total_pages']
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)