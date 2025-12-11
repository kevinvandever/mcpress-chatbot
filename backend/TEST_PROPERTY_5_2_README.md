# Property Test 5.2: Author Updates Propagate

## Overview
This test validates **Property 15: Author updates propagate** from the multi-author-metadata-enhancement feature.

**Validates: Requirements 5.6**

## Property Statement
*For any* author associated with multiple documents, when updating the author's information, all documents should reflect the updated information.

## Test Location
`backend/test_author_service.py::test_author_updates_propagate_property`

## Test Strategy
1. Create an author with initial information (name and optional URL)
2. Associate the author with multiple documents (1-5 documents)
3. Update the author's name and/or URL
4. Retrieve the author information from each document
5. Verify all documents reflect the updated author information

## Running the Test

### On Railway (Required)
According to the project's testing guidelines, all database tests must be run on Railway where DATABASE_URL is available.

#### Option 1: Using Railway CLI
```bash
# Connect to Railway
railway run python -m pytest backend/test_author_service.py::test_author_updates_propagate_property -v --tb=short

# Or use the helper script
railway run python backend/run_property_test_5_2.py
```

#### Option 2: Via Railway Shell
```bash
# Open Railway shell
railway shell

# Run the test
python -m pytest backend/test_author_service.py::test_author_updates_propagate_property -v --tb=short
```

#### Option 3: SSH to Railway Instance
```bash
# SSH to Railway
railway ssh

# Navigate to app directory
cd /app

# Run the test
python -m pytest backend/test_author_service.py::test_author_updates_propagate_property -v --tb=short
```

## Test Configuration
- **Framework**: Hypothesis (property-based testing)
- **Iterations**: 100 examples per test run
- **Timeout**: None (disabled for database operations)
- **Health Checks**: function_scoped_fixture suppressed

## Expected Behavior
The test should:
1. ✅ Pass when author updates correctly propagate to all associated documents
2. ❌ Fail if any document shows stale author information after update
3. ❌ Fail if the author's direct retrieval shows incorrect information
4. ❌ Fail if the document count is incorrect

## Dependencies
- `asyncpg` - PostgreSQL async driver
- `hypothesis` - Property-based testing framework
- `pytest` - Test framework
- `pytest-asyncio` - Async test support

## Database Requirements
- `authors` table must exist
- `document_authors` junction table must exist
- `books` table must exist
- Migration 003 must be completed

## Cleanup
The test automatically cleans up:
- Test authors (prefixed with `TEST_`)
- Test documents created during the test
- Document-author associations

## Troubleshooting

### Test Skipped
If the test is skipped with "DATABASE_URL not set", ensure you're running on Railway where the environment variable is available.

### Tables Don't Exist
If you see "authors table does not exist", run migration 003:
```bash
python backend/run_migration_003.py
```

### Connection Timeout
If you see connection timeouts, check:
1. Railway database is running
2. DATABASE_URL is correct
3. Network connectivity to Railway

## Related Tests
- `test_author_deduplication_property` - Property 2
- `test_get_or_create_behavior_property` - Property 14
- `test_url_validation_property` - Property 10

## Implementation Details
The test uses Hypothesis strategies to generate:
- Random author names (prefixed with `TEST_` for cleanup)
- Random valid/invalid URLs
- Random number of documents (1-5)
- Random updated names and URLs

This ensures the property holds across a wide range of inputs and scenarios.
