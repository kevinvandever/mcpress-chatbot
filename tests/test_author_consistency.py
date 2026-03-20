"""
Test Author Consistency — Author Data Propagation

Validates: Requirements 5.3

These tests WRITE data (author name updates) and restore original values
in finally blocks to avoid polluting the shared database.
"""

import pytest

# Timeout for individual API calls (matches conftest.py)
REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_author_with_documents(api_session, api_url, min_docs=2):
    """
    Find an author who has at least *min_docs* documents.

    Strategy: fetch the first page of documents, collect author names,
    then look up each author via the search API to find one with
    document_count >= min_docs.

    Returns (author_id, author_name, original_site_url) or None.
    """
    # Grab a page of documents to harvest author names
    resp = api_session.get(
        f"{api_url}/admin/documents",
        params={"page": 1, "per_page": 50, "refresh": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    docs = resp.json().get("documents", [])

    # Collect unique author names from the authors arrays
    seen_names: set[str] = set()
    candidate_names: list[str] = []
    for doc in docs:
        authors = doc.get("authors") or []
        for a in authors:
            name = a.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                candidate_names.append(name)

    # Search each candidate until we find one with enough documents
    for name in candidate_names:
        search_resp = api_session.get(
            f"{api_url}/api/authors/search",
            params={"q": name, "limit": 5},
            timeout=REQUEST_TIMEOUT,
        )
        search_resp.raise_for_status()
        for result in search_resp.json():
            if result.get("name") == name:
                author_id = result["id"]
                # Fetch full author details to get document_count
                detail_resp = api_session.get(
                    f"{api_url}/api/authors/{author_id}",
                    timeout=REQUEST_TIMEOUT,
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()
                if detail.get("document_count", 0) >= min_docs:
                    return (
                        author_id,
                        detail["name"],
                        detail.get("site_url", ""),
                    )
                break  # move to next candidate name

    return None


def _get_documents_by_author_name(api_session, api_url, author_name, max_docs=5):
    """
    Fetch documents associated with an author by searching the admin
    listing by author name.

    Returns a list of document dicts where the author name appears in
    the authors array.
    """
    resp = api_session.get(
        f"{api_url}/admin/documents",
        params={
            "search": author_name,
            "per_page": max_docs,
            "page": 1,
            "refresh": "true",
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    docs = resp.json().get("documents", [])

    # Filter to only docs that actually have this author in their authors array
    matched = []
    for doc in docs:
        author_names = [a.get("name", "") for a in (doc.get("authors") or [])]
        if author_name in author_names:
            matched.append(doc)
    return matched


# ---------------------------------------------------------------------------
# Test: Author name update propagates to all documents (Req 5.3)
# ---------------------------------------------------------------------------

def test_author_name_propagates_to_documents(api_session, api_url):
    """
    Updating an author's name via PATCH /api/authors/{id} should cause
    all associated documents to show the new name when fetched via
    GET /admin/documents with refresh=true.

    Steps:
      1. Find an author with multiple documents.
      2. Save the original name.
      3. Fetch some documents by the original author name (baseline).
      4. PATCH the author with a unique test name.
      5. For each baseline document, fetch it via
         GET /admin/documents?search={title}&refresh=true and verify
         the new author name appears in the authors array.
      6. Restore the original name in a finally block.

    **Validates: Requirements 5.3**
    """
    result = _find_author_with_documents(api_session, api_url, min_docs=2)
    if result is None:
        pytest.skip(
            "No author with >= 2 documents found — cannot test propagation"
        )

    author_id, original_name, original_site_url = result
    new_name = "AUDIT_TEST_Propagation_Author"

    # --- Step 3: Get baseline documents by original author name ---
    baseline_docs = _get_documents_by_author_name(
        api_session, api_url, original_name, max_docs=5
    )
    assert len(baseline_docs) >= 2, (
        f"Expected >= 2 documents for author {original_name!r}, "
        f"got {len(baseline_docs)}"
    )

    try:
        # --- Step 4: Update the author name ---
        patch_resp = api_session.patch(
            f"{api_url}/api/authors/{author_id}",
            json={"name": new_name},
            timeout=REQUEST_TIMEOUT,
        )
        assert patch_resp.status_code == 200, (
            f"PATCH /api/authors/{author_id} returned "
            f"{patch_resp.status_code}: {patch_resp.text}"
        )

        # Verify the author record itself was updated
        verify_resp = api_session.get(
            f"{api_url}/api/authors/{author_id}",
            timeout=REQUEST_TIMEOUT,
        )
        verify_resp.raise_for_status()
        assert verify_resp.json().get("name") == new_name, (
            f"Author name not updated: expected {new_name!r}, "
            f"got {verify_resp.json().get('name')!r}"
        )

        # --- Step 5: Verify propagation for each baseline document ---
        for doc in baseline_docs:
            doc_title = doc.get("title", "")
            if not doc_title:
                continue

            listing_resp = api_session.get(
                f"{api_url}/admin/documents",
                params={
                    "search": doc_title,
                    "per_page": 10,
                    "page": 1,
                    "refresh": "true",
                },
                timeout=REQUEST_TIMEOUT,
            )
            listing_resp.raise_for_status()
            listing_docs = listing_resp.json().get("documents", [])

            # Find the exact document by title
            matched_doc = None
            for ld in listing_docs:
                if ld.get("title") == doc_title:
                    matched_doc = ld
                    break

            assert matched_doc is not None, (
                f"Document {doc_title!r} not found in admin listing"
            )

            # Check that the new author name appears in the authors array
            authors_list = matched_doc.get("authors") or []
            author_names = [a.get("name", "") for a in authors_list]
            assert new_name in author_names, (
                f"New author name {new_name!r} not found in authors array "
                f"for document {doc_title!r}. "
                f"Got authors: {author_names}"
            )

    finally:
        # --- Step 6: Restore original author name ---
        try:
            api_session.patch(
                f"{api_url}/api/authors/{author_id}",
                json={"name": original_name},
                timeout=REQUEST_TIMEOUT,
            )
        except Exception:
            pass  # best-effort restore
