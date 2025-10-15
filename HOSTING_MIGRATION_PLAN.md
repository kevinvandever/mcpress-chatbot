# MC Press Chatbot - Hosting Migration Plan

**Created:** October 7, 2025
**Owner:** Kevin Vandever
**Current Cost:** $80+/month
**Target Cost:** $25-35/month (60% savings)
**Launch Date:** October 31, 2025

---

## 📊 Current State

### Infrastructure
```
Frontend: Netlify (React/Vite)
Backend: Railway (FastAPI/Python)
Database: Railway PostgreSQL + pgvector (2.7GB, 235k docs)
Total Cost: $80+/month
```

### Cost Breakdown (Estimated)
- **Railway Backend + Database:** ~$70-75/month
  - PostgreSQL with pgvector (2.7GB storage)
  - FastAPI service (RAM/CPU hours)
- **Netlify:** ~$5-10/month (or should be FREE - needs verification)
- **Total:** $80+/month

### Issues
- ❌ **Too expensive** for zero traffic
- ❌ **Railway database** is main cost driver (~$50-60/month)
- ⚠️ **Netlify billing unclear** - should be free tier
- ⚠️ **No traffic yet** - over-provisioned

---

## 🎯 Recommended Strategy: Hybrid Optimization

### Phase 1: Database Migration (Immediate)
**Move database from Railway → Supabase Pro**

**Why Supabase?**
- ✅ pgvector support built-in
- ✅ $25/month for 8GB (vs ~$50-60 on Railway)
- ✅ Excellent dashboard and tools
- ✅ Auto-backups included
- ✅ Can grow to 8GB (you need 2.7GB now, more docs coming)

**Cost Savings:** ~$30-40/month

### Phase 2: Backend Optimization (Post-Launch)
**Evaluate after October 31 launch**

Options:
1. **Keep Railway backend** ($20-30/month) - if working well
2. **Migrate to Render/Fly.io FREE** - if traffic stays low
3. **Move to VPS** ($5-12/month) - if you want full control

### Phase 3: Frontend Audit (This Week)
**Check Netlify billing**

Expected outcome:
- Should be **FREE** (100GB bandwidth, 300 build min)
- If paying, investigate why and downgrade

---

## 🔍 Action Items for Kevin

### Immediate (This Week - Oct 7-13)

#### 1. Audit Netlify Billing
**Steps:**
1. Log into Netlify dashboard: https://app.netlify.com
2. Go to: User Settings → Billing
3. Check current plan and usage
4. Review all deployed sites

**Questions to answer:**
- [ ] What plan am I on? (Free / Pro / Business)
- [ ] How many sites deployed?
- [ ] Monthly bandwidth usage?
- [ ] Monthly build minutes?
- [ ] Any overages?

**Expected outcome:** Should be FREE or <$10/month

**Action:** If paying unnecessarily, downgrade to Free tier

---

#### 2. Check ScalaHosting Capabilities
**Contact MC Press website owner and ask:**

1. **What type of hosting plan?**
   - [ ] Shared hosting (cPanel)
   - [ ] VPS (Virtual Private Server)
   - [ ] Cloud hosting
   - [ ] Dedicated server

2. **Technical capabilities:**
   - [ ] SSH access available?
   - [ ] Can run Docker containers?
   - [ ] Current resource usage (CPU, RAM, disk)?
   - [ ] How much free capacity?

3. **Permission questions:**
   - [ ] Would they allow chatbot on their hosting?
   - [ ] Willing to share resources?
   - [ ] Who manages deployments?

**If ScalaHosting is shared hosting:**
- ❌ Cannot run Python/FastAPI
- ❌ Cannot run PostgreSQL with pgvector
- ❌ Migration not viable

**If ScalaHosting is VPS/Cloud with resources:**
- ✅ Could host entire stack
- ✅ Zero additional cost
- ⚠️ Requires owner approval
- ⚠️ You manage everything (security, updates)

---

### Decision Matrix (After Gathering Info)

