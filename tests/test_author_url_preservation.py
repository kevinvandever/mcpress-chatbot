#!/usr/bin/env python3
"""
Preservation property tests: Verify existing import behavior is unchanged.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests MUST PASS on unfixed code — they establish the baseline behavior
that must be preserved after the fix is applied.
"""

import requests
import sys
import os

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-staging.up.railway.app")
REQUEST_TIMEOUT = 30

# Article-imported authors — these should already have non-NULL site_url
# because the article import path correctly passes author_url (Req 3.2)
ARTICLE_AUTHORS = [
    {"name": "Jim Buck", "id": 7736},
    {"name": "Ted Holt", "id": 8390},
    {"name": "Bob Cozzi", "id": 7767},
]

# Book-only authors with no matching article URL — site_url should be NULL (Req 3.1)
BOOK_ONLY_AUTHORS = [
    {"name": "Dan Riehl", "id": 8393},
    {"name": "Phil Coulthard", "id": 8497},
    {"name": "Doug Pence", "id": 7766},
]


def test_article_authors_have_site_url():
    """
    Verify article-imported authors already have non-NULL site_url.
    The article import path passes author_url to _get_or_create_author_in_transaction().
    This baseline must be preserved after the fix. (Req 3.2)
    """
    for author_info in ARTICLE_AUTHORS:
        response = requests.get(
            f"{API_URL}/api/authors/search",
            params={"q": author_info["name"]},
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Search for '{author_info['name']}' failed: {response.status_code}"
        )
        authors = response.json()
        assert len(authors) > 0, f"Author '{author_info['name']}' not found"

        author = authors[0]
        site_url = author.get("site_url")
        print(f"  Article author '{author['name']}': site_url={site_url}")
        assert site_url is not None, (
            f"Article author '{author['name']}' should have non-NULL site_url "
            f"(set via article import path)"
        )
        assert site_url.startswith("http"), (
            f"Article author '{author['name']}' site_url should be a valid URL, "
            f"got: {site_url}"
        )


def test_book_authors_have_document_associations():
    """
    Verify book authors have correct document associations via document_count.
    The author detail endpoint returns document_count which reflects
    document_authors associations. (Req 3.4)
    """
    for author_info in BOOK_ONLY_AUTHORS:
        response = requests.get(
            f"{API_URL}/api/authors/{author_info['id']}",
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Author detail for '{author_info['name']}' (id={author_info['id']}) "
            f"failed: {response.status_code}"
        )
        author = response.json()
        doc_count = author.get("document_count", 0)
        print(f"  Book author '{author['name']}': document_count={doc_count}")
        assert doc_count > 0, (
            f"Book author '{author['name']}' should have at least 1 document association"
        )


def test_unmatched_authors_have_null_site_url():
    """
    Verify authors with no matching article URL have NULL site_url.
    Book-only authors that don't appear in article data should not
    have fabricated URLs. (Req 3.1)
    """
    for author_info in BOOK_ONLY_AUTHORS:
        response = requests.get(
            f"{API_URL}/api/authors/search",
            params={"q": author_info["name"]},
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == 200, (
            f"Search for '{author_info['name']}' failed: {response.status_code}"
        )
        authors = response.json()
        assert len(authors) > 0, f"Author '{author_info['name']}' not found"

        author = authors[0]
        site_url = author.get("site_url")
        print(f"  Book-only author '{author['name']}': site_url={site_url}")
        assert site_url is None, (
            f"Book-only author '{author['name']}' should have NULL site_url "
            f"(no matching article URL), got: {site_url}"
        )


def test_book_import_endpoint_returns_expected_response():
    """
    Verify the book import endpoint exists and responds correctly.
    GET should return 405 (Method Not Allowed) since it's a POST endpoint.
    This confirms the endpoint is registered and routing works. (Req 3.4, 3.5)
    """
    response = requests.get(
        f"{API_URL}/api/excel/import/books",
        timeout=REQUEST_TIMEOUT,
    )
    print(f"  GET /api/excel/import/books: status={response.status_code}")
    assert response.status_code == 405, (
        f"Expected 405 Method Not Allowed for GET on book import endpoint, "
        f"got: {response.status_code}"
    )


if __name__ == "__main__":
    print(f"Testing against: {API_URL}")
    print("=" * 60)
    print("Preservation property tests (should PASS on unfixed code)")
    print("=" * 60)

    tests = [
        test_article_authors_have_site_url,
        test_book_authors_have_document_associations,
        test_unmatched_authors_have_null_site_url,
        test_book_import_endpoint_returns_expected_response,
    ]

    passed = 0
    failed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        try:
            test()
            passed += 1
            print(f"  ✅ PASSED")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(0 if failed == 0 else 1)
