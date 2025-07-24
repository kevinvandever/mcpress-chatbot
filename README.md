# PDF Technical Book Chatbot

A complete solution for processing technical PDFs (with text, images, and code) and querying them through an AI chatbot.

## Features
- Extract text, images, and code from PDFs
- Semantic search using vector embeddings
- Chat interface with streaming responses
- Support for technical documentation

## Architecture
- **Backend**: FastAPI + Python
- **PDF Processing**: PyMuPDF + Unstructured
- **Vector DB**: ChromaDB
- **Frontend**: Next.js + React
- **LLM**: OpenAI GPT-4

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