Once you have Netlify and ScalaHosting details, choose path:

#### Path A: ScalaHosting Can Host Everything
**If:** VPS/Cloud with SSH, Docker, available resources, owner approves

**Action:**
- Migrate entire stack to ScalaHosting
- Use Docker Compose
- Set up Coolify for git auto-deploy
- **New cost:** $0 additional
- **Timeline:** 2-3 weeks

#### Path B: ScalaHosting Cannot Host (Most Likely)
**If:** Shared hosting OR insufficient resources OR owner declines

**Action:**
- Proceed with Supabase database migration
- Keep Railway backend (optimize later)
- Fix Netlify billing
- **New cost:** $25-35/month
- **Timeline:** 1-2 weeks

---

## 📋 Migration Plan (Path B - Recommended)

### Week 1: Oct 7-13 (Preparation)

#### Action Items:
- [ ] **Complete audits** (Netlify + ScalaHosting)
- [ ] **Create Supabase account** → https://supabase.com
  - Sign up for Pro plan ($25/month)
  - Create new project
  - Choose region (US East to match Railway)
- [ ] **Enable pgvector extension**
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- [ ] **Test migration with sample data** (1,000 docs)
- [ ] **Validate search queries work**

**Deliverable:** Working Supabase instance with test data

---

### Week 2: Oct 14-20 (Database Migration)

#### Action Items:

**1. Export Railway Database**
```bash
# Connect to Railway PostgreSQL
railway login
railway link [your-project]

# Export database (run from local machine)
pg_dump $DATABASE_URL > mcpress_backup_$(date +%Y%m%d).sql

# Verify export
ls -lh mcpress_backup_*.sql  # Should be ~500MB-1GB
```

**2. Prepare Supabase**
```sql
-- Connect to Supabase via dashboard SQL editor
-- Run schema creation
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX documents_filename_idx ON documents (filename);
CREATE INDEX documents_metadata_idx ON documents USING gin (metadata);
```

**3. Import Data to Supabase**
```bash
# Get Supabase connection string from dashboard
# Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Import (may take 30-60 minutes for 235k docs)
psql $SUPABASE_DATABASE_URL < mcpress_backup_20251014.sql

# Verify import
psql $SUPABASE_DATABASE_URL -c "SELECT COUNT(*) FROM documents;"
# Expected: 235,409
```

**4. Update Railway Backend**
```bash
# In Railway dashboard
# Update environment variable:
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Redeploy backend (Railway will restart automatically)
```

**5. Test Thoroughly**
```bash
# Test from local machine
cd /Users/kevinvandever/kev-dev/mcpress-chatbot
python3 test_pgvector_chatbot.py

# Test queries:
# - "What is RPG programming?"
# - "How do I configure DB2?"
# - "Subfile examples"

# Verify:
# - Sources returned: 5-12
# - Response quality: Good
# - Search speed: <500ms
```

**6. Monitor for 48 Hours**
- [ ] Check Railway logs for errors
- [ ] Test chatbot from frontend
- [ ] Verify no connection issues
- [ ] Confirm search performance

**Deliverable:** Chatbot running on Supabase database

---

### Week 3: Oct 21-27 (Polish & Prep)

#### Action Items:
- [ ] **Add remaining documents** to Supabase
- [ ] **Performance tuning**
  - Adjust search thresholds if needed
  - Optimize queries
- [ ] **Frontend polish**
  - UI/UX improvements
  - Error handling
  - Loading states
- [ ] **Pre-launch testing**
  - Cross-browser testing
  - Mobile testing
  - Load testing (simulate 10-20 concurrent users)
- [ ] **Documentation updates**
  - Update TECHNOLOGY_STACK.md
  - Update connection strings
  - Document new architecture

**Deliverable:** Production-ready chatbot

---

### Week 4: Oct 28-31 (Launch)

#### Action Items:
- [ ] **Final testing** (Oct 28-29)
- [ ] **Soft launch** (Oct 30)
  - Share with small group
  - Monitor closely
