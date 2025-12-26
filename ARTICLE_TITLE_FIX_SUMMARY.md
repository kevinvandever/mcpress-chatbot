# Article Title Fix Summary

**Date**: December 22, 2024  
**Issue**: Articles showing ID numbers (5805, 6274, etc.) instead of proper titles  
**Status**: ✅ **CODE FIXED - NEEDS DEPLOYMENT**

---

## Problem Identified

The article metadata import was missing the article title column (Column B) from the Excel file. The import service was only reading:
- Column A: id
- Column H: feature_article  
- Column J: author
- Column K: article_url
- Column L: author_url

But it was **NOT reading Column B: title**, which contains the actual article names.

---

## Solution Implemented

Updated `backend/excel_import_service.py` in three places:

### 1. Column Mapping (Line ~220)
```python
df = df.rename(columns={
    df.columns[0]: 'id',           # Column A
    df.columns[1]: 'title',        # Column B  ← ADDED
    df.columns[7]: 'feature_article',  # Column H
    df.columns[9]: 'author',       # Column J
    df.columns[10]: 'article_url', # Column K
    df.columns[11]: 'author_url'   # Column L
})
required_columns = ['id', 'title', 'feature_article', 'author', 'article_url', 'author_url']
```

### 2. Preview Validation (Line ~336)
```python
row_data = {
    'id': str(row.get('id', '')),
    'title': str(row.get('title', '')),  ← ADDED
    'feature_article': str(row.get('feature_article', '')),
    'author': str(row.get('author', '')),
    'article_url': str(row.get('article_url', '')),
    'author_url': str(row.get('author_url', ''))
}
```

### 3. Article Import Logic (Line ~715)
```python
# Extract title from Excel
article_title = str(row.get('title', '')).strip()  ← ADDED

# Update database with title
await conn.execute("""
    UPDATE books 
    SET title = $1, article_url = $2, document_type = 'article'  ← UPDATED
    WHERE id = $3
""", article_title if article_title else None, article_url if article_url else None, book_id)
```

---

## Next Steps

### Step 1: Deploy to Railway ✅ REQUIRED

The code changes are in the local `backend/excel_import_service.py` file but haven't been deployed to Railway yet.

**Option A: Git Push (Recommended)**
```bash
# Commit the changes
git add backend/excel_import_service.py
git commit -m "Fix: Add article title column to Excel import service"

# Push to trigger Railway deployment
git push origin main
```

**Option B: Manual Railway Deployment**
- Go to Railway dashboard
- Trigger manual redeploy
- Wait ~10-15 minutes for deployment

### Step 2: Re-run Article Import

After Railway deployment completes:

```bash
python3 import_article_metadata.py
```

**Expected Results:**
- Articles processed: ~6,319
- Articles matched: ~6,155 (matching uploaded PDFs)
- Documents updated: ~6,155
- Authors created/updated: varies

### Step 3: Verify Fix

Test the chat interface at https://mcpress-chatbot.netlify.app

**Before Fix:**
- Articles show: "5805", "6274", "7672", "15981"
- No "Read" buttons
- Authors not clickable

**After Fix:**
- Articles show: Proper article titles from Excel
- "Read" buttons appear for articles with URLs
- Author names clickable if they have website URLs

---

## Files Modified

- `backend/excel_import_service.py` - Added title column mapping and database update

---

## Testing Commands

After deployment and re-import:

```bash
# Test specific article IDs
curl -X GET "https://mcpress-chatbot-production.up.railway.app/api/books?search=5805&limit=1" | jq

# Test chat interface
curl -X POST "https://mcpress-chatbot-production.up.railway.app/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about RPG programming", "conversation_id": "test", "user_id": "test"}' \
  --no-buffer
```

---

## Success Criteria

✅ Articles display proper titles instead of ID numbers  
✅ "Read" buttons appear for articles with article_url  
✅ Author names are clickable links when they have site_url  
✅ document_type is set to 'article' for feature articles  
✅ Chat interface shows complete metadata for all sources

---

**Status**: Code is ready, waiting for Railway deployment and re-import.
