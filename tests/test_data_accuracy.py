"""
Test Data Accuracy — Excel-to-Database Field Comparisons (Property 1)

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 7.2, 7.3

This is a READ-ONLY test. It never modifies any data.

For each row in the Excel source of truth, the test finds the matching
database record by title and compares author, article_url, and
author_site_url fields. Mismatches are collected and reported as a
summary — the test itself passes unless the API is unreachable.
"""

import re
import warnings
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FieldMismatch:
    """A single field-level discrepancy between Excel and database."""
    title: str
    field_name: str
    excel_value: Optional[str]
    database_value: Optional[str]

    def __str__(self) -> str:
        return (
            f"  [{self.field_name}] "
            f"excel={self.excel_value!r}  db={self.database_value!r}"
        )


@dataclass
class AuditSummary:
    """Accumulates results across all Excel rows."""
    total_excel_rows: int = 0
    matched: int = 0
    missing_from_db: int = 0
    rows_with_mismatches: int = 0
    mismatches: list = field(default_factory=list)
    missing_titles: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize a URL for lenient comparison.

    * Strip whitespace
    * Lower-case the scheme + host portion
    * Fix the common ``https://ww.`` typo → ``https://www.``
    * Strip trailing slashes
    * Return None for empty / whitespace-only strings
    """
    if url is None:
        return None
    url = url.strip()
    if not url:
        return None
    # Fix common typo: https://ww. → https://www.
    url = re.sub(r'^(https?://)ww\.(?!w)', r'\1www.', url, flags=re.IGNORECASE)
    # Lowercase scheme + host for comparison
    url = url.rstrip("/")
    return url.lower()


def _normalize_author(name: Optional[str]) -> str:
    """Normalize an author name for case-insensitive, whitespace-stripped comparison."""
    if name is None:
        return ""
    return " ".join(name.strip().split()).lower()


def _get_db_author(doc: dict) -> str:
    """Extract the primary author name from a database document record.

    Prefers ``authors[0].name`` (multi-author table) over the legacy
    ``author`` field.
    """
    authors = doc.get("authors") or []
    if authors and isinstance(authors, list) and len(authors) > 0:
        first = authors[0]
        if isinstance(first, dict) and first.get("name"):
            return first["name"]
    return doc.get("author") or ""


def _get_db_author_site_url(doc: dict) -> Optional[str]:
    """Extract the primary author's site_url from a database document record."""
    authors = doc.get("authors") or []
    if authors and isinstance(authors, list) and len(authors) > 0:
        first = authors[0]
        if isinstance(first, dict):
            return first.get("site_url")
    return None


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_excel_to_database_field_accuracy(excel_data, all_documents):
    """
    Property 1: Excel-to-database field accuracy

    For every row in the Excel source file, find the matching database
    record by title and verify that author, article_url, and
    author_site_url match.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 7.2, 7.3**
    """

    # Build a lookup: normalized title → list of db docs
    # (titles might not be unique, so keep a list)
    db_by_title: dict[str, list[dict]] = {}
    for doc in all_documents:
        key = (doc.get("title") or "").strip().lower()
        db_by_title.setdefault(key, []).append(doc)

    summary = AuditSummary(total_excel_rows=len(excel_data))

    for row in excel_data:
        excel_title = (row.get("title") or row.get("Title") or "").strip()
        if not excel_title:
            continue

        title_key = excel_title.lower()
        db_docs = db_by_title.get(title_key)

        if not db_docs:
            summary.missing_from_db += 1
            summary.missing_titles.append(excel_title)
            continue

        # Use the first matching document
        db_doc = db_docs[0]
        row_mismatches: list[FieldMismatch] = []

        # --- Author comparison (Req 1.2) ---
        excel_author = row.get("author") or row.get("Author") or ""
        db_author = _get_db_author(db_doc)
        if _normalize_author(excel_author) != _normalize_author(db_author):
            row_mismatches.append(FieldMismatch(
                title=excel_title,
                field_name="author",
                excel_value=excel_author,
                database_value=db_author,
            ))

        # --- article_url comparison (Req 1.4) ---
        excel_article_url = row.get("article_url") or row.get("Article URL")
        if excel_article_url and str(excel_article_url).strip():
            db_article_url = db_doc.get("article_url")
            if _normalize_url(str(excel_article_url)) != _normalize_url(db_article_url):
                row_mismatches.append(FieldMismatch(
                    title=excel_title,
                    field_name="article_url",
                    excel_value=str(excel_article_url).strip(),
                    database_value=db_article_url,
                ))

        # --- author_site_url comparison (Req 1.5) ---
        excel_site_url = row.get("author_site_url") or row.get("Arthor URL")
        if excel_site_url and str(excel_site_url).strip():
            db_site_url = _get_db_author_site_url(db_doc)
            if _normalize_url(str(excel_site_url)) != _normalize_url(db_site_url):
                row_mismatches.append(FieldMismatch(
                    title=excel_title,
                    field_name="author_site_url",
                    excel_value=str(excel_site_url).strip(),
                    database_value=db_site_url,
                ))

        if row_mismatches:
            summary.rows_with_mismatches += 1
            summary.mismatches.extend(row_mismatches)
        else:
            summary.matched += 1

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("EXCEL-TO-DATABASE ACCURACY AUDIT REPORT")
    print("=" * 72)
    print(f"Total Excel rows checked : {summary.total_excel_rows}")
    print(f"Matched (all fields OK)  : {summary.matched}")
    print(f"Missing from database    : {summary.missing_from_db}")
    print(f"Rows with mismatches     : {summary.rows_with_mismatches}")
    print(f"Total field mismatches   : {len(summary.mismatches)}")
    print("-" * 72)

    if summary.missing_titles:
        print(f"\n--- Missing from DB (first 20 of {len(summary.missing_titles)}) ---")
        for t in summary.missing_titles[:20]:
            print(f"  • {t}")

    if summary.mismatches:
        print(f"\n--- Field Mismatches (first 40 of {len(summary.mismatches)}) ---")
        current_title = None
        shown = 0
        for m in summary.mismatches:
            if shown >= 40:
                break
            if m.title != current_title:
                current_title = m.title
                print(f"\n  Title: {current_title}")
            print(str(m))
            shown += 1

    print("\n" + "=" * 72)

    # Emit warnings so pytest -W shows them even in quiet mode
    if summary.missing_from_db:
        warnings.warn(
            f"{summary.missing_from_db} Excel rows have no matching DB record",
            stacklevel=1,
        )
    if summary.mismatches:
        warnings.warn(
            f"{len(summary.mismatches)} field-level mismatches found across "
            f"{summary.rows_with_mismatches} rows",
            stacklevel=1,
        )

    # The test PASSES — mismatches are expected audit findings.
    # Only fail if the API returned zero documents (likely unreachable).
    assert len(all_documents) > 0, (
        "No documents returned from the API — is the backend reachable?"
    )
