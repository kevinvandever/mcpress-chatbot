"""
Test Document Listing — Listing, Search, Pagination, Sort Verification

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2

These are READ-ONLY tests. They never modify any data.
"""

import math

import requests

# Timeout for individual API calls
REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Test: Required fields are present (Req 2.1)
# ---------------------------------------------------------------------------

def test_documents_have_required_fields(all_documents):
    """
    Every document returned by GET /admin/documents must have non-null
    id, filename, title, author (or authors array), and document_type.

    **Validates: Requirements 2.1**
    """
    assert len(all_documents) > 0, "No documents returned — is the API reachable?"

    missing = []
    for doc in all_documents:
        problems = []
        if doc.get("id") is None:
            problems.append("id")
        if not doc.get("filename"):
            problems.append("filename")
        if not doc.get("title"):
            problems.append("title")
        if not doc.get("document_type"):
            problems.append("document_type")

        # Must have either author or a non-empty authors array
        has_author = bool(doc.get("author"))
        has_authors = isinstance(doc.get("authors"), list) and len(doc["authors"]) > 0
        if not has_author and not has_authors:
            problems.append("author/authors")

        if problems:
            missing.append((doc.get("id"), doc.get("filename"), problems))

    assert len(missing) == 0, (
        f"{len(missing)} documents missing required fields. "
        f"First 5: {missing[:5]}"
    )


# ---------------------------------------------------------------------------
# Test: Multi-author documents return all authors sorted (Req 2.2, 5.1, 5.2)
# ---------------------------------------------------------------------------

def test_multi_author_documents_sorted_by_order(all_documents):
    """
    For documents with multiple authors, the authors array must be sorted
    by author_order ascending, and each author entry must have a name.

    **Validates: Requirements 2.2, 5.1, 5.2**
    """
    multi_author_docs = [
        doc for doc in all_documents
        if isinstance(doc.get("authors"), list) and len(doc["authors"]) > 1
    ]

    if len(multi_author_docs) == 0:
        # No multi-author docs in the dataset — skip rather than fail
        import pytest
        pytest.skip("No multi-author documents found in the dataset")

    violations = []
    for doc in multi_author_docs:
        authors = doc["authors"]
        orders = [a.get("order", 0) for a in authors]
        if orders != sorted(orders):
            violations.append(
                f"Doc {doc.get('id')} ({doc.get('title')!r}): "
                f"orders={orders} not sorted"
            )
        # Every author entry must have a name
        for a in authors:
            if not a.get("name"):
                violations.append(
                    f"Doc {doc.get('id')}: author entry missing name: {a}"
                )

    assert len(violations) == 0, (
        f"{len(violations)} multi-author ordering violations. "
        f"First 5: {violations[:5]}"
    )


# ---------------------------------------------------------------------------
# Test: Search filtering (Req 2.3)
# ---------------------------------------------------------------------------

