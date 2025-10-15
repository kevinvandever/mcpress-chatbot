# Finish PGVector Migration - Guide

**Migration Status (Completed Oct 7, 2025):**
- ✅ COMPLETE: 235,409 documents (100%)
- ✅ Final ID: 380,647
- 🎉 All documents successfully migrated!

---

## 🎯 What This Does

The `finish_migration.py` script will:
1. Resume from ID 372,111 (where you left off)
2. Migrate the remaining 3.6% of documents
3. Preserve your progress with automatic saves
4. Handle errors gracefully (retry on failure)
5. Verify completion at the end

**Important**: This is compatible with our schema fixes - it properly handles:
- pgvector `vector(384)` type
- JSONB metadata
- Distance semantics we just fixed

---

## 🚀 How to Run

### Step 1: First Test Your Current Setup Works

Before adding more data, make sure search is working:

```bash
# Wait for Railway deployment to finish (~5 minutes)
# Then test:
python3 test_pgvector_chatbot.py
```

**Expected results:**
- 5-12 sources per query
- Confidence 0.3-0.8
- Good book excerpts

**If this fails, DON'T migrate more data yet!** Fix search first.

### Step 2: Run the Finish Migration Script

Once search works:

```bash
python3 finish_migration.py
```

**What it will do:**
```
====================================
🚀 Resuming PGVector Migration
====================================

🔍 Checking databases...
📊 OLD database: 235,409 documents (max ID: 380,000)
📊 NEW database: 227,032 documents (188,672 with embeddings)
📊 pgvector enabled: True

📍 Resuming from ID: 372,111
📍 Already migrated: 227,032 documents

📦 Estimated remaining: 8,377 documents
📦 Completion: 96.4%

Continue migration? (y/n): y

====================================
🔄 Starting migration batches...
====================================

📦 Batch 1 (from ID 372,111)...
   Fetched 500 documents (IDs 372,112 to 372,611)
   ✅ Migrated 500 documents
   📊 Total progress: 227,532/235,409 (96.7%)

📦 Batch 2 (from ID 372,611)...
   Fetched 500 documents (IDs 372,612 to 373,111)
   ✅ Migrated 500 documents
   📊 Total progress: 228,032/235,409 (96.9%)

...

✅ No more documents to migrate!

====================================
🎉 MIGRATION COMPLETE!
====================================
⏱️  Time elapsed: 120 seconds (2.0 minutes)
📊 Documents migrated in this session: 8,377
📊 Final count in new database: 235,409
```

---

## ⏱️ Expected Timeline

- **Remaining documents**: ~8,377
- **Rate**: ~70 docs/second
- **Estimated time**: ~2 minutes

Much faster than initial migration because:
- Smaller dataset
- No cold start
- Optimized batch size

---

## 🔍 Monitor Progress

The script shows real-time progress:

```
📦 Batch 5 (from ID 373,500)...
   ✅ Migrated 500 documents
   📊 Total progress: 228,532/235,409 (97.1%)
   💾 Progress saved: ID 373,500, Total 228,532
```

**Progress is automatically saved** after each batch, so you can:
- Stop and resume anytime (Ctrl+C)
- Recover from network issues
- Continue if Railway restarts

---

## 🐛 Troubleshooting

### Problem: "Connection timeout" or "connection is closed"

**Cause**: Long-running inserts cause old database connection to timeout

**What you'll see**:
```
ERROR - ❌ Error migrating document ID 372699: connection was closed
ERROR - ❌ Error migrating document ID 372700: connection is closed
...
✅ Migrated 87 documents (partial batch)
💾 Progress saved: ID 372698
```

**Solution**:
- ✅ Script auto-saves progress and continues with next batch
- ✅ Fresh connection on next batch usually succeeds
- ✅ No action needed - let it continue
- If it fails completely, just run again - it will resume from last saved ID

**Note**: This is normal! Batch 2 of Oct 7 migration had this issue but recovered automatically.

### Problem: "Error migrating document ID XXXXX"

**Cause**: Specific document is corrupted or invalid

**Solution**:
- Script automatically skips and continues
- Individual errors won't stop the whole migration
- Check logs to see which documents failed

### Problem: "Migration stuck at XX%"

