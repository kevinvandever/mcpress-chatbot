"""
One-time data migration: Split legacy books.author field into proper document_authors entries.

The 120 books were loaded before the multi-author migration existed, so each book only has
one entry in document_authors (the full comma-separated author string as a single author).
This endpoint splits those into individual author records.
"""

import re
import logging
from fastapi import APIRouter
import asyncpg
import os

logger = logging.getLogger(__name__)

fix_book_authors_router = APIRouter()


def parse_authors(author_string: str) -> list:
    """Parse multiple authors from a string with various delimiters."""
    if not author_string:
        return []
    author_string = author_string.strip()
    if not author_string:
        return []
    if ";" in author_string:
        return [a.strip() for a in author_string.split(";") if a.strip()]
    if " and " in author_string:
        if "," in author_string:
            parts = author_string.split(",")
            authors = []
            for i, part in enumerate(parts):
                part = part.strip()
                if i == len(parts) - 1 and part.startswith("and "):
                    part = part[4:]
                if part:
                    authors.append(part)
            return authors
        else:
            return [a.strip() for a in author_string.split(" and ") if a.strip()]
    if author_string.endswith(" and"):
        return [author_string[:-4].strip()]
    if "," in author_string:
        return [a.strip() for a in author_string.split(",") if a.strip()]
    return [author_string.strip()]


@fix_book_authors_router.get("/api/fix-book-authors/debug")
async def debug_data():
    """Debug: Show sample data from books table to understand the author field."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        # Get table columns
        columns = await conn.fetch("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'books' ORDER BY ordinal_position
        """)

        # Sample books with author containing comma, semicolon, or " and "
        multi_author_samples = await conn.fetch("""
            SELECT id, title, author, document_type
            FROM books
            WHERE author LIKE '%,%' OR author LIKE '%;%' OR author LIKE '% and %'
            LIMIT 20
        """)

        # Count by document_type
        type_counts = await conn.fetch("""
            SELECT document_type, COUNT(*) as cnt FROM books GROUP BY document_type ORDER BY cnt DESC
        """)

        # Sample of books with document_type = 'book'
        book_samples = await conn.fetch("""
            SELECT id, title, author FROM books WHERE document_type = 'book' LIMIT 10
        """)

        # Check document_authors table
        da_counts = await conn.fetch("""
            SELECT book_id, COUNT(*) as author_count
            FROM document_authors
            GROUP BY book_id
            HAVING COUNT(*) > 1
            LIMIT 20
        """)

        # Total counts
        total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
        total_da = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")

        return {
            "table_columns": [{"name": c["column_name"], "type": c["data_type"]} for c in columns],
            "total_rows_in_books": total_books,
            "total_document_authors": total_da,
            "total_authors": total_authors,
            "type_counts": [{"type": t["document_type"], "count": t["cnt"]} for t in type_counts],
            "multi_author_samples": [
                {"id": b["id"], "title": b["title"], "author": b["author"], "type": b["document_type"]}
                for b in multi_author_samples
            ],
            "book_type_samples": [
                {"id": b["id"], "title": b["title"], "author": b["author"]}
                for b in book_samples
            ],
            "books_with_multiple_da_entries": [
                {"book_id": d["book_id"], "author_count": d["author_count"]}
                for d in da_counts
            ]
        }
    finally:
        await conn.close()


