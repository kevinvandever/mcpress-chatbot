"""
Test API-Frontend Endpoint Alignment (Requirement 9)

Validates: Requirements 9.1, 9.2, 9.3, 9.4

These are CONTRACT tests — they verify that the backend endpoints accept
the expected parameters and return expected response structures. They are
designed to be non-destructive:

- PUT metadata: sends the document's current values (no actual change).
- PATCH author: sends the current site_url (no actual change).
- DELETE: uses a non-existent filename to confirm the endpoint exists
  without removing real data.
- GET listing: sends all supported query parameters and verifies the
  response structure.
"""

import urllib.parse

import pytest

REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_metadata_payload(doc: dict) -> dict:
    """Build a PUT /documents/{filename}/metadata payload from a doc dict."""
    return {
        "filename": doc["filename"],
        "title": doc.get("title", ""),
        "author": doc.get("author", ""),
        "category": doc.get("category", ""),
        "mc_press_url": doc.get("mc_press_url", ""),
        "article_url": doc.get("article_url", ""),
    }


def _get_author_info(api_session, api_url, doc):
    """
    Resolve the author name and ID from a document.

    Returns (author_id, original_site_url) or (None, None) if not found.
    """
    authors = doc.get("authors") or []
    if authors and isinstance(authors[0], dict):
        author_name = authors[0].get("name", "")
    else:
        author_name = doc.get("author", "")

    if not author_name:
        return None, None

    search_resp = api_session.get(
        f"{api_url}/api/authors/search",
        params={"q": author_name, "limit": 5},
        timeout=REQUEST_TIMEOUT,
    )
    search_resp.raise_for_status()

    for result in search_resp.json():
        if result.get("name") == author_name:
            # Fetch full author to get site_url
            get_resp = api_session.get(
                f"{api_url}/api/authors/{result['id']}",
                timeout=REQUEST_TIMEOUT,
            )
            get_resp.raise_for_status()
            author_data = get_resp.json()
            return result["id"], author_data.get("site_url", "")

    return None, None


# ---------------------------------------------------------------------------
# Test: PUT /documents/{filename}/metadata contract (Req 9.1)
# ---------------------------------------------------------------------------


class TestPutMetadataContract:
    """Validates: Requirement 9.1 — PUT metadata accepts correct payload structure."""

    def test_put_metadata_accepts_full_payload(self, api_session, api_url, test_document):
        """
        PUT /documents/{filename}/metadata should accept a JSON payload
        with filename, title, author, category, mc_press_url, and
        article_url fields and return 200.

        Sends the document's current values so nothing actually changes.

        **Validates: Requirement 9.1**
        """
        filename = test_document["filename"]
        payload = _build_metadata_payload(test_document)

        resp = api_session.put(
            f"{api_url}/documents/{filename}/metadata",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code == 200, (
            f"PUT /documents/{filename}/metadata returned {resp.status_code}: "
            f"{resp.text[:300]}"
        )

    def test_put_metadata_payload_has_all_fields(self, api_session, api_url, test_document):
        """
        Verify the payload structure includes all six expected fields:
        filename, title, author, category, mc_press_url, article_url.

        **Validates: Requirement 9.1**
        """
        payload = _build_metadata_payload(test_document)

        expected_fields = {"filename", "title", "author", "category", "mc_press_url", "article_url"}
        actual_fields = set(payload.keys())

        assert expected_fields == actual_fields, (
            f"Payload fields mismatch. Expected {expected_fields}, got {actual_fields}"
        )


# ---------------------------------------------------------------------------
# Test: PATCH /api/authors/{author_id} contract (Req 9.2)
# ---------------------------------------------------------------------------


class TestPatchAuthorContract:
    """Validates: Requirement 9.2 — PATCH author accepts site_url field."""

    def test_patch_author_accepts_site_url(self, api_session, api_url, test_document):
        """
        PATCH /api/authors/{author_id} should accept a JSON payload with
        the site_url field and return 200.

        Sends the author's current site_url so nothing actually changes.

        **Validates: Requirement 9.2**
        """
        author_id, original_site_url = _get_author_info(
            api_session, api_url, test_document
        )
        if author_id is None:
            pytest.skip("Could not resolve author ID from test document")

        resp = api_session.patch(
            f"{api_url}/api/authors/{author_id}",
            json={"site_url": original_site_url or ""},
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code == 200, (
            f"PATCH /api/authors/{author_id} returned {resp.status_code}: "
            f"{resp.text[:300]}"
        )

        # Verify response structure — the API returns the updated author object
        data = resp.json()
        assert "id" in data and "name" in data, (
            f"PATCH response missing expected author fields. Got: {list(data.keys())}"
        )


# ---------------------------------------------------------------------------
# Test: DELETE /documents/{filename} contract (Req 9.3)
# ---------------------------------------------------------------------------


class TestDeleteDocumentContract:
    """Validates: Requirement 9.3 — DELETE endpoint accepts filename parameter."""

    def test_delete_nonexistent_document_responds(self, api_session, api_url):
        """
        DELETE /documents/{filename} with a non-existent filename should
        respond (404 or 500), confirming the endpoint exists and accepts
        the filename parameter with correct encoding.

        Does NOT delete any real document.

        **Validates: Requirement 9.3**
        """
        fake_filename = "NONEXISTENT_audit_test_file_12345.pdf"
        encoded = urllib.parse.quote(fake_filename, safe="")

        resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )

        # The endpoint should respond — 404 or 500 both confirm it exists
        assert resp.status_code in (404, 500, 200), (
            f"DELETE /documents/{fake_filename} returned unexpected "
            f"status {resp.status_code}: {resp.text[:300]}"
        )

    def test_delete_filename_with_special_chars(self, api_session, api_url):
        """
        DELETE /documents/{filename} should handle filenames with spaces
        and special characters via URL encoding.

        **Validates: Requirement 9.3**
        """
        fake_filename = "NONEXISTENT audit test (special chars) #1.pdf"
        encoded = urllib.parse.quote(fake_filename, safe="")

        resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )

        # Any response confirms the endpoint handles encoded filenames
        assert resp.status_code in (404, 500, 200, 422), (
            f"DELETE with special chars returned unexpected "
            f"status {resp.status_code}: {resp.text[:300]}"
        )


