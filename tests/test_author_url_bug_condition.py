#!/usr/bin/env python3
"""
Bug condition exploration test: Book authors missing site_url during import

**Validates: Requirements 1.1, 1.2, 1.3**

Bug Condition: author.name IN article_excel_mapping AND author was created/updated
via import_book_metadata() → author.site_url should be non-NULL but is NULL.

This test MUST FAIL on unfixed code — failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
"""

import requests
import sys
import os

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-staging.up.railway.app")

# Known book author who also has a URL in article Excel data (one of the 37 matches)
TEST_AUTHOR_NAME = "Jim Buck"

# Timeout for API calls
REQUEST_TIMEOUT = 30


def test_book_author_has_site_url():
    """
    Bug Condition: isBugCondition(author) = author.name IN article_excel_mapping
                   AND author was created/updated via import_book_metadata()
    Expected Behavior: expectedBehavior(author) = author.site_url == article_excel_mapping[author.name]
                       (non-NULL, matching the article data)

    This test MUST FAIL on unfixed code — failure confirms the bug exists.
    """
    # Search for Jim Buck — a known book author who also has a URL in article data
    response = requests.get(
        f"{API_URL}/api/authors/search",
        params={"q": TEST_AUTHOR_NAME},
        timeout=REQUEST_TIMEOUT,
    )
    assert response.status_code == 200, f"Search failed: {response.status_code}"

    authors = response.json()
    assert len(authors) > 0, f"Author '{TEST_AUTHOR_NAME}' not found in database"

    author = authors[0]
    print(f"Author: {author['name']}")
    print(f"site_url: {author.get('site_url')}")

    # This assertion should FAIL on unfixed code (site_url will be NULL)
    assert author.get("site_url") is not None, (
        f"BUG CONFIRMED: Author '{author['name']}' has site_url=NULL "
        f"despite having URL in article Excel data"
    )
    print("PASS: Author has non-NULL site_url")


if __name__ == "__main__":
    print(f"Testing against: {API_URL}")
    print(f"Looking up author: {TEST_AUTHOR_NAME}")
    print("-" * 60)
    try:
        test_book_author_has_site_url()
        print("\n✅ All bug condition tests PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Bug condition test FAILED (expected on unfixed code): {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Bug condition test FAILED (expected on unfixed code): {e}")
        sys.exit(1)
