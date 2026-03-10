# Technology Stack

## Architecture
- **Monorepo**: Frontend and backend in single repository
- **Deployment**: Railway (backend), Netlify (frontend)
- **Database**: Supabase PostgreSQL 16+ with pgvector extension

## Backend Stack

### Core Framework
- **Language**: Python 3.11+
- **Framework**: FastAPI (async)
- **Server**: Uvicorn with async support
- **Database Driver**: asyncpg (async PostgreSQL)

### AI/ML Components
- **LLM**: OpenAI GPT-4 (gpt-4o-mini model)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- **Vector Search**: pgvector with cosine distance operator (`<=>`)
- **Token Counting**: tiktoken

### PDF Processing
- **Primary**: PyMuPDF (fitz) for text/image extraction
- **Supplementary**: pdfplumber, pytesseract for OCR
- **Text Splitting**: langchain-text-splitters (recursive character splitter)
- **Chunk Size**: ~1000 characters with 200 character overlap

### Key Dependencies
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
openai>=1.3.0
sentence-transformers>=2.2.2
asyncpg>=0.29.0
PyMuPDF>=1.23.0
```

## Frontend Stack

### Core Framework
- **Framework**: Next.js 14.0.3
- **Language**: TypeScript 5.x
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3.3

### Key Dependencies
- **HTTP Client**: axios
- **Markdown**: react-markdown with remark-gfm
- **Code Highlighting**: react-syntax-highlighter
- **File Upload**: react-dropzone

### Build Configuration
- **Build Command**: `SKIP_TYPE_CHECK=true next build`
- **Type Checking**: Disabled for builds (legacy codebase)
- **ESLint**: Disabled during builds

## Database Schema

### Primary Table
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    embedding vector(384),  -- pgvector type
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index
CREATE INDEX documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Testing and Deployment Workflow

### CRITICAL: All Testing is Done on Railway
- **NO LOCAL TESTING**: Do not attempt to run tests locally
- **NO LOCAL DATABASE**: There is no local database setup
- **Railway-only**: All tests, migrations, and database operations must be executed on Railway
- **Test execution**: Push code to trigger Railway deployment, then run tests via Railway CLI or SSH
- **Python Command**: Always use `python3` instead of `python` (macOS requirement)

### Testing Commands
```bash
# WRONG - Do not use locally
python -m pytest backend/test_file.py

# CORRECT - Use python3 for any local scripts
python3 test_script.py

# CORRECT - Run tests on Railway via SSH
railway shell
python3 -m pytest backend/test_file.py
```

## CRITICAL: When to Deploy to Railway

**ALWAYS DEPLOY FIRST** when any of these files are modified:

### Backend Files (Require Railway Deployment)
- `backend/*.py` - All Python backend code
- `requirements.txt` - Python dependencies
- `Procfile` - Railway startup configuration
- `runtime.txt` - Python version specification
- Any database migration files

### Frontend Files (Require Netlify Deployment)
- `frontend/**/*` - All frontend code
- `package.json` - Node.js dependencies
- `netlify.toml` - Netlify configuration

### Deployment Process
```bash
# 1. Commit and push changes
git add .
git commit -m "Description of changes"
git push origin main

# 2. Wait for deployment (10-15 minutes for Railway, 2-3 minutes for Netlify)
# Monitor at: https://railway.app/dashboard

# 3. THEN run tests on Railway
railway run python3 your_test_script.py
```

### Files That DON'T Require Deployment
- Root-level test scripts (e.g., `test_*.py`, `check_*.py`, `debug_*.py`)
- Documentation files (`.md` files)
- Configuration examples (`.env.example`)
- Data files (`.csv`, `.json`)

### How to Tell if Deployment is Needed
**If you modify code that the application imports or executes, you MUST deploy first.**

Examples:
- ✅ Modified `backend/excel_import_service.py` → **DEPLOY FIRST**
- ✅ Modified `frontend/components/ChatInterface.tsx` → **DEPLOY FIRST**  
- ❌ Created `test_new_feature.py` in root → **No deployment needed**
- ❌ Updated `README.md` → **No deployment needed**

### Testing Workflow
1. **Make code changes**
2. **Deploy if needed** (see rules above)
3. **Wait for deployment to complete**
4. **Run tests on Railway** (not locally)
5. **Verify functionality**

**Remember: This project has NO local development environment. All testing must be done on Railway after deployment.**

## Running Scripts on Railway

### 🚨 CRITICAL: DO NOT USE RAILWAY SHELL - IT WILL FAIL! 🚨

**Railway shell (`railway shell`) is UNRELIABLE and WILL FAIL.**

**✅ ALWAYS use API-based scripts instead:**
1. Create an API endpoint in `backend/` for your functionality
2. Register it in `backend/main.py`
3. Deploy to Railway (git push)
4. Call the API from a local Python script using `requests`
5. Run the script locally: `python3 my_script.py`

**See examples below for the correct pattern.**

---

### Overview
Since this project has no local development environment, scripts that need database access must use one of two approaches: API-based testing (PREFERRED) or Railway shell execution (PROBLEMATIC).

### ⚠️ CRITICAL: Railway Shell is UNRELIABLE - Use API Endpoints Instead!

**Railway shell (`railway shell`) is known to fail frequently and should be AVOIDED.**

### ✅ PREFERRED METHOD: API-Based Testing

**Create API endpoints for backend functionality and call them via HTTP requests.**

This is the RELIABLE and RECOMMENDED approach:

```python
# Example: API-based script (runs locally, no Railway shell needed)
import requests

