# Manual Testing Guide for Task 6

## Prerequisites
- Railway deployment is live
- Migration 003 has been run (authors and document_authors tables exist)
- At least one document exists in the database

## Test Sequence

### 1. Check Health
```bash
curl https://your-railway-url.railway.app/test-document-author/health
```

Expected: All services should be `true`

### 2. Get a Document ID
First, list documents to get an ID:
```bash
curl https://your-railway-url.railway.app/admin/documents
```

Pick a document ID from the response (e.g., `123`)

### 3. Add First Author
```bash
curl -X POST https://your-railway-url.railway.app/api/documents/123/authors \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Test Author One",
    "author_site_url": "https://example.com/author1",
    "order": 0
  }'
```

Expected: Success message with author_id

### 4. Add Second Author
```bash
curl -X POST https://your-railway-url.railway.app/api/documents/123/authors \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Test Author Two",
    "author_site_url": "https://example.com/author2",
    "order": 1
  }'
```

Expected: Success message with different author_id

### 5. Get Document with Authors
```bash
curl https://your-railway-url.railway.app/api/documents/123
```

Expected: Document with `authors` array containing both authors in order

### 6. Try to Add Duplicate (Should Fail)
```bash
curl -X POST https://your-railway-url.railway.app/api/documents/123/authors \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Test Author One",
    "order": 2
  }'
```

Expected: 400 error about duplicate association

### 7. Reorder Authors
```bash
curl -X PUT https://your-railway-url.railway.app/api/documents/123/authors/order \
  -H "Content-Type: application/json" \
  -d '{
    "author_ids": [<author2_id>, <author1_id>]
  }'
```

Replace `<author1_id>` and `<author2_id>` with actual IDs from step 5.

Expected: Success message

### 8. Verify Reorder
```bash
curl https://your-railway-url.railway.app/api/documents/123
```

Expected: Authors should now be in reversed order

### 9. Remove One Author
```bash
curl -X DELETE https://your-railway-url.railway.app/api/documents/123/authors/<author2_id>
```

Expected: Success message

### 10. Try to Remove Last Author (Should Fail)
```bash
curl -X DELETE https://your-railway-url.railway.app/api/documents/123/authors/<author1_id>
```

Expected: 400 error about needing at least one author

### 11. Run Property Test 1
```bash
curl -X POST https://your-railway-url.railway.app/test-document-author/property-1-multiple-author-association
```

Expected: `"status": "passed"` with 50 examples run

### 12. Run Property Test 7
```bash
curl -X POST https://your-railway-url.railway.app/test-document-author/property-7-document-type-in-responses
```

Expected: `"status": "passed"` with 50 examples run

## Cleanup
After testing, you may want to remove the test authors:
```bash
# This would require admin access to the database
# Or you can leave them - they won't interfere with normal operation
```

## Success Criteria
- ✅ All manual API calls work as expected
- ✅ Duplicate prevention works
- ✅ Last author prevention works
- ✅ Both property tests pass with 50 examples each
- ✅ Document type is included in all responses
- ✅ Authors are returned in correct order