- [ ] **Official launch** (Oct 31)
- [ ] **Monitor first 24 hours**

#### Post-Launch (Nov 1+):
- [ ] **Cancel Railway database** (keep backend running)
  - Verify Supabase is stable for 1 week first
  - Download final backup before canceling
- [ ] **Verify new billing**
  - Railway: ~$20-30/month (backend only)
  - Supabase: $25/month
  - Netlify: $0/month (hopefully)
  - **New total: $25-35/month**

**Deliverable:** Live chatbot, $50/month savings

---

## 🔧 Migration Scripts (To Be Created)

### 1. Database Export Script
**File:** `scripts/export_railway_db.sh`
```bash
#!/bin/bash
# Export Railway PostgreSQL database
# Usage: ./export_railway_db.sh

set -e

echo "🔄 Exporting Railway database..."

# Get database URL from Railway
railway link
DATABASE_URL=$(railway variables get DATABASE_URL)

# Export with timestamp
BACKUP_FILE="backups/mcpress_railway_$(date +%Y%m%d_%H%M%S).sql"
pg_dump $DATABASE_URL > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

echo "✅ Export complete: ${BACKUP_FILE}.gz"
ls -lh ${BACKUP_FILE}.gz
```

---

### 2. Supabase Import Script
**File:** `scripts/import_to_supabase.sh`
```bash
#!/bin/bash
# Import database to Supabase
# Usage: ./import_to_supabase.sh [backup-file]

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.sql>"
    exit 1
fi

BACKUP_FILE=$1
SUPABASE_URL=$SUPABASE_DATABASE_URL

echo "🔄 Importing to Supabase..."
echo "📁 File: $BACKUP_FILE"

# Decompress if needed
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "📦 Decompressing..."
    gunzip -k $BACKUP_FILE
    BACKUP_FILE="${BACKUP_FILE%.gz}"
fi

# Import
psql $SUPABASE_URL < $BACKUP_FILE

# Verify
echo "🔍 Verifying import..."
DOCUMENT_COUNT=$(psql $SUPABASE_URL -t -c "SELECT COUNT(*) FROM documents;")
echo "✅ Documents imported: $DOCUMENT_COUNT"

# Create indexes
echo "📊 Creating indexes..."
psql $SUPABASE_URL << EOF
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename);
CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING gin (metadata);
EOF

echo "✅ Import complete!"
```

---

### 3. Validation Script
**File:** `scripts/validate_migration.py`
```python
#!/usr/bin/env python3
"""
Validate database migration from Railway to Supabase
Usage: python3 validate_migration.py
"""

import os
import asyncpg
import asyncio
from datetime import datetime

async def validate():
    # Connection strings
    railway_url = os.getenv('RAILWAY_DATABASE_URL')
    supabase_url = os.getenv('SUPABASE_DATABASE_URL')

    print("🔍 Validating migration...")
    print(f"⏰ {datetime.now()}\n")

    # Connect to both databases
    railway_conn = await asyncpg.connect(railway_url)
    supabase_conn = await asyncpg.connect(supabase_url)

    # Compare document counts
    railway_count = await railway_conn.fetchval("SELECT COUNT(*) FROM documents")
    supabase_count = await supabase_conn.fetchval("SELECT COUNT(*) FROM documents")

    print(f"📊 Document Counts:")
    print(f"   Railway:  {railway_count:,}")
    print(f"   Supabase: {supabase_count:,}")

    if railway_count == supabase_count:
        print("   ✅ Counts match!\n")
    else:
        print(f"   ❌ Missing {railway_count - supabase_count:,} documents\n")
        return False

    # Compare embedding counts
    railway_emb = await railway_conn.fetchval(
        "SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL"
    )
    supabase_emb = await supabase_conn.fetchval(
        "SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL"
    )

    print(f"🎯 Embeddings:")
    print(f"   Railway:  {railway_emb:,}")
    print(f"   Supabase: {supabase_emb:,}")

    if railway_emb == supabase_emb:
        print("   ✅ Embeddings match!\n")
    else:
        print(f"   ❌ Missing {railway_emb - supabase_emb:,} embeddings\n")
        return False

    # Test vector search
    print("🔎 Testing vector search...")
    test_embedding = [0.1] * 384  # Dummy embedding

    results = await supabase_conn.fetch(
        """
        SELECT filename, 1 - (embedding <=> $1::vector) as similarity
        FROM documents
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT 5
        """,
        test_embedding
    )

    if results:
        print(f"   ✅ Vector search working! Found {len(results)} results")
        for r in results[:3]:
            print(f"      - {r['filename']}: {r['similarity']:.3f}")
    else:
        print("   ❌ Vector search failed!")
        return False

    # Check indexes
    print("\n📑 Checking indexes...")
    indexes = await supabase_conn.fetch(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'documents'
        """
    )

    for idx in indexes:
        print(f"   ✅ {idx['indexname']}")

    # Close connections
    await railway_conn.close()
    await supabase_conn.close()

    print("\n🎉 Migration validation complete!")
    return True

if __name__ == '__main__':
    asyncio.run(validate())
```

