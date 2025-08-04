from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncpg
import json
from typing import List, Dict, Any

app = FastAPI(title="MC Press PDF Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "MC Press PDF Chatbot API is running"}

@app.get("/")
async def root():
    return {
        "message": "MC Press PDF Chatbot API", 
        "version": "1.0.0",
        "status": "Demo Ready",
        "endpoints": ["/health", "/chat", "/documents"]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Demo chat endpoint - returns mock responses for now"""
    
    # Mock responses for demo
    mock_responses = [
        "I can help you find information about MC Press books and technical topics.",
        "Based on the documents I have access to, here's what I found...",
        "Let me search through the available PDF content for that information.",
        "I found several relevant sections in the uploaded documents.",
        "That's an interesting question about the technical documentation."
    ]
    
    import random
    response = random.choice(mock_responses)
    
    mock_sources = [
        {
            "filename": "mc_press_catalog.pdf",
            "page_number": 1,
            "content": "Sample content from MC Press catalog...",
            "relevance": 0.95
        }
    ]
    
    return ChatResponse(
        response=f"Demo Response: {response} (Question: {request.message})",
        sources=mock_sources
    )

@app.get("/documents")
async def list_documents():
    """Demo endpoint showing available documents"""
    return {
        "documents": {
            "mc_press_catalog.pdf": {
                "pages": 50,
                "uploaded_at": "2024-01-01T00:00:00Z",
                "status": "processed"
            },
            "technical_guide.pdf": {
                "pages": 25,
                "uploaded_at": "2024-01-02T00:00:00Z", 
                "status": "processed"
            }
        },
        "total_documents": 2,
        "status": "Demo ready - PostgreSQL integration available"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)