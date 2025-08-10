import os
from pathlib import Path

# Base data directory - use existing structure for local development
# In production, this uses /app/data, but for local dev we use existing paths
DATA_DIR = Path(os.getenv("DATA_DIR", "./"))
if not DATA_DIR.exists():
    DATA_DIR.mkdir(exist_ok=True)

# Create subdirectories - use existing paths for local development
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_DB_PATH", "./backend/chroma_db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./backend/uploads"))

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