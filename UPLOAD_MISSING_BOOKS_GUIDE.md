# Upload Missing Books - Guide

**Current Status**: 108 books in database
**Target**: 115 books
**Missing**: 7 books

---

## 📋 Overview

You have two options for uploading the missing 7 books:

1. **Automated Script** (Recommended) - Uses the upload script I created
2. **Manual API Upload** - Upload via API endpoint directly

---

## ✅ Option 1: Automated Script (Recommended)

### Step 1: Check Current Books

First, see which books are already in the database:

```bash
python3 check_current_books.py
```

This will show you:
- All 108 books currently in database
- How many chunks each book has
- List of filenames

### Step 2: Prepare Your PDFs

Make sure you have:
- All 115 MC Press PDF files in one directory
- PDFs are named correctly (matching expected filenames)

### Step 3: Run Upload Script

```bash
python3 upload_missing_books.py
```

The script will:
1. Ask for the PDF directory path
2. Check which books are already uploaded
3. Show you the 7 missing books
4. Ask for confirmation
5. Upload only the missing ones
6. Generate embeddings automatically

**Example Run:**
```
$ python3 upload_missing_books.py

====================================
📚 MC Press Books - Upload Missing PDFs
====================================

🔍 Checking existing books in database...
   Found 108 books already in database

Enter path to directory containing PDFs: /Users/kevinvandever/Downloads/mcpress-books

📁 Found 115 PDF files in /Users/kevinvandever/Downloads/mcpress-books

📊 Summary:
   Total PDFs found: 115
   Already in database: 108
   Missing (to upload): 7

📋 Missing PDFs:
   1. Book_A.pdf
   2. Book_B.pdf
   3. Book_C.pdf
   4. Book_D.pdf
   5. Book_E.pdf
   6. Book_F.pdf
   7. Book_G.pdf

Upload 7 missing PDFs? (y/n): y

====================================
🚀 Starting uploads...
====================================

[1/7] 📤 Uploading: Book_A.pdf
   ✅ Success: Document processed and added to database
   ⏳ Waiting 2 seconds before next upload...

[2/7] 📤 Uploading: Book_B.pdf
...
```

---

## 🔧 Option 2: Manual API Upload

If the script doesn't work, you can upload manually:

### Using cURL

```bash
# Upload a single PDF
curl -X POST "https://mcpress-chatbot-production.up.railway.app/upload" \
  -F "file=@/path/to/book.pdf" \
  -F "author=Author Name" \
  -F "category=RPG Programming"
```

### Using Python requests

```python
import requests

pdf_path = "/path/to/book.pdf"
api_url = "https://mcpress-chatbot-production.up.railway.app"

with open(pdf_path, 'rb') as f:
    files = {'file': ('book.pdf', f, 'application/pdf')}
    data = {
        'author': 'Author Name',
        'category': 'RPG Programming'
    }
    response = requests.post(f"{api_url}/upload", files=files, data=data)
    print(response.json())
```

### Using the Web Interface (if available)

Some upload endpoints may have a web UI - check:
- https://mcpress-chatbot-production.up.railway.app/upload/dashboard

---

## 🔍 Verify Uploads

After uploading, verify the books were added:

### Check via Script

```bash
python3 check_current_books.py
# Should now show 115 books
```

### Check via API

```bash
curl "https://mcpress-chatbot-production.up.railway.app/documents" | jq '.documents | length'
```

### Check in Database

```python
python3 -c "
import asyncio
import asyncpg
import os

async def check():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    count = await conn.fetchval('SELECT COUNT(DISTINCT filename) FROM documents')
    print(f'Total books: {count}')
    await conn.close()

asyncio.run(check())
"
```

---

## ⚡ Generate Embeddings

After uploading, you need to generate embeddings for the new documents.

### Option 1: Automatic (via upload endpoint)

The `/upload` endpoint should automatically generate embeddings. Check logs to confirm.

### Option 2: Manual Regeneration

