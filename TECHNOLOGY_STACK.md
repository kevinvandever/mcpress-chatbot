# MC Press Chatbot - Technology Stack & Architecture

**Last Updated**: October 7, 2025
**Owner**: Kevin Vandever
**Purpose**: Reference document for AI agents and future development

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Frontend (Netlify)](#frontend-netlify)
3. [Backend (Railway)](#backend-railway)
4. [Database & Vector Store](#database--vector-store)
5. [Key Configuration](#key-configuration)
6. [Deployment Process](#deployment-process)
7. [Known Issues & Solutions](#known-issues--solutions)
8. [Migration History](#migration-history)

---

## 🏗️ Architecture Overview

### Current Architecture (October 2025)

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                    (Netlify Deployment)                      │
│                                                              │
│  - React/TypeScript                                          │
│  - Vite Build System                                         │
│  - MC Press Design System                                    │
│  - Brand colors: #000080 (navy), #FF6B35 (coral)           │
│                                                              │
│  URL: https://mcpress-chatbot.netlify.app                   │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS/REST API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                              │
│                    (Railway Deployment)                      │
│                                                              │
│  - FastAPI (Python)                                          │
│  - Chat Handler (OpenAI GPT-3.5-turbo)                      │
│  - PDF Processor (PyMuPDF, sentence-transformers)           │
│  - Admin Endpoints                                           │
│                                                              │
│  URL: https://mcpress-chatbot-production.up.railway.app     │
└──────────────────────┬───────────────────────────────────────┘
                       │ asyncpg connection
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE & VECTORS                        │
│                    (Railway PostgreSQL)                      │
│                                                              │
│  - PostgreSQL 16+ with pgvector extension                   │
│  - 227,032 document chunks with embeddings                  │
│  - IVFFlat index for vector similarity                      │
│  - 384-dimension embeddings (all-MiniLM-L6-v2)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Frontend (Netlify)

### Technology Stack

| Component | Technology | Version/Notes |
|-----------|-----------|---------------|
| **Framework** | React | 18.x with TypeScript |
| **Build Tool** | Vite | Modern ES modules |
| **Styling** | Tailwind CSS | MC Press brand colors |
| **Components** | Custom Design System | Button, Input, Card |
| **State** | React hooks | No Redux/Zustand |
| **API Client** | fetch API | Native browser API |

### Key Files

```
frontend/
├── src/
│   ├── App.tsx                 # Main app component
│   ├── components/
│   │   ├── ChatInterface.tsx   # Main chat UI
│   │   ├── Button.tsx          # Brand button component
│   │   ├── Input.tsx           # Brand input component
│   │   └── Card.tsx            # Brand card component
│   ├── pages/
│   │   └── HomePage.tsx        # Landing page
│   └── styles/
│       └── index.css           # Tailwind + custom styles
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript config
└── package.json                # Dependencies
```

### Brand Colors

```css
/* MC Press Official Colors */
--mc-press-navy: #000080;      /* Primary brand color */
--mc-press-coral: #FF6B35;     /* Secondary/accent color */
--mc-press-light-gray: #F5F5F5;
--mc-press-dark-gray: #333333;
```

### Netlify Configuration

**Build Settings:**
- Build command: `cd frontend && npm install && npm run build`
- Publish directory: `frontend/dist`
- Node version: 18.x

**Environment Variables:**
```bash
VITE_API_URL=https://mcpress-chatbot-production.up.railway.app
```

**Deployment:**
- Automatic deploys from `main` branch
- Deploy previews for pull requests
- Build time: ~2-3 minutes
- CDN: Global edge network

---

## ⚙️ Backend (Railway)

### Technology Stack

| Component | Technology | Version/Notes |
|-----------|-----------|---------------|
| **Framework** | FastAPI | Modern async Python web framework |
| **Python** | 3.11+ | Required for asyncio features |
| **AI/ML** | OpenAI API | GPT-3.5-turbo for chat |
| **Embeddings** | sentence-transformers | all-MiniLM-L6-v2 model |
| **PDF Processing** | PyMuPDF (fitz) | Extract text, images, metadata |
| **Database** | asyncpg | Async PostgreSQL driver |
| **Vector Ops** | pgvector | PostgreSQL extension |

### Key Files

```
backend/
├── main.py                          # FastAPI app entry point
├── chat_handler.py                  # OpenAI integration + RAG
├── vector_store_postgres.py         # pgvector integration
├── pdf_processor_full.py            # PDF chunking + embedding
├── config.py                        # Configuration settings
├── background_embeddings.py         # Async embedding generation
├── admin_documents.py               # Document management endpoints
├── category_mapper.py               # Book categorization
└── requirements.txt                 # Python dependencies
```

### Core Dependencies

```
# requirements.txt (key packages)
fastapi==0.104.1
uvicorn[standard]==0.24.0
openai==1.3.5
sentence-transformers==2.2.2
PyMuPDF==1.23.8
asyncpg==0.29.0
python-dotenv==1.0.0
tiktoken==0.5.1
```

### Railway Configuration

**Service Type:** Web Service
**Region:** US East
**Runtime:** Python 3.11

**Start Command:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```bash
# Required
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway
USE_POSTGRESQL=true
OPENAI_API_KEY=sk-...

# Optional
RELEVANCE_THRESHOLD=0.55
MAX_SOURCES=12
INITIAL_SEARCH_RESULTS=30
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000
```

**Port:** Dynamic (`$PORT` assigned by Railway)

**Health Check:**
- Endpoint: `/health`
- Expected: `200 OK`
- Timeout: 30s

---

## 🗄️ Database & Vector Store

### PostgreSQL with pgvector

**Current State (October 2025):**
- **Database Type**: PostgreSQL 16 with pgvector extension
- **Total Documents**: 227,032 chunks
- **With Embeddings**: 188,672 (83%)
- **Embedding Dimension**: 384 (all-MiniLM-L6-v2)
- **Index Type**: IVFFlat with cosine distance
- **Storage**: ~2.5 GB (including indexes)

### Schema

```sql
-- Main documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    embedding vector(384),              -- pgvector type
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index (IVFFlat)
CREATE INDEX documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Metadata indexes
CREATE INDEX documents_filename_idx ON documents (filename);
CREATE INDEX documents_metadata_idx ON documents USING gin (metadata);
```

### Vector Search Query

```sql
-- Semantic similarity search using pgvector
SELECT
    filename, content, page_number, chunk_index, metadata,
    1 - (embedding <=> $1::vector) as similarity,  -- Convert to similarity
    (embedding <=> $1::vector) as distance         -- Cosine distance
FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector                  -- Sort by distance
LIMIT $2;
```

**Distance Metric Notes:**
- Operator: `<=>` (cosine distance)
- Range: 0 (identical) to 2 (opposite)
- Lower is better (closer match)
- `1 - distance` = similarity (0-1 scale)

### Embedding Model

**Model**: `all-MiniLM-L6-v2`
**Source**: sentence-transformers
**Dimension**: 384
**Speed**: ~40 docs/second
**Quality**: Good for semantic search, optimized for speed

**Embedding Process:**
1. Extract text chunks from PDFs (500-1000 chars)
2. Generate embeddings using sentence-transformers
3. Store in PostgreSQL as `vector(384)` type
4. Create IVFFlat index for fast similarity search

---

## ⚙️ Key Configuration

### Search Configuration

**File**: `backend/config.py`

```python
SEARCH_CONFIG = {
    # Distance threshold for relevance (0-2 scale, lower = more permissive)
    "relevance_threshold": 0.55,

    # Maximum sources to include in context
    "max_sources": 12,

    # Initial candidates to retrieve before filtering
    "initial_search_results": 30
}
```

**Why 0.55 threshold?**
- pgvector uses cosine distance (0=identical, 2=opposite)
- 0.55 distance ≈ 72.5% similarity
- Good balance between precision and recall
- Tested with 227k document corpus

### Dynamic Thresholds

**File**: `backend/chat_handler.py:230-258`

Different query types get different thresholds:

```python
# RPG/IBM i queries (very permissive)
rpg_keywords = ['subprocedure', 'subfile', 'rpg', 'ile', 'cl', 'db2', 'sql']
→ threshold: 0.70

# Code/technical queries (permissive)
code_keywords = ['function', 'class', 'method', 'error', 'code']
→ threshold: 0.65

# Setup/config queries (moderate)
tech_keywords = ['configure', 'install', 'setup', 'parameter']
→ threshold: 0.60

# Exact matches (strict)
'"quoted text"'
→ threshold: 0.40

# General queries (default)
Everything else
→ threshold: 0.55
```

### OpenAI Configuration

```python
OPENAI_CONFIG = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.3,        # Low for factual responses
    "max_tokens": 2000,        # Reasonable for book excerpts
    "stream": True             # Server-sent events
}
```

### Context Limits

```python
max_context_tokens = 6000     # Total context budget
# Breakdown:
# - System prompt: ~500 tokens
# - Retrieved context: ~5000 tokens
# - User query: ~100 tokens
# - Conversation history: ~400 tokens
```

---

## 🚀 Deployment Process

### Frontend (Netlify)

**Automatic Deployment:**
1. Push to `main` branch on GitHub
2. Netlify webhook triggers build
3. Build command: `cd frontend && npm install && npm run build`
4. Publish: `frontend/dist` directory
5. Deploy to CDN (~2-3 minutes)

**Manual Deployment:**
```bash
cd frontend
npm run build
netlify deploy --prod
```

### Backend (Railway)

**Automatic Deployment:**
1. Push to `main` branch (or manual trigger in Railway dashboard)
2. Railway detects Python project
3. Installs dependencies: `pip install -r requirements.txt`
4. Starts service: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Health check on `/health` endpoint
6. Deploy complete (~3-5 minutes)

**Manual Deployment:**
```bash
# Trigger redeploy in Railway dashboard
# OR update environment variable to force restart
railway up
```

**Startup Verification:**

Check Railway logs for:
```
✅ Vector Store Class: PostgresVectorStore
📊 pgvector enabled: True
📊 Total documents in database: 227,032
✅ Using native pgvector with cosine distance operator
```

---

## 🐛 Known Issues & Solutions

### Issue 1: Search Returns Too Few Results

**Symptoms:**
- Only 0-3 sources returned
- Confidence scores very low
- Generic answers without book excerpts

**Cause:**
- Threshold too high (> 0.65)
- 5,000 document limit in fallback mode

**Solution:**
```python
# backend/config.py
"relevance_threshold": 0.55  # NOT 0.75!

# backend/vector_store_postgres.py
# Remove LIMIT 5000 from fallback query
# Ensure pgvector is enabled
```

### Issue 2: Metadata AttributeError

**Symptoms:**
```
AttributeError: 'str' object has no attribute 'update'
```

**Cause:**
- PostgreSQL returns JSONB as dict
- Some rows have JSON strings
- Metadata could be None

**Solution:**
```python
# Robust metadata handling
if row['metadata'] is None:
    metadata = {}
elif isinstance(row['metadata'], dict):
    metadata = row['metadata'].copy()
elif isinstance(row['metadata'], str):
    metadata = json.loads(row['metadata'])
```

### Issue 3: pgvector Not Detected

**Symptoms:**
```
⚠️ pgvector not available
🔄 Using pure PostgreSQL with embedding similarity calculation
```

**Cause:**
- DATABASE_URL points to wrong database
- pgvector extension not installed

**Solution:**
```sql
-- Connect to Railway database
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Issue 4: Railway Deployment Timeout

**Symptoms:**
- Health check fails
- Deployment timeout after 10 minutes

**Cause:**
- Database connection timeout (10s default)
- Large table queries during startup

**Solution:**
```python
# backend/vector_store_postgres.py
self.pool = await asyncpg.create_pool(
    self.database_url,
    statement_cache_size=0,
    min_size=1,
    max_size=10,
    command_timeout=60  # Increased from 10s
)
```

---

## 📜 Migration History

### Timeline

| Date | Migration | Status | Notes |
|------|-----------|--------|-------|
| **Aug 2024** | ChromaDB | ✅ Working | Local file-based vector DB |
| **Sep 2024** | PostgreSQL (no pgvector) | ⚠️ Limited | 5k doc limit, Python similarity |
| **Oct 5, 2024** | pgvector Migration Start | 🚧 In Progress | New Railway DB with pgvector |
| **Oct 6, 2024** | pgvector Deployed | ❌ Poor Results | Wrong config, 5k limit |
| **Oct 7, 2024 AM** | "Fix" Attempt | ❌ Made Worse | Increased threshold to 0.75 |
| **Oct 7, 2024 PM** | Proper Fixes | ✅ Current | This document's fixes |

### What Changed in Each Migration

**ChromaDB → PostgreSQL (no pgvector):**
```diff
- ChromaDB local file storage
+ PostgreSQL with JSONB embeddings
+ Async database operations
- 5,000 document search limit added (bottleneck)
- Python-based similarity calculation (slow)
```

**PostgreSQL → pgvector:**
```diff
+ Native vector operations (100x faster)
+ IVFFlat index for similarity search
+ Can search all 227k documents efficiently
+ Cosine distance operator <=>
- Initially configured wrong (5k limit, high threshold)
```

### Key Learnings

1. **Don't increase thresholds blindly** - Higher threshold = FEWER results (not better)
2. **pgvector needs different thresholds** - Cosine distance semantics differ from similarity
3. **Remove artificial limits** - pgvector is fast enough to search everything
4. **Test after migration** - Always verify with actual queries
5. **Add logging early** - Helps diagnose issues quickly

---

## 📊 Performance Metrics

### Current Performance (with fixes)

| Metric | Value | Notes |
|--------|-------|-------|
| **Search Speed** | <500ms | Database-level vector ops |
| **Sources Returned** | 5-12 | Depends on query |
| **Confidence Score** | 0.3-0.8 | Average ~0.55 |
| **Context Tokens** | 2000-5000 | Fits in GPT-3.5 context |
| **Search Space** | 227,032 docs | Full corpus |
| **Embedding Speed** | 40 docs/sec | Sentence-transformers |

### Before Fixes (Oct 7 AM)

| Metric | Value | Impact |
|--------|-------|--------|
| Search Speed | <500ms | Good |
| Sources Returned | 0-3 | ❌ Too few |
| Confidence Score | 0.1-0.3 | ❌ Too low |
| Search Space | 5,000 docs | ❌ 2% of corpus |
| Threshold | 0.75 | ❌ Too strict |

---

## 🔐 Security Notes

### API Keys
- OpenAI API key in Railway environment variables (never commit)
- Database password in Railway environment variables
- Frontend has no secrets (public API URL only)

### Database Access
- Railway provides internal network access
- External access via proxy with SSL
- Connection pooling limits (max 10)

### Rate Limiting
- OpenAI: Pay-as-you-go (no hard limit)
- Railway: Fair use policy
- Netlify: 100GB/month bandwidth

---

## 🎯 Quick Reference for AI Agents

### Common Tasks

**Deploy frontend changes:**
```bash
git add frontend/
git commit -m "Update frontend"
git push origin main
# Netlify auto-deploys in 2-3 min
```

**Deploy backend changes:**
```bash
git add backend/
git commit -m "Update backend"
git push origin main
# Railway auto-deploys in 3-5 min
```

**Test search locally:**
```bash
cd /Users/kevinvandever/kev-dev/mcpress-chatbot
python3 test_fixes_local.py
```

**Test production deployment:**
```bash
python3 test_pgvector_chatbot.py
```

**Check Railway logs:**
```bash
# In Railway dashboard: Deployments > [latest] > View Logs
# Or use CLI:
railway logs
```

**Adjust search threshold:**
```python
# backend/config.py
"relevance_threshold": 0.55  # Lower = more results, Higher = fewer results
```

### Important Constraints

1. **Never increase threshold above 0.65** - Will return too few results
2. **Always use pgvector** - 100x faster than Python fallback
3. **Test with real queries** - "What is RPG programming?" should return 5+ sources
4. **Check startup logs** - Verify pgvector is enabled
5. **Keep 5k limit removed** - Only limit final results, not search space

---

## 📞 Support

**Issues:** https://github.com/kevinvandever/mcpress-chatbot/issues
**Owner:** Kevin Vandever
**Contact:** kevin@kevinvandever.com

---

**Document Version:** 1.0
**Last Updated:** October 7, 2025
**Next Review:** When making infrastructure changes
