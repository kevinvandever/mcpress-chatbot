# 🤖 README for AI Agents

**Project**: MC Press Chatbot
**Owner**: Kevin Vandever
**Purpose**: Quick reference for AI assistants working on this codebase

---

## ⚡ Quick Start

### What This Project Is

A **Retrieval-Augmented Generation (RAG) chatbot** for MC Press technical books:
- **Frontend**: React/TypeScript on Netlify
- **Backend**: FastAPI (Python) on Railway
- **Database**: PostgreSQL 16 with pgvector on Railway
- **AI**: OpenAI GPT-3.5-turbo for responses
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)

### Key Files You Should Know

```
mcpress-chatbot/
├── TECHNOLOGY_STACK.md       ← Complete tech documentation
├── DEPLOYMENT_GUIDE.md        ← Netlify & Railway deployment
├── CHANGES_SUMMARY.md         ← What changed and why
├── PGVECTOR_FIXES_SUMMARY.md  ← Vector search fixes
├── backend/
│   ├── main.py                ← FastAPI app entry point
│   ├── chat_handler.py        ← RAG logic + OpenAI integration
│   ├── vector_store_postgres.py ← pgvector search
│   ├── config.py              ← IMPORTANT: Thresholds here!
│   └── requirements.txt       ← Python dependencies
└── frontend/
    ├── src/
    │   ├── App.tsx            ← Main React app
    │   └── components/
    │       └── ChatInterface.tsx ← Chat UI
    └── package.json           ← Node dependencies
```

---

## 🎯 Critical Configuration

### Search Thresholds (backend/config.py)

```python
SEARCH_CONFIG = {
    "relevance_threshold": 0.55,     # CRITICAL: Don't go above 0.65!
    "max_sources": 12,                # Sources to include in context
    "initial_search_results": 30      # Initial candidates
}
```

**⚠️ IMPORTANT RULES:**
1. **NEVER increase threshold above 0.65** - Will filter out too many results
2. **Lower threshold = more results** (0.55 is the sweet spot)
3. **Higher threshold = fewer results** (distance-based, not similarity!)
4. pgvector uses **cosine distance** where 0=identical, 2=opposite

### Dynamic Thresholds (backend/chat_handler.py:230-258)

```python
# Lower = more permissive (better for pgvector distance)
rpg_keywords:  0.70   # Very permissive
code_keywords: 0.65   # Permissive
tech_keywords: 0.60   # Moderate
exact_matches: 0.40   # Strict
general:       0.55   # Default
```

---

## 🚫 What NOT To Do

### ❌ DON'T:
1. **Increase thresholds thinking it improves quality** - It filters out good results!
2. **Add `LIMIT 5000` to pgvector queries** - It can search all 227k docs efficiently
3. **Mix up distance and similarity** - pgvector returns DISTANCE (lower=better)
4. **Commit secrets** - Use Railway/Netlify environment variables
5. **Deploy without testing** - Always run `test_fixes_local.py` first

### ✅ DO:
1. **Lower thresholds** when users complain about few results
2. **Check startup logs** to verify pgvector is enabled
3. **Test with real queries** after config changes
4. **Add logging** when debugging issues
5. **Read TECHNOLOGY_STACK.md** before making architecture changes

---

## 🔍 Common Tasks

### Task: User Says "Not Enough Results"

```python
# backend/config.py
# Lower the threshold (currently 0.55)
"relevance_threshold": 0.50  # More permissive

# Or adjust dynamic threshold for specific query type
# backend/chat_handler.py
rpg_keywords: 0.75  # Was 0.70, now more permissive
```

### Task: User Says "Results Not Relevant"

```python
# backend/config.py
# Slightly raise threshold (but not above 0.65!)
"relevance_threshold": 0.60  # More strict

# Or increase max_sources to get more context
"max_sources": 15  # Was 12
```

### Task: Deploy Changes

```bash
# 1. Test locally
python3 test_fixes_local.py

# 2. Commit and push
git add .
git commit -m "Description of changes"
git push origin main

# 3. Verify deployment (both auto-deploy)
# - Netlify: 2-3 minutes
# - Railway: 3-5 minutes

# 4. Test production
python3 test_pgvector_chatbot.py
```

### Task: Check If pgvector Is Working

```bash
# Check Railway logs for:
✅ Vector Store Class: PostgresVectorStore
📊 pgvector enabled: True
📊 Total documents in database: 227,032

# If you see:
❌ ⚠️ pgvector not available

# Then:
# 1. Check DATABASE_URL in Railway env vars
# 2. Verify USE_POSTGRESQL=true
# 3. Connect to database and run: CREATE EXTENSION IF NOT EXISTS vector;
```

### Task: Investigate Slow Queries

```python
# Check these in backend/vector_store_postgres.py:

# 1. Connection timeout (line 66)
command_timeout=60  # Increase if queries timeout

# 2. Pool size (line 65)
max_size=10  # Increase if many concurrent users

# 3. Check for LIMIT clauses that shouldn't be there
# Should only limit FINAL results, not search space
```

---

## 🐛 Debugging Guide

### Problem: No sources returned

**Check:**
1. Threshold too high? (should be 0.55)
2. Query logging shows what's being filtered
3. Database has documents with embeddings?

**Fix:**
```python
# backend/config.py
"relevance_threshold": 0.55  # Lower if needed

# Check database:
SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;
# Should return ~188,672 or more
```

### Problem: Deployment fails

**Check:**
- Railway logs for error message
- Environment variables set correctly
- Health check endpoint responding

**Common causes:**
- DATABASE_URL not set or wrong
- OPENAI_API_KEY missing
- Python dependency installation failed

### Problem: CORS errors in browser

**Fix:**
```python
# backend/main.py
# Ensure CORS includes Netlify URL:
allow_origins=["https://mcpress-chatbot.netlify.app"]
```

---

## 📊 Understanding The Metrics

### Distance vs Similarity

```
pgvector cosine distance: 0.0 ─────────────────► 2.0
                      (identical)           (opposite)

Similarity (converted):  1.0 ◄───────────────── 0.0
                      (identical)           (opposite)

Conversion: similarity = 1 - distance
```

### What Good Results Look Like

```
Query: "What is RPG programming?"

✅ Good:
- 8-12 sources returned
- Confidence: 0.45-0.70
- Distance range: 0.30-0.55
- Response includes book excerpts with page numbers

❌ Bad:
- 0-2 sources returned
- Confidence: 0.05-0.20
- Distance range: 0.80-1.50
- Generic response without book citations
```

### Threshold Sweet Spots

```
0.40 = Very strict (exact matches only)
0.55 = ✅ SWEET SPOT (balanced quality + quantity)
0.65 = Maximum permissive (don't go higher!)
0.75 = ❌ Too strict (filters out good results)
```

---

## 📚 Documentation Index

For detailed information, read:

1. **TECHNOLOGY_STACK.md** - Full technology overview
   - Architecture diagrams
   - All dependencies
   - Database schema
   - Configuration details

2. **DEPLOYMENT_GUIDE.md** - Netlify & Railway setup
   - Environment variables
   - Deployment process
   - Troubleshooting
   - Rollback procedures

3. **CHANGES_SUMMARY.md** - What changed on Oct 7, 2025
   - Visual comparison
   - Why changes were made
   - Impact analysis

4. **PGVECTOR_FIXES_SUMMARY.md** - Vector search fixes
   - 5 critical issues identified
   - Fixes applied
   - Expected results

---

## 🔑 Key Principles

### 1. Distance Semantics Matter

```python
# pgvector cosine distance (0=identical, 2=opposite)
# Lower threshold = MORE results (more permissive)
# Higher threshold = FEWER results (more strict)

# This is OPPOSITE of similarity!
# similarity (0=unrelated, 1=identical)
# Lower threshold = FEWER results
# Higher threshold = MORE results
```

### 2. pgvector Is Fast

```python
# DON'T limit search space
# ❌ LIMIT 5000  # Old PostgreSQL fallback
# ✅ No limit!   # pgvector can handle 227k docs

# Only limit FINAL results:
LIMIT $2  # User's requested number of results
```

### 3. Test Everything

```bash
# Before deploying:
python3 test_fixes_local.py

# After deploying:
python3 test_pgvector_chatbot.py

# Query that should work:
"What is RPG programming?"
→ Should return 8+ sources with confidence >0.45
```

---

## 🎓 Learning Resources

### Understanding RAG (Retrieval-Augmented Generation)

1. **Embed** - Convert text to vectors (sentence-transformers)
2. **Store** - Save vectors in database (pgvector)
3. **Retrieve** - Find similar vectors to query (cosine distance)
4. **Augment** - Add retrieved content to prompt
5. **Generate** - LLM creates response (OpenAI GPT-3.5)

### pgvector Operators

```sql
-- Cosine distance (what we use)
embedding <=> query_vector

-- L2 distance
embedding <-> query_vector

-- Inner product
embedding <#> query_vector

-- We use <=> (cosine distance) because:
-- 1. Works well for semantic similarity
-- 2. Normalized (always 0-2 range)
-- 3. Not affected by vector magnitude
```

---

## 🚨 Emergency Procedures

### If Production Is Broken

1. **Check Railway logs** - Identify error
2. **Check Netlify logs** - Verify frontend built
3. **Test health endpoint** - `curl .../health`
4. **Roll back if needed**:
   ```bash
   # Railway dashboard → Deployments → Previous → Redeploy
   # Or:
   git revert HEAD
   git push origin main
   ```

### If Search Returns Nothing

```python
# Temporary fix - lower threshold significantly:
# backend/config.py
"relevance_threshold": 0.45  # Emergency permissive mode

# Then investigate why threshold is too strict
# Check query logs to see what's being filtered
```

### If Database Connection Fails

```bash
# Check Railway dashboard:
# - PostgreSQL service running?
# - DATABASE_URL environment variable set?

# Test connection:
railway connect postgres

# If needed, recreate pool in backend code
```

---

## ✅ Validation Checklist

Before saying "done" on any task:

- [ ] Code changes tested locally
- [ ] No secrets committed to git
- [ ] Documentation updated if architecture changed
- [ ] Thresholds validated (not above 0.65)
- [ ] Logs show pgvector is enabled (if backend changed)
- [ ] Test queries return reasonable results
- [ ] Deployment succeeded (both services)
- [ ] Production health check passes
- [ ] No errors in Railway logs for 10+ minutes

---

## 💡 Pro Tips

1. **Read the logs** - Railway logs show exactly what's happening
2. **Trust the tests** - `test_pgvector_chatbot.py` catches most issues
3. **Lower is better** - For distance thresholds, lower = more permissive
4. **pgvector scales** - Don't add artificial limits
5. **Document everything** - Future agents will thank you

---

## 📞 When You Need Help

**Check in this order:**
1. This file (quick reference)
2. TECHNOLOGY_STACK.md (detailed info)
3. DEPLOYMENT_GUIDE.md (infrastructure)
4. Railway logs (runtime errors)
5. Git history (what changed)

**Ask Kevin if:**
- Changing architecture
- Modifying database schema
- Updating deployment configuration
- Confused about distance vs similarity

---

**Last Updated**: October 7, 2025
**Next Review**: When making significant changes

---

## 🎯 One-Line Summary

**MC Press chatbot uses pgvector (not ChromaDB) on Railway with threshold 0.55 - never go above 0.65 or results disappear!**
