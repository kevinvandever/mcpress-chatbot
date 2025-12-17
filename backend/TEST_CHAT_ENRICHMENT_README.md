# Chat Enrichment Unit Tests

## Overview

This test suite validates the `ChatHandler._enrich_source_metadata()` method for the chat-metadata-enrichment-fix feature.

## Test Coverage

### Task 2.1: Successful Enrichment with Multiple Authors

**File**: `backend/test_chat_enrichment.py`

**Tests**:
1. `test_enrich_source_metadata_with_multiple_authors` - Tests enrichment with 3 authors in specific order
2. `test_enrich_source_metadata_article_with_url` - Tests enrichment for article type documents

**Requirements Validated**:
- 1.4: Author records joined with authors table to retrieve names and URLs
- 2.1: Book documents include mc_press_url in enriched metadata
- 2.2: Article documents include article_url in enriched metadata
- 2.3: Enriched metadata includes document_type field

## Running Tests on Railway

Since all testing must be done on Railway (per tech.md steering guide), follow these steps:

### Option 1: Using Railway CLI

```bash
# Connect to Railway shell
railway shell

# Run all chat enrichment tests
python3 -m pytest backend/test_chat_enrichment.py -v -s

# Run specific test
python3 -m pytest backend/test_chat_enrichment.py::test_enrich_source_metadata_with_multiple_authors -v -s
```

### Option 2: Using the Helper Script

```bash
# Connect to Railway shell
railway shell

# Run the helper script
python3 backend/run_test_chat_enrichment.py
```

### Option 3: Direct SSH to Railway

```bash
# SSH into Railway container
railway shell

# Navigate to project directory
cd /app

# Run tests
python3 -m pytest backend/test_chat_enrichment.py -v -s
```

## Test Details

### Test 1: Multiple Authors Enrichment

**Scenario**: Book with 3 authors in specific order

**Mock Data**:
- Book: "Test Book Title" (book type)
- Authors:
  1. Alice Johnson (order 0, has site_url)
  2. Bob Smith (order 1, has site_url)
  3. Charlie Davis (order 2, no site_url)
- mc_press_url: https://mcpress.com/test-book
- article_url: None

**Assertions**:
- ✅ All required fields present (author, mc_press_url, article_url, document_type, authors)
- ✅ Author field contains comma-separated names: "Alice Johnson, Bob Smith, Charlie Davis"
- ✅ mc_press_url is included
- ✅ article_url is None for book type
- ✅ document_type is "book"
- ✅ Authors array contains all 3 author objects with correct details
- ✅ SQL query uses `da.book_id` (not `da.document_id`)

### Test 2: Article with URL

**Scenario**: Article document with article_url

**Mock Data**:
- Article: "Test Article Title" (article type)
- Author: Article Author (single author)
- mc_press_url: empty string
- article_url: https://mcpress.com/articles/test-article

**Assertions**:
- ✅ article_url is included
- ✅ document_type is "article"
- ✅ mc_press_url is empty for article

## Expected Output

When tests pass, you should see:

```
============================= test session starts ==============================
backend/test_chat_enrichment.py::test_enrich_source_metadata_with_multiple_authors PASSED
✅ Test passed: Enrichment with multiple authors works correctly

backend/test_chat_enrichment.py::test_enrich_source_metadata_article_with_url PASSED
✅ Test passed: Article enrichment with article_url works correctly

============================== 2 passed in 0.XX s ===============================
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running from the project root:
```bash
cd /app
python3 -m pytest backend/test_chat_enrichment.py -v -s
```

### Missing Dependencies

If pytest is not available:
```bash
pip3 install pytest pytest-asyncio
```

### Mock Issues

The tests use `unittest.mock` which is part of Python's standard library. If you encounter issues:
- Verify Python version is 3.7+ (asyncio support)
- Check that asyncpg is installed (for type hints)

## Next Steps

After these tests pass:
- Proceed to Task 2.2: Write property test for author ordering
- Proceed to Task 2.3: Write property test for legacy author fallback
- Proceed to Task 2.4: Write property test for complete metadata structure

## Notes

- These are **unit tests** with mocked database connections
- No actual database queries are executed
- Tests validate the logic and structure of the enrichment method
- Property-based tests will be added in subsequent tasks for broader coverage
