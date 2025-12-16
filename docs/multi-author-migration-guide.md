# Multi-Author Database Migration Guide

## Overview

This guide provides detailed instructions for migrating from the single-author system to the multi-author metadata enhancement. The migration transforms the existing `books.author` column into a normalized many-to-many relationship between documents and authors.

## Migration Architecture

### Before Migration
```
books table:
- id (primary key)
- filename
- title
- author (single text field)
- category
- mc_press_url
- ... other fields
```

### After Migration
```
books table:
- id (primary key)
- filename  
- title
- document_type (new: 'book' or 'article')
- article_url (new: for article-type documents)
- category
- mc_press_url (existing)
- ... other fields
- author (removed after migration)

authors table (new):
- id (primary key)
- name (unique)
- site_url (optional)
- created_at
- updated_at

document_authors table (new):
- id (primary key)
- book_id (foreign key to books.id)
- author_id (foreign key to authors.id)
- author_order (display order)
- created_at
```

## Pre-Migration Requirements

### System Requirements
- PostgreSQL 12+ with admin access
- Python 3.11+ with required dependencies
- Railway deployment environment
- Minimum 2GB available disk space
- Estimated downtime: 30-60 minutes

### Backup Requirements
```bash
# Create full database backup
pg_dump $DATABASE_URL > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Verify backup integrity
pg_restore --list backup_pre_migration_*.sql | head -20
```

### Pre-Migration Validation
```bash
# Run pre-migration checks
python3 backend/pre_migration_check_003.py

# Expected output:
# ✓ Books table exists with author column
# ✓ No existing authors or document_authors tables
# ✓ All documents have non-null author values
# ✓ Database has sufficient disk space
# ✓ Required permissions available
```

## Migration Execution Steps

### Step 1: Deploy Migration Code

```bash
# Ensure latest code is deployed to Railway
git push origin main

# Verify deployment completed
railway logs --tail 50
```

### Step 2: Execute Schema Migration

Create the new tables and columns:

```bash
# Connect to Railway environment
railway shell

# Run schema migration
python3 backend/run_migration_003.py --schema-only

# Expected output:
# Creating authors table...
# Creating document_authors table...
# Adding document_type column to books...
# Adding article_url column to books...
# Creating indexes...
# Schema migration completed successfully
```

**Verification:**
```sql
-- Verify new tables exist
\dt authors
\dt document_authors

-- Verify new columns exist
\d books
```

### Step 3: Execute Data Migration

Transform existing author data:

```bash
# Run data migration (still in railway shell)
python3 backend/run_migration_003.py --data-only

# Expected output:
# Processing 1,250 documents...
# Extracting unique authors...
# Found 342 unique authors
# Creating author records...
# Creating document-author associations...
# Setting default document_type to 'book'...
# Data migration completed successfully
```

**Progress Monitoring:**
```bash
# Monitor migration progress (in separate terminal)
railway shell
python3 -c "
import asyncpg
import asyncio
async def check_progress():
    conn = await asyncpg.connect('$DATABASE_URL')
    authors = await conn.fetchval('SELECT COUNT(*) FROM authors')
    associations = await conn.fetchval('SELECT COUNT(*) FROM document_authors')
    print(f'Authors: {authors}, Associations: {associations}')
    await conn.close()
asyncio.run(check_progress())
"
```

### Step 4: Verify Migration Results

```bash
# Run comprehensive verification
python3 backend/verify_data_migration_003.py

# Expected output:
# ✓ All 1,250 documents have at least one author
# ✓ 342 unique authors created
# ✓ 1,250 document-author associations created
# ✓ No orphaned records found
# ✓ Author names match original data
# ✓ All documents have document_type set
# ✓ No data loss detected
```

### Step 5: Test Critical Functionality

```bash
# Test author search
curl -X GET "$API_URL/api/authors/search?q=Smith" | jq

# Test document retrieval with authors
curl -X GET "$API_URL/api/documents/1" | jq '.authors'

# Test adding new author to document
curl -X POST "$API_URL/api/documents/1/authors" \
  -H "Content-Type: application/json" \
  -d '{"author_name": "Test Author", "order": 1}' | jq

# Test CSV export with new format
curl -X GET "$API_URL/api/admin/export/csv" -o test_export.csv
head -5 test_export.csv
```

### Step 6: Remove Legacy Author Column

