# Deployment Guide - Netlify & Railway

**Project**: MC Press Chatbot
**Owner**: Kevin Vandever
**Last Updated**: October 7, 2025

---

## 🏗️ Infrastructure Overview

### Two-Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│  NETLIFY                                                 │
│  Frontend Hosting + CDN                                  │
│                                                          │
│  - React/Vite build                                      │
│  - Global CDN distribution                               │
│  - Automatic SSL                                         │
│  - Deploy previews for PRs                               │
│                                                          │
│  URL: https://mcpress-chatbot.netlify.app              │
└────────────────┬─────────────────────────────────────────┘
                 │
                 │ API calls to
                 ▼
┌─────────────────────────────────────────────────────────┐
│  RAILWAY                                                 │
│  Backend API + Database                                  │
│                                                          │
│  Service 1: FastAPI Backend                              │
│  - Python 3.11 runtime                                   │
│  - REST API endpoints                                    │
│  - OpenAI integration                                    │
│  URL: https://mcpress-chatbot-production.up.railway.app │
│                                                          │
│  Service 2: PostgreSQL Database                          │
│  - PostgreSQL 16 with pgvector                           │
│  - 227k document vectors                                 │
│  - Internal network access                               │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 Frontend Deployment (Netlify)

### Current Configuration

**Site Name**: `mcpress-chatbot`
**URL**: https://mcpress-chatbot.netlify.app
**Repository**: Connected to GitHub
**Branch**: `main` (auto-deploy)

### Build Settings

**Base Directory**: `frontend/`
**Build Command**: `npm run build`
**Publish Directory**: `dist/` (Vite output)
**Node Version**: 18.x

### Environment Variables

Set in Netlify dashboard: **Site Settings** → **Environment Variables**

```bash
# Required
VITE_API_URL=https://mcpress-chatbot-production.up.railway.app

# Optional (for local dev)
NODE_VERSION=18
```

### netlify.toml Configuration

**Location**: `frontend/netlify.toml`

```toml
[build]
  command = "npm run build"
  publish = "dist"  # Vite output directory

[build.environment]
  VITE_API_URL = "https://mcpress-chatbot-production.up.railway.app"

# API proxy (if needed)
[[redirects]]
  from = "/api/*"
  to = "https://mcpress-chatbot-production.up.railway.app/:splat"
  status = 200
  force = true
```

### Deployment Process

#### Automatic (Recommended)

1. Push to `main` branch:
   ```bash
   git add frontend/
   git commit -m "Update frontend"
   git push origin main
   ```

2. Netlify auto-detects changes
3. Triggers build (~2-3 minutes)
4. Deploys to production CDN
5. Check deploy status: https://app.netlify.com/sites/mcpress-chatbot/deploys

#### Manual

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Build locally
cd frontend
npm run build

# Deploy
netlify deploy --prod
```

### Deploy Previews

Every pull request automatically gets a preview deployment:
- URL format: `https://deploy-preview-XXX--mcpress-chatbot.netlify.app`
- Test changes before merging
- Automatic when PR is opened

### Troubleshooting Netlify

**Build fails with "Command failed":**
```bash
# Check build logs in Netlify dashboard
# Common issues:
# 1. Missing dependencies
# 2. TypeScript errors
# 3. Environment variables not set

# Test locally first:
cd frontend
npm install
npm run build
```

**Site loads but can't connect to API:**
```bash
# Check environment variables
# Verify VITE_API_URL is set correctly
# Test API directly: curl https://mcpress-chatbot-production.up.railway.app/health
```

**Deploy succeeded but changes not visible:**
```bash
# Clear CDN cache
# In Netlify dashboard: Deploys → Trigger deploy → Clear cache and deploy site
```

---

## ⚙️ Backend Deployment (Railway)

### Current Configuration

**Project Name**: `mcpress-chatbot`
**Service Name**: `mcpress-chatbot-production`
**Region**: US East
**URL**: https://mcpress-chatbot-production.up.railway.app