@fix_book_authors_router.get("/api/fix-book-authors/author-urls")
async def author_url_report():
    """Report on author URL coverage — how many have URLs vs missing."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM authors")
        with_url = await conn.fetchval(
            "SELECT COUNT(*) FROM authors WHERE site_url IS NOT NULL AND site_url != ''"
        )
        without_url = await conn.fetchval(
            "SELECT COUNT(*) FROM authors WHERE site_url IS NULL OR site_url = ''"
        )

        # Authors with URLs — sample
        url_samples = await conn.fetch("""
            SELECT a.id, a.name, a.site_url,
                   (SELECT COUNT(*) FROM document_authors da WHERE da.author_id = a.id) as doc_count
            FROM authors a
            WHERE a.site_url IS NOT NULL AND a.site_url != ''
            ORDER BY (SELECT COUNT(*) FROM document_authors da WHERE da.author_id = a.id) DESC
            LIMIT 20
        """)

        # Authors WITHOUT URLs who are associated with books (document_type='book')
        book_authors_missing_url = await conn.fetch("""
            SELECT DISTINCT a.id, a.name,
                   (SELECT COUNT(*) FROM document_authors da WHERE da.author_id = a.id) as doc_count
            FROM authors a
            JOIN document_authors da ON da.author_id = a.id
            JOIN books b ON b.id = da.book_id
            WHERE b.document_type = 'book'
              AND (a.site_url IS NULL OR a.site_url = '')
            ORDER BY a.name
        """)

        # Authors WITHOUT URLs who are associated with articles
        article_authors_missing_url = await conn.fetch("""
            SELECT DISTINCT a.id, a.name,
                   (SELECT COUNT(*) FROM document_authors da WHERE da.author_id = a.id) as doc_count
            FROM authors a
            JOIN document_authors da ON da.author_id = a.id
            JOIN books b ON b.id = da.book_id
            WHERE b.document_type = 'article'
              AND (a.site_url IS NULL OR a.site_url = '')
            ORDER BY (SELECT COUNT(*) FROM document_authors da WHERE da.author_id = a.id) DESC
            LIMIT 30
        """)

        return {
            "total_authors": total,
            "with_url": with_url,
            "without_url": without_url,
            "url_coverage_pct": round(with_url / total * 100, 1) if total > 0 else 0,
            "authors_with_urls_sample": [
                {"id": a["id"], "name": a["name"], "site_url": a["site_url"], "doc_count": a["doc_count"]}
                for a in url_samples
            ],
            "book_authors_missing_url": [
                {"id": a["id"], "name": a["name"], "doc_count": a["doc_count"]}
                for a in book_authors_missing_url
            ],
            "article_authors_missing_url_top30": [
                {"id": a["id"], "name": a["name"], "doc_count": a["doc_count"]}
                for a in article_authors_missing_url
            ]
        }
    finally:
        await conn.close()


@fix_book_authors_router.get("/api/fix-book-authors/preview")
async def preview_fix():
    """Preview which books need multi-author splitting (dry run)."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        books = await conn.fetch("""
            SELECT b.id, b.title, b.author as legacy_author,
                   (SELECT COUNT(*) FROM document_authors da WHERE da.book_id = b.id) as current_author_count
            FROM books b
            WHERE b.author IS NOT NULL AND b.author != ''
            ORDER BY b.id
        """)

        needs_fix = []
        already_ok = []
        for book in books:
            parsed = parse_authors(book["legacy_author"])
            current_count = book["current_author_count"]
            if len(parsed) > 1 and current_count < len(parsed):
                needs_fix.append({
                    "book_id": book["id"],
                    "title": book["title"],
                    "legacy_author": book["legacy_author"],
                    "parsed_authors": parsed,
                    "current_da_count": current_count,
                    "needed_da_count": len(parsed)
                })
            elif len(parsed) > 1:
                already_ok.append({
                    "book_id": book["id"],
                    "title": book["title"],
                    "current_da_count": current_count
                })

        return {
            "total_books": len(books),
            "needs_fix": len(needs_fix),
            "already_correct": len(already_ok),
            "books_to_fix": needs_fix
        }
    finally:
        await conn.close()


@fix_book_authors_router.post("/api/fix-book-authors/run")
async def run_fix():
    """
    Split legacy books.author into individual document_authors entries.
    For each multi-author book:
    1. Clear existing document_authors entries
    2. Parse the legacy author string into individual names
    3. Get or create each author in the authors table
    4. Create document_authors entries with proper ordering
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        books = await conn.fetch("""
            SELECT b.id, b.title, b.author as legacy_author
            FROM books b
            WHERE b.author IS NOT NULL AND b.author != ''
            ORDER BY b.id
        """)

        fixed = []
        skipped = []
        errors = []

        for book in books:
            parsed = parse_authors(book["legacy_author"])
            if len(parsed) <= 1:
                continue  # Single author, skip

            # Check current state
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM document_authors WHERE book_id = $1",
                book["id"]
            )
            if current_count >= len(parsed):
                skipped.append({"book_id": book["id"], "title": book["title"], "reason": "already has correct author count"})
                continue

            try:
                # Clear existing associations
                await conn.execute("DELETE FROM document_authors WHERE book_id = $1", book["id"])

                authors_added = []
                for order, author_name in enumerate(parsed):
                    # Get or create author
                    author_id = await conn.fetchval(
                        "SELECT id FROM authors WHERE name = $1", author_name
                    )
                    if not author_id:
                        author_id = await conn.fetchval(
                            "INSERT INTO authors (name) VALUES ($1) RETURNING id",
                            author_name
                        )

                    # Create association
                    await conn.execute("""
                        INSERT INTO document_authors (book_id, author_id, author_order)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (book_id, author_id) DO NOTHING
                    """, book["id"], author_id, order)

                    authors_added.append({"name": author_name, "id": author_id, "order": order})

                fixed.append({
                    "book_id": book["id"],
                    "title": book["title"],
                    "legacy_author": book["legacy_author"],
                    "authors_added": authors_added
                })
            except Exception as e:
                errors.append({
                    "book_id": book["id"],
                    "title": book["title"],
                    "error": str(e)
                })

        return {
            "fixed": len(fixed),
            "skipped": len(skipped),
            "errors": len(errors),
            "details": {
                "fixed_books": fixed,
                "skipped_books": skipped,
                "error_books": errors
            }
        }
    finally:
        await conn.close()


# ---- Author URL Bulk Update ----
# Exact matches from export_subset_DMU_v2.xlsm (Excel CMS user table)
EXCEL_EXACT_MATCHES = {
    "Bryan Meyers": "https://www.mcpressonline.com/archive/authors/author/12239",
    "John Boyer": "https://www.mcpressonline.com/archive/authors/author/131246",
    "Kameron Cole": "https://www.mcpressonline.com/archive/authors/author/65940",
    "Thanh Pham": "https://www.mcpressonline.com/archive/authors/author/117558",
}

# Name variants: book author name -> article author name (who already has a URL in DB)
# These are the same person under different name spellings
NAME_VARIANT_COPIES = {
    "Bob Cozzi": "Robert Cozzi",
    "Roger E. Sanders": "Roger Sanders",
    "Ken Milberg": "Kenneth Milberg",
}


@fix_book_authors_router.get("/api/fix-book-authors/update-urls-preview")
async def update_urls_preview():
    """Preview which author URLs will be updated (dry run)."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        will_update = []
        already_has_url = []
        not_found_in_db = []

        # Check exact matches from Excel
        for name, url in EXCEL_EXACT_MATCHES.items():
            row = await conn.fetchrow(
                "SELECT id, name, site_url FROM authors WHERE name = $1", name
            )
            if row:
                if row["site_url"] and row["site_url"].strip():
                    already_has_url.append({
                        "id": row["id"], "name": row["name"],
                        "current_url": row["site_url"], "new_url": url,
                        "source": "excel_exact"
                    })
                else:
                    will_update.append({
                        "id": row["id"], "name": row["name"],
                        "new_url": url, "source": "excel_exact"
                    })
            else:
                not_found_in_db.append({"name": name, "url": url, "source": "excel_exact"})

        # Check name variant copies
        for book_name, article_name in NAME_VARIANT_COPIES.items():
            book_row = await conn.fetchrow(
                "SELECT id, name, site_url FROM authors WHERE name = $1", book_name
            )
            article_row = await conn.fetchrow(
                "SELECT id, name, site_url FROM authors WHERE name = $1", article_name
            )
            if book_row and article_row and article_row["site_url"]:
                if book_row["site_url"] and book_row["site_url"].strip():
                    already_has_url.append({
                        "id": book_row["id"], "name": book_row["name"],
                        "current_url": book_row["site_url"],
                        "new_url": article_row["site_url"],
                        "source": f"name_variant_of_{article_name}"
                    })
                else:
                    will_update.append({
                        "id": book_row["id"], "name": book_row["name"],
                        "new_url": article_row["site_url"],
                        "source": f"name_variant_of_{article_name}"
                    })
            elif not book_row:
                not_found_in_db.append({
                    "name": book_name, "source": f"name_variant_of_{article_name}",
                    "reason": "book author not found in DB"
                })
            elif not article_row or not article_row["site_url"]:
                not_found_in_db.append({
                    "name": book_name, "source": f"name_variant_of_{article_name}",
                    "reason": f"article author '{article_name}' has no URL"
                })

        return {
            "will_update": len(will_update),
            "already_has_url": len(already_has_url),
            "not_found": len(not_found_in_db),
            "updates": will_update,
            "skipped_has_url": already_has_url,
            "skipped_not_found": not_found_in_db
        }
    finally:
        await conn.close()


@fix_book_authors_router.post("/api/fix-book-authors/update-urls")
async def update_urls():
    """Apply author URL updates for exact matches and name variants."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"error": "DATABASE_URL not set"}

    conn = await asyncpg.connect(database_url)
    try:
        updated = []
        skipped = []
        errors = []

        # Apply exact matches from Excel
        for name, url in EXCEL_EXACT_MATCHES.items():
            try:
                row = await conn.fetchrow(
                    "SELECT id, site_url FROM authors WHERE name = $1", name
                )
                if not row:
                    skipped.append({"name": name, "reason": "not found in DB"})
                    continue
                if row["site_url"] and row["site_url"].strip():
                    skipped.append({"name": name, "reason": "already has URL",
                                    "current_url": row["site_url"]})
                    continue
                await conn.execute(
                    "UPDATE authors SET site_url = $1 WHERE id = $2", url, row["id"]
                )
                updated.append({"id": row["id"], "name": name, "url": url,
                                "source": "excel_exact"})
            except Exception as e:
                errors.append({"name": name, "error": str(e)})

        # Apply name variant copies
        for book_name, article_name in NAME_VARIANT_COPIES.items():
            try:
                book_row = await conn.fetchrow(
                    "SELECT id, site_url FROM authors WHERE name = $1", book_name
                )
                article_row = await conn.fetchrow(
                    "SELECT id, site_url FROM authors WHERE name = $1", article_name
                )
                if not book_row:
                    skipped.append({"name": book_name, "reason": "not found in DB"})
                    continue
                if book_row["site_url"] and book_row["site_url"].strip():
                    skipped.append({"name": book_name, "reason": "already has URL",
                                    "current_url": book_row["site_url"]})
                    continue
                if not article_row or not article_row["site_url"]:
                    skipped.append({"name": book_name,
                                    "reason": f"variant '{article_name}' has no URL"})
                    continue
                url = article_row["site_url"]
                await conn.execute(
                    "UPDATE authors SET site_url = $1 WHERE id = $2", url, book_row["id"]
                )
                updated.append({"id": book_row["id"], "name": book_name, "url": url,
                                "source": f"name_variant_of_{article_name}"})
            except Exception as e:
                errors.append({"name": book_name, "error": str(e)})

        return {
            "updated": len(updated),
            "skipped": len(skipped),
            "errors": len(errors),
            "details": {
                "updated_authors": updated,
                "skipped_authors": skipped,
                "error_authors": errors
            }
        }
    finally:
        await conn.close()
