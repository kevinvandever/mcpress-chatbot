# MC Press PDF Chatbot - Setup Guide

## Overview
AI-powered chatbot for MC Press technical books with semantic search through 115 PDFs (146,074 chunks) using ChromaDB and OpenAI GPT-3.5-turbo.

## Quick Start

### 1. Environment Setup
```bash
# Ensure you have your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

### 2. Start the Application
```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend  
cd frontend
npm run dev
```

### 3. Local Access
- Frontend: http://localhost:3003
- Backend: http://localhost:8000

## Remote Demo Setup

### Prerequisites
- VPN must be turned OFF for stable tunneling
- Both backend and frontend must be running

### Start Remote Access
```bash
./tunnel_control.sh start
```

This will provide:
- **URL:** https://mcpress-stable.loca.lt
- **Password:** Your current public IP

### Tunnel Management Commands
```bash
./tunnel_control.sh start    # Start tunnel
./tunnel_control.sh stop     # Stop tunnel  
./tunnel_control.sh restart  # Restart tunnel
./tunnel_control.sh status   # Check status
```

### Sharing with Partners
1. Turn off VPN
2. Start tunnel: `./tunnel_control.sh start`
3. Share the URL and password shown in output
4. Partner visits URL, enters password once, then has full access

## Troubleshooting

### Chat Not Working
- Check that `OPENAI_API_KEY` is set: `echo $OPENAI_API_KEY`
- Restart backend: `cd backend && python main.py`

### Tunnel Issues  
- VPN must be OFF
- Check status: `./tunnel_control.sh status`
- Restart: `./tunnel_control.sh restart`
- IP changes require new password - run status to get current IP

### Search Results
- System prioritizes text over images (images get +0.3 penalty)
- Returns top 8 most relevant chunks above 70% similarity
- Search covers all 115 PDFs with 146,074 total chunks

## File Structure
```
pdf-chatbot/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── chat_handler.py      # Chat logic & OpenAI integration  
│   ├── vector_store_chroma.py # ChromaDB search
│   └── chroma_db/          # Vector database
├── frontend/
│   ├── app/page.tsx        # Main chat interface
│   └── config/api.ts       # API configuration
├── tunnel_control.sh       # Tunnel management script
├── start_demo.sh          # Local demo startup
└── .env                   # Environment variables
```

## Database Info
- **Vector Store:** ChromaDB (local)
- **Document Count:** 115 PDFs
- **Chunk Count:** 146,074 semantic chunks
- **Search Algorithm:** Cosine similarity with content-type penalties
- **Relevance Threshold:** 70% similarity minimum

## Key Features
- Real-time chat with source citations
- Semantic search across all MC Press books
- Content-type prioritization (text > code > images)  
- Source links to MC Press website
- Conversation context maintained per session