### Services

#### 1. Backend API Service

**Runtime**: Python 3.11
**Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
**Port**: Dynamic (Railway assigns via `$PORT` env var)

**Source**:
- Connected to GitHub repository
- Auto-deploys from `main` branch
- Dockerfile: Not used (Railway auto-detects Python)

#### 2. PostgreSQL Database Service

**Type**: PostgreSQL 16
**Storage**: Persistent volume
**Backups**: Automatic daily backups
**Access**: Internal network only

**Extensions**:
- `pgvector` (vector similarity search)

### Environment Variables

Set in Railway dashboard: **Service** → **Variables**

```bash
# ===== REQUIRED =====

# Database (automatically set by Railway when you add PostgreSQL)
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway

# Enable PostgreSQL mode (CRITICAL!)
USE_POSTGRESQL=true
ENABLE_POSTGRESQL=true

# OpenAI API key
OPENAI_API_KEY=sk-proj-...

# ===== OPTIONAL (with defaults) =====

# Search configuration
RELEVANCE_THRESHOLD=0.55
MAX_SOURCES=12
INITIAL_SEARCH_RESULTS=30

# OpenAI configuration
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000

# Frontend URL (for CORS)
FRONTEND_URL=https://mcpress-chatbot.netlify.app
CORS_ORIGINS=["https://mcpress-chatbot.netlify.app"]
```

### Deployment Process

#### Automatic (Recommended)

1. Push to `main` branch:
   ```bash
   git add backend/
   git commit -m "Update backend"
   git push origin main
   ```

2. Railway auto-detects changes
3. Builds new deployment (~3-5 minutes)
4. Runs health checks
5. Switches traffic to new deployment
6. Check logs: Railway dashboard → Deployments → [latest] → View Logs

#### Manual via Dashboard

1. Go to Railway dashboard
2. Select `mcpress-chatbot-production` service
3. Click **Deployments** tab
4. Click **Deploy** button (redeploys latest commit)

#### Manual via CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

### Health Checks

Railway automatically checks:
- **Endpoint**: `/health`
- **Expected Response**: `200 OK`
- **Timeout**: 30 seconds

Example response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_store": "PostgresVectorStore",
  "openai": "configured"
}
```

### Startup Verification

Check Railway logs for these messages:

**✅ Good (pgvector working):**
```
============================================================
🔍 VECTOR STORE INITIALIZATION
============================================================
✅ Vector Store Class: PostgresVectorStore
📊 pgvector enabled: True
📊 Total documents in database: 227,032
✅ Using native pgvector with cosine distance operator
============================================================
```

**❌ Bad (pgvector not working):**
```
⚠️ pgvector not available
🔄 Using pure PostgreSQL with embedding similarity calculation
```

**If you see the bad message:**
1. Check `DATABASE_URL` points to correct database
2. Verify `USE_POSTGRESQL=true` is set
3. Confirm pgvector extension is installed:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Troubleshooting Railway

**Deployment timeout / health check fails:**
```bash
# Check logs for errors
# Common issues:
# 1. Database connection timeout (increase command_timeout in code)
# 2. Missing environment variables
# 3. Python dependency issues

# Check DATABASE_URL is set:
railway variables

# Test database connection:
railway run python3 -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(os.getenv('DATABASE_URL')))"
```

**High memory usage / crashes:**
```bash
# Check for memory leaks in logs
# Increase Railway plan if needed (Pro plan: 8GB RAM)

# Monitor usage:
# Railway dashboard → Service → Metrics
```

**pgvector not detected:**
```bash
# Connect to database via Railway dashboard
# Or use psql:
railway connect postgres

# Install extension:
CREATE EXTENSION IF NOT EXISTS vector;

# Verify:
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Slow startup / migrations taking forever:**
```bash
# Increase command_timeout in backend/vector_store_postgres.py
# Currently set to 60 seconds (line 66)

# Check database has indexes:
\d documents

# Should show:
# - documents_embedding_idx (ivfflat)
# - documents_filename_idx
# - documents_metadata_idx
```

