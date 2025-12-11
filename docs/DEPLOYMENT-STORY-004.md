# Story 004 Deployment Instructions

## Overview
Story 004 implements the Metadata Management System with fixed admin endpoints that properly reuse the existing database connection pool.

## Deployment Steps

### 1. ✅ Code Deployed (Automatic)
The code has been pushed to GitHub and Railway should automatically deploy it.

### 2. Verify Deployment
Check Railway deployment status:
- Go to Railway dashboard
- Verify the deployment completed successfully
- Check logs for: "✅ Using fixed admin documents endpoints"

### 3. Run Database Migration

**Option A: Via Railway Shell**
```bash
# Connect to Railway shell
railway shell

# Navigate to backend directory
cd backend

# Run the migration
python migrate_story_004.py
```

**Option B: Via API Endpoint (if shell not available)**
You can trigger the migration via the existing endpoint:
```
GET https://mcpress-chatbot-production-569b.up.railway.app/run-story4-migration
```

### 4. Verify Migration Success
The migration script will:
1. Create `books` table with all metadata fields
2. Migrate existing document data from `documents` table
3. Create `metadata_history` table for audit logging
4. Add necessary indexes
5. Show statistics of migrated data

Expected output:
```
📚 MIGRATION COMPLETE
Total books: 115
Categories: X
Average pages: XX
Max pages: XXX
```

### 5. Test Admin Endpoints

Test the admin endpoints are working:

1. **Check Admin Documents List**
   ```
   GET https://mcpress-chatbot-production-569b.up.railway.app/admin/documents
   ```
   Should return documents with proper IDs and metadata

2. **Check Admin Stats**
   ```
   GET https://mcpress-chatbot-production-569b.up.railway.app/admin/stats
   ```
   Should return document statistics

3. **Test Frontend**
   - Navigate to: https://mc-press-chatbot.netlify.app/admin/documents
   - Login with admin credentials
   - Verify table shows documents with IDs
   - Test inline editing
   - Test CSV export

### 6. Monitor for Issues

Watch for any errors in Railway logs:
- No "network error" messages
- No "connection timeout" errors
- Admin endpoints returning data properly

## Rollback Plan (if needed)

If issues occur:

1. **Quick Fix**: The frontend will automatically fall back to regular `/documents` endpoint if admin endpoints fail

2. **Full Rollback** (if critical issues):
   ```bash
   # Revert to previous commit
   git revert HEAD
   git push origin main
   ```

3. **Database Rollback** (if migration causes issues):
   ```sql
   -- Connect to database and run:
   DROP TABLE IF EXISTS metadata_history CASCADE;
   -- Books table can remain as it doesn't affect existing functionality
   ```

## Success Criteria

✅ Deployment is successful when:
- [ ] Railway deployment completed without errors
- [ ] Migration script ran successfully
- [ ] Admin endpoints return data at `/admin/documents`
- [ ] Frontend shows document IDs and metadata
- [ ] Inline editing works
- [ ] CSV export/import functions
- [ ] No network errors in logs
- [ ] Login and other features still work

## Key Files Changed

- `backend/admin_documents_fixed.py` - New fixed admin router
- `backend/migrate_story_004.py` - Migration script
- `backend/main.py` - Updated to use fixed router
- `docs/admin-endpoints-attempt-log.md` - Documentation of issues and fixes

## Notes

The main fix was changing from creating new database connections (`asyncpg.connect()`) to reusing the existing vector store's connection pool (`_vector_store.pool`). This prevents connection conflicts that were causing network errors throughout the application.

## Support

If issues arise during deployment:
1. Check Railway logs for specific error messages
2. Verify DATABASE_URL environment variable is set
3. Ensure PostgreSQL has sufficient connections available
4. Frontend will gracefully fall back if admin endpoints aren't available