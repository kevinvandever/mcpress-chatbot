# Pinecone Migration Guide - MC Press Chatbot

**Created:** October 8, 2025
**Owner:** Kevin Vandever
**Purpose:** Guide for migrating embeddings from Railway PostgreSQL to Pinecone Serverless

---

## 📋 Table of Contents

1. [When to Migrate](#when-to-migrate)
2. [Cost Analysis](#cost-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Migration Steps](#migration-steps)
6. [Code Changes Required](#code-changes-required)
7. [Testing & Validation](#testing--validation)
8. [Rollback Plan](#rollback-plan)
9. [Post-Migration Cleanup](#post-migration-cleanup)

---

## ⏰ When to Migrate

### Decision Triggers:

Migrate when **ANY** of these conditions are met:

1. ✅ **Cost Trigger**
   - Railway bill exceeds **$25/month** for 2+ consecutive months
   - Database size exceeds **5 GB**
   - Current: ~$15-20/mo (Stay on Railway)

2. ✅ **Growth Trigger**
   - Total PDF collection exceeds **10 GB**
   - Document chunks exceed **500,000**
   - Current: 235,409 chunks (Stay on Railway)

3. ✅ **Performance Trigger**
   - Vector search latency exceeds **1 second** consistently
   - Database query timeouts become frequent
   - Current: <500ms (Stay on Railway)

4. ✅ **Scale Planning**
   - Planning to add **100+ new books** (>3 GB)
   - Business requires faster search (<200ms)
   - Current: Occasional additions (Stay on Railway)

### Current Status (Oct 2025):
```
🟢 STAY ON RAILWAY
- Cost: ~$15-20/mo (acceptable after cleanup)
- Size: 2.7 GB (well under limits)
- Performance: Good (<500ms searches)
- Recommendation: Revisit in 3-6 months or when DB hits 5GB
```

---

## 💰 Cost Analysis

### Current Architecture (Railway Only):

| Component | Size | Cost/Month |
|-----------|------|------------|
| Backend (FastAPI) | N/A | $5-8 |
| PostgreSQL (Metadata + Embeddings) | 2.7 GB | $10-15 |
| **Total** | **2.7 GB** | **$15-23/mo** |

### After Pinecone Migration:

| Component | Size | Cost/Month |
|-----------|------|------------|
| Backend (FastAPI) | N/A | $5-8 |
| PostgreSQL (Metadata only) | ~300 MB | $0-5 |
| Pinecone Serverless (Embeddings) | 2.7 GB | $0.26 |
| **Total** | **2.7 GB** | **$5.26-13.26/mo** |

**Immediate Savings:** $2-10/month

### Cost at Scale:

| Scenario | Railway Only | Pinecone Hybrid | Savings |
|----------|--------------|-----------------|---------|
| **Current (2.7GB)** | $20/mo | $8/mo | $12/mo |
| **+5GB PDFs (7.7GB)** | $40/mo | $8.50/mo | $31.50/mo |
| **+10GB PDFs (12.7GB)** | $60/mo | $9/mo | $51/mo |
| **+20GB PDFs (22.7GB)** | $100/mo | $10/mo | $90/mo |

**Break-even point:** Pinecone becomes significantly cheaper at >5 GB

---

## 🏗️ Architecture Overview

### Current Architecture:

```
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│         (Railway Service)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     PostgreSQL with pgvector            │
│         (Railway Database)              │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │ Metadata (filenames, content)    │  │
│  │ ~300 MB                          │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │ Embeddings (384-dim vectors)     │  │
│  │ ~2.4 GB                          │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Target Architecture (After Migration):

```
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│         (Railway Service)               │
└──────┬──────────────────────┬───────────┘
       │                      │
       │                      │
       ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│   PostgreSQL     │   │    Pinecone      │
│  (Railway DB)    │   │  (Serverless)    │
│                  │   │                  │
│  Metadata:       │   │  Embeddings:     │
│  - filenames     │   │  - 384-dim       │
│  - content       │   │    vectors       │
│  - page numbers  │   │  - 235k docs     │
│  - chunk index   │   │  - ~2.4 GB       │
│  - metadata      │   │                  │
│                  │   │  Optimized for   │
│  ~300 MB         │   │  vector search   │
└──────────────────┘   └──────────────────┘
```

### Data Flow:

**1. User Query:**
```
User → FastAPI → Pinecone (get similar doc IDs)
                    ↓
       PostgreSQL ← (fetch full content by IDs)
                    ↓
       OpenAI GPT ← (generate answer)
                    ↓
                  User
```

**2. Adding New PDFs:**
```
PDF Upload → FastAPI → sentence-transformers (generate embeddings)
                            ↓
                    ┌───────┴────────┐
                    ▼                ▼
              PostgreSQL        Pinecone
              (metadata)       (embeddings)
```

---

## ✅ Prerequisites

### 1. Accounts & API Keys

- [ ] **Pinecone Account** (Free tier available)
  - Sign up: https://www.pinecone.io/
  - Free tier: 1 index, unlimited vectors, serverless pricing
  - Get API key from dashboard

- [ ] **Railway Access**
  - Current PostgreSQL connection string
  - Ability to modify environment variables

### 2. Python Dependencies

Add to `backend/requirements.txt`:
```txt
pinecone-client>=3.0.0
```

### 3. Data Backup

**CRITICAL: Backup before migration!**

```bash
# Backup PostgreSQL embeddings
pg_dump $DATABASE_URL \
  --table=documents \
  --data-only \
  --file=embeddings_backup_$(date +%Y%m%d).sql

# Or use Python script (see migration_scripts/backup_embeddings.py)
```

### 4. Estimated Time

| Task | Duration |
|------|----------|
| Setup Pinecone account | 15 min |
| Export embeddings from PostgreSQL | 30-60 min |
| Upload to Pinecone | 60-90 min |
| Code changes | 2-3 hours |
| Testing | 1-2 hours |
| **Total** | **4-6 hours** |

---

## 🚀 Migration Steps

### Step 1: Create Pinecone Index

**Script:** `migration_scripts/01_create_pinecone_index.py`

```python
#!/usr/bin/env python3
"""
Create Pinecone serverless index for MC Press embeddings
"""

from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone
pc = Pinecone(api_key="YOUR_PINECONE_API_KEY")

# Create serverless index
index_name = "mcpress-chatbot-embeddings"

pc.create_index(
    name=index_name,
    dimension=384,  # all-MiniLM-L6-v2 dimension
    metric="cosine",  # Same as pgvector
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"  # Choose closest to Railway
    )
)

print(f"✅ Created Pinecone index: {index_name}")
print(f"   Dimension: 384")
print(f"   Metric: cosine")
print(f"   Type: Serverless")
```

**Run:**
```bash
cd migration_scripts
python3 01_create_pinecone_index.py
```

---

### Step 2: Export Embeddings from PostgreSQL

**Script:** `migration_scripts/02_export_embeddings.py`

```python
#!/usr/bin/env python3
"""
Export embeddings from PostgreSQL to Pinecone format
"""

import asyncpg
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def export_embeddings():
    """Export all embeddings from PostgreSQL"""

    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url, command_timeout=300)

    print("🔍 Fetching embeddings from PostgreSQL...")

    # Fetch in batches to avoid memory issues
    batch_size = 1000
    offset = 0
    all_vectors = []

    while True:
        rows = await conn.fetch(f"""
            SELECT
                id,
                filename,
                page_number,
                chunk_index,
                embedding
            FROM documents
            WHERE embedding IS NOT NULL
            ORDER BY id
            LIMIT {batch_size} OFFSET {offset}
        """)

        if not rows:
            break

        print(f"   Fetched {len(rows)} embeddings (offset: {offset})...")

        for row in rows:
            # Convert PostgreSQL vector to list
            embedding = list(row['embedding'])

            # Create Pinecone vector format
            vector = {
                'id': str(row['id']),  # Pinecone requires string IDs
                'values': embedding,
                'metadata': {
                    'filename': row['filename'],
                    'page_number': row['page_number'],
                    'chunk_index': row['chunk_index']
                }
            }
            all_vectors.append(vector)

        offset += batch_size

    await conn.close()

    # Save to JSON file
    output_file = 'embeddings_export.json'
    with open(output_file, 'w') as f:
        json.dump(all_vectors, f)

    print(f"\n✅ Exported {len(all_vectors):,} embeddings to {output_file}")
    print(f"   File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

    return output_file

if __name__ == "__main__":
    asyncio.run(export_embeddings())
```

**Run:**
```bash
cd migration_scripts
python3 02_export_embeddings.py
```

**Output:** `embeddings_export.json` (~500-800 MB)

---

### Step 3: Upload to Pinecone

**Script:** `migration_scripts/03_upload_to_pinecone.py`

```python
#!/usr/bin/env python3
"""
Upload embeddings to Pinecone serverless index
"""

from pinecone import Pinecone
import json
from tqdm import tqdm

# Initialize Pinecone
pc = Pinecone(api_key="YOUR_PINECONE_API_KEY")
index = pc.Index("mcpress-chatbot-embeddings")

# Load exported embeddings
print("📂 Loading embeddings...")
with open('embeddings_export.json', 'r') as f:
    vectors = json.load(f)

print(f"✅ Loaded {len(vectors):,} vectors")

# Upload in batches (Pinecone recommends 100-1000 per batch)
batch_size = 100
total_batches = (len(vectors) + batch_size - 1) // batch_size

print(f"\n📤 Uploading to Pinecone in {total_batches} batches...")

for i in tqdm(range(0, len(vectors), batch_size)):
    batch = vectors[i:i + batch_size]
    index.upsert(vectors=batch)

print(f"\n✅ Upload complete!")

# Verify upload
stats = index.describe_index_stats()
print(f"\n📊 Pinecone Index Stats:")
print(f"   Total vectors: {stats.total_vector_count:,}")
print(f"   Dimension: {stats.dimension}")
print(f"   Index fullness: {stats.index_fullness}")
```

**Run:**
```bash
cd migration_scripts
python3 03_upload_to_pinecone.py
```

**Duration:** 60-90 minutes for 235k vectors

---

### Step 4: Update Backend Code

Create new vector store for Pinecone:

**File:** `backend/vector_store_pinecone.py`

```python
"""
Pinecone vector store implementation
"""

from pinecone import Pinecone
import os
from typing import List, Dict, Tuple
import asyncpg

class PineconeVectorStore:
    def __init__(self, pinecone_api_key: str, index_name: str, database_url: str):
        """Initialize Pinecone vector store"""
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        self.database_url = database_url
        self.pool = None

    async def initialize(self):
        """Initialize PostgreSQL connection pool for metadata"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )

    async def search(self, query_embedding: List[float], limit: int = 30) -> List[Dict]:
        """
        Search for similar documents

        Args:
            query_embedding: Query vector (384-dim)
            limit: Number of results to return

        Returns:
            List of documents with content and metadata
        """
        # 1. Search Pinecone for similar vectors
        results = self.index.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True
        )

        # 2. Extract document IDs
        doc_ids = [int(match['id']) for match in results['matches']]

        if not doc_ids:
            return []

        # 3. Fetch full content from PostgreSQL
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id,
                    filename,
                    content,
                    page_number,
                    chunk_index,
                    metadata
                FROM documents
                WHERE id = ANY($1)
            """, doc_ids)

        # 4. Merge Pinecone scores with PostgreSQL content
        id_to_row = {row['id']: row for row in rows}

        documents = []
        for match in results['matches']:
            doc_id = int(match['id'])
            if doc_id in id_to_row:
                row = id_to_row[doc_id]

                # Convert distance to similarity (Pinecone returns similarity directly)
                similarity = match['score']
                distance = 1 - similarity  # Convert to distance for consistency

                documents.append({
                    'id': doc_id,
                    'filename': row['filename'],
                    'content': row['content'],
                    'page_number': row['page_number'],
                    'chunk_index': row['chunk_index'],
                    'metadata': row['metadata'],
                    'similarity': similarity,
                    'distance': distance
                })

        return documents

    async def add_document(self, doc_id: int, content: str, embedding: List[float],
                          filename: str, page_number: int, chunk_index: int,
                          metadata: Dict):
        """
        Add document to both Pinecone and PostgreSQL

        Args:
            doc_id: Document ID
            content: Text content
            embedding: 384-dim vector
            filename: Source filename
            page_number: Page number
            chunk_index: Chunk index
            metadata: Additional metadata
        """
        # 1. Add to Pinecone
        self.index.upsert(vectors=[{
            'id': str(doc_id),
            'values': embedding,
            'metadata': {
                'filename': filename,
                'page_number': page_number,
                'chunk_index': chunk_index
            }
        }])

        # 2. Add to PostgreSQL (without embedding)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO documents
                (id, filename, content, page_number, chunk_index, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    content = EXCLUDED.content,
                    page_number = EXCLUDED.page_number,
                    chunk_index = EXCLUDED.chunk_index,
                    metadata = EXCLUDED.metadata
            """, doc_id, filename, content, page_number, chunk_index, metadata)

    async def delete_by_filename(self, filename: str) -> int:
        """Delete all chunks for a filename"""
        # 1. Get IDs from PostgreSQL
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id FROM documents WHERE filename = $1
            """, filename)

            doc_ids = [str(row['id']) for row in rows]

            # 2. Delete from Pinecone
            if doc_ids:
                self.index.delete(ids=doc_ids)

            # 3. Delete from PostgreSQL
            deleted = await conn.execute("""
                DELETE FROM documents WHERE filename = $1
            """, filename)

        return len(doc_ids)

    async def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        # Pinecone stats
        pinecone_stats = self.index.describe_index_stats()

        # PostgreSQL stats
        async with self.pool.acquire() as conn:
            pg_count = await conn.fetchval("SELECT COUNT(*) FROM documents")

        return {
            'pinecone_vectors': pinecone_stats.total_vector_count,
            'postgres_documents': pg_count,
            'dimension': pinecone_stats.dimension,
            'index_fullness': pinecone_stats.index_fullness
        }

    async def close(self):
        """Close connections"""
        if self.pool:
            await self.pool.close()
```

---

### Step 5: Update main.py

**File:** `backend/main.py`

```python
# Add at top
from backend.vector_store_pinecone import PineconeVectorStore

# Replace vector store initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global vector_store

    # Check which vector store to use
    use_pinecone = os.getenv('USE_PINECONE', 'false').lower() == 'true'

    if use_pinecone:
        print("🔧 Using Pinecone Vector Store")
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        pinecone_index = os.getenv('PINECONE_INDEX_NAME', 'mcpress-chatbot-embeddings')
        database_url = os.getenv('DATABASE_URL')

        vector_store = PineconeVectorStore(
            pinecone_api_key=pinecone_api_key,
            index_name=pinecone_index,
            database_url=database_url
        )
        await vector_store.initialize()

        stats = await vector_store.get_stats()
        print(f"✅ Pinecone vectors: {stats['pinecone_vectors']:,}")
        print(f"✅ PostgreSQL documents: {stats['postgres_documents']:,}")
    else:
        print("🔧 Using PostgreSQL Vector Store (pgvector)")
        # ... existing PostgreSQL code ...

    yield

    # Shutdown
    if vector_store:
        await vector_store.close()
```

---

### Step 6: Update Environment Variables

**Railway Dashboard → Backend Service → Variables:**

Add:
```bash
USE_PINECONE=true
PINECONE_API_KEY=your-api-key-here
PINECONE_INDEX_NAME=mcpress-chatbot-embeddings
```

Keep existing:
```bash
DATABASE_URL=postgresql://...  # Still needed for metadata
OPENAI_API_KEY=sk-...
```

---

### Step 7: Remove Embeddings from PostgreSQL

**Script:** `migration_scripts/04_cleanup_postgres.py`

```python
#!/usr/bin/env python3
"""
Remove embedding column from PostgreSQL to save space
Run AFTER verifying Pinecone migration works!
"""

import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup_postgres():
    """Remove embeddings from PostgreSQL"""

    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url, command_timeout=600)

    print("⚠️  WARNING: This will permanently delete the embedding column!")
    print("   Make sure Pinecone migration is working before proceeding.")
    response = input("\nType 'DELETE EMBEDDINGS' to proceed: ")

    if response != 'DELETE EMBEDDINGS':
        print("❌ Cancelled")
        return

    print("\n🗑️  Dropping embedding column...")

    # Get size before
    size_before = await conn.fetchval("""
        SELECT pg_size_pretty(pg_total_relation_size('documents'))
    """)
    print(f"   Size before: {size_before}")

    # Drop column
    await conn.execute("ALTER TABLE documents DROP COLUMN embedding")

    # Drop index
    await conn.execute("DROP INDEX IF EXISTS documents_embedding_idx")

    # Vacuum to reclaim space
    print("🧹 Vacuuming table to reclaim space...")
    await conn.execute("VACUUM FULL documents")

    # Get size after
    size_after = await conn.fetchval("""
        SELECT pg_size_pretty(pg_total_relation_size('documents'))
    """)
    print(f"   Size after: {size_after}")

    await conn.close()

    print("\n✅ Cleanup complete!")
    print("   Embedding column removed")
    print("   Space reclaimed")

if __name__ == "__main__":
    asyncio.run(cleanup_postgres())
```

**Run ONLY after verifying Pinecone works:**
```bash
cd migration_scripts
python3 04_cleanup_postgres.py
```

**Expected result:** Database shrinks from 2.7GB → ~300MB

---

## 🧪 Testing & Validation

### Test Checklist:

**1. Search Quality Test**

```bash
# Test search returns same quality results
python3 test_pinecone_search.py
```

Create `test_pinecone_search.py`:
```python
import requests

API_URL = "https://mcpress-chatbot-production.up.railway.app"

test_queries = [
    "What is RPG programming?",
    "How do I configure DB2?",
    "Explain ILE concepts",
    "What are subprocedures?",
]

for query in test_queries:
    print(f"\n🔍 Query: {query}")
    response = requests.post(f"{API_URL}/chat", json={"message": query})

    if response.status_code == 200:
        # Count sources returned
        data = response.json()
        print(f"   ✅ Success - Sources: {len(data.get('sources', []))}")
    else:
        print(f"   ❌ Failed - Status: {response.status_code}")
```

**2. Performance Test**

```bash
# Measure search latency
python3 test_pinecone_performance.py
```

**Expected:**
- Pinecone search: 50-150ms
- Total request time: 200-500ms (including GPT)

**3. Load Test**

```bash
# Send 100 concurrent requests
ab -n 100 -c 10 -p query.json -T application/json \
  https://mcpress-chatbot-production.up.railway.app/chat
```

**4. Cost Validation**

After 24 hours, check:
- Pinecone dashboard → Usage tab
- Confirm storage cost: ~$0.26/mo for 2.7GB
- Confirm query cost: ~$0.01/mo for typical usage

---

## 🔄 Rollback Plan

**If migration fails, rollback:**

### Option A: Quick Rollback (Pinecone stays, re-enable pgvector)

```bash
# 1. Railway → Variables → Set USE_PINECONE=false
# 2. Redeploy backend
# 3. Embeddings still in PostgreSQL (if you didn't run cleanup yet)
```

### Option B: Full Rollback (Remove Pinecone)

```bash
# 1. Restore PostgreSQL embeddings from backup
pg_restore -d $DATABASE_URL embeddings_backup.sql

# 2. Railway → Variables → Remove Pinecone vars
# 3. Redeploy backend

# 4. Delete Pinecone index (optional)
# Pinecone dashboard → Delete index
```

---

## 🧹 Post-Migration Cleanup

**After 1 week of successful Pinecone operation:**

1. ✅ **Delete PostgreSQL embedding column** (run script from Step 7)
2. ✅ **Delete local backup files**
   ```bash
   rm embeddings_export.json
   rm embeddings_backup_*.sql
   ```
3. ✅ **Remove old vector store code** (optional)
   ```bash
   # Keep vector_store_postgres.py for reference
   # But remove from imports in main.py
   ```
4. ✅ **Update documentation**
   - Update TECHNOLOGY_STACK.md with new architecture
   - Document Pinecone credentials in password manager

---

## 📊 Success Metrics

**Migration is successful when:**

- [ ] All 235k+ embeddings uploaded to Pinecone
- [ ] Search quality remains same (5-12 sources per query)
- [ ] Response time <500ms (same as before)
- [ ] Railway database size <500 MB
- [ ] Pinecone cost <$1/mo
- [ ] Total infrastructure cost <$10/mo
- [ ] New PDF uploads work correctly
- [ ] No errors in logs for 1 week

---

## 📞 Support & Resources

**Pinecone Documentation:**
- Serverless: https://docs.pinecone.io/docs/serverless
- Python SDK: https://docs.pinecone.io/docs/python-client

**Troubleshooting:**
- Pinecone status: https://status.pinecone.io/
- Railway status: https://status.railway.app/

**Contact:**
- Kevin Vandever: kevin@kevinvandever.com

---

## 📝 Migration Checklist

Print this and check off as you go:

### Pre-Migration
- [ ] Railway bill >$25/mo OR database >5GB (migration trigger)
- [ ] Created Pinecone account
- [ ] Got Pinecone API key
- [ ] Backed up PostgreSQL database
- [ ] Read this guide completely
- [ ] Estimated 4-6 hours available

### Migration Day
- [ ] Created Pinecone index (Step 1)
- [ ] Exported embeddings from PostgreSQL (Step 2)
- [ ] Uploaded to Pinecone (Step 3)
- [ ] Updated backend code (Step 4)
- [ ] Updated main.py (Step 5)
- [ ] Set Railway environment variables (Step 6)
- [ ] Deployed to Railway
- [ ] Verified deployment successful

### Testing (Same Day)
- [ ] Search quality test passed
- [ ] Performance test passed
- [ ] Load test passed
- [ ] Frontend chatbot works
- [ ] No errors in Railway logs

### Post-Migration (Week 1)
- [ ] Monitor Pinecone costs daily
- [ ] Monitor search quality
- [ ] Check error rates
- [ ] User testing feedback

### Cleanup (After 1 Week)
- [ ] Run PostgreSQL cleanup script (Step 7)
- [ ] Verify database size reduced to <500MB
- [ ] Delete backup files
- [ ] Update TECHNOLOGY_STACK.md
- [ ] Archive this checklist

---

**Document Version:** 1.0
**Last Updated:** October 8, 2025
**Next Review:** When migration triggers are met (DB >5GB or cost >$25/mo)
