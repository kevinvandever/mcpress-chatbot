# Migration to PGVector - Next Steps

## Current Status
- ✅ New pgVector database deployed
- ✅ Migration script running (ETA: ~4 hours)
- ⏳ Waiting for migration to complete

---

## When Migration Completes

### Step 1: Verify Migration Success

Run this to check final count:
```bash
python3 -c "
import asyncpg, asyncio
async def check():
    conn = await asyncpg.connect('postgresql://postgres:OxATCwPVTNVdadKbPNTGvUyrktrTObOh@shortline.proxy.rlwy.net:18459/railway')
    count = await conn.fetchval('SELECT COUNT(*) FROM documents')
    with_embeddings = await conn.fetchval('SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL')
    print(f'Total documents: {count:,}')
    print(f'With embeddings: {with_embeddings:,}')
    await conn.close()
asyncio.run(check())
"
```

**Expected:** ~235,409 documents total

---

### Step 2: Update Railway Environment Variables

1. Go to Railway: https://railway.app
2. Open your **mcpress-chatbot** service (NOT the databases)
3. Click **Variables** tab
4. Find **DATABASE_URL**
5. Update it to:
   ```
   postgresql://postgres:OxATCwPVTNVdadKbPNTGvUyrktrTObOh@pgvector-railway.railway.internal:5432/railway
   ```
   (This is the **internal** URL for the pgVector database)

6. **Also update/add these variables:**
   ```
   USE_POSTGRESQL=true
   ENABLE_POSTGRESQL=true
   ```

7. Click **Save** - this will automatically restart your app

---

### Step 3: Verify App is Using PGVector

After the app restarts (~30 seconds), check the logs:

1. In Railway, go to **mcpress-chatbot** service
2. Click **Deployments** tab
3. Click on the latest deployment
4. Look for this in logs:
   ```
   ✅ pgvector extension enabled - using vector similarity
   ✅ Using PostgreSQL with semantic embeddings (persistent, reliable)
   ```

**If you see this ❌:**
```
⚠️ pgvector not available
```
Then the DATABASE_URL is wrong - double-check Step 2.

---

### Step 4: Test Search Quality

1. Go to your chatbot: https://mcpress-chatbot-production.up.railway.app
2. Try these test queries:
   - "What is RPG programming?"
   - "How do I use SQL in DB2?"
   - "Explain IBM i security"

**What to look for:**
- ✅ Responses should include relevant book excerpts
- ✅ Source citations with page numbers
- ✅ Higher quality, more relevant answers than before

---

### Step 5: Monitor Performance

Check the backend logs for search queries:
```
Found X similar documents for query
```

**With pgvector:** Search should be fast (<1 second) even with 235k documents

---

### Step 6: Clean Up Old Database (After 24-48 Hours)

**ONLY after confirming everything works for a day or two:**

1. In Railway, click on old **Postgres** service
2. Click **Settings** tab
3. Scroll to bottom → **Delete Service**

**This will save you $5-10/month on Railway costs**

---

## Troubleshooting

### Problem: App won't start after updating DATABASE_URL

**Solution:** Make sure you used the **internal** URL:
```
pgvector-railway.railway.internal:5432
```
NOT the public URL with `shortline.proxy.rlwy.net`

### Problem: Still seeing "pgvector not available"

**Solution:**
1. Check DATABASE_URL points to new database
2. Check `USE_POSTGRESQL=true` is set
3. Restart the app manually

### Problem: Search is slow

**Solution:** Verify the ivfflat index was created:
```sql
\d documents
```
Should show an index on the `embedding` column

---

## Summary of Changes

### Before:
- ❌ No pgvector extension
- ❌ JSONB embeddings (slow, limited)
- ❌ Only searching 5000 documents max
- ❌ Python-based similarity calculation

### After:
- ✅ pgvector extension enabled
- ✅ Proper vector(384) embeddings
- ✅ Searching ALL 235k documents
- ✅ Database-level similarity with ivfflat index
- ✅ 10-100x faster search performance

---

## Need Help?

If anything goes wrong during the switch, you can easily roll back:

1. Change DATABASE_URL back to old database
2. Restart app
3. Contact support or check logs

The old database is preserved until you manually delete it!