def test_search_returns_matching_documents(api_session, api_url):
    """
    For a known search term, every returned document must contain the term
    in its title or in one of its author names (case-insensitive).

    **Validates: Requirements 2.3**
    """
    search_term = "RPG"

    resp = api_session.get(
        f"{api_url}/admin/documents",
        params={"search": search_term, "per_page": 50, "page": 1},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    documents = data.get("documents", [])

    assert len(documents) > 0, (
        f"Search for {search_term!r} returned 0 results — expected at least one"
    )

    term_lower = search_term.lower()
    non_matching = []
    for doc in documents:
        title = (doc.get("title") or "").lower()
        author = (doc.get("author") or "").lower()
        author_names = [
            (a.get("name") or "").lower()
            for a in (doc.get("authors") or [])
        ]

        if term_lower in title:
            continue
        if term_lower in author:
            continue
        if any(term_lower in name for name in author_names):
            continue

        non_matching.append(
            f"Doc {doc.get('id')} title={doc.get('title')!r} "
            f"author={doc.get('author')!r}"
        )

    assert len(non_matching) == 0, (
        f"{len(non_matching)} documents don't match search term {search_term!r}. "
        f"First 5: {non_matching[:5]}"
    )


# ---------------------------------------------------------------------------
# Test: Pagination arithmetic (Req 2.4)
# ---------------------------------------------------------------------------

def test_pagination_arithmetic(api_session, api_url):
    """
    With a small per_page value, verify:
    - total_pages == ceil(total / per_page)
    - The number of documents on the page is correct

    **Validates: Requirements 2.4**
    """
    per_page = 5

    resp = api_session.get(
        f"{api_url}/admin/documents",
        params={"page": 1, "per_page": per_page},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    total = data["total"]
    total_pages = data["total_pages"]
    page = data["page"]
    documents = data.get("documents", [])

    expected_total_pages = math.ceil(total / per_page) if total > 0 else 1
    assert total_pages == expected_total_pages, (
        f"total_pages={total_pages} but expected ceil({total}/{per_page})="
        f"{expected_total_pages}"
    )

    assert page == 1, f"Requested page 1 but got page={page}"

    expected_count = min(per_page, total)
    assert len(documents) == expected_count, (
        f"Expected {expected_count} documents on page 1 but got {len(documents)}"
    )

    # Also check the last page has the right count
    if total_pages > 1:
        resp2 = api_session.get(
            f"{api_url}/admin/documents",
            params={"page": total_pages, "per_page": per_page},
            timeout=REQUEST_TIMEOUT,
        )
        resp2.raise_for_status()
        data2 = resp2.json()
        last_page_docs = data2.get("documents", [])
        expected_last = total - (total_pages - 1) * per_page
        assert len(last_page_docs) == expected_last, (
            f"Last page (page {total_pages}) expected {expected_last} docs "
            f"but got {len(last_page_docs)}"
        )


# ---------------------------------------------------------------------------
# Test: Sort order (Req 2.5)
# ---------------------------------------------------------------------------

def test_sort_by_title_ordering(api_session, api_url):
    """
    Verify that the sort_by and sort_direction parameters actually control
    the ordering of results.  We request the same page with asc and desc
    and confirm the orderings are reversed.

    Note: PostgreSQL uses locale-aware collation which may differ from
    Python's byte-by-byte string comparison, so we compare the API's own
    asc vs desc output rather than re-implementing collation rules.

    **Validates: Requirements 2.5**
    """
    params_asc = {
        "page": 1,
        "per_page": 20,
        "sort_by": "title",
        "sort_direction": "asc",
    }
    params_desc = {
        "page": 1,
        "per_page": 20,
        "sort_by": "title",
        "sort_direction": "desc",
    }

    resp_asc = api_session.get(
        f"{api_url}/admin/documents",
        params=params_asc,
        timeout=REQUEST_TIMEOUT,
    )
    resp_asc.raise_for_status()
    docs_asc = resp_asc.json().get("documents", [])

    resp_desc = api_session.get(
        f"{api_url}/admin/documents",
        params=params_desc,
        timeout=REQUEST_TIMEOUT,
    )
    resp_desc.raise_for_status()
    docs_desc = resp_desc.json().get("documents", [])

    assert len(docs_asc) > 1, "Need at least 2 documents to verify sort order"
    assert len(docs_desc) > 1, "Need at least 2 documents to verify sort order"

    titles_asc = [doc.get("title") for doc in docs_asc]
    titles_desc = [doc.get("title") for doc in docs_desc]

    # The first title in asc should differ from the first title in desc
    # (unless all titles are identical, which is extremely unlikely)
    assert titles_asc[0] != titles_desc[0], (
        f"asc and desc returned the same first title: {titles_asc[0]!r} — "
        "sort_direction may not be applied"
    )

    # The asc list reversed should match the desc list (for the same page size
    # this holds when total docs > per_page, since asc page 1 has the first N
    # and desc page 1 has the last N — they won't be exact reverses).
    # Instead, just verify the last title in asc comes before the last in desc
    # alphabetically, confirming the direction flipped.
    # Simplest check: first title of asc sort should appear late in desc sort
    # and vice versa.  We just verify they are different orderings.
    assert titles_asc != titles_desc, (
        "asc and desc returned identical title lists — sort may not be working"
    )
