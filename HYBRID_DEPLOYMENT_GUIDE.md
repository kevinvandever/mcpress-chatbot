# MC Press Chatbot - Hybrid Deployment Guide

## Architecture Overview

This hybrid approach separates heavy PDF processing (done locally) from lightweight query serving (Railway/Vercel).

### Components:
1. **Local Processing**: One-time preprocessing of 113 PDFs
2. **Railway Backend**: Query-only API (no uploads/processing)
3. **Vercel Frontend**: User interface for search/chat
4. **PostgreSQL + pgvector**: Vector storage on Railway

## Step 1: Local Preprocessing (One-Time Setup)

### Prerequisites
```bash
# Ensure you have Python 3.9+ and pip installed
python --version

# Install required packages locally
pip install asyncpg sentence-transformers tqdm python-dotenv
```

### Configure Database Connection
```bash
# Copy your Railway PostgreSQL DATABASE_URL to .env file
echo "DATABASE_URL=postgresql://..." > .env
```

### Run Preprocessing
```bash
# Process all PDFs and upload vectors to Railway
python preprocess_books_locally.py
```

This will:
- Process all 113 PDFs in `backend/uploads/`
- Generate embeddings for each text chunk
- Store everything in Railway PostgreSQL
- Create a `preprocessing_log.json` to track progress
- Can be interrupted and resumed (skips already processed files)

Expected output:
```
🚀 MC Press Books Local Preprocessor
📁 Processing PDFs from: backend/uploads
🗄️  Storing to: Railway PostgreSQL
📚 Found 113 PDF files
...
📊 Processing Complete!
✅ Successfully processed: 113 books
```

## Step 2: Deploy Simplified Backend to Railway

### Update Railway Deployment

1. **Update Procfile:**
```bash
web: python backend/main_query_only.py
```

2. **Update requirements.txt:**
```txt
fastapi==0.104.1
uvicorn==0.24.0
asyncpg==0.29.0
sentence-transformers==2.2.2
numpy==1.24.3
python-dotenv==1.0.0
```

3. **Deploy to Railway:**
```bash
# Commit changes
git add backend/main_query_only.py Procfile requirements.txt
git commit -m "Switch to query-only backend for demo"

# Push to Railway
git push railway main
```

### Verify Deployment

Test the API endpoints:
```bash
# Health check
curl https://your-railway-app.railway.app/

# Get statistics
curl https://your-railway-app.railway.app/api/stats

# Test search
curl -X POST https://your-railway-app.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "IBM i5", "limit": 3}'
```

## Step 3: Update Frontend for Demo Mode

### Modify Frontend Components

1. **Remove Upload UI** - Update `frontend/components/BookUpload.tsx`:
```tsx
// Replace upload component with info message
export function BookUpload() {
  return (
    <div className="info-banner">
      <h3>📚 Pre-loaded Knowledge Base</h3>
      <p>This demo includes 113 MC Press technical books.</p>
      <p>Start searching or ask questions about IBM, AS/400, DB2, and more!</p>
    </div>
  );
}
```

2. **Update API Base URL** in `frontend/config/api.ts`:
```typescript
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  'https://your-railway-app.railway.app';
```

3. **Deploy to Vercel:**
```bash
# From frontend directory
vercel --prod
```

## Step 4: Monitoring & Maintenance

### Check Database Status
```sql
-- Connect to Railway PostgreSQL
-- Check book count
SELECT COUNT(*) FROM books;

-- Check embedding count  
SELECT COUNT(*) FROM embeddings;

-- Check categories
SELECT DISTINCT category, COUNT(*) 
FROM books 
GROUP BY category;
```

### Re-process Books (if needed)
```bash
# Delete preprocessing log to force re-processing
rm preprocessing_log.json

# Run preprocessor again
python preprocess_books_locally.py
```

### Add New Books
1. Add PDF to `backend/uploads/`
2. Run `python preprocess_books_locally.py`
3. Script will only process new files

## Cost Analysis

### Current Approach (Hybrid)
- **Railway**: ~$5/month (PostgreSQL + minimal backend)
- **Vercel**: Free tier
- **Total**: ~$5/month

### Benefits
- No processing costs on Railway
- Stable, fast queries
- Can handle many concurrent users
- Easy to add/update books locally

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check DATABASE_URL in .env
   - Ensure Railway PostgreSQL is running
   - Check network connectivity

2. **Embeddings not found**
   - Verify preprocessing completed
   - Check `preprocessing_log.json` for errors
   - Re-run failed books

3. **Frontend can't connect to backend**
   - Verify CORS settings in `main_query_only.py`
   - Check Railway deployment logs
   - Verify API_BASE_URL in frontend

## Future Enhancements

When ready for production:

1. **Add LLM Integration**: Connect OpenAI/Anthropic for chat responses
2. **Implement Caching**: Add Redis for frequently accessed queries
3. **Add Authentication**: Secure endpoints with API keys
4. **Scale Processing**: Use cloud functions for PDF processing
5. **Add Admin Panel**: Web UI for managing books

## Quick Commands Reference

```bash
# Local preprocessing
python preprocess_books_locally.py

# Check Railway logs
railway logs

# Test local backend
python backend/main_query_only.py

# Deploy to Railway
git push railway main

# Deploy frontend to Vercel
cd frontend && vercel --prod
```

## Support

For issues or questions:
- Check `preprocessing_log.json` for processing errors
- Review Railway logs: `railway logs`
- Check PostgreSQL connection: `railway connect postgresql`