If embeddings aren't generated automatically, trigger them manually:

```bash
curl -X POST "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-start?batch_size=500"
```

Check status:
```bash
curl "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-status"
```

---

## 📊 Expected Results

After uploading 7 new books:

| Metric | Before | After |
|--------|--------|-------|
| **Unique books** | 108 | 115 ✅ |
| **Total chunks** | 227,032 | ~245,000 |
| **With embeddings** | 188,672 | ~205,000 |

**Processing time per book:**
- Chunking: 30-60 seconds
- Embedding generation: 2-5 minutes
- Total per book: 3-6 minutes

**For 7 books:**
- Estimated time: 21-42 minutes total

---

## 🐛 Troubleshooting

### Upload Fails with "File too large"

```bash
# Check file size
ls -lh /path/to/book.pdf

# If over 50MB, may need to increase limit
# Or split into smaller uploads
```

### Upload Succeeds but No Embeddings

```bash
# Check background job status
curl "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-status"

# If stuck, restart embedding job
curl -X POST "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-start?batch_size=500"
```

### "Connection timeout" Error

```bash
# Increase timeout in upload script
# Or upload via Railway directly (no network issues)

railway run python3 upload_missing_books.py
```

### Books Upload but Not Searchable

```bash
# Check if embeddings exist
python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    total = await conn.fetchval('SELECT COUNT(*) FROM documents')
    with_emb = await conn.fetchval('SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL')
    print(f'Total: {total:,}, With embeddings: {with_emb:,} ({with_emb/total*100:.1f}%)')
    await conn.close()
asyncio.run(check())
"

# If low percentage, regenerate embeddings
```

---

## 📝 Upload Checklist

Before uploading:
- [ ] Test search is working with current 108 books
- [ ] Have all 115 PDF files in one directory
- [ ] PDFs are valid (not corrupted)
- [ ] Enough disk space on Railway

During upload:
- [ ] Run `check_current_books.py` to see current state
- [ ] Run `upload_missing_books.py` to upload missing 7
- [ ] Monitor upload progress (script shows status)
- [ ] Verify each upload succeeds

After upload:
- [ ] Run `check_current_books.py` again (should show 115)
- [ ] Wait for embedding generation (3-6 min per book)
- [ ] Test queries with new book content
- [ ] Check `/documents` endpoint shows all 115 books
- [ ] Verify search results include new books

---

## 🔐 Security Notes

- Scripts use `DATABASE_URL` from environment (never hardcoded)
- PDFs are uploaded via HTTPS (encrypted)
- No credentials are stored in scripts
- Railway environment variables remain secure

---

## 🚀 Quick Commands

```bash
# 1. Check current books
python3 check_current_books.py

# 2. Upload missing books
python3 upload_missing_books.py

# 3. Verify upload
python3 check_current_books.py

# 4. Test search with new books
python3 test_pgvector_chatbot.py

# 5. Check embedding status
curl "https://mcpress-chatbot-production.up.railway.app/admin/regenerate-embeddings-status"
```

---

## 📞 Questions to Answer

Before running the upload:

1. **Where are your PDF files stored?**
   - Local directory path?
   - External drive?
   - Cloud storage (need to download first)?

2. **Do you know which 7 books are missing?**
   - Run `check_current_books.py` to see
   - Compare with your complete list of 115 books

3. **Do you have database access?**
   - DATABASE_URL set in `.env` file?
   - Can connect to Railway database?

4. **Is the backend deployed and working?**
   - Test: `curl https://mcpress-chatbot-production.up.railway.app/health`
   - Should return `200 OK`

---

## ✅ Success Criteria

Upload is successful when:
- ✅ All 7 new books appear in `check_current_books.py`
- ✅ Total book count is 115
- ✅ New books have embeddings generated
- ✅ Search queries can find content from new books
- ✅ `/documents` endpoint lists all 115 books
- ✅ No errors in Railway logs

---

**Ready to upload?** Run `python3 check_current_books.py` to start!
