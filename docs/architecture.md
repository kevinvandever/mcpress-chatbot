# MC Press Chatbot - System Architecture Document

**Version:** 1.0  
**Date:** September 22, 2025  
**Type:** Brownfield Documentation  
**Current State:** Production Deployed on Railway with Supabase Database

---

## Executive Summary

The MC Press Chatbot is a specialized AI-powered assistant for IBM i professionals, providing semantic search and conversational AI across MC Press technical documentation. The system is currently deployed on Railway with a Supabase PostgreSQL backend using pgvector for efficient vector similarity search.

---

## System Overview

### Core Capabilities
- **PDF Processing**: Extract and index technical books and articles
- **Semantic Search**: Vector-based similarity search using embeddings
- **Conversational AI**: GPT-4 powered chat interface
- **E-commerce Integration**: Direct purchase links to MC Store
- **Persistent Storage**: PostgreSQL with pgvector extension

### Current Statistics
- **Documents Indexed**: 5 complete books (1,698 chunks)
- **Pending Upload**: 110+ additional PDFs identified
- **Search Performance**: ~433ms average response time
- **Vector Dimensions**: 384-dimensional embeddings

---

## Technical Stack

### Frontend
- **Framework**: Next.js 14.0.3
- **Language**: TypeScript 5.x
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3.3
- **Components**:
  - `ChatInterface.tsx` - Main chat UI
  - `CompactSources.tsx` - Source attribution display
  - `FileUpload.tsx` - PDF upload interface
  - `SearchInterface.tsx` - Search functionality (to be removed)
  - `DocumentList.tsx` - Document management
  - `BatchUpload.tsx` - Bulk upload interface
- **Key Dependencies**:
  - axios - API communication
  - react-markdown - Markdown rendering
  - react-dropzone - File upload handling
  - react-syntax-highlighter - Code display

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Server**: Uvicorn with async support
- **Core Modules**:
  - `main.py` - API endpoints and routing
  - `pdf_processor_full.py` - PDF extraction pipeline
  - `chat_handler.py` - Chat orchestration
  - `vector_store_postgres.py` - PostgreSQL/pgvector integration
  - `vector_store_chroma.py` - ChromaDB fallback
  - `async_upload.py` - Asynchronous upload handling
- **Key Dependencies**:
  - OpenAI API - GPT-4 integration
  - sentence-transformers - Embedding generation
  - PyMuPDF - PDF processing
  - asyncpg - PostgreSQL async driver
  - chromadb - Vector database fallback

### Database
- **Primary**: Supabase PostgreSQL
  - pgvector extension for vector similarity
  - JSONB for metadata storage
  - 384-dimensional vector embeddings
- **Connection**: Session pooler for IPv4 compatibility
- **Schema**:
  ```sql
  documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    content TEXT,
    metadata JSONB,
    embedding JSONB,  -- 384-dim vectors
    created_at TIMESTAMP
  )
  ```

### Infrastructure
- **Hosting**: Railway (Backend + Frontend)
- **Database**: Supabase (PostgreSQL + pgvector)
- **Storage**: Temporary file storage for uploads
- **Environment**: Production deployment at https://mcpress-chatbot-production-569b.up.railway.app

---

## System Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                │
│  ┌──────────────────────────────────────────────┐  │
│  │          Chat Interface Component            │  │
│  │  ┌────────┐  ┌──────────┐  ┌────────────┐  │  │
│  │  │  Chat  │  │  Sources  │  │   Upload   │  │  │
│  │  └────────┘  └──────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTPS/REST
┌──────────────────▼──────────────────────────────────┐
│                Backend (FastAPI)                    │
│  ┌──────────────────────────────────────────────┐  │
│  │              API Layer                       │  │
│  │  ┌────────┐  ┌──────────┐  ┌────────────┐  │  │
│  │  │  Chat  │  │  Upload  │  │  Documents  │  │  │
│  │  └────────┘  └──────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │           Processing Layer                   │  │
│  │  ┌────────┐  ┌──────────┐  ┌────────────┐  │  │
│  │  │  PDF   │  │ Embeddings│  │   Chat     │  │  │
│  │  │Process │  │ Generator │  │  Handler   │  │  │
│  │  └────────┘  └──────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │ SQL/pgvector
┌──────────────────▼──────────────────────────────────┐
│         Database (Supabase PostgreSQL)              │
│  ┌──────────────────────────────────────────────┐  │
│  │         Documents + Embeddings               │  │
│  │    ┌──────────┐      ┌──────────┐          │  │
│  │    │ Metadata │      │ Vectors  │          │  │
│  │    └──────────┘      └──────────┘          │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Data Flow

1. **Document Ingestion**:
   ```
   PDF Upload → Text Extraction → Chunking → 
   Embedding Generation → Vector Storage
   ```

2. **Query Processing**:
   ```
   User Query → Embedding → Vector Search → 
   Context Retrieval → GPT-4 Generation → Response
   ```

3. **Chat Workflow**:
   ```
   Question → Semantic Search (top-k chunks) → 
   Context Assembly → GPT-4 Prompt → Stream Response
   ```

---

## API Endpoints

### Core Endpoints

```python
POST   /api/chat          # Chat with context
POST   /api/upload        # Upload single PDF
POST   /api/batch-upload  # Upload multiple PDFs
GET    /api/documents     # List all documents
GET    /api/search        # Search documents (to be removed)
DELETE /api/documents/{id} # Delete document
```

### Upload Endpoints

