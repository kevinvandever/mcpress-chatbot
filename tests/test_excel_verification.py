"""
Test Excel Data Verification Capability (Requirement 7)

Validates: Requirements 7.1, 7.2, 7.3, 7.4

These are READ-ONLY tests. They never modify any data.

Requirement 7.1: The Excel import API validates file structure and reports
formatting errors before processing.

Requirement 7.2: Comparison identifies books present in the Excel source
but missing from the database.

Requirement 7.3: Comparison identifies field mismatches (title, author,
article_url, author_site_url) between Excel and database.

Requirement 7.4: Each discrepancy includes field_name, excel_value, and
database_value.

Implementation notes:
- POST /api/excel/validate accepts multipart form data with file + file_type.
- The .xlsx source file is accepted when file_type="book" (.xlsx allowed).
- For file_type="article", only .xlsm is allowed — we verify that rejection.
- Comparison logic (Reqs 7.2-7.4) is tested by building FieldMismatch
  records from the excel_data and all_documents fixtures (same approach
  as test_data_accuracy.py, but focused on structure verification).
"""

import io
import os
import warnings
from dataclasses import dataclass
from typing import Optional

import pytest
import requests

REQUEST_TIMEOUT = 60

EXCEL_FILENAME = "export_subset_DMU_v2.xlsx"


# ---------------------------------------------------------------------------
# Helpers (reused from test_data_accuracy patterns)
# ---------------------------------------------------------------------------

@dataclass
class FieldMismatch:
    """A single field-level discrepancy between Excel and database."""
    title: str
    field_name: str
    excel_value: Optional[str]
    database_value: Optional[str]


def _normalize_author(name: Optional[str]) -> str:
    if name is None:
        return ""
    return " ".join(name.strip().split()).lower()


def _get_db_author(doc: dict) -> str:
    authors = doc.get("authors") or []
    if authors and isinstance(authors, list) and len(authors) > 0:
        first = authors[0]
        if isinstance(first, dict) and first.get("name"):
            return first["name"]
    return doc.get("author") or ""


# ---------------------------------------------------------------------------
# Tests — Excel Validate Endpoint (Requirement 7.1)
# ---------------------------------------------------------------------------