```bash
# Final step: remove old author column
python3 backend/run_migration_003.py --cleanup

# Expected output:
# Dropping author column from books table...
# Migration cleanup completed successfully
```

## Migration Verification Queries

### Data Integrity Checks

```sql
-- 1. Verify all documents have authors
SELECT COUNT(*) as documents_without_authors
FROM books b
LEFT JOIN document_authors da ON b.id = da.book_id
WHERE da.book_id IS NULL;
-- Expected: 0

-- 2. Verify author count matches original
SELECT 
  COUNT(DISTINCT author) as original_authors,
  (SELECT COUNT(*) FROM authors) as migrated_authors
FROM books_backup;  -- Assuming backup table exists

-- 3. Check for duplicate author associations
SELECT book_id, author_id, COUNT(*)
FROM document_authors
GROUP BY book_id, author_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- 4. Verify document types are set
SELECT document_type, COUNT(*)
FROM books
GROUP BY document_type;
-- Expected: All documents have 'book' or 'article'

-- 5. Check author order consistency
SELECT book_id, COUNT(*) as author_count,
       MIN(author_order) as min_order,
       MAX(author_order) as max_order
FROM document_authors
GROUP BY book_id
HAVING MIN(author_order) != 0 OR MAX(author_order) != COUNT(*) - 1;
-- Expected: 0 rows (orders should be 0-based and consecutive)
```

### Performance Verification

```sql
-- Check index usage
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM authors WHERE name ILIKE '%Smith%';

EXPLAIN (ANALYZE, BUFFERS)
SELECT b.*, a.name, a.site_url
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE b.id = 1;
```

## Rollback Procedures

### Automatic Rollback

If migration fails or verification shows issues:

```bash
# Execute automatic rollback
python3 backend/run_migration_003_rollback.py

# Expected output:
# Restoring author column to books table...
# Populating author column from document_authors...
# Dropping document_authors table...
# Dropping authors table...
# Removing document_type and article_url columns...
# Rollback completed successfully
```

### Manual Rollback from Backup

If automatic rollback fails:

```bash
# Stop application
railway service disconnect

# Restore from backup
pg_restore --clean --no-acl --no-owner -d $DATABASE_URL backup_pre_migration_*.sql

# Verify restoration
psql $DATABASE_URL -c "SELECT COUNT(*) FROM books WHERE author IS NOT NULL;"

# Restart application
railway service connect
```

### Partial Rollback (Schema Only)

If data migration succeeded but schema changes need reversal:

```sql
-- Remove new columns (keep data in new tables)
ALTER TABLE books DROP COLUMN IF EXISTS document_type;
ALTER TABLE books DROP COLUMN IF EXISTS article_url;

-- Restore author column
ALTER TABLE books ADD COLUMN author TEXT;

-- Populate from document_authors
UPDATE books SET author = (
  SELECT a.name 
  FROM document_authors da
  JOIN authors a ON da.author_id = a.id
  WHERE da.book_id = books.id
  ORDER BY da.author_order
  LIMIT 1
);
```

## Post-Migration Tasks

### Update Application Configuration

```bash
# Update environment variables if needed
railway variables set MULTI_AUTHOR_ENABLED=true

# Restart services to pick up changes
railway service restart
```

### Frontend Deployment

```bash
# Deploy updated frontend with multi-author components
cd frontend
npm run build
# Netlify will auto-deploy from git push
```

### Monitoring Setup

```bash
# Set up monitoring for new endpoints
curl -X GET "$API_URL/api/admin/stats" | jq '.authors'
curl -X GET "$API_URL/api/admin/stats" | jq '.document_authors'
```

### Performance Optimization

```sql
-- Update table statistics
ANALYZE authors;
ANALYZE document_authors;
ANALYZE books;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename IN ('authors', 'document_authors', 'books')
  AND n_distinct > 100;
```

## Troubleshooting Common Issues

### Migration Hangs or Times Out

**Symptoms:** Migration script runs for hours without completing

**Solutions:**
```bash
# Check for blocking queries
SELECT pid, state, query, query_start
FROM pg_stat_activity
WHERE state != 'idle' AND query NOT LIKE '%pg_stat_activity%';

# Kill blocking queries if safe
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE ...;

# Restart migration with smaller batches
python3 backend/run_migration_003.py --batch-size 100
```

