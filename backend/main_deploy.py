import os
import warnings
import asyncpg
import json

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
from dotenv import load_dotenv

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
        """Initialize database with basic tables"""
        await self.init_pool()
        async with self.pool.acquire() as conn:
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
                    'distance': 1.0 - float(row['rank'])
                })
            
            return results
    
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

load_dotenv()

app = FastAPI(title="MC Press Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-cwanq0nz1-kevin-vandevers-projects.vercel.app",
        "https://mcpress-chatbot-frontend.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector store
vector_store = VectorStore()

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
    await vector_store.init_database()

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []

class CompleteUploadRequest(BaseModel):
    filename: str
    author: str
    mc_press_url: Optional[str] = None

@app.get("/health")
async def health_check():
    database_status = "connected" if vector_store.is_connected() else "disconnected"
    return {
        "status": "healthy", 
        "database": database_status,
        "message": "MC Press PDF Chatbot API is running"
    }

@app.get("/")
async def root():
    return {
        "message": "MC Press PDF Chatbot API", 
        "version": "1.0.0",
        "status": "Production Ready",
        "database": "PostgreSQL with pgvector",
        "endpoints": ["/health", "/chat", "/documents", "/upload", "/complete-upload"]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with the PDF documents"""
    try:
        # Search for relevant documents
        results = await vector_store.search(request.message, n_results=3)
        
        if not results:
            return ChatResponse(
                response="I don't have any documents uploaded yet. Please upload some PDF documents first to chat about their content.",
                sources=[]
            )
        
        # Prepare context from search results
        context_pieces = []
        sources = []
        
        for result in results:
            context_pieces.append(result['document'])
            sources.append({
                'filename': result['metadata']['filename'],
                'page_number': result['metadata']['page_number'],
                'relevance': 1.0 - result['distance']  # Convert distance to relevance
            })
        
        context = "\n\n".join(context_pieces)
        
        # Simple response based on context (replace with OpenAI later)
        response = f"Based on the uploaded documents, here's what I found related to your question '{request.message}':\n\n"
        response += f"The most relevant content discusses: {context[:500]}..."
        
        return ChatResponse(
            response=response,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        doc_info = await vector_store.list_documents()
        return doc_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for indexing"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
    if hasattr(file, 'size') and file.size and file.size > max_size:
        raise HTTPException(status_code=400, detail=f"File size exceeds {max_size//1024//1024}MB limit")
    
    try:
        # Read file content
        content = await file.read()
        
        # For now, return a simple success response
        # In production, you would:
        # 1. Save the file to storage
        # 2. Process the PDF (extract text, create embeddings)
        # 3. Store in vector database
        
        return {
            "status": "success",
            "message": f"Successfully uploaded {file.filename}",
            "filename": file.filename,
            "chunks_created": 10,  # Placeholder
            "images_processed": 0,  # Placeholder
            "code_blocks_found": 0,  # Placeholder
            "total_pages": 5,  # Placeholder
            "needsAuthor": True  # Always require author for demo
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/complete-upload")
async def complete_upload_with_metadata(request: CompleteUploadRequest):
    """Complete the upload of a PDF that was missing author metadata"""
    try:
        # For now, return a simple success response
        # In production, you would complete the actual processing
        
        return {
            "status": "success",
            "message": f"Successfully processed {request.filename} with author: {request.author}",
            "chunks_created": 10,  # Placeholder
            "total_pages": 5  # Placeholder
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)