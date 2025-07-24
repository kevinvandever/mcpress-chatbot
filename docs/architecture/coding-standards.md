# PDF Chatbot Coding Standards

## Overview
This document defines the coding standards for the PDF Chatbot project, a full-stack application with FastAPI backend and Next.js frontend.

## Project Structure
```
pdf-chatbot/
├── backend/           # FastAPI Python backend
├── frontend/          # Next.js TypeScript frontend
├── docs/              # Project documentation
└── docker-compose.yml # Container orchestration
```

## Backend Standards (Python/FastAPI)

### File Organization
- **Core modules**: `main.py`, `pdf_processor_*.py`, `vector_store.py`, `chat_handler.py`
- **Tests**: `test_*.py` in backend root
- **Uploads**: `uploads/` directory for temporary file storage
- **Database**: `chroma_db/` for ChromaDB persistence

### Naming Conventions
- **Files**: snake_case (e.g., `pdf_processor_text_only.py`)
- **Classes**: PascalCase (e.g., `PDFProcessorTextOnly`, `VectorStore`)
- **Functions**: snake_case (e.g., `process_pdf`, `get_relevant_chunks`)
- **Variables**: snake_case (e.g., `conversation_id`, `max_file_size`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE_MB`, `OPENAI_API_KEY`)

### Code Organization
```python
# Standard library imports
import os
import asyncio
import json

# Third-party imports
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv

# Local imports
from pdf_processor_text_only import PDFProcessorTextOnly
from vector_store import VectorStore
```

### FastAPI Patterns
- **Pydantic models** for request/response validation
- **Dependency injection** for shared resources
- **Async/await** for I/O operations
- **HTTPException** for error handling
- **CORS middleware** for frontend communication

### Error Handling
```python
try:
    result = await process_operation()
    return {"status": "success", "data": result}
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### Environment Variables
- Use `.env` files for configuration
- Load with `python-dotenv`
- Required vars: `OPENAI_API_KEY`, `MAX_FILE_SIZE_MB`

## Frontend Standards (TypeScript/Next.js)

### File Organization
- **App Router**: `app/` directory structure
- **Components**: `components/` for reusable UI components
- **Styles**: `globals.css` for global styles
- **Config**: `next.config.js`, `tailwind.config.ts`

### Naming Conventions
- **Components**: PascalCase (e.g., `ChatInterface.tsx`, `FileUpload.tsx`)
- **Files**: PascalCase for components, camelCase for utilities
- **Variables**: camelCase (e.g., `userName`, `isLoading`)
- **Types**: PascalCase (e.g., `ChatMessage`, `DocumentInfo`)
- **CSS Classes**: lowercase-with-hyphens (e.g., `chat-container`, `upload-area`)

### Component Structure
```typescript
import React, { useState, useEffect } from 'react';

interface ComponentProps {
  // Props definition
}

const ComponentName: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  // State declarations
  const [state, setState] = useState<Type>(initialValue);
  
  // Effect hooks
  useEffect(() => {
    // Effect logic
  }, [dependencies]);
  
  // Event handlers
  const handleEvent = (event: EventType) => {
    // Handler logic
  };
  
  // Render
  return (
    <div className="component-container">
      {/* JSX content */}
    </div>
  );
};

export default ComponentName;
```

### State Management
- **React hooks** for local state (`useState`, `useEffect`)
- **Props** for parent-child communication
- **Event handlers** for user interactions
- **Async operations** with proper loading states

### API Communication
```typescript
const response = await fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(data),
});

if (!response.ok) {
  throw new Error('API request failed');
}

const result = await response.json();
```

### Styling Standards
- **Tailwind CSS** for utility-first styling
- **Responsive design** with mobile-first approach
- **Consistent spacing** using Tailwind spacing scale
- **Dark mode** considerations (if applicable)

## Database Standards (ChromaDB)

### Collection Naming
- **Collections**: descriptive names (e.g., `pdf_documents`, `chat_history`)
- **Metadata**: consistent keys (`page_number`, `document_id`, `chunk_type`)

### Document Structure
```python
{
    "id": "unique_identifier",
    "content": "document_text",
    "metadata": {
        "page_number": 1,
        "document_id": "filename.pdf",
        "chunk_type": "text|code|image",
        "source": "file_path"
    }
}
```

## Testing Standards

### Backend Testing
- **pytest** for test framework
- **Test files**: `test_*.py` pattern
- **Test functions**: `test_function_name()` pattern
- **Fixtures** for shared test data
- **Async tests** for async functions

### Frontend Testing
- **Jest** with React Testing Library
- **Component tests** in `__tests__/` directories
- **Integration tests** for API communication
- **E2E tests** for critical user flows

## Code Quality

### Linting and Formatting
- **Backend**: `black`, `isort`, `flake8`
- **Frontend**: ESLint, Prettier
- **TypeScript**: strict mode enabled
- **Import sorting**: consistent order

### Documentation
- **Docstrings** for Python functions and classes
- **Type hints** for all function parameters and returns
- **JSDoc** for complex TypeScript functions
- **README** files for setup and usage

### Security
- **Input validation** with Pydantic models
- **File upload limits** and type restrictions
- **API key management** through environment variables
- **CORS** properly configured
- **No sensitive data** in logs or responses

## Performance

### Backend Optimization
- **Async operations** for I/O-bound tasks
- **Chunked processing** for large files
- **Database indexing** for efficient queries
- **Memory management** for file uploads

### Frontend Optimization
- **Code splitting** with Next.js dynamic imports
- **Image optimization** with Next.js Image component
- **Lazy loading** for non-critical components
- **Caching** for API responses

## Version Control

### Commit Standards
- **Conventional commits**: `type(scope): description`
- **Types**: feat, fix, docs, style, refactor, test, chore
- **Scope**: backend, frontend, docs, docker
- **Examples**: 
  - `feat(backend): add image processing to PDF parser`
  - `fix(frontend): handle upload errors gracefully`
  - `docs: update API documentation`

### Branch Strategy
- **Main branch**: production-ready code
- **Feature branches**: `feature/description`
- **Bug fixes**: `fix/description`
- **Documentation**: `docs/description`

## Environment Setup

### Development Requirements
- **Python**: 3.8+
- **Node.js**: 18+
- **Docker**: for containerized development
- **OpenAI API**: for chat functionality

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

## Dependencies Management

### Backend Dependencies
- **Core**: FastAPI, Uvicorn, Pydantic
- **PDF Processing**: PyMuPDF, Pillow, pytesseract
- **Vector Store**: ChromaDB, sentence-transformers
- **AI**: OpenAI API client
- **Utilities**: python-dotenv, aiofiles

### Frontend Dependencies
- **Core**: Next.js, React, TypeScript
- **UI**: Tailwind CSS, react-dropzone
- **Markdown**: react-markdown, remark-gfm
- **HTTP**: Built-in fetch API

This coding standards document ensures consistent, maintainable, and scalable code across the PDF Chatbot project.