### Duplicate Author Names

**Symptoms:** Migration creates multiple authors with same name

**Solutions:**
```sql
-- Find duplicates
SELECT name, COUNT(*) 
FROM authors 
GROUP BY name 
HAVING COUNT(*) > 1;

-- Merge duplicates (manual process)
-- 1. Choose canonical author ID
-- 2. Update document_authors to use canonical ID
-- 3. Delete duplicate author records
```

### Missing Author Associations

**Symptoms:** Some documents have no authors after migration

**Solutions:**
```sql
-- Find documents without authors
SELECT b.id, b.filename, b.title
FROM books b
LEFT JOIN document_authors da ON b.id = da.book_id
WHERE da.book_id IS NULL;

-- Create default author association
INSERT INTO authors (name) VALUES ('Unknown Author') 
ON CONFLICT (name) DO NOTHING;

INSERT INTO document_authors (book_id, author_id, author_order)
SELECT b.id, a.id, 0
FROM books b
LEFT JOIN document_authors da ON b.id = da.book_id
CROSS JOIN authors a
WHERE da.book_id IS NULL AND a.name = 'Unknown Author';
```

### Performance Issues After Migration

**Symptoms:** Slow queries on author-related endpoints

**Solutions:**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_document_authors_book_order 
ON document_authors(book_id, author_order);

CREATE INDEX CONCURRENTLY idx_authors_name_trgm 
ON authors USING gin(name gin_trgm_ops);

-- Update query planner statistics
ANALYZE authors;
ANALYZE document_authors;
```

### CSV Export Format Issues

**Symptoms:** Exported CSV has malformed multi-author data

**Solutions:**
```bash
# Test CSV export
curl -X GET "$API_URL/api/admin/export/csv" -o test.csv

# Verify pipe-delimited format
head -5 test.csv | cut -d',' -f4  # authors column
head -5 test.csv | cut -d',' -f6  # author_site_urls column

# Check for proper escaping
grep -n '|' test.csv | head -10
```

## Migration Timeline

### Typical Migration Schedule

**Week -2: Preparation**
- Deploy migration code to staging
- Test migration on staging database
- Prepare rollback procedures
- Schedule maintenance window

**Week -1: Final Preparation**
- Create production backup
- Verify staging migration results
- Prepare monitoring scripts
- Notify stakeholders

**Migration Day:**
- T-60min: Final backup
- T-30min: Deploy migration code
- T-0min: Begin maintenance window
- T+5min: Execute schema migration
- T+15min: Execute data migration
- T+45min: Verify results
- T+60min: End maintenance window

**Post-Migration:**
- Day +1: Monitor performance
- Day +3: Verify CSV exports
- Week +1: Full system validation

## Success Criteria

Migration is considered successful when:

- [ ] All documents have at least one author
- [ ] Author count matches pre-migration unique count
- [ ] No duplicate author associations exist
- [ ] All new API endpoints respond correctly
- [ ] CSV export includes multi-author data
- [ ] Frontend displays multiple authors correctly
- [ ] Performance meets baseline requirements
- [ ] No data loss detected in verification queries

## Emergency Contacts

**Database Issues:**
- Primary DBA: [Contact Info]
- Backup DBA: [Contact Info]

**Application Issues:**
- Lead Developer: [Contact Info]
- DevOps Engineer: [Contact Info]

**Business Stakeholders:**
- Product Owner: [Contact Info]
- System Administrator: [Contact Info]

## Migration Log Template

```
Migration Execution Log
Date: ___________
Operator: ___________
Start Time: ___________

Pre-Migration Checklist:
[ ] Backup created and verified
[ ] Staging migration tested
[ ] Rollback procedures ready
[ ] Stakeholders notified

Schema Migration:
Start: ___________
End: ___________
Status: ___________
Issues: ___________

Data Migration:
Start: ___________
End: ___________
Documents Processed: ___________
Authors Created: ___________
Associations Created: ___________
Errors: ___________

Verification:
[ ] All documents have authors
[ ] Author count correct
[ ] No orphaned records
[ ] API endpoints working
[ ] CSV export correct

Post-Migration:
[ ] Frontend deployed
[ ] Monitoring active
[ ] Performance acceptable
[ ] Stakeholders notified

Final Status: SUCCESS / ROLLBACK
Completion Time: ___________
Notes: ___________
```