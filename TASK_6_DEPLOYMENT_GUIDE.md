# Task 6: Document-Author Relationship API - Deployment & Testing Guide

## Overview
Task 6 implements the document-author relationship API endpoints that allow:
- Adding authors to documents
- Removing authors from documents  
- Reordering authors
- Getting documents with their authors
- Includes document_type in responses

## Files Created/Modified

### New Files:
1. `backend/document_author_routes.py` - API endpoints for document-author relationships
2. `backend/test_document_author_endpoint.py` - HTTP-accessible property tests
3. `backend/test_document_author_routes.py` - Local pytest property tests

### Modified Files:
1. `backend/main.py` - Added router registration for new endpoints

## Deployment Steps

### 1. Commit and Push to Git

```bash
# Add all new files
git add backend/document_author_routes.py
git add backend/test_document_author_endpoint.py
git add backend/test_document_author_routes.py
git add TASK_6_DEPLOYMENT_GUIDE.md

# Commit changes
git commit -m "Task 6: Implement document-author relationship API endpoints

- Add POST /api/documents/{id}/authors endpoint
- Add DELETE /api/documents/{id}/authors/{author_id} endpoint
- Add PUT /api/documents/{id}/authors/order endpoint
- Add GET /api/documents/{id} with authors array
- Include document_type in responses
- Add property-based tests for multiple author association
- Add property-based tests for document type in responses
- Validates Requirements 1.1, 1.3, 1.4, 1.5, 2.4, 5.1, 5.3, 5.4, 5.7"

# Push to trigger Railway deployment
git push origin main
```

### 2. Wait for Railway Deployment
- Railway will automatically detect the push and deploy
- Check Railway dashboard for deployment status
- Wait for "Deployed" status (usually 2-3 minutes)

## Testing on Railway

### Test Endpoints Available

Once deployed, you can access these test endpoints:

#### 1. Run All Property Tests
```bash
curl https://your-railway-url.up.railway.app/test-task-6/run-property-tests
```

This runs:
- **Property 1**: Multiple author association (50 iterations)
  - Validates: Requirements 1.1, 1.3
  - Tests that all authors can be associated and retrieved in order
  
- **Property 7**: Document type in responses (50 iterations)
  - Validates: Requirements 2.4
  - Tests that document_type is always present in responses

Expected output:
```json
{
  "test_suite": "Task 6: Document-Author Relationship API",
  "total_iterations": 100,
  "status": "PASSED",
  "properties": {
    "property_1_multiple_author_association": {
      "validates": "Requirements 1.1, 1.3",
      "iterations": 50,
      "passed": 50,
      "failed": 0,
      "success_rate": "100%",
      "status": "PASSED",
      "failures": []
    },
    "property_7_document_type_in_responses": {
      "validates": "Requirements 2.4",
      "iterations": 50,
      "passed": 50,
      "failed": 0,
      "success_rate": "100%",
      "status": "PASSED",
      "failures": []
    }
  }
}
```

#### 2. Test Duplicate Prevention
```bash
curl https://your-railway-url.up.railway.app/test-task-6/test-duplicate-prevention
```

Tests that adding the same author twice to a document is prevented.

Expected output:
```json
{
  "test": "Duplicate author prevention",
  "validates": "Requirements 1.4",
  "status": "PASSED",
  "duplicate_prevented": true,
  "association_count": 1,
  "message": "Duplicate prevention working correctly"
}
```

#### 3. Test Last Author Prevention
```bash
curl https://your-railway-url.up.railway.app/test-task-6/test-last-author-prevention
```

Tests that documents must have at least one author.

Expected output:
```json
{
  "test": "Last author removal prevention",
  "validates": "Requirements 5.7",
  "status": "PASSED",
  "author_count": 1,
  "message": "Document has exactly one author (API should prevent removal)"
}
```

#### 4. Cleanup Test Data
```bash
curl https://your-railway-url.up.railway.app/test-task-6/cleanup
```

Cleans up any test data left over from testing.

## API Endpoints Available

### 1. Add Author to Document
```bash
POST /api/documents/{document_id}/authors
Content-Type: application/json

{
  "author_name": "John Doe",
  "author_site_url": "https://johndoe.com",
  "order": 0
}
```

### 2. Remove Author from Document
```bash
DELETE /api/documents/{document_id}/authors/{author_id}
```

### 3. Reorder Authors
```bash
PUT /api/documents/{document_id}/authors/order
Content-Type: application/json

{
  "author_ids": [1, 3, 2]
}
```

### 4. Get Document with Authors
```bash
GET /api/documents/{document_id}
```

Response includes:
- All authors in order
- document_type field
- All other document metadata

## Testing Locally (Optional)

If you want to test locally with pytest:

```bash
# Set DATABASE_URL to your Railway database
export DATABASE_URL="postgresql://..."

# Run property tests
python -m pytest backend/test_document_author_routes.py -v -s

# Run specific test
python -m pytest backend/test_document_author_routes.py::test_property_multiple_author_association -v -s
```

## Verification Checklist

- [ ] Code committed and pushed to git
- [ ] Railway deployment completed successfully
- [ ] Property test endpoint returns "PASSED" status
- [ ] All 100 iterations pass (50 for each property)
- [ ] Duplicate prevention test passes
- [ ] Last author prevention test passes
- [ ] Test data cleanup successful

## Troubleshooting

### Tests are skipped locally
- This is expected if DATABASE_URL is not set
- Tests will run on Railway where DATABASE_URL is configured

### Property tests fail
- Check the "failures" array in the response for details
- Common issues:
  - Migration not run (tables don't exist)
  - Database connection issues
  - Constraint violations

### Endpoints return 503
- Services not initialized
- Check Railway logs for initialization errors
- Verify DATABASE_URL is set in Railway environment

## Next Steps

After successful deployment and testing:

1. Verify all tests pass on Railway
2. Document any issues found
3. Proceed to Task 7: Update admin documents endpoints for multi-author support

## Requirements Validated

This task validates the following requirements:
- **1.1**: Support associating multiple authors with documents
- **1.3**: Return authors in consistent order
- **1.4**: Prevent duplicate author associations
- **1.5**: Remove associations while preserving shared authors
- **2.4**: Include document_type in responses
- **5.1**: Display all associated authors
- **5.3**: Create new author if doesn't exist
- **5.4**: Reuse existing author if exists
- **5.7**: Prevent removing last author

## Property Tests Implemented

### Property 1: Multiple author association
*For any* document and any list of authors, when associating those authors with the document, all authors should be retrievable from the document in the same order.

### Property 7: Document type in responses
*For any* document retrieval, the response should include the document_type field.
