# Railway Full-Stack Deployment Guide

## Prerequisites
- Railway Pro account ✅ (you have this)
- Existing Railway project with PostgreSQL ✅ (you have this)

## Deployment Steps

### 1. Commit the new files
```bash
git add .
git commit -m "Add Railway full-stack deployment configuration"
```

### 2. Deploy to Railway
```bash
# If you haven't connected Railway CLI:
railway login
railway link

# Deploy the full-stack app:
railway up
```

### 3. Environment Variables
Ensure these are set in your Railway project:
- `DATABASE_URL` (should be auto-set by Railway PostgreSQL)
- `OPENAI_API_KEY` (your OpenAI key)
- `DATA_DIR` (set to `/tmp/data`)

### 4. Verify Deployment
After deployment, Railway will give you a URL like:
`https://your-app-name.railway.app`

Test these endpoints:
- `https://your-app-name.railway.app` (frontend)
- `https://your-app-name.railway.app/api/health` (backend health)
- `https://your-app-name.railway.app/api/documents` (document list)

## Architecture
```
Railway Container:
├── Next.js Frontend (Port $PORT - public)
├── FastAPI Backend (Port 8000 - internal)
├── PostgreSQL Database (Railway service)
└── File Storage (/tmp/data)
```

## Benefits of This Approach
✅ **Single Deployment** - One Railway service, not two
✅ **Simpler Networking** - No cross-service communication issues  
✅ **Cost Effective** - One Railway service instead of multiple
✅ **Reliable** - No external dependencies like Vercel
✅ **Professional URL** - Custom Railway domain

## Troubleshooting

### If deployment fails:
```bash
# Check Railway logs
railway logs

# Redeploy with verbose output
railway up --verbose
```

### If frontend/backend can't communicate:
- The frontend uses `/api/*` routes which get rewritten to `localhost:8000`
- This works because both services run in the same Railway container

### If you need to update:
```bash
git add .
git commit -m "Update deployment"
railway up
```

## Partner Access
Once deployed, share this URL with your partner:
`https://your-app-name.railway.app`

No tunnel setup required - it's live 24/7!