---

## 🔄 Deployment Workflow

### Typical Development Cycle

```bash
# 1. Work on feature locally
cd /Users/kevinvandever/kev-dev/mcpress-chatbot
git checkout -b feature/my-feature

# 2. Test locally
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload

# In another terminal:
cd frontend
npm install
npm run dev

# 3. Commit changes
git add .
git commit -m "Add my feature"

# 4. Push and create PR
git push origin feature/my-feature
# Create PR on GitHub

# 5. Review Netlify deploy preview
# URL appears as comment on PR

# 6. Merge to main
# Both Netlify and Railway auto-deploy

# 7. Verify production
python3 test_pgvector_chatbot.py
```

### Rollback Process

**Netlify:**
1. Go to Netlify dashboard → Deploys
2. Find previous working deployment
3. Click **Publish deploy**
4. Previous version is now live

**Railway:**
1. Go to Railway dashboard → Deployments
2. Find previous working deployment
3. Click **⋮** menu → **Redeploy**
4. Confirm redeployment
5. Wait for health checks to pass

**Or revert git commit:**
```bash
git revert HEAD
git push origin main
# Both services auto-deploy previous version
```

---

## 🔐 Environment Variable Management

### Where They're Set

| Variable | Netlify | Railway | Notes |
|----------|---------|---------|-------|
| `VITE_API_URL` | ✅ | ❌ | Frontend only |
| `DATABASE_URL` | ❌ | ✅ Auto | Set by Railway |
| `USE_POSTGRESQL` | ❌ | ✅ | Must be `true` |
| `OPENAI_API_KEY` | ❌ | ✅ | Secret |
| `RELEVANCE_THRESHOLD` | ❌ | ✅ | Optional |
| `FRONTEND_URL` | ❌ | ✅ | For CORS |

### Adding New Variables

**Netlify:**
1. Dashboard → Site Settings → Environment Variables
2. Click **Add a variable**
3. Key: `VITE_SOMETHING` (must start with `VITE_`)
4. Value: your value
5. Click **Save**
6. Trigger new deploy (changes require rebuild)

**Railway:**
1. Dashboard → Service → Variables
2. Click **+ New Variable**
3. Key: `SOMETHING`
4. Value: your value
5. Click **Add**
6. Service auto-restarts with new variable

### Secrets Management

**DO NOT commit secrets to git!**

Instead:
1. Add to `.env` file (gitignored)
2. Set in Railway/Netlify dashboards
3. Use environment variable references in code

Example:
```python
# ❌ BAD
OPENAI_API_KEY = "sk-proj-abc123..."

# ✅ GOOD
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")
```

---

## 📊 Monitoring & Logs

### Netlify Logs

**Build Logs:**
- Dashboard → Deploys → [deployment] → Deploy log
- Shows npm install, build output, publish status

**Function Logs:**
- Not used in this project (no serverless functions)

### Railway Logs

**Application Logs:**
- Dashboard → Service → Deployments → [latest] → View Logs
- Real-time streaming
- Filter by log level

**Database Logs:**
- Dashboard → PostgreSQL service → Metrics
- Query performance
- Connection pool usage

### Log Viewing

**Netlify CLI:**
```bash
netlify logs --function
netlify logs --stream
```

**Railway CLI:**
```bash
railway logs
railway logs --follow  # Stream logs
```

**Direct from code:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Something happened")
# Appears in Railway logs
```

---

## 🚨 Common Deployment Issues

### Issue 1: Netlify build succeeds but site doesn't work

**Symptoms**: Build logs show success, but site is broken

**Causes**:
- Environment variables not set
- API URL incorrect
- Build output directory wrong

**Solution**:
```bash
# Check environment variables in Netlify dashboard
# Verify VITE_API_URL is correct
# Test API: curl https://mcpress-chatbot-production.up.railway.app/health

# Check build output:
cd frontend
npm run build
ls dist/  # Should contain index.html, assets/, etc.
```

### Issue 2: Railway deployment timeout

**Symptoms**: Deployment fails with "Health check timeout"

**Causes**:
- Database connection slow/failing
- Missing environment variables
- Startup code taking too long

**Solution**:
```bash
# Check logs in Railway dashboard
# Look for error messages

# Verify DATABASE_URL:
railway variables | grep DATABASE_URL

# Test database connection:
railway run python3 -c "import os; print(os.getenv('DATABASE_URL'))"

# Increase command_timeout in backend/vector_store_postgres.py
```

### Issue 3: CORS errors in browser

**Symptoms**: `Access-Control-Allow-Origin` errors in console

**Causes**:
- CORS_ORIGINS not configured
- Frontend URL not in allowed origins

**Solution**:
```python
# backend/main.py - check CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mcpress-chatbot.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Or set in Railway:
CORS_ORIGINS=["https://mcpress-chatbot.netlify.app"]
```

### Issue 4: Database connection pool exhausted

**Symptoms**: `asyncpg.exceptions.TooManyConnectionsError`

**Causes**:
- Too many concurrent requests
- Connection pool too small
- Connections not being closed

**Solution**:
```python
# backend/vector_store_postgres.py
self.pool = await asyncpg.create_pool(
    self.database_url,
    min_size=1,
    max_size=10,  # Increase if needed
    command_timeout=60
)

# Always close connections:
async with self.pool.acquire() as conn:
    # Use connection
    pass  # Auto-closes
```

---

## 📝 Deployment Checklist

### Before Deploying

- [ ] Run tests locally: `python3 test_fixes_local.py`
- [ ] Check for TypeScript errors: `cd frontend && npm run build`
- [ ] Review changed files: `git diff`
- [ ] Update version in code if needed
- [ ] Commit with clear message

### After Deploying

- [ ] Check Netlify deploy status
- [ ] Check Railway deploy status and logs
- [ ] Verify health endpoint: `curl https://mcpress-chatbot-production.up.railway.app/health`
- [ ] Test frontend: Open https://mcpress-chatbot.netlify.app
- [ ] Run production tests: `python3 test_pgvector_chatbot.py`
- [ ] Check error rates in logs
- [ ] Monitor for 15 minutes for errors

### If Something Goes Wrong

- [ ] Check logs immediately (Netlify and Railway)
- [ ] Identify error message
- [ ] Roll back if critical: Redeploy previous version
- [ ] Fix issue locally
- [ ] Test fix thoroughly
- [ ] Deploy again with fix

---

## 🎯 Quick Commands Reference

```bash
# === NETLIFY ===

# Deploy preview
netlify deploy

# Deploy to production
netlify deploy --prod

# View logs
netlify logs

# Open dashboard
netlify open


# === RAILWAY ===

# View logs
railway logs

# Stream logs
railway logs --follow

# Connect to database
railway connect postgres

# Run command
railway run python3 script.py

# Open dashboard
railway open


# === GIT ===

# Deploy both services
git push origin main

# Create feature branch
git checkout -b feature/name

# Revert bad deploy
git revert HEAD
git push origin main


# === TESTING ===

# Test local backend
cd backend
python3 -m uvicorn backend.main:app --reload

# Test local frontend
cd frontend
npm run dev

# Test production
python3 test_pgvector_chatbot.py
```

---

## 📞 Support Resources

**Netlify:**
- Docs: https://docs.netlify.com
- Status: https://www.netlifystatus.com
- Support: https://answers.netlify.com

**Railway:**
- Docs: https://docs.railway.app
- Status: https://status.railway.app
- Discord: https://discord.gg/railway

**Project:**
- Repository: https://github.com/kevinvandever/mcpress-chatbot
- Issues: https://github.com/kevinvandever/mcpress-chatbot/issues
- Owner: Kevin Vandever

---

**Document Version:** 1.0
**Last Updated:** October 7, 2025