API_URL = "https://mcpress-chatbot-production.up.railway.app"

# Call API endpoint instead of importing backend modules
response = requests.get(f"{API_URL}/api/diagnostics/authors")
data = response.json()
print(f"Found {data['total_issues']} issues")
```

**Why API-based is better:**
- ✅ Runs locally on your machine (no Railway shell needed)
- ✅ Reliable and consistent
- ✅ No dependency installation required
- ✅ Works with file uploads via multipart/form-data
- ✅ Can be tested immediately without deployment
- ✅ Follows established patterns in the codebase

**Examples of API-based scripts in the codebase:**
- `run_author_diagnostics_via_api.py` - Calls `/api/diagnostics/authors`
- `compare_csv_via_api.py` - Calls `/api/compare-csv-database`
- `verify_excel_import.py` - Calls `/api/association-checker/compare-excel`
- `run_author_corrections.py` - Calls `/api/fix-book-authors-from-csv`
- `run_url_corrections.py` - Calls `/api/fix-book-urls-from-csv`

**How to create API-based scripts:**

1. **Create an API endpoint** in `backend/` (e.g., `backend/my_feature_endpoint.py`):
```python
from fastapi import APIRouter, UploadFile, File
from backend.my_service import MyService

router = APIRouter()

@router.get("/api/my-feature/check")
async def check_feature():
    service = MyService()
    result = await service.check()
    return {"status": "ok", "data": result}

@router.post("/api/my-feature/upload")
async def upload_file(file: UploadFile = File(...)):
    # Process uploaded file
    return {"message": "File processed"}
```

2. **Register the endpoint** in `backend/main.py`:
```python
try:
    from my_feature_endpoint import router as my_feature_router
    app.include_router(my_feature_router)
    print("✅ My feature endpoint enabled")
except Exception as e:
    print(f"⚠️ My feature endpoint not available: {e}")
```

3. **Create a local script** that calls the API:
```python
#!/usr/bin/env python3
import requests
import sys

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def main():
    response = requests.get(f"{API_URL}/api/my-feature/check")
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    main()
```

4. **Run locally** (no Railway shell needed!):
```bash
python3 my_script.py
```

### ❌ AVOID: Railway Shell (Interactive Execution)

**Railway shell is UNRELIABLE and should only be used as a last resort.**

This method frequently fails and is NOT recommended:

### ❌ AVOID: Railway Shell (Interactive Execution)

**Railway shell is UNRELIABLE and should only be used as a last resort.**

This method frequently fails and is NOT recommended:

```bash
# ❌ AVOID - Railway shell is unreliable
railway shell
python3 script_name.py
exit
```

**Why Railway shell DOESN'T WORK reliably:**
- Frequently hangs or times out
- Connection issues are common
- Difficult to debug when it fails
- Not suitable for production workflows

**If you absolutely must use Railway shell:**
1. Ensure your script is idempotent (can be run multiple times safely)
2. Keep scripts short and focused
3. Have a backup plan (API endpoint) ready
4. Expect failures and plan accordingly

### Why `railway run` DOESN'T WORK

`railway run python3 script.py` executes the script LOCALLY with Railway environment variables:
- The script still runs on your local machine, not on Railway
- Backend imports will fail because dependencies aren't installed locally
- Database connections will fail because the DATABASE_URL points to a remote host

**Example:**
```bash
# ❌ WRONG - Runs locally with Railway env vars (will fail)
railway run python3 diagnose_author_issues.py
```

### Migration Path: Converting Railway Shell Scripts to API-Based

If you have an existing script that uses Railway shell, convert it to API-based:

**Before (Railway shell - unreliable):**
```python
# diagnose_issues.py - Must run in railway shell
from backend.my_service import MyService

