"""
Shared fixtures for the admin-page-audit test suite.

All tests run against the Railway-deployed backend via HTTP.
The Excel file export_subset_DMU_v2.xlsx is the source of truth.
"""

import os
import math
from typing import Optional

import openpyxl
import pytest
import requests


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "https://mcpress-chatbot-staging.up.railway.app"
REQUEST_TIMEOUT = 60  # seconds


# ---------------------------------------------------------------------------
# Typed dict for Excel rows
# ---------------------------------------------------------------------------

class ExcelBookRecord(dict):
    """A single row from the Excel source of truth (dict subclass for easy access)."""
    pass


# ---------------------------------------------------------------------------
# Helper functions (importable by any test module)
# ---------------------------------------------------------------------------

def fetch_document_by_title(
    session: requests.Session,
    api_url: str,
    title: str,
) -> Optional[dict]:
    """Search for a document by exact title. Returns the first match or None."""
    resp = session.get(
        f"{api_url}/admin/documents",
        params={"search": title, "per_page": 10, "page": 1, "refresh": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    for doc in data.get("documents", []):
        if doc.get("title") == title:
            return doc
    return None


def update_metadata(
    session: requests.Session,
    api_url: str,
    filename: str,
    payload: dict,
) -> requests.Response:
    """Update document metadata via PUT /documents/{filename}/metadata."""
    resp = session.put(
        f"{api_url}/documents/{filename}/metadata",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    return resp


def delete_document(
    session: requests.Session,
    api_url: str,
    filename: str,
) -> requests.Response:
    """Delete a document via DELETE /documents/{filename}."""
    resp = session.delete(
        f"{api_url}/documents/{filename}",
        timeout=REQUEST_TIMEOUT,
    )
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def api_url():
    """Base URL for the Railway backend (override with API_URL env var)."""
    return os.environ.get("API_URL", DEFAULT_API_URL)


@pytest.fixture(scope="session")
def api_session(api_url):
    """A requests.Session pre-configured with default timeout."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Smoke-test: make sure the API is reachable
    try:
        resp = s.get(f"{api_url}/health", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        pytest.skip(f"API not reachable at {api_url}: {exc}")
    yield s
    s.close()


@pytest.fixture(scope="session")
def excel_data():
    """
    Load the Excel source of truth and return a list of ExcelBookRecord dicts.

    Only rows where 'Feature Article Y/N' == 'Yes' are included (6,319 rows).
    Each record has: title, author, article_url, author_site_url, document_type.

    Column mapping (0-indexed):
        0  id
        1  title
        2  alias
        3  catid
        4  created_by
        5  created_by_alias
        6  hits
        7  Feature Article Y/N
        8  vLookup catid
        9  vlookup created-by
       10  Article URL
       11  Arthor URL          (note: typo in Excel header)
    """
    excel_path = os.path.join(os.path.dirname(__file__), "..", "export_subset_DMU_v2.xlsx")
    excel_path = os.path.normpath(excel_path)

    wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
    ws = wb["export_subset"]

    records: list[ExcelBookRecord] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Filter: only Feature Articles
        feature_flag = row[7]
        if feature_flag != "Yes":
            continue

        # Author: prefer 'vlookup created-by' (col 9), fall back to 'created_by_alias' (col 5)
        author = row[9] if row[9] is not None else row[5]
        author = str(author) if author is not None else ""

        title = str(row[1]) if row[1] is not None else ""
        article_url = str(row[10]) if row[10] is not None else None
        author_site_url = str(row[11]) if row[11] is not None else None

        records.append(ExcelBookRecord(
            title=title,
            author=author,
            article_url=article_url,
            author_site_url=author_site_url,
            document_type="article",
        ))

    wb.close()
    return records


@pytest.fixture(scope="session")
def all_documents(api_session, api_url):
    """
    Fetch every document from GET /admin/documents by paginating through all pages.

    Returns the full list of document dicts.
    """
    documents: list[dict] = []
    page = 1
    per_page = 100  # max allowed

    while True:
        resp = api_session.get(
            f"{api_url}/admin/documents",
            params={"page": page, "per_page": per_page},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        docs = data.get("documents", [])
        documents.extend(docs)

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return documents


@pytest.fixture(scope="function")
def test_document(api_session, api_url, all_documents):
    """
    Identify a dedicated test document for write tests.

    Picks the first document from the listing and captures its original
    metadata so it can be restored during teardown.
    """
    assert len(all_documents) > 0, "No documents found in the database"

    # Pick a document that is unlikely to be critical — use the last one
    doc = all_documents[-1]
    original = {
        "filename": doc["filename"],
        "title": doc.get("title", ""),
        "author": doc.get("author", ""),
        "category": doc.get("category", ""),
        "mc_press_url": doc.get("mc_press_url", ""),
        "article_url": doc.get("article_url", ""),
    }

    yield doc

    # Teardown: restore original values
    try:
        update_metadata(api_session, api_url, original["filename"], original)
    except Exception:
        pass  # best-effort restore; don't fail teardown
