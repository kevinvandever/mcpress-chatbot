import os
from pathlib import Path

# Base data directory
# Railway persistence configuration
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

if IS_RAILWAY:
    # Check for Railway volume first (persistent), fallback to ephemeral
    if Path("/data").exists():
        DATA_DIR = Path("/data")
        print(f"✅ Using Railway VOLUME (persistent) at {DATA_DIR}")
    elif Path("/mnt/data").exists():
        DATA_DIR = Path("/mnt/data") 
        print(f"✅ Using Railway VOLUME (persistent) at {DATA_DIR}")
    else:
        DATA_DIR = Path("/app/data")
        print(f"⚠️  Using Railway ephemeral storage at {DATA_DIR}")
        print("❌ WARNING: Data will be LOST on redeploys! Set up a Railway Volume!")
else:
    # Local development
    DATA_DIR = Path("./")

if not DATA_DIR.exists():
    DATA_DIR.mkdir(exist_ok=True, parents=True)

# Create subdirectories
if IS_RAILWAY:
    # Use persistent directory subdirectories
    CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"
    UPLOAD_DIR = DATA_DIR / "uploads"
else:
    # Local development paths
    CHROMA_PERSIST_DIR = Path("./backend/chroma_db")
    UPLOAD_DIR = Path("./backend/uploads")

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

# Set CHROMA_DB_PATH environment variable for the vector store
# This ensures ChromaVectorStore uses the same persistent path
os.environ["CHROMA_DB_PATH"] = CHROMA_PERSIST_DIR
os.environ["DATA_DIR"] = str(DATA_DIR)
os.environ["UPLOAD_DIR"] = UPLOAD_DIR