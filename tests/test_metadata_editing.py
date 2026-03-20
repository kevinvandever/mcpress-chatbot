"""
Test Metadata Editing — Edit Operations and Validation

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 5.4

These tests WRITE data and restore original values in finally blocks.
The ``test_document`` fixture (from conftest.py) picks a document and
restores its metadata on teardown.
"""

# Timeout for individual API calls (matches conftest.py)
REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_metadata_payload(doc: dict, **overrides) -> dict:
    """Build a PUT /documents/{filename}/metadata payload from a doc dict."""
    payload = {
        "filename": doc["filename"],
        "title": overrides.get("title", doc.get("title", "")),
        "author": overrides.get("author", doc.get("author", "")),
        "category": overrides.get("category", doc.get("category", "")),
        "mc_press_url": overrides.get("mc_press_url", doc.get("mc_press_url", "")),
        "article_url": overrides.get("article_url", doc.get("article_url", "")),
    }
    return payload


def _update_metadata(session, api_url, filename, payload):
    """Update document metadata via PUT /documents/{filename}/metadata."""
    return session.put(
        f"{api_url}/documents/{filename}/metadata",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )


def _read_back_document(api_session, api_url, title: str) -> dict | None:
    """Search for a document by title with cache bypass and return it."""
    resp = api_session.get(
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


# ---------------------------------------------------------------------------
# Test: Title round-trip (Req 3.1, 4.1, 4.2, 4.3)
# ---------------------------------------------------------------------------

def test_edit_title_round_trip(api_session, api_url, test_document):
    """
    Edit a document's title via PUT, then read it back via GET with
    refresh=true and verify the new title is returned.

    **Validates: Requirements 3.1, 4.1, 4.2, 4.3**
    """
    filename = test_document["filename"]
    new_title = "AUDIT_TEST_Title_Round_Trip"

    payload = _build_metadata_payload(test_document, title=new_title)
    resp = _update_metadata(api_session, api_url, filename, payload)
    assert resp.status_code == 200, (
        f"PUT metadata returned {resp.status_code}: {resp.text}"
    )

    # Read back with cache bypass
    doc = _read_back_document(api_session, api_url, new_title)
    assert doc is not None, (
        f"Document with title {new_title!r} not found after update"
    )
    assert doc["title"] == new_title, (
        f"Expected title {new_title!r} but got {doc['title']!r}"
    )


# ---------------------------------------------------------------------------
# Test: Author round-trip (Req 3.2, 4.1)
# ---------------------------------------------------------------------------

def test_edit_author_round_trip(api_session, api_url, test_document):
    """
    Edit a document's author via PUT, then read it back and verify.

    **Validates: Requirements 3.2, 4.1**
    """
    filename = test_document["filename"]
    new_author = "AUDIT_TEST_Author_Round_Trip"

    payload = _build_metadata_payload(test_document, author=new_author)
    resp = _update_metadata(api_session, api_url, filename, payload)
    assert resp.status_code == 200, (
        f"PUT metadata returned {resp.status_code}: {resp.text}"
    )

    # Read back — search by original title since we didn't change it
    title = test_document.get("title", "")
    doc = _read_back_document(api_session, api_url, title)
    assert doc is not None, (
        f"Document with title {title!r} not found after author update"
    )
    # The author field or authors array should reflect the change
    db_author = doc.get("author", "")
    assert db_author == new_author, (
        f"Expected author {new_author!r} but got {db_author!r}"
    )


# ---------------------------------------------------------------------------
# Test: mc_press_url round-trip (Req 3.3, 4.1)
# ---------------------------------------------------------------------------

def test_edit_mc_press_url_round_trip(api_session, api_url, test_document):
    """
    Edit a document's mc_press_url via PUT, then read it back and verify.

    **Validates: Requirements 3.3, 4.1**
    """
    filename = test_document["filename"]
    new_url = "https://audit-test-mc-press-url.example.com"

    payload = _build_metadata_payload(test_document, mc_press_url=new_url)
    resp = _update_metadata(api_session, api_url, filename, payload)
    assert resp.status_code == 200, (
        f"PUT metadata returned {resp.status_code}: {resp.text}"
    )

    title = test_document.get("title", "")
    doc = _read_back_document(api_session, api_url, title)
    assert doc is not None, (
        f"Document with title {title!r} not found after mc_press_url update"
    )
    assert doc.get("mc_press_url") == new_url, (
        f"Expected mc_press_url {new_url!r} but got {doc.get('mc_press_url')!r}"
    )


# ---------------------------------------------------------------------------
# Test: article_url round-trip (Req 3.4, 4.1)
# ---------------------------------------------------------------------------

def test_edit_article_url_round_trip(api_session, api_url, test_document):
    """
    Edit a document's article_url via PUT, then read it back and verify.

    **Validates: Requirements 3.4, 4.1**
    """
    filename = test_document["filename"]
    new_url = "https://audit-test-article-url.example.com"

    payload = _build_metadata_payload(test_document, article_url=new_url)
    resp = _update_metadata(api_session, api_url, filename, payload)
    assert resp.status_code == 200, (
        f"PUT metadata returned {resp.status_code}: {resp.text}"
    )

    title = test_document.get("title", "")
    doc = _read_back_document(api_session, api_url, title)
    assert doc is not None, (
        f"Document with title {title!r} not found after article_url update"
    )
    assert doc.get("article_url") == new_url, (
        f"Expected article_url {new_url!r} but got {doc.get('article_url')!r}"
    )



# ---------------------------------------------------------------------------
# Test: author_site_url round-trip via PATCH /api/authors/{id} (Req 3.5, 5.4)
# ---------------------------------------------------------------------------

def test_edit_author_site_url_round_trip(api_session, api_url, test_document):
    """
    Edit an author's site_url via PATCH /api/authors/{id}, then read it
    back via GET /api/authors/{id} and verify.

    Looks up the author ID via the search API using the author name from
    the test_document. Restores the original site_url in a finally block.

    **Validates: Requirements 3.5, 5.4**
    """
    # Get author name from the document's authors array or legacy field
    authors = test_document.get("authors") or []
    if authors and isinstance(authors[0], dict):
        author_name = authors[0].get("name", "")
    else:
        author_name = test_document.get("author", "")
    assert author_name, (
        "test_document has no author name — cannot test author_site_url"
    )

    # Look up author ID via search API
    search_resp = api_session.get(
        f"{api_url}/api/authors/search",
        params={"q": author_name, "limit": 5},
        timeout=REQUEST_TIMEOUT,
    )
    search_resp.raise_for_status()
    search_results = search_resp.json()

    # Find exact match by name
    author_id = None
    for result in search_results:
        if result.get("name") == author_name:
            author_id = result["id"]
            break
    assert author_id is not None, (
        f"Author {author_name!r} not found via search API"
    )

    # Capture original site_url for restoration
    get_resp = api_session.get(
        f"{api_url}/api/authors/{author_id}",
        timeout=REQUEST_TIMEOUT,
    )
    get_resp.raise_for_status()
    original_author = get_resp.json()
    original_site_url = original_author.get("site_url", "")

    new_site_url = "https://audit-test-author-site-url.example.com"

    try:
        # Update via PATCH
        patch_resp = api_session.patch(
            f"{api_url}/api/authors/{author_id}",
            json={"site_url": new_site_url},
            timeout=REQUEST_TIMEOUT,
        )
        assert patch_resp.status_code == 200, (
            f"PATCH /api/authors/{author_id} returned "
            f"{patch_resp.status_code}: {patch_resp.text}"
        )

        # Read back via GET
        verify_resp = api_session.get(
            f"{api_url}/api/authors/{author_id}",
            timeout=REQUEST_TIMEOUT,
        )
        verify_resp.raise_for_status()
        updated_author = verify_resp.json()

        assert updated_author.get("site_url") == new_site_url, (
            f"Expected site_url {new_site_url!r} but got "
            f"{updated_author.get('site_url')!r}"
        )
    finally:
        # Restore original site_url
        try:
            api_session.patch(
                f"{api_url}/api/authors/{author_id}",
                json={"site_url": original_site_url or ""},
                timeout=REQUEST_TIMEOUT,
            )
        except Exception:
            pass  # best-effort restore


# ---------------------------------------------------------------------------
# Test: Empty title rejection (Req 3.6)
# ---------------------------------------------------------------------------

def test_empty_title_rejected(api_session, api_url, test_document):
    """
    Submitting an empty or whitespace-only title via PUT should return
    HTTP 400 and leave the document title unchanged.

    **Validates: Requirements 3.6**
    """
    filename = test_document["filename"]
    original_title = test_document.get("title", "")

    # Test with empty string
    payload_empty = _build_metadata_payload(test_document, title="")
    resp_empty = _update_metadata(api_session, api_url, filename, payload_empty)
    assert resp_empty.status_code == 400, (
        f"Expected 400 for empty title but got {resp_empty.status_code}: "
        f"{resp_empty.text}"
    )

    # Test with whitespace-only string
    payload_ws = _build_metadata_payload(test_document, title="   ")
    resp_ws = _update_metadata(api_session, api_url, filename, payload_ws)
    assert resp_ws.status_code == 400, (
        f"Expected 400 for whitespace title but got {resp_ws.status_code}: "
        f"{resp_ws.text}"
    )

    # Verify the title is unchanged
    doc = _read_back_document(api_session, api_url, original_title)
    assert doc is not None, (
        f"Document with original title {original_title!r} not found — "
        "title may have been overwritten by empty value"
    )
    assert doc["title"] == original_title, (
        f"Title changed to {doc['title']!r} after rejected empty update"
    )
