# Product Overview

## MC Press Chatbot

An AI-powered technical documentation assistant for IBM i professionals. The system provides semantic search and conversational AI across MC Press technical books and articles.

### Core Features
- **PDF Processing**: Extract and index technical books with text, images, and code
- **Semantic Search**: Vector-based similarity search using 384-dimensional embeddings
- **Conversational AI**: GPT-4 powered chat with streaming responses
- **Document Management**: Admin interface for uploading and managing PDFs
- **E-commerce Integration**: Direct purchase links to MC Store

### Current State
- **Production**: Deployed on Railway (backend) and Netlify (frontend)
- **Database**: Supabase PostgreSQL with pgvector extension
- **Documents**: 227,032+ indexed chunks from technical books
- **Target Audience**: IBM i developers, RPG programmers, system administrators

### Key Differentiators
- Specialized for IBM i technical content (RPG, ILE, CL, DB2)
- Context-aware responses with source attribution
- Integration with MC Press book catalog
- Optimized for technical code examples and documentation
