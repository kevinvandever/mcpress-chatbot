# Migration 003 Property-Based Tests

## Overview

The `test_migration_003.py` file contains property-based tests for Migration 003 (Multi-Author Metadata Enhancement), specifically testing **Property 13: Migration preserves metadata**.

## Test Structure

The test file contains two types of tests:

### 1. Logic Tests (Run Locally)
These tests verify the migration logic without requiring database access:

- `test_migration_logic_preserves_metadata_structure` - Unit test verifying metadata structure preservation
- `test_migration_metadata_preservation_logic` - Property-based test using Hypothesis (100 examples)

**Run locally:**
```bash
python -m pytest backend/test_migration_003.py::test_migration_logic_preserves_metadata_structure -v
python -m pytest backend/test_migration_003.py::test_migration_metadata_preservation_logic -v
```

### 2. Integration Tests (Run on Railway)
These tests require DATABASE_URL and will be skipped locally:

- `test_migration_preserves_metadata_property` - Full property-based test with database
- `test_migration_handles_empty_author` - Edge case: empty author field
- `test_migration_handles_null_author` - Edge case: NULL author field
- `test_migration_preserves_special_characters` - Edge case: special characters in metadata

**Run on Railway:**
```bash
# SSH into Railway or use Railway CLI
python -m pytest backend/test_migration_003.py -v
```

## Property 13: Migration Preserves Metadata

**Validates:** Requirements 4.4

**Property Statement:**
> For any document before migration, all metadata fields (title, category, URLs) should have identical values after migration.

**Preserved Fields:**
- `filename`
- `title`
- `category`
- `subcategory`
- `mc_press_url`
- `description`
- `tags`
- `year`
- `total_pages`
- `file_hash`
- `processed_at`

## Test Results

✅ **Local Tests:** 2 passed
- Logic tests verify the migration transformation is correct
- Property-based test runs 100 examples with random data

⏭️ **Railway Tests:** 4 skipped locally (will run on Railway)
- Integration tests verify actual database operations
- Full end-to-end migration testing with real database

## Running All Tests

```bash
# Run all tests (local tests will pass, Railway tests will skip)
python -m pytest backend/test_migration_003.py -v

# Run only local tests
python -m pytest backend/test_migration_003.py -v -k "logic"

# Run with coverage
python -m pytest backend/test_migration_003.py --cov=backend --cov-report=html
```

## Notes

- The logic tests use Hypothesis for property-based testing with 100 examples per test
- Integration tests are designed to run on Railway where DATABASE_URL is available
- All tests follow the pattern: **Feature: multi-author-metadata-enhancement, Property 13: Migration preserves metadata**