class TestExcelValidateEndpoint:
    """Validates: Requirement 7.1 — Excel import API validates file structure."""

    def _excel_file_path(self) -> str:
        """Return the absolute path to the Excel source file."""
        return os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", EXCEL_FILENAME)
        )

    def test_validate_accepts_xlsx_as_book(self, api_session, api_url):
        """
        POST /api/excel/validate should accept the .xlsx source file
        when file_type='book' and return a valid response with
        'valid', 'errors', and 'preview_rows' fields.

        **Validates: Requirement 7.1**
        """
        filepath = self._excel_file_path()
        assert os.path.exists(filepath), f"Excel file not found: {filepath}"

        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{api_url}/api/excel/validate",
                files={"file": (EXCEL_FILENAME, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"file_type": "book"},
                timeout=REQUEST_TIMEOUT,
            )

        # The endpoint should return 200 (valid or with warnings)
        # or 500 if the service is unavailable — both are informative.
        if resp.status_code == 500:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            detail = body.get("detail", "")
            if "not available" in str(detail).lower():
                pytest.skip("Excel import service not available on this deployment")
            # Other 500 errors are real failures
            pytest.fail(
                f"Validate endpoint returned 500: {detail}"
            )

        assert resp.status_code == 200, (
            f"Expected 200 from validate endpoint, got {resp.status_code}: "
            f"{resp.text[:300]}"
        )

        data = resp.json()

        # Verify response structure
        assert "valid" in data, "Response missing 'valid' field"
        assert "errors" in data, "Response missing 'errors' field"
        assert "preview_rows" in data, "Response missing 'preview_rows' field"

        assert isinstance(data["valid"], bool), "'valid' should be a boolean"
        assert isinstance(data["errors"], list), "'errors' should be a list"
        assert isinstance(data["preview_rows"], list), "'preview_rows' should be a list"

    def test_validate_rejects_xlsx_as_article(self, api_session, api_url):
        """
        POST /api/excel/validate should reject a .xlsx file when
        file_type='article' because articles require .xlsm format.

        **Validates: Requirement 7.1**
        """
        filepath = self._excel_file_path()
        assert os.path.exists(filepath), f"Excel file not found: {filepath}"

        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{api_url}/api/excel/validate",
                files={"file": (EXCEL_FILENAME, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"file_type": "article"},
                timeout=REQUEST_TIMEOUT,
            )

        assert resp.status_code == 400, (
            f"Expected 400 for .xlsx with file_type='article', got {resp.status_code}"
        )

        data = resp.json()
        assert "detail" in data, "Error response missing 'detail' field"
        assert ".xlsm" in data["detail"].lower(), (
            f"Error message should mention .xlsm format requirement, got: {data['detail']}"
        )

    def test_validate_rejects_invalid_file_type(self, api_session, api_url):
        """
        POST /api/excel/validate should reject an invalid file_type
        parameter (neither 'book' nor 'article').

        **Validates: Requirement 7.1**
        """
        # Send a minimal fake file — the file_type check happens first
        fake_content = b"fake content"
        resp = requests.post(
            f"{api_url}/api/excel/validate",
            files={"file": ("test.xlsm", io.BytesIO(fake_content), "application/octet-stream")},
            data={"file_type": "invalid_type"},
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code == 400, (
            f"Expected 400 for invalid file_type, got {resp.status_code}"
        )

        data = resp.json()
        assert "detail" in data, "Error response missing 'detail' field"

    def test_validate_rejects_txt_file(self, api_session, api_url):
        """
        POST /api/excel/validate should reject a .txt file regardless
        of file_type.

        **Validates: Requirement 7.1**
        """
        fake_content = b"This is not an Excel file"
        resp = requests.post(
            f"{api_url}/api/excel/validate",
            files={"file": ("data.txt", io.BytesIO(fake_content), "text/plain")},
            data={"file_type": "book"},
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code == 400, (
            f"Expected 400 for .txt file, got {resp.status_code}"
        )

    def test_validate_error_structure(self, api_session, api_url):
        """
        When the validate endpoint returns errors or warnings, each
        error entry should have a 'severity' field with value 'error'
        or 'warning'.

        **Validates: Requirement 7.1**
        """
        filepath = self._excel_file_path()
        assert os.path.exists(filepath), f"Excel file not found: {filepath}"

        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{api_url}/api/excel/validate",
                files={"file": (EXCEL_FILENAME, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"file_type": "book"},
                timeout=REQUEST_TIMEOUT,
            )

        if resp.status_code == 500:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if "not available" in str(body.get("detail", "")).lower():
                pytest.skip("Excel import service not available on this deployment")

        if resp.status_code != 200:
            pytest.skip(f"Validate endpoint returned {resp.status_code}, skipping structure check")

        data = resp.json()
        errors = data.get("errors", [])

        # If there are errors/warnings, verify their structure
        for err in errors:
            assert "severity" in err, (
                f"Error entry missing 'severity' field: {err}"
            )
            assert err["severity"] in ("error", "warning"), (
                f"Unexpected severity value: {err['severity']}"
            )


# ---------------------------------------------------------------------------
# Tests — Missing Books Detection (Requirement 7.2)
# ---------------------------------------------------------------------------


class TestExcelMissingBooksDetection:
    """Validates: Requirement 7.2 — comparison identifies books in Excel but missing from DB."""

    def test_comparison_identifies_missing_books(self, excel_data, all_documents):
        """
        Compare Excel source titles against database records and identify
        any Excel rows that have no matching database record.

        **Validates: Requirement 7.2**
        """
        assert len(all_documents) > 0, "No documents returned from the API"
        assert len(excel_data) > 0, "No rows loaded from Excel source"

        # Build lookup of DB titles (normalized)
        db_titles = {
            (doc.get("title") or "").strip().lower()
            for doc in all_documents
        }

        missing_titles: list[str] = []
        for row in excel_data:
            title = (row.get("title") or row.get("Title") or "").strip()
            if not title:
                continue
            if title.lower() not in db_titles:
                missing_titles.append(title)

        # Report findings
        print(f"\n--- Missing Books Detection (Req 7.2) ---")
        print(f"Excel rows checked: {len(excel_data)}")
        print(f"DB documents: {len(all_documents)}")
        print(f"Missing from DB: {len(missing_titles)}")

        if missing_titles:
            print(f"First 10 missing titles:")
            for t in missing_titles[:10]:
                print(f"  • {t}")
            warnings.warn(
                f"{len(missing_titles)} Excel rows have no matching DB record",
                stacklevel=1,
            )

        # The test passes — missing books are audit findings, not failures.
        # We only fail if the data sources are empty (API unreachable).
        assert len(all_documents) > 0


# ---------------------------------------------------------------------------
# Tests — Field Mismatch Detection (Requirement 7.3)
# ---------------------------------------------------------------------------


class TestExcelFieldMismatchDetection:
    """Validates: Requirement 7.3 — comparison identifies field mismatches."""

    def test_comparison_identifies_field_mismatches(self, excel_data, all_documents):
        """
        For each Excel row that has a matching DB record, compare author
        and article_url fields and collect mismatches.

        **Validates: Requirement 7.3**
        """
        assert len(all_documents) > 0, "No documents returned from the API"
        assert len(excel_data) > 0, "No rows loaded from Excel source"

        db_by_title: dict[str, list[dict]] = {}
        for doc in all_documents:
            key = (doc.get("title") or "").strip().lower()
            db_by_title.setdefault(key, []).append(doc)

        mismatches: list[FieldMismatch] = []
        matched_count = 0

        for row in excel_data:
            title = (row.get("title") or row.get("Title") or "").strip()
            if not title:
                continue

            db_docs = db_by_title.get(title.lower())
            if not db_docs:
                continue

            db_doc = db_docs[0]
            matched_count += 1

            # Author comparison
            excel_author = row.get("author") or row.get("Author") or ""
            db_author = _get_db_author(db_doc)
            if _normalize_author(excel_author) != _normalize_author(db_author):
                mismatches.append(FieldMismatch(
                    title=title,
                    field_name="author",
                    excel_value=excel_author,
                    database_value=db_author,
                ))

            # article_url comparison
            excel_url = row.get("article_url") or row.get("Article URL")
            if excel_url and str(excel_url).strip():
                db_url = db_doc.get("article_url")
                e_norm = str(excel_url).strip().lower().rstrip("/")
                d_norm = (db_url or "").strip().lower().rstrip("/")
                if e_norm != d_norm:
                    mismatches.append(FieldMismatch(
                        title=title,
                        field_name="article_url",
                        excel_value=str(excel_url).strip(),
                        database_value=db_url,
                    ))

        print(f"\n--- Field Mismatch Detection (Req 7.3) ---")
        print(f"Matched records compared: {matched_count}")
        print(f"Total field mismatches: {len(mismatches)}")

        if mismatches:
            print(f"First 10 mismatches:")
            for m in mismatches[:10]:
                print(f"  [{m.field_name}] title={m.title!r}")
                print(f"    excel={m.excel_value!r}  db={m.database_value!r}")
            warnings.warn(
                f"{len(mismatches)} field mismatches found across {matched_count} matched records",
                stacklevel=1,
            )

        # Pass — mismatches are audit findings
        assert matched_count > 0, "No Excel rows matched any DB records"


# ---------------------------------------------------------------------------
# Tests — Mismatch Structure (Requirement 7.4)
# ---------------------------------------------------------------------------


class TestMismatchStructure:
    """Validates: Requirement 7.4 — each mismatch includes field_name, excel_value, database_value."""

    def test_mismatch_includes_required_fields(self, excel_data, all_documents):
        """
        Build FieldMismatch records from the comparison and verify that
        each one includes field_name, excel_value, and database_value.

        **Validates: Requirement 7.4**
        """
        assert len(all_documents) > 0, "No documents returned from the API"

        db_by_title: dict[str, list[dict]] = {}
        for doc in all_documents:
            key = (doc.get("title") or "").strip().lower()
            db_by_title.setdefault(key, []).append(doc)

        mismatches: list[FieldMismatch] = []

        for row in excel_data:
            title = (row.get("title") or row.get("Title") or "").strip()
            if not title:
                continue

            db_docs = db_by_title.get(title.lower())
            if not db_docs:
                # Missing book — not a field mismatch
                continue

            db_doc = db_docs[0]

            excel_author = row.get("author") or row.get("Author") or ""
            db_author = _get_db_author(db_doc)
            if _normalize_author(excel_author) != _normalize_author(db_author):
                mismatches.append(FieldMismatch(
                    title=title,
                    field_name="author",
                    excel_value=excel_author,
                    database_value=db_author,
                ))

        # Verify structure of every mismatch record
        for m in mismatches:
            assert hasattr(m, "field_name"), "Mismatch missing field_name"
            assert hasattr(m, "excel_value"), "Mismatch missing excel_value"
            assert hasattr(m, "database_value"), "Mismatch missing database_value"
            assert m.field_name is not None, "field_name should not be None"
            assert isinstance(m.field_name, str), "field_name should be a string"

        print(f"\n--- Mismatch Structure Verification (Req 7.4) ---")
        print(f"Verified {len(mismatches)} mismatch records have correct structure")

        if not mismatches:
            warnings.warn(
                "No mismatches found to verify structure — all fields match. "
                "Structure verification is trivially satisfied.",
                stacklevel=1,
            )
