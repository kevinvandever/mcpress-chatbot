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

# Convert paths to strings for compatibility
CHROMA_PERSIST_DIR = str(CHROMA_PERSIST_DIR)
UPLOAD_DIR = str(UPLOAD_DIR)