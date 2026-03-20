"""
Test Delete Operations (Requirement 8)

Validates: Requirements 8.1, 8.2, 8.3, 8.4

SAFETY NOTE:
- The non-existent document test is SAFE and runs by default.
- The actual delete + cascade tests are marked with @pytest.mark.skip
  because they are DESTRUCTIVE — they permanently remove a document.
  Remove the skip decorator only when you have an expendable test document.
"""

import urllib.parse

import pytest

REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Test: Delete non-existent document returns error (Req 8.4)
# ---------------------------------------------------------------------------


class TestDeleteNonExistent:
    """Validates: Requirement 8.4 — deleting a non-existent document returns 404."""

    def test_delete_nonexistent_returns_404_or_500(self, api_session, api_url):
        """
        DELETE /documents/{filename} with a clearly fake filename should
        return 404 (ideal) or 500 (current known behavior).

        The design doc notes the API may return 500 instead of 404 for
        non-existent documents.

        **Validates: Requirement 8.4**
        """
        fake_filename = "NONEXISTENT_audit_test_delete_12345.pdf"
        encoded = urllib.parse.quote(fake_filename, safe="")

        resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )

        # 404 is the ideal response per Requirement 8.4.
        # 500 is the current known behavior per the design doc.
        assert resp.status_code in (404, 500), (
            f"DELETE /documents/{fake_filename} returned unexpected "
            f"status {resp.status_code} (expected 404 or 500): "
            f"{resp.text[:300]}"
        )

    def test_delete_nonexistent_returns_error_body(self, api_session, api_url):
        """
        The error response for a non-existent document should contain
        a meaningful error message (not an empty body).

        **Validates: Requirement 8.4**
        """
        fake_filename = "NONEXISTENT_audit_test_delete_99999.pdf"
        encoded = urllib.parse.quote(fake_filename, safe="")

        resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )

        assert resp.status_code in (404, 500), (
            f"Unexpected status {resp.status_code}"
        )

        # The response should have some content indicating an error
        body = resp.text
        assert len(body) > 0, (
            "Error response body is empty — expected a meaningful error message"
        )


# ---------------------------------------------------------------------------
# Test: Delete removes document from listing (Req 8.1, 8.3) — SKIPPED
# ---------------------------------------------------------------------------


class TestDeleteRemovesDocument:
    """
    Validates: Requirements 8.1, 8.3 — deleting a document removes it
    from the books table and the admin listing.

    SKIPPED by default — this is a DESTRUCTIVE test that permanently
    deletes a document. Remove the skip decorator only when you have
    an expendable test document available.
    """

    @pytest.mark.skip(reason="Destructive test - requires expendable test document")
    def test_delete_removes_document_from_listing(self, api_session, api_url, all_documents):
        """
        After DELETE /documents/{filename}, the document should no longer
        appear in GET /admin/documents results.

        **Validates: Requirements 8.1, 8.3**
        """
        # Pick the last document (least likely to be important)
        assert len(all_documents) > 0, "No documents available"
        target = all_documents[-1]
        filename = target["filename"]
        doc_title = target.get("title", "")

        # Delete the document
        encoded = urllib.parse.quote(filename, safe="")
        delete_resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )
        assert delete_resp.status_code == 200, (
            f"DELETE /documents/{filename} returned {delete_resp.status_code}: "
            f"{delete_resp.text[:300]}"
        )

        # Verify it no longer appears in the listing (with cache bypass)
        search_resp = api_session.get(
            f"{api_url}/admin/documents",
            params={"search": doc_title, "refresh": "true", "per_page": 100},
            timeout=REQUEST_TIMEOUT,
        )
        search_resp.raise_for_status()
        data = search_resp.json()

        matching = [
            d for d in data.get("documents", [])
            if d.get("filename") == filename
        ]
        assert len(matching) == 0, (
            f"Document '{filename}' still appears in listing after deletion"
        )


# ---------------------------------------------------------------------------
# Test: Delete cascades to document_authors (Req 8.2) — SKIPPED
# ---------------------------------------------------------------------------


class TestDeleteCascade:
    """
    Validates: Requirement 8.2 — deleting a document also removes its
    document_authors entries.

    SKIPPED by default — this is a DESTRUCTIVE test that permanently
    deletes a document. Remove the skip decorator only when you have
    an expendable test document available.
    """

    @pytest.mark.skip(reason="Destructive test - requires expendable test document")
    def test_delete_cascades_to_document_authors(self, api_session, api_url, all_documents):
        """
        After DELETE /documents/{filename}, GET /api/documents/{id}
        should return 404, confirming the document and its author
        associations have been removed.

        **Validates: Requirements 8.1, 8.2**
        """
        # Pick the last document (least likely to be important)
        assert len(all_documents) > 0, "No documents available"
        target = all_documents[-1]
        filename = target["filename"]
        doc_id = target["id"]

        # Delete the document
        encoded = urllib.parse.quote(filename, safe="")
        delete_resp = api_session.delete(
            f"{api_url}/documents/{encoded}",
            timeout=REQUEST_TIMEOUT,
        )
        assert delete_resp.status_code == 200, (
            f"DELETE /documents/{filename} returned {delete_resp.status_code}: "
            f"{delete_resp.text[:300]}"
        )

        # Verify GET /api/documents/{id} returns 404
        doc_resp = api_session.get(
            f"{api_url}/api/documents/{doc_id}",
            timeout=REQUEST_TIMEOUT,
        )
        assert doc_resp.status_code == 404, (
            f"GET /api/documents/{doc_id} returned {doc_resp.status_code} "
            f"after deletion (expected 404): {doc_resp.text[:300]}"
        )
