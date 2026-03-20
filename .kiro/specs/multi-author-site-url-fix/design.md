# Bugfix Design Document

## Overview

Fix the missing author `site_url` values during book metadata import by cross-referencing the article Excel data (`export_subset_DMU_v2.xlsx`) to build an author name → URL mapping, then passing matched URLs to `_get_or_create_author_in_transaction()` during book import. Additionally, provide a standalone API endpoint to backfill author URLs for authors already in the database.

## Root Cause

In `backend/excel_import_service.py`, the `import_book_metadata()` method (line ~750) calls:
```python
author_id = await self._get_or_create_author_in_transaction(conn, author_name)
```
without passing `site_url`. The method already accepts an optional `site_url` parameter and handles it correctly via `INSERT...ON CONFLICT` with `COALESCE`. The fix is to look up each author's URL from the article data and pass it.

## Design

### 1. New Method: `build_author_url_mapping()`

Add to `ExcelImportService`:

```python
def build_author_url_mapping(self, article_excel_path: str) -> Dict[str, str]:
```

- Reads `export_subset_DMU_v2.xlsx` with `openpyxl` using `data_only=True` (cells contain formulas)
- Iterates the `export_subset` sheet, extracting column J (author name) and column L ("Arthor URL")
- Builds a `Dict[str, str]` mapping `author_name → author_url`
- Normalizes URLs via existing `_normalize_url()`
- Validates URLs via existing `_is_valid_url()`
- Returns the mapping (959 unique entries expected)

### 2. Modify `import_book_metadata()` Signature

```python
async def import_book_metadata(
    self, 
    file_path: str, 
    author_url_mapping: Optional[Dict[str, str]] = None
) -> ImportResult:
```

- New optional parameter `author_url_mapping` defaults to `None` (backward compatible)
- In the author processing loop, look up `author_name` in the mapping:
  ```python
  site_url = author_url_mapping.get(author_name) if author_url_mapping else None
  author_id = await self._get_or_create_author_in_transaction(conn, author_name, site_url)
  ```
- Track `authors_updated` count when a URL is applied

### 3. New API Endpoint: `POST /api/excel/backfill-author-urls`

Add to `backend/excel_import_routes.py`:

```python
@router.post("/api/excel/backfill-author-urls")
async def backfill_author_urls(file: UploadFile = File(...)):
```

- Accepts the article Excel file (`export_subset_DMU_v2.xlsx`)
- Calls `build_author_url_mapping()` to extract author URLs
- Iterates the mapping and calls `_get_or_create_author_in_transaction()` for each author with their URL (the `ON CONFLICT` upsert will update existing authors' `site_url` via `COALESCE`)
- Returns stats: `{ authors_checked, authors_updated, authors_not_found }`
- This endpoint allows updating author URLs independently of book import

### 4. Modify Existing Book Import Endpoint

Update `POST /api/excel/import/books` in `excel_import_routes.py`:

```python
async def import_book_metadata(
    file: UploadFile = File(...),
    author_url_file: Optional[UploadFile] = File(None)
):
```

- Accept optional second file `author_url_file` for the article Excel
- If provided, call `build_author_url_mapping()` and pass result to `import_book_metadata()`
- If not provided, behavior is identical to current (backward compatible)

### 5. Local Script: `backfill_author_urls.py`

Root-level API-based script following project patterns:

```python
#!/usr/bin/env python3
import requests
API_URL = "https://mcpress-chatbot-staging.up.railway.app"

with open('export_subset_DMU_v2.xlsx', 'rb') as f:
    response = requests.post(
        f"{API_URL}/api/excel/backfill-author-urls",
        files={'file': ('export_subset_DMU_v2.xlsx', f)}
    )
print(response.json())
```

## Files Changed

| File | Change |
|------|--------|
| `backend/excel_import_service.py` | Add `build_author_url_mapping()`, modify `import_book_metadata()` signature to accept `author_url_mapping` |
| `backend/excel_import_routes.py` | Add `backfill_author_urls` endpoint, modify `import_book_metadata` route to accept optional `author_url_file` |
| `backfill_author_urls.py` | New root-level script to call backfill endpoint |

## Correctness Properties

P1: For every author name that exists in both the article Excel mapping and the `authors` table, after backfill the author's `site_url` SHALL be non-NULL and match the mapping value.

P2: For every author name that does NOT exist in the article Excel mapping, the author's `site_url` SHALL remain unchanged (NULL if it was NULL, existing value if it had one).

P3: The `build_author_url_mapping()` method SHALL return a dictionary where every value is a valid URL starting with `http://` or `https://`.

P4: After running `import_book_metadata()` with an `author_url_mapping`, every author-document association SHALL still exist identically to running without the mapping (no associations lost or duplicated).

P5: The `import_article_metadata()` method SHALL continue to pass `author_url` to `_get_or_create_author_in_transaction()` identically to its current behavior.
