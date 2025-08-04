import os
import warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from dotenv import load_dotenv

from vector_store import VectorStore

load_dotenv()

app = FastAPI(title="MC Press Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "endpoints": ["/health", "/chat", "/documents"]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)