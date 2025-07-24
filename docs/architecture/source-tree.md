# PDF Chatbot Source Tree

## Project Structure Overview
```
pdf-chatbot/
├── README.md                      # Project documentation
├── docker-compose.yml            # Container orchestration
├── docs/                         # Architecture documentation
│   └── architecture/
│       ├── coding-standards.md   # Development standards
│       ├── tech-stack.md         # Technology documentation
│       └── source-tree.md        # This file
├── backend/                      # FastAPI Python backend
│   ├── main.py                   # FastAPI application entry point
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile               # Backend container configuration
│   │
│   ├── pdf_processor.py         # Legacy PDF processor (unused)
│   ├── pdf_processor_text_only.py  # Active text-only PDF processor
│   ├── pdf_processor_full.py    # Full PDF processor with image support
│   ├── pdf_processor_simple.py  # Simplified PDF processor
│   ├── pdf_processor_minimal.py # Minimal PDF processor
│   │
│   ├── vector_store.py          # ChromaDB vector database interface
│   ├── chat_handler.py          # OpenAI chat integration
│   ├── book_manager.py          # Document management utilities
│   │
│   ├── test_search.py           # Vector search tests
│   ├── test_chat_context.py     # Chat context tests
│   │
│   ├── uploads/                 # Temporary PDF storage
│   │   └── 5104 - 9781583470947_Text.pdf
│   │
│   └── chroma_db/               # ChromaDB persistence
│       ├── chroma.sqlite3       # SQLite database
│       └── b9ccbf91-b4a1-40ff-8587-4b7eb64591bd/
│           ├── data_level0.bin  # Vector index files
│           ├── header.bin
│           ├── length.bin
│           └── link_lists.bin
│
└── frontend/                    # Next.js TypeScript frontend
    ├── package.json             # Node.js dependencies
    ├── package-lock.json        # Dependency lock file
    ├── Dockerfile              # Frontend container configuration
    ├── next.config.js          # Next.js configuration
    ├── next-env.d.ts           # Next.js TypeScript declarations
    ├── tsconfig.json           # TypeScript configuration
    ├── tailwind.config.ts      # Tailwind CSS configuration
    ├── postcss.config.js       # PostCSS configuration
    │
    ├── app/                    # Next.js App Router
    │   ├── layout.tsx          # Root layout component
    │   ├── page.tsx            # Main page component
    │   └── globals.css         # Global styles
    │
    ├── components/             # React components
    │   ├── ChatInterface.tsx   # Chat UI component
    │   ├── DocumentList.tsx    # Document management component
    │   └── FileUpload.tsx      # PDF upload component
    │
    ├── pdf-chatbot/            # Duplicate directory (cleanup needed)
    │   └── frontend/
    │       ├── app/
    │       └── components/
    │
    └── node_modules/           # Node.js dependencies
```

## Core Components

### Backend Architecture (`backend/`)

#### Application Entry Point
- **`main.py`**: FastAPI application with CORS, routing, and middleware
  - Endpoints: `/`, `/upload`, `/chat`, `/documents`, `/health`
  - Middleware: CORS for frontend communication
  - Dependencies: PDF processor, vector store, chat handler

#### PDF Processing Layer
- **`pdf_processor_text_only.py`**: Currently active processor
  - Text extraction with PyMuPDF
  - Page-by-page processing
  - Code block detection
  - Metadata preservation

- **`pdf_processor_full.py`**: Full-featured processor (inactive)
  - Image extraction capabilities
  - OCR integration with Pytesseract
  - Advanced text processing
  - Comprehensive metadata

- **`pdf_processor_simple.py`**: Simplified implementation
- **`pdf_processor_minimal.py`**: Minimal implementation
- **`pdf_processor.py`**: Legacy processor (deprecated)

#### Data Management Layer
- **`vector_store.py`**: ChromaDB integration
  - Vector embedding with Sentence Transformers
  - Semantic search functionality
  - Document metadata management
  - Persistent storage interface

- **`chat_handler.py`**: OpenAI API integration
  - GPT-4 Turbo chat completion
  - Streaming response handling
  - Context management
  - Source citation generation

- **`book_manager.py`**: Document management utilities
  - File organization
  - Document metadata
  - Storage management

