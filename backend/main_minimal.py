"""
Minimal FastAPI app to test if Railway deployment works at all
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MC Press Chatbot API - Minimal")

# Basic CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "Minimal API is running",
        "version": "minimal-test",
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "port": os.getenv("PORT", "8080")
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "minimal": True
    }

@app.get("/test")
def test_endpoint():
    return {"test": "working"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)