```python
POST   /api/upload/start   # Initialize upload job
GET    /api/upload/status  # Check upload progress
POST   /api/upload/metadata # Add document metadata
```

---

## Key Algorithms

### Text Chunking Strategy
- **Method**: Recursive character splitter
- **Chunk Size**: ~1000 characters
- **Overlap**: 200 characters
- **Rationale**: Balance context vs. retrieval precision

### Embedding Generation
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Dimensions**: 384
- **Normalization**: L2 normalized vectors
- **Storage**: JSONB in PostgreSQL

### Similarity Search
- **Algorithm**: pgvector with cosine similarity
- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Top-K**: Default 5 chunks per query
- **Threshold**: 0.7 similarity score minimum

---

## Security Considerations

### Current Implementation
- Environment variables for secrets
- CORS middleware configured
- Temporary file cleanup after processing
- No persistent storage of uploaded files

### Gaps to Address
- No authentication system
- Missing role-based access control
- No rate limiting
- Lack of input validation on some endpoints
- No audit logging

---

## Performance Characteristics

### Current Metrics
- **Upload Processing**: ~2-5 seconds per PDF
- **Embedding Generation**: ~100ms per chunk
- **Vector Search**: ~433ms average
- **Chat Response**: 1-3 seconds first token

### Bottlenecks Identified
- Large PDF processing can timeout
- Bulk uploads overwhelm Railway resources
- No caching layer for frequent queries
- Sequential processing of batch uploads

---

## Deployment Configuration

### Railway Environment
```env
RAILWAY_ENVIRONMENT=production
DATABASE_URL=postgresql://...@supabase.com
ENABLE_POSTGRESQL=true
OPENAI_API_KEY=sk-...
```

### Supabase Configuration
- Free tier: 500MB storage
- pgvector extension enabled
- Session pooler for connections
- IPv4 compatibility via pooler

---

## Technical Debt

### High Priority
1. **Search Feature**: Non-functional, adds confusion
2. **Admin Interface**: No UI for content management
3. **Metadata Management**: Many documents missing author/purchase links
4. **Error Handling**: Inconsistent across modules

### Medium Priority
1. **Code Duplication**: Multiple PDF processor variants
2. **Import Paths**: Inconsistent Railway vs. local imports
3. **Test Coverage**: Minimal automated testing
4. **Documentation**: Sparse inline documentation

### Low Priority
1. **Type Hints**: Incomplete Python type annotations
2. **Logging**: Inconsistent logging patterns
3. **Configuration**: Hardcoded values in some modules

---

## Migration History

### From ChromaDB to PostgreSQL
- **Issue**: ChromaDB data loss on redeploys
- **Solution**: PostgreSQL with persistent storage
- **Status**: Partially complete (text search only)

### From PostgreSQL to pgvector
- **Issue**: Slow search with 125k chunks
- **Solution**: Supabase with pgvector extension
- **Status**: Complete, 5 documents migrated

---

## Monitoring & Observability

### Current State
- Basic console logging
- Railway deployment logs
- No structured metrics
- No alerting system

### Needed Improvements
- Structured logging (JSON format)
- Performance metrics collection
- Error tracking (Sentry/similar)
- Usage analytics

---

## Scalability Considerations

### Current Limitations
- Single server deployment
- No horizontal scaling
- Sequential PDF processing
- Memory-intensive embedding generation

### Future Architecture Needs
- Queue-based processing (Celery/Redis)
- Microservices separation
- CDN for static assets
- Database connection pooling

---

## Integration Points

### External Services
- **OpenAI API**: Chat completions
- **MC Store**: Purchase links (manual)
- **Supabase**: Database and storage

### Future Integrations
- MC Store API (automated pricing)
- Payment processing
- Email notifications
- Analytics platforms

---

## Development Workflow

### Current Process
1. Local development on main branch
2. Direct deployment to Railway
3. Manual testing in production
4. Database migrations via scripts

### Recommended Improvements
1. Feature branch workflow
2. Staging environment
3. Automated testing pipeline
4. Database migration framework

---

## Disaster Recovery

### Current Backup Strategy
- Supabase automated backups (daily)
- No application-level backups
- No documented recovery process

### Needed Improvements
- Document recovery procedures
- Test restore process
- Implement point-in-time recovery
- Cross-region backup storage

---

## Compliance & Standards

### Current State
- No formal compliance framework
- Basic security practices
- No data retention policy

### Requirements for Enterprise
- SOC 2 compliance roadmap
- GDPR considerations
- Data encryption at rest
- Audit trail implementation

---

## Appendix: File Structure

```
mcpress-chatbot/
├── frontend/
│   ├── components/      # React components
│   ├── pages/           # Next.js pages
│   ├── styles/          # CSS/Tailwind
│   └── package.json
├── backend/
│   ├── main.py          # API entry point
│   ├── pdf_processor*.py # PDF processing variants
│   ├── vector_store*.py  # Vector store implementations
│   ├── chat_handler.py   # Chat orchestration
│   └── requirements.txt
├── docs/
│   ├── architecture.md   # This document
│   └── MC-Press-Chatbot-Feature-Roadmap.md
└── scripts/
    └── Various upload and migration scripts
```

---

## Next Steps

1. Remove non-functional search feature
2. Implement admin dashboard for content management
3. Complete metadata for all documents
4. Standardize code architecture patterns
5. Implement authentication system
6. Add monitoring and observability

---

*This architecture document represents the current state of the MC Press Chatbot system as of September 2025. It should be updated as the system evolves.*