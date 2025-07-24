# PDF Chatbot Technology Stack

## Project Overview
PDF Chatbot is a full-stack AI-powered application that enables users to upload PDF documents and interact with them through natural language queries. The system processes PDFs, creates vector embeddings, and provides contextual responses using OpenAI's GPT models.

## Architecture Pattern
**Microservices Architecture** with containerized deployment:
- **Frontend**: Next.js SPA serving the user interface
- **Backend**: FastAPI REST API handling PDF processing and chat logic
- **Database**: ChromaDB for vector storage and document management
- **AI Service**: OpenAI API for language model capabilities

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
- **File Upload**: React Dropzone 14.2.3
  - Drag-and-drop file upload interface
  - File type validation
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

### Vector Database & AI
- **Vector Store**: ChromaDB 0.4.0+
  - Local vector database
  - Semantic search capabilities
  - Persistent storage
- **Embeddings**: Sentence Transformers 2.2.0+
  - all-MiniLM-L6-v2 model for text embeddings
  - Multilingual support
  - Optimized for semantic similarity
- **Language Model**: OpenAI API 1.3.0+
  - GPT-4 Turbo for chat responses
  - Streaming response support
  - Function calling capabilities
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
6. **Storage**: ChromaDB persistence with metadata

### Chat Processing Pipeline
1. **Query**: User message from frontend
2. **Retrieval**: Semantic search in ChromaDB
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
- **Testing**: pytest (implied, not in requirements)

### Frontend Development
- **Package Manager**: npm with package-lock.json
- **TypeScript**: 5.0+ for static type checking
- **Linting**: Next.js built-in ESLint configuration
- **Build Tool**: Next.js built-in Webpack configuration
- **Dev Server**: Next.js development server with hot reload

## Infrastructure & Deployment

### Containerization
- **Docker**: Multi-stage builds for frontend and backend
- **Docker Compose**: Orchestration for local development
- **Base Images**: 
  - Frontend: Node.js Alpine
  - Backend: Python 3.8+ slim

### Database Storage
- **Vector Database**: ChromaDB with SQLite backend
- **File Storage**: Local filesystem with uploads directory
- **Persistence**: Volume mounts for data continuity

### Environment Configuration
- **Backend Port**: 8000 (development), 8001 (production)
- **Frontend Port**: 3000 (development)
- **CORS**: Configured for localhost development
- **API Keys**: Environment variable management

## Performance Characteristics

### Processing Performance
- **PDF Processing**: ~1-2 seconds per MB
- **Embedding Generation**: ~500ms per document chunk
- **Vector Search**: <100ms for similarity queries
- **Chat Response**: 1-3 seconds (depends on OpenAI API)

### Scalability Considerations
- **File Size Limit**: 50MB per PDF (configurable)
- **Memory Usage**: ~100MB base + 50MB per processed document
- **Concurrent Users**: Limited by OpenAI API rate limits
- **Storage**: Local filesystem (can be migrated to cloud)

## Security Features

### Input Validation
- **File Type**: PDF-only uploads
- **File Size**: Configurable limits
- **Content Validation**: Pydantic models for API requests
- **CORS**: Restricted to localhost in development

### Data Protection
- **API Keys**: Environment variable storage
- **File Isolation**: Uploads directory separation
- **No Persistence**: Sensitive data not logged
- **Local Processing**: No external data transmission except OpenAI API

## Monitoring & Observability

### Logging
- **FastAPI**: Built-in request/response logging
- **Error Handling**: HTTPException with detailed messages
- **Debug Information**: Development mode verbose logging

### Health Checks
- **API Health**: `/health` endpoint
- **Database Status**: ChromaDB connection validation
- **Service Dependencies**: OpenAI API availability

## Development Workflow

### Local Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Development
```bash
docker-compose up --build
```

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **E2E Tests**: Full workflow validation

## Future Considerations

### Planned Enhancements
- **Authentication**: User management system
- **Cloud Storage**: AWS S3 or similar for document storage
- **Batch Processing**: Multiple document handling
- **Advanced OCR**: Better image text extraction
- **Analytics**: Usage metrics and performance monitoring

### Technology Migrations
- **Database**: PostgreSQL for production scalability
- **Vector Store**: Pinecone or Weaviate for cloud deployment
- **Deployment**: Kubernetes for container orchestration
- **Monitoring**: Prometheus and Grafana for observability

This technology stack provides a robust foundation for AI-powered document processing with room for scalability and enhancement.