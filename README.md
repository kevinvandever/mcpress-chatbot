# MC Press Chatbot

An AI-powered technical documentation assistant for IBM i professionals. The system provides semantic search and conversational AI across MC Press technical books and articles.

## Features
- Extract text, images, and code from PDFs
- Semantic search using vector embeddings
- Chat interface with streaming responses
- Multi-author document management
- Document type classification (books vs articles)
- Admin interface for document management
- CSV export/import with multi-author support
- Comprehensive author management

## Architecture
- **Backend**: FastAPI + Python 3.11+
- **PDF Processing**: PyMuPDF + pdfplumber
- **Vector DB**: PostgreSQL with pgvector extension
- **Frontend**: Next.js 14 + React + TypeScript
- **LLM**: OpenAI GPT-4 (gpt-4o-mini)
- **Deployment**: Railway (backend) + Netlify (frontend)
- **Database**: Supabase PostgreSQL

## Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add your OpenAI API key
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000 to use the chatbot.

## Multi-Author Enhancement

The system supports comprehensive multi-author metadata management:

### Key Features
- **Multiple Authors per Document**: Associate multiple authors with books and articles
- **Author Deduplication**: Automatic reuse of existing author records
- **Document Types**: Distinguish between books and articles with appropriate URL fields
- **Author Websites**: Store and display author website URLs
- **Ordered Authors**: Maintain author display order for proper attribution
- **CSV Support**: Export/import multi-author data in pipe-delimited format

### Documentation
- **[API Documentation](docs/multi-author-api-documentation.md)**: Complete API reference for multi-author endpoints
- **[Migration Guide](docs/multi-author-migration-guide.md)**: Step-by-step database migration procedures
- **[Usage Examples](docs/multi-author-examples.md)**: Practical examples and testing scenarios
- **[Manual Testing Guide](docs/manual-testing-guide.md)**: curl commands for testing functionality

### Database Schema
The enhancement adds two new tables:
- `authors`: Stores unique author information with optional website URLs
- `document_authors`: Junction table for many-to-many document-author relationships
- Enhanced `books` table with `document_type` and `article_url` fields

### API Endpoints
- `GET /api/authors/search` - Author autocomplete
- `GET /api/authors/{id}` - Author details
- `PATCH /api/authors/{id}` - Update author information
- `POST /api/documents/{id}/authors` - Add author to document
- `DELETE /api/documents/{id}/authors/{author_id}` - Remove author association
- `PUT /api/documents/{id}/authors/order` - Reorder document authors

See the [API Documentation](docs/multi-author-api-documentation.md) for complete endpoint details.