---

### 4. Rollback Plan
**File:** `ROLLBACK.md`

**If migration fails:**

```bash
# Step 1: Revert Railway backend DATABASE_URL
# In Railway dashboard, change back to Railway database URL
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway

# Step 2: Restart Railway backend
railway restart

# Step 3: Verify chatbot works
curl https://mcpress-chatbot-production.up.railway.app/health

# Step 4: Investigate issue
# Check Railway logs
railway logs

# Step 5: Keep Railway database active
# Do NOT cancel Railway database service

# Step 6: Debug Supabase migration
# Re-run validation script
python3 scripts/validate_migration.py
```

---

## 💰 Cost Comparison

### Current State
```
Railway (Backend + DB): ~$75/month
Netlify:                ~$5/month (TBD)
─────────────────────────────────
Total:                  $80/month
```

### After Migration (Path B)
```
Railway (Backend only): ~$25/month
Supabase (Database):    $25/month
Netlify:                $0/month
─────────────────────────────────
Total:                  $50/month
Savings:                $30/month (37%)
```

### Future Optimization (Post-Launch)
```
Render/Fly.io (Backend): $0/month (free tier)
Supabase (Database):     $25/month
Netlify:                 $0/month
──────────────────────────────────
Total:                   $25/month
Savings:                 $55/month (69%)
```

### Alternative: ScalaHosting (Path A)
```
ScalaHosting (Everything): $0/month (if approved)
Netlify:                   $0/month
─────────────────────────────────────
Total:                     $0/month
Savings:                   $80/month (100%)
```

---

## 🚦 Decision Checkpoint

**After completing Netlify + ScalaHosting audits, answer:**

1. **Netlify actual cost:** $_____/month
2. **ScalaHosting type:** [Shared / VPS / Cloud / Unknown]
3. **ScalaHosting available:** [Yes / No / Maybe]
4. **Owner approval:** [Yes / No / Pending]

**Then choose:**
- [ ] **Path A:** Migrate to ScalaHosting (if VPS/Cloud + approved)
- [ ] **Path B:** Supabase migration (if ScalaHosting unavailable)
- [ ] **Path C:** Custom solution (if neither fits)

---

## 📞 Next Steps

1. **Complete audits this week** (Oct 7-13)
2. **Report findings** to Mason (the architect)
3. **Finalize migration path** (A or B)
4. **Begin execution** (Week 2)

---

## 🔗 Resources

- **Supabase Docs:** https://supabase.com/docs
- **Supabase pgvector Guide:** https://supabase.com/docs/guides/ai/vector-columns
- **Railway Docs:** https://docs.railway.com
- **Netlify Pricing:** https://www.netlify.com/pricing

---

**Document Version:** 1.0
**Last Updated:** October 7, 2025
**Next Review:** After audit completion (Oct 13, 2025)
