import os
from pathlib import Path

# Base data directory - single volume mount point
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
DATA_DIR.mkdir(exist_ok=True)

# Create subdirectories
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure subdirectories exist
CHROMA_PERSIST_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Other config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["*"]')

# OpenAI Configuration
OPENAI_CONFIG = {
    "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
    "stream": True
}

# Vector Search Configuration
SEARCH_CONFIG = {
    "relevance_threshold": float(os.getenv("RELEVANCE_THRESHOLD", "0.7")),
    "max_sources": int(os.getenv("MAX_SOURCES", "8")),
    "initial_search_results": int(os.getenv("INITIAL_SEARCH_RESULTS", "10"))
}

# Response Configuration
RESPONSE_CONFIG = {
    "max_conversation_history": int(os.getenv("MAX_CONVERSATION_HISTORY", "10")),
    "include_metadata": os.getenv("INCLUDE_METADATA", "true").lower() == "true",
    "include_confidence_score": os.getenv("INCLUDE_CONFIDENCE_SCORE", "true").lower() == "true"
}

# Convert paths to strings for compatibility
CHROMA_PERSIST_DIR = str(CHROMA_PERSIST_DIR)
UPLOAD_DIR = str(UPLOAD_DIR)