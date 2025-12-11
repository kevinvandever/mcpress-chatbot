# MC Press Chatbot Technology Stack

## Project Overview
MC Press Chatbot is a full-stack AI-powered application that enables users to upload PDF documents and interact with them through natural language queries. The system processes PDFs, creates vector embeddings, and provides contextual responses using OpenAI's GPT models.

## Architecture Pattern
**Cloud-Native Microservices** with managed hosting:
- **Frontend**: Next.js SPA on Netlify (static site with API proxying)
- **Backend**: FastAPI REST API on Railway (Python async framework)
- **Database**: PostgreSQL with pgvector on Railway (vector similarity search)
- **AI Service**: OpenAI API (GPT-4o-mini for chat responses)

### Deployment Topology
```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Netlify       │         │   Railway        │         │  OpenAI     │
│   (Frontend)    │────────▶│   (Backend)      │────────▶│  API        │
│                 │  HTTPS  │                  │  HTTPS  │             │
│  Next.js App    │  Proxy  │  FastAPI         │         │  GPT-4o     │
│  Static Assets  │         │  Python 3.8+     │         │             │
└─────────────────┘         └────────┬─────────┘         └─────────────┘
                                     │
                            ┌────────▼─────────┐
                            │  PostgreSQL      │
                            │  + pgvector      │
                            │  (Railway DB)    │
                            └──────────────────┘
```

## Core Technologies

### Frontend Stack
- **Framework**: Next.js 14.0.3
  - React 18 with App Router
  - TypeScript for type safety
  - Server-side rendering (SSR) capabilities
- **Styling**: Tailwind CSS 3.3.0
  - Utility-first CSS framework
  - Responsive design components
  - PostCSS and Autoprefixer
- **HTTP Client**: Native Fetch API
  - Built-in browser fetch for API calls
  - Axios 1.6.2 for advanced request handling
- **File Upload**: React Dropzone 14.3.8
  - Drag-and-drop file upload interface
  - PDF and code file support
- **Markdown Rendering**: React Markdown 9.0.1
  - GitHub Flavored Markdown (GFM) support
  - Syntax highlighting for code blocks
  - remark-gfm plugin for extended features

### Backend Stack
- **Framework**: FastAPI 0.104.0+
  - High-performance async Python web framework
  - Automatic OpenAPI documentation
  - Pydantic integration for data validation
- **Runtime**: Python 3.8+
  - Asynchronous programming with asyncio
  - Type hints for better code quality
- **ASGI Server**: Uvicorn with standard extras
  - Production-ready ASGI server
  - Hot reload for development
  - WebSocket support for streaming

### PDF Processing
- **PDF Engine**: PyMuPDF (fitz) 1.23.8+
  - Fast PDF parsing and text extraction
  - Image extraction capabilities
  - Metadata extraction
- **OCR Engine**: Pytesseract 0.3.10+
  - Optical Character Recognition
  - Image-to-text conversion
  - Multiple language support
- **Image Processing**: Pillow 10.0.0+
  - Image manipulation and optimization
  - Format conversion support
  - Preprocessing for OCR
- **Text Processing**: LangChain Text Splitters 0.0.1+
  - Intelligent text chunking
  - Overlap strategies for better context
  - Multiple splitting algorithms

### Database & Vector Search
- **Database**: PostgreSQL with pgvector extension
  - Railway managed PostgreSQL database
  - Native vector similarity search using cosine distance
  - Async database operations with asyncpg
- **Embeddings**: Sentence Transformers 2.2.2+
  - all-MiniLM-L6-v2 model (384-dimensional embeddings)
  - In-process embedding generation
  - Optimized for semantic similarity
- **Language Model**: OpenAI API 1.3.0+
  - GPT-4o-mini for chat responses
  - Streaming response support
  - Configurable temperature and token limits
- **Prompt Engineering**: Custom prompt templates
  - Context-aware response generation
  - Source citation integration
  - Conversation history management

## Data Flow Architecture

### Document Processing Pipeline
1. **Upload**: Frontend → FastAPI upload endpoint
2. **Validation**: File type, size, and format checks
3. **Processing**: PDF text/image extraction with PyMuPDF
4. **Chunking**: Text segmentation with LangChain splitters
5. **Embedding**: Vector generation with Sentence Transformers
6. **Storage**: PostgreSQL with pgvector and metadata

### Chat Processing Pipeline
1. **Query**: User message from frontend
2. **Retrieval**: Semantic search in PostgreSQL (pgvector cosine similarity)
3. **Context**: Relevant document chunks assembly
4. **Generation**: OpenAI API call with context
5. **Streaming**: Real-time response delivery
6. **Citation**: Source attribution with page numbers

## Development Tools

### Backend Development
- **Package Manager**: pip with requirements.txt
- **Environment**: python-dotenv 1.0.0+ for configuration
- **File Handling**: aiofiles 23.2.0+ for async file operations
- **Data Validation**: Pydantic 2.5.0+ and Pydantic Settings 2.1.0+
- **HTTP Client**: python-multipart 0.0.6+ for file uploads
- **Authentication**: JWT (PyJWT 2.8.0+) + bcrypt (4.0.1+) for admin security

### Frontend Development
- **Package Manager**: npm with package-lock.json
- **TypeScript**: 5.0+ for static type checking
- **Linting**: Next.js built-in ESLint configuration
- **Build Tool**: Next.js built-in Webpack configuration
- **Dev Server**: Next.js development server with hot reload

## Infrastructure & Deployment

### Production Hosting
- **Frontend**: Netlify
  - Static site hosting with CDN
  - API proxy to Railway backend
  - Automatic deploys from Git
- **Backend**: Railway
  - Managed Python hosting
  - PostgreSQL database with pgvector
  - Persistent volume storage for uploads
- **Database**: Railway PostgreSQL
  - Managed PostgreSQL with pgvector extension
  - Automatic backups and scaling

### Environment Configuration
- **Frontend URL**: Netlify CDN
- **Backend API**: Railway app URL
- **Database**: Railway PostgreSQL connection string
- **File Storage**: Railway persistent volume
- **API Keys**: Environment variables in Railway dashboard

## Performance Characteristics

### Processing Performance
- **PDF Processing**: ~1-2 seconds per MB
- **Embedding Generation**: ~500ms per document chunk
- **Vector Search**: Fast pgvector similarity queries with cosine distance
- **Chat Response**: 1-3 seconds (streaming from OpenAI API)

### Scalability Considerations
- **File Size Limit**: 50MB per PDF (configurable)
- **Concurrent Users**: Scales with Railway resources and OpenAI API limits
- **Storage**: Railway persistent volumes with PostgreSQL
- **Database**: Managed PostgreSQL scales with Railway plans

## Security Features

### Authentication & Authorization
- **Admin Authentication**: JWT tokens with bcrypt password hashing
- **Session Management**: Database-backed sessions with 24-hour expiration
- **Rate Limiting**: 5 failed login attempts per IP, 15-minute lockout
- **Password Policy**: 12+ characters with complexity requirements

### Input Validation
- **File Type**: PDF and code file validation
- **File Size**: Configurable limits (50MB default)
- **Content Validation**: Pydantic models for API requests
- **CORS**: Configured for production domains

### Data Protection
- **API Keys**: Environment variable storage in Railway
- **Database Security**: Managed PostgreSQL with encrypted connections
- **Token Security**: SHA256 hashed tokens in database
- **Audit Trail**: Last login tracking and session management

## Monitoring & Observability

### Logging
- **FastAPI**: Built-in request/response logging
- **Error Handling**: HTTPException with detailed messages
- **Debug Information**: Development mode verbose logging

### Health Checks
- **API Health**: `/health` endpoint
- **Database Status**: PostgreSQL connection validation
- **Service Dependencies**: OpenAI API availability

## Development Workflow

### Production Development
All development and testing occurs directly in Railway production environment:
- **Backend**: Railway deployment triggers from Git push
- **Frontend**: Netlify deployment triggers from Git push
- **Database**: Railway managed PostgreSQL

### Testing Strategy
- **Production Testing**: All testing performed in Railway environment
- **Integration Tests**: API endpoint testing
- **Manual QA**: Feature validation in production

## Recent Architecture Evolution

### Completed Migrations
- ✅ **ChromaDB → PostgreSQL pgvector**: Migrated from local ChromaDB to Railway PostgreSQL with pgvector extension for production scalability
- ✅ **Supabase → Railway**: Consolidated hosting from Supabase to Railway for simplified infrastructure
- ✅ **Storage Optimization**: Resolved 500MB Railway storage constraints with persistent volumes
- ✅ **JWT Authentication**: Implemented admin authentication with JWT tokens and bcrypt

### Current Features
- **Conversation History**: Persistent chat history with PostgreSQL storage (STORY-011)
- **Conversation Export**: PDF and Markdown export functionality (STORY-012 in progress)
- **Code File Upload**: Support for uploading and querying code files (.py, .js, .ts, etc.)
- **Admin Dashboard**: Document management interface for content administrators

### Future Considerations
- **User Authentication**: Expand beyond admin-only to end-user authentication
- **Analytics Dashboard**: Usage metrics and performance monitoring
- **Advanced Export**: Custom branding and formatting options
- **Rate Limiting Enhancement**: Move from in-memory to PostgreSQL-backed rate limiting

This technology stack provides a robust, cloud-native foundation for AI-powered document processing with proven scalability in production.