**Check**:
```bash
# View current progress
cat migration_progress.json

# Check if old database is still accessible
railway run python3 -c "
import asyncpg, asyncio, os
async def check():
    conn = await asyncpg.connect('OLD_DB_URL')
    count = await conn.fetchval('SELECT COUNT(*) FROM documents WHERE id > 372111')
    print(f'Remaining in old DB: {count}')
    await conn.close()
asyncio.run(check())
"
```

### Problem: "Too many consecutive errors"

**Cause**: Database connection issues or schema mismatch

**Solution**:
1. Check Railway database is online
2. Verify DATABASE_URL in script is correct
3. Check old database (ballast) is still accessible
4. Run again - it will resume from last good point

---

## 📊 After Migration Completes

### 1. Verify Document Count

```bash
# Should show ~235,409 documents
python3 check_current_books.py
```

### 2. Check Embeddings

```bash
# Check how many have embeddings
python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    total = await conn.fetchval('SELECT COUNT(*) FROM documents')
    with_emb = await conn.fetchval('SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL')
    print(f'Total: {total:,}')
    print(f'With embeddings: {with_emb:,} ({with_emb/total*100:.1f}%)')
    await conn.close()
asyncio.run(check())
"
```

**If less than 90% have embeddings**, generate them:

```bash
curl -X POST "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-start?batch_size=500"
```

### 3. Test Search Quality

```bash
python3 test_pgvector_chatbot.py
```

**Expected**:
- Even more sources available (searching 235k docs instead of 227k)
- Better answers with more content
- Same threshold (0.55) works well

### 4. Verify All Books Present

```bash
# Check unique book count
python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    count = await conn.fetchval('SELECT COUNT(DISTINCT filename) FROM documents')
    print(f'Unique books: {count}')
    await conn.close()
asyncio.run(check())
"
```

Should be **115 books** (or close to it).

---

## 🎯 Success Criteria

Migration is complete when:
- ✅ New database has ~235,409 documents (or 99%+ of old database)
- ✅ At least 90% have embeddings
- ✅ Search quality is good (test_pgvector_chatbot.py passes)
- ✅ All 115 books are present
- ✅ No critical errors in logs

---

## 🗑️ Cleanup (After Verification)

**ONLY after 24-48 hours of successful operation:**

1. Verify everything works perfectly
2. Back up old database (just in case)
3. Delete old database service in Railway

**This saves $5-10/month** on Railway costs.

**To delete:**
1. Railway dashboard → Select "ballast" PostgreSQL service
2. Settings tab → Scroll to bottom
3. "Delete Service" button
4. Confirm deletion

---

## 📝 Pre-Flight Checklist

Before running migration:

- [ ] Current search is working (test_pgvector_chatbot.py passes)
- [ ] DATABASE_URL is correct in .env
- [ ] Railway is not experiencing issues
- [ ] Have 10-15 minutes available (don't interrupt)
- [ ] Understand you can stop/resume anytime

---

## 🔐 Safety Features

The script includes:
- ✅ **Progress saving** - Can resume from any point
- ✅ **Auto-retry** - Recovers from network issues (5 attempts)
- ✅ **Error skipping** - Bad documents don't block migration
- ✅ **Batch processing** - 500 docs at a time (manageable)
- ✅ **Graceful shutdown** - Ctrl+C saves progress

---

## 🚀 Quick Commands

```bash
# 1. Test current setup works
python3 test_pgvector_chatbot.py

# 2. Finish migration
python3 finish_migration.py

# 3. Check completion
cat migration_progress.json

# 4. Verify count
python3 check_current_books.py

# 5. Generate missing embeddings if needed
curl -X POST "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-start?batch_size=500"
```

---

## ❓ Common Questions

**Q: Will this affect my production chatbot?**
A: No, it only adds more documents. Current documents keep working.

**Q: What if I stop it mid-migration?**
A: No problem! Progress is saved. Just run the script again.

**Q: Will search get slower with more documents?**
A: No! pgvector is optimized for large datasets. 235k docs is fine.

**Q: Do I need to update thresholds?**
A: No, the 0.55 threshold we just set works great for any doc count.

**Q: What about the old database after migration?**
A: Keep it for 24-48 hours, then delete to save costs.

---

**Ready to finish the migration?**

Run: `python3 test_pgvector_chatbot.py` first to verify search works, then `python3 finish_migration.py` to complete the migration!