async def main():
    service = MyService()
    result = await service.diagnose()
    print(result)
```

**After (API-based - reliable):**

1. Create endpoint (`backend/my_service_endpoint.py`):
```python
from fastapi import APIRouter
from backend.my_service import MyService

router = APIRouter()

@router.get("/api/my-service/diagnose")
async def diagnose():
    service = MyService()
    result = await service.diagnose()
    return result
```

2. Create local script (`diagnose_issues.py`):
```python
import requests

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def main():
    response = requests.get(f"{API_URL}/api/my-service/diagnose")
    print(response.json())

if __name__ == "__main__":
    main()
```

3. Run locally:
```bash
python3 diagnose_issues.py  # No Railway shell needed!
```

### Common Issues and Solutions

#### Issue: "No module named 'backend.module_name'" or database connection errors
**Cause**: Script is trying to import backend modules locally
**Solution**: Convert to API-based approach (see examples above)

```bash
# ❌ WRONG - Trying to import backend modules locally
python3 script_with_backend_imports.py
# Error: ModuleNotFoundError: No module named 'backend'

# ✅ CORRECT - Use API endpoint instead
python3 script_using_api_calls.py
# Success: Calls Railway API, no imports needed
```

#### Issue: Need to process a file with backend logic
**Cause**: Want to upload and process a file using backend services
**Solution**: Create API endpoint that accepts file uploads

```python
# API endpoint (backend/my_endpoint.py)
from fastapi import APIRouter, UploadFile, File

@router.post("/api/process-file")
async def process_file(file: UploadFile = File(...)):
    content = await file.read()
    # Process file
    return {"status": "processed"}

# Local script
import requests

with open('myfile.csv', 'rb') as f:
    files = {'file': ('myfile.csv', f)}
    response = requests.post(f"{API_URL}/api/process-file", files=files)
    print(response.json())
