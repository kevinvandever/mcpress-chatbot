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
