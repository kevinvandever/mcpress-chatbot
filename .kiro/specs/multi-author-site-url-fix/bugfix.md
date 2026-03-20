# Bugfix Requirements Document

## Introduction

When importing book metadata via `import_book_metadata()` in `backend/excel_import_service.py`, author `site_url` values are never stored in the database. The book Excel file (`MC Press Books - URL-Title-Author.xlsx`) does not contain author page URLs, but the article Excel file (`export_subset_DMU_v2.xlsx`) has an "Arthor URL" column (column L) with mcpressonline.com author page URLs. Of the 132 unique book authors, 37 have matching URLs in the article data. The bug is that `import_book_metadata()` calls `_get_or_create_author_in_transaction(conn, author_name)` without passing a `site_url`, so even when an author's URL is available from the article data, it is never cross-referenced or applied during book import. This leaves the majority of book authors with `NULL` site_url values in the `authors` table.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `import_book_metadata()` processes a book with multiple authors THEN the system calls `_get_or_create_author_in_transaction(conn, author_name)` without a `site_url` parameter, resulting in all book authors being created or updated with `NULL` site_url.

1.2 WHEN a book author name matches an author who has a known page URL in the article Excel data (`export_subset_DMU_v2.xlsx`, column L) THEN the system does not cross-reference the article data, so the matching author's site_url remains `NULL` in the database.

1.3 WHEN the user imports book metadata independently (without first importing article metadata) THEN the system has no mechanism to look up or apply author site_urls from the article data source, leaving all 132 book authors without site_url values.

### Expected Behavior (Correct)

2.1 WHEN `import_book_metadata()` processes a book with multiple authors THEN the system SHALL look up each author's site_url from a pre-built mapping derived from the article Excel data and pass it to `_get_or_create_author_in_transaction(conn, author_name, site_url)`.

2.2 WHEN a book author name matches an author who has a known page URL in the article Excel data THEN the system SHALL apply that author's site_url to the `authors` table via the `INSERT...ON CONFLICT` upsert (which uses `COALESCE(EXCLUDED.site_url, authors.site_url)` to preserve existing URLs).

2.3 WHEN the user imports book metadata THEN the system SHALL support accepting the article Excel file (or a pre-built author-URL mapping) as an additional input so that author site_urls can be cross-referenced and stored during the book import flow.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `import_book_metadata()` processes books with authors that have no matching URL in the article data THEN the system SHALL CONTINUE TO create those authors with `NULL` site_url (no fabricated URLs).

3.2 WHEN `import_article_metadata()` processes articles THEN the system SHALL CONTINUE TO pass `author_url` to `_get_or_create_author_in_transaction(conn, author_name, author_url)` as it does today.

3.3 WHEN `_get_or_create_author_in_transaction()` is called with a `site_url` for an author that already has a `site_url` in the database THEN the system SHALL CONTINUE TO preserve the existing site_url via the `COALESCE(EXCLUDED.site_url, authors.site_url)` logic.

3.4 WHEN `import_book_metadata()` processes book titles, mc_press_url values, and author-document associations THEN the system SHALL CONTINUE TO perform fuzzy title matching, URL updates, author parsing, and document_authors association creation identically to the current behavior.

3.5 WHEN authors are parsed from the book Excel Author column (comma/and-separated) THEN the system SHALL CONTINUE TO split and trim author names using the existing `parse_authors()` logic.