```

#### Issue: Railway shell hangs or times out
**Cause**: Railway shell is unreliable
**Solution**: Don't use Railway shell - convert to API-based approach instead

### Script Categories

#### ✅ PREFERRED: API-based scripts (run locally)
- Scripts using `requests` to call Railway API endpoints
- File upload scripts using multipart/form-data
- Data analysis scripts that fetch data via API
- Diagnostic scripts that call `/api/diagnostics/*` endpoints
- Correction scripts that call `/api/fix-*` endpoints

**Examples:**
- `verify_excel_import.py` - Uploads Excel and compares via API
- `run_author_diagnostics_via_api.py` - Calls diagnostics API
- `compare_csv_via_api.py` - Compares CSV via API
- `run_author_corrections.py` - Applies corrections via API

#### ⚠️ AVOID: Railway shell scripts
- Scripts importing from `backend.*` modules
- Scripts requiring asyncpg or other backend dependencies
- Database migration scripts (convert to API endpoints)
- Scripts using backend services directly

**If you must use Railway shell:**
- Keep scripts very short (< 50 lines)
- Make them idempotent
- Have an API-based backup ready
- Expect failures

### Best Practices

1. **ALWAYS prefer API-based scripts over Railway shell** - Railway shell is unreliable
2. **Create API endpoints for new functionality** - Makes testing easier and more reliable
3. **Use `requests` library for API calls** - Simple and works everywhere
4. **Check deployment status** before testing (ensure latest code is deployed)
5. **Use descriptive endpoint names** - `/api/feature/action` pattern
6. **Return structured JSON** from API endpoints for easy parsing
7. **Handle file uploads via multipart/form-data** - Works reliably with `requests`
8. **Add error handling** in both endpoint and script
9. **Log API responses** for debugging
10. **Test endpoints with curl first** before writing Python scripts

### Quick Reference: API-Based Script Template

```python
#!/usr/bin/env python3
"""
Description of what this script does

Usage:
    python3 my_script.py [arguments]
"""

import requests
import sys
import os

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-production.up.railway.app")

def main():
    """Main entry point"""
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 my_script.py <argument>")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    try:
        # Call API endpoint
        response = requests.get(
            f"{API_URL}/api/my-endpoint",
            params={"arg": arg},
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        # Process response
        data = response.json()
        print(f"✅ Success: {data}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: API request failed: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
```

### Example Patterns

#### ✅ RECOMMENDED: API-based test (runs locally, reliable)
```python
import requests

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_service():
    response = requests.get(f"{API_URL}/api/health")
    return response.status_code == 200

def test_with_file_upload():
    with open('data.csv', 'rb') as f:
        files = {'file': ('data.csv', f)}
        response = requests.post(
            f"{API_URL}/api/upload-endpoint",
            files=files
        )
    return response.json()
```

#### ❌ AVOID: Direct module import (requires Railway shell, unreliable)
```python
# This will fail locally and Railway shell is unreliable
from backend.excel_import_service import ExcelImportService

def process_file():
    service = ExcelImportService()
    # ... this won't work locally
```

#### ✅ SOLUTION: Create API endpoint instead
```python
# backend/excel_import_endpoint.py
from fastapi import APIRouter, UploadFile, File
from backend.excel_import_service import ExcelImportService

router = APIRouter()

@router.post("/api/excel/import")
async def import_excel(file: UploadFile = File(...)):
    service = ExcelImportService()
    result = await service.process(file)
    return {"status": "success", "result": result}

# Then call it from local script:
# python3 import_excel.py myfile.xlsx
```

### Debugging API-Based Scripts

1. **Test endpoint with curl first**:
```bash
curl https://mcpress-chatbot-production.up.railway.app/api/my-endpoint
```

2. **Check Railway logs** for backend errors:
```bash
railway logs
```

3. **Verify deployment**: Ensure latest code is deployed to Railway

4. **Use verbose mode** in requests:
```python
response = requests.get(url, timeout=60)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text}")
```

5. **Test locally with Railway API**: No need to deploy for testing

6. **Check API documentation**: Review endpoint parameters and expected responses

### Debugging Railway Shell Scripts (if you must use them)

1. **Check Railway logs**: `railway logs`
2. **Verify deployment**: Ensure latest code is deployed
3. **Keep scripts short**: < 50 lines to minimize failure points
4. **Add print statements**: For debugging progress
5. **Make idempotent**: So you can retry safely
6. **Have API backup**: Convert to API-based if shell fails

### Local Development Limitations
- **No FastAPI server**: Cannot run `uvicorn` locally due to missing dependencies
- **No database access**: All database operations must be done on Railway
- **Limited testing**: Only isolated functions can be tested locally (no imports from backend modules)
- **Deployment required**: All integration testing requires Railway deployment

### Backend (Railway)
- **Auto-deploy**: Push to `main` branch triggers Railway deployment
- **Manual deploy**: Trigger redeploy in Railway dashboard
- **Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Health check**: `/health` endpoint
- **Deploy time**: ~10-15 minutes
- **Run tests on Railway**: Use Railway CLI or connect via SSH to execute `python3 -m pytest`

### Frontend (Netlify)
- **Auto-deploy**: Push to `main` branch triggers Netlify deployment
- **Build command**: `cd frontend && npm install && npm run build`
- **Publish directory**: `frontend/dist`
- **Deploy time**: ~2-3 minutes

### Database Operations
```bash
# Run migrations (via Railway or direct connection)
python3 backend/run_migration_003.py

# Check database status
python3 check_pgvector.py
```

## Environment Variables

### Backend (Railway)
```
DATABASE_URL=postgresql://...
USE_POSTGRESQL=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.5
OPENAI_MAX_TOKENS=3000
RELEVANCE_THRESHOLD=0.55
MAX_SOURCES=12
INITIAL_SEARCH_RESULTS=30
```

### Frontend (Netlify)
```
VITE_API_URL=https://mcpress-chatbot-production.up.railway.app
```

## Critical Configuration Notes

### Vector Search Thresholds
- **pgvector uses cosine distance**: 0 = identical, 2 = opposite
- **Lower threshold = more permissive** (returns more results)
- **Default threshold**: 0.55 (DO NOT increase above 0.65)
- **Dynamic thresholds** in `chat_handler.py` adjust based on query type

### Import Paths
- **Railway deployment**: Use `backend.module_name` format
- **Local development**: Use relative imports or `backend.module_name`
- **Always test imports work in both environments**

## Performance Targets
- **Vector Search**: <500ms
- **Chat First Token**: 1-3 seconds
- **PDF Processing**: 2-5 seconds per document
- **Embedding Generation**: ~40 docs/second