#### Testing Layer
- **`test_search.py`**: Vector search functionality tests
- **`test_chat_context.py`**: Chat context and response tests

#### Data Storage
- **`uploads/`**: Temporary PDF file storage
- **`chroma_db/`**: ChromaDB vector database persistence
  - SQLite backend for metadata
  - Binary files for vector indices

### Frontend Architecture (`frontend/`)

#### Next.js App Router (`app/`)
- **`layout.tsx`**: Root layout with global structure
- **`page.tsx`**: Main application page
- **`globals.css`**: Global CSS styles and Tailwind imports

#### React Components (`components/`)
- **`ChatInterface.tsx`**: Main chat UI component
  - Message display and input
  - Streaming response handling
  - Conversation history
  - Markdown rendering with syntax highlighting

- **`FileUpload.tsx`**: PDF upload component
  - Drag-and-drop interface
  - File validation
  - Upload progress indication
  - Error handling

- **`DocumentList.tsx`**: Document management component
  - List uploaded documents
  - Document deletion
  - Document metadata display

#### Configuration Files
- **`next.config.js`**: Next.js build and runtime configuration
- **`tsconfig.json`**: TypeScript compiler configuration
- **`tailwind.config.ts`**: Tailwind CSS customization
- **`postcss.config.js`**: PostCSS processing configuration

## File Relationships

### Backend Dependencies
```
main.py
├── pdf_processor_text_only.py
├── vector_store.py
└── chat_handler.py
    └── vector_store.py
```

### Frontend Dependencies
```
app/page.tsx
├── components/ChatInterface.tsx
├── components/FileUpload.tsx
└── components/DocumentList.tsx
```

## Data Flow

### PDF Processing Flow
1. **Upload**: `FileUpload.tsx` → `main.py:/upload`
2. **Processing**: `pdf_processor_text_only.py` extracts text
3. **Vectorization**: `vector_store.py` creates embeddings
4. **Storage**: ChromaDB persists vectors and metadata

### Chat Interaction Flow
1. **Query**: `ChatInterface.tsx` → `main.py:/chat`
2. **Search**: `vector_store.py` retrieves relevant chunks
3. **Generation**: `chat_handler.py` calls OpenAI API
4. **Response**: Streaming response back to frontend

## Development Workflow

### Local Development Setup
```bash
# Backend
cd backend/
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend/
npm install
npm run dev
```

### Docker Development
```bash
docker-compose up --build
```

### Testing
```bash
# Backend tests
cd backend/
python -m pytest test_search.py test_chat_context.py

# Frontend tests (if configured)
cd frontend/
npm test
```

## Configuration Management

### Environment Variables
- **Backend**: `.env` file for API keys and settings
- **Frontend**: Next.js automatic environment variable handling
- **Docker**: Environment variables in docker-compose.yml

### Database Configuration
- **ChromaDB**: Automatic initialization in `vector_store.py`
- **SQLite**: Backend storage for ChromaDB metadata
- **File Storage**: Local filesystem with upload directory

## Build and Deployment

### Backend Build
- **Docker**: Multi-stage build with Python slim base
- **Dependencies**: pip install from requirements.txt
- **Runtime**: Uvicorn ASGI server

### Frontend Build
- **Next.js**: Static site generation with `npm run build`
- **Docker**: Node.js Alpine base image
- **Output**: Optimized static files and server components

## Cleanup Opportunities

### Duplicate Directories
- **`frontend/pdf-chatbot/`**: Duplicate structure that should be removed
- **Unused processors**: Consider removing inactive PDF processors

### Legacy Files
- **`pdf_processor.py`**: Legacy processor that can be removed
- **Test cleanup**: Consolidate test files and add more coverage

## Future Structure Considerations

### Potential Additions
```
pdf-chatbot/
├── tests/                  # Centralized test directory
├── scripts/               # Deployment and utility scripts
├── config/                # Configuration files
├── logs/                  # Application logs
└── migrations/            # Database migrations
```

### Production Considerations
- **Environment separation**: dev/staging/production configs
- **Monitoring**: Health check endpoints and metrics
- **Logging**: Structured logging configuration
- **Security**: API authentication and authorization

This source tree provides a clear foundation for a scalable PDF chatbot application with room for enhancement and production deployment.