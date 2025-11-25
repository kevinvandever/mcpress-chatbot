# Technology Stack

## Architecture
- **Monorepo**: Frontend and backend in single repository
- **Deployment**: Railway (backend), Netlify (frontend)
- **Database**: Supabase PostgreSQL 16+ with pgvector extension

## Backend Stack

### Core Framework
- **Language**: Python 3.11+
- **Framework**: FastAPI (async)
- **Server**: Uvicorn with async support
- **Database Driver**: asyncpg (async PostgreSQL)

### AI/ML Components
- **LLM**: OpenAI GPT-4 (gpt-4o-mini model)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- **Vector Search**: pgvector with cosine distance operator (`<=>`)
- **Token Counting**: tiktoken

### PDF Processing
- **Primary**: PyMuPDF (fitz) for text/image extraction
- **Supplementary**: pdfplumber, pytesseract for OCR
- **Text Splitting**: langchain-text-splitters (recursive character splitter)
- **Chunk Size**: ~1000 characters with 200 character overlap

### Key Dependencies
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
openai>=1.3.0
sentence-transformers>=2.2.2
asyncpg>=0.29.0
PyMuPDF>=1.23.0
```

## Frontend Stack

### Core Framework
- **Framework**: Next.js 14.0.3
- **Language**: TypeScript 5.x
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3.3

### Key Dependencies
- **HTTP Client**: axios
- **Markdown**: react-markdown with remark-gfm
- **Code Highlighting**: react-syntax-highlighter
- **File Upload**: react-dropzone

### Build Configuration
- **Build Command**: `SKIP_TYPE_CHECK=true next build`
- **Type Checking**: Disabled for builds (legacy codebase)
- **ESLint**: Disabled during builds

## Database Schema

### Primary Table
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    embedding vector(384),  -- pgvector type
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index
CREATE INDEX documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Testing and Deployment Workflow

### CRITICAL: All Testing is Done on Railway
- **NO LOCAL TESTING**: Do not attempt to run tests locally
- **NO LOCAL DATABASE**: There is no local database setup
- **Railway-only**: All tests, migrations, and database operations must be executed on Railway
- **Test execution**: Push code to trigger Railway deployment, then run tests via Railway CLI or SSH

### Backend (Railway)
- **Auto-deploy**: Push to `main` branch triggers Railway deployment
- **Manual deploy**: Trigger redeploy in Railway dashboard
- **Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Health check**: `/health` endpoint
- **Deploy time**: ~10-15 minutes
- **Run tests on Railway**: Use Railway CLI or connect via SSH to execute pytest

### Frontend (Netlify)
- **Auto-deploy**: Push to `main` branch triggers Netlify deployment
- **Build command**: `cd frontend && npm install && npm run build`
- **Publish directory**: `frontend/dist`
- **Deploy time**: ~2-3 minutes

### Database Operations
```bash
# Run migrations (via Railway or direct connection)
python backend/run_migration_003.py

# Check database status
python check_pgvector.py
```

## Environment Variables

### Backend (Railway)
```
DATABASE_URL=postgresql://...
USE_POSTGRESQL=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.5
OPENAI_MAX_TOKENS=3000
RELEVANCE_THRESHOLD=0.55
MAX_SOURCES=12
INITIAL_SEARCH_RESULTS=30
```

### Frontend (Netlify)
```
VITE_API_URL=https://mcpress-chatbot-production.up.railway.app
```

## Critical Configuration Notes

### Vector Search Thresholds
- **pgvector uses cosine distance**: 0 = identical, 2 = opposite
- **Lower threshold = more permissive** (returns more results)
- **Default threshold**: 0.55 (DO NOT increase above 0.65)
- **Dynamic thresholds** in `chat_handler.py` adjust based on query type

### Import Paths
- **Railway deployment**: Use `backend.module_name` format
- **Local development**: Use relative imports or `backend.module_name`
- **Always test imports work in both environments**

## Performance Targets
- **Vector Search**: <500ms
- **Chat First Token**: 1-3 seconds
- **PDF Processing**: 2-5 seconds per document
- **Embedding Generation**: ~40 docs/second