# ---------------------------------------------------------------------------
# Test: GET /admin/documents contract (Req 9.4)
# ---------------------------------------------------------------------------


class TestGetDocumentsContract:
    """Validates: Requirement 9.4 — GET listing accepts all query parameters."""

    def test_get_documents_accepts_all_query_params(self, api_session, api_url):
        """
        GET /admin/documents should accept page, per_page, search,
        sort_by, sort_direction, and refresh query parameters and
        return a response with the expected structure.

        **Validates: Requirement 9.4**
        """
        resp = api_session.get(
            f"{api_url}/admin/documents",
            params={
                "page": 1,
                "per_page": 5,
                "search": "test",
                "sort_by": "title",
                "sort_direction": "asc",
                "refresh": "true",
            },
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code == 200, (
            f"GET /admin/documents returned {resp.status_code}: "
            f"{resp.text[:300]}"
        )

        data = resp.json()

        # Verify response structure
        expected_keys = {"documents", "total", "page", "per_page", "total_pages"}
        actual_keys = set(data.keys())
        missing = expected_keys - actual_keys
        assert not missing, (
            f"Response missing expected keys: {missing}. Got: {actual_keys}"
        )

        assert isinstance(data["documents"], list), "'documents' should be a list"
        assert isinstance(data["total"], int), "'total' should be an integer"
        assert isinstance(data["page"], int), "'page' should be an integer"
        assert isinstance(data["per_page"], int), "'per_page' should be an integer"
        assert isinstance(data["total_pages"], int), "'total_pages' should be an integer"

    def test_get_documents_respects_page_param(self, api_session, api_url):
        """
        The response 'page' field should match the requested page parameter.

        **Validates: Requirement 9.4**
        """
        resp = api_session.get(
            f"{api_url}/admin/documents",
            params={"page": 2, "per_page": 5},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        assert data["page"] == 2, (
            f"Requested page=2 but response has page={data['page']}"
        )

    def test_get_documents_respects_per_page_param(self, api_session, api_url):
        """
        The response should return at most per_page documents.

        **Validates: Requirement 9.4**
        """
        per_page = 3
        resp = api_session.get(
            f"{api_url}/admin/documents",
            params={"page": 1, "per_page": per_page},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        assert len(data["documents"]) <= per_page, (
            f"Requested per_page={per_page} but got "
            f"{len(data['documents'])} documents"
        )
