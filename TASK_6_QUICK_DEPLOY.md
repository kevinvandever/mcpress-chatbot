# Task 6: Quick Deploy & Test Commands

## Deploy to Railway

```bash
# Add all files
git add backend/main.py backend/document_author_routes.py backend/test_document_author_endpoint.py backend/test_document_author_routes.py TASK_6_DEPLOYMENT_GUIDE.md TASK_6_FIX_RAILWAY_INIT.md TASK_6_QUICK_DEPLOY.md

# Commit
git commit -m "Task 6: Implement document-author API + fix Railway init"

# Push (triggers Railway deployment)
git push origin main
```

## Wait for Deployment
- Check Railway dashboard: https://railway.app
- Wait for "Deployed" status (2-3 minutes)
- Check logs for: `✅ Task 6 test endpoints enabled at /test-task-6/*`

## Test on Railway

### Run All Property Tests (100 iterations)
```bash
curl https://mcpress-chatbot-production.up.railway.app/test-task-6/run-property-tests
```

### Test Duplicate Prevention
```bash
curl https://mcpress-chatbot-production.up.railway.app/test-task-6/test-duplicate-prevention
```

### Test Last Author Prevention
```bash
curl https://mcpress-chatbot-production.up.railway.app/test-task-6/test-last-author-prevention
```

### Cleanup Test Data
```bash
curl https://mcpress-chatbot-production.up.railway.app/test-task-6/cleanup
```

## Expected Success Output

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
      "status": "PASSED"
    },
    "property_7_document_type_in_responses": {
      "validates": "Requirements 2.4",
      "iterations": 50,
      "passed": 50,
      "failed": 0,
      "success_rate": "100%",
      "status": "PASSED"
    }
  }
}
```

## API Endpoints Now Available

### Add Author to Document
```bash
curl -X POST https://mcpress-chatbot-production.up.railway.app/api/documents/1/authors \
  -H "Content-Type: application/json" \
  -d '{"author_name": "John Doe", "author_site_url": "https://johndoe.com", "order": 0}'
```

### Get Document with Authors
```bash
curl https://mcpress-chatbot-production.up.railway.app/api/documents/1
```

### Remove Author from Document
```bash
curl -X DELETE https://mcpress-chatbot-production.up.railway.app/api/documents/1/authors/2
```

### Reorder Authors
```bash
curl -X PUT https://mcpress-chatbot-production.up.railway.app/api/documents/1/authors/order \
  -H "Content-Type: application/json" \
  -d '{"author_ids": [1, 3, 2]}'
```

## Troubleshooting

### If deployment hangs:
- Check Railway logs for errors
- Verify DATABASE_URL is set in Railway environment
- Look for initialization errors in startup logs

### If tests fail:
- Check the "failures" array in response
- Verify migration 003 was run successfully
- Ensure tables exist: `authors`, `document_authors`, `books`

### If endpoints return 503:
- Services not initialized
- Check Railway logs for: `✅ Author management endpoints enabled`
- Verify DATABASE_URL is configured

## Railway Project
- **URL**: https://mcpress-chatbot-production.up.railway.app
- **Dashboard**: https://railway.app
