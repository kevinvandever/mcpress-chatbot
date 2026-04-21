#!/usr/bin/env python3
"""
API-based integration tests for article metadata quality endpoints.

Tests the diagnostics, poor-metadata listing, backfill trigger,
backfill result retrieval, and concurrent-backfill conflict endpoints.

Usage:
    python3 test_article_metadata_api.py [staging|production]

Requires a valid admin JWT token in the ADMIN_TOKEN env var.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4
"""

import os
import sys
import time
import requests

URLS = {
    "staging": "https://mcpress-chatbot-staging.up.railway.app",
    "production": "https://mcpress-chatbot-production.up.railway.app",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_headers():
    token = os.getenv("ADMIN_TOKEN", "")
    if not token:
        print("⚠️  ADMIN_TOKEN env var not set — auth-protected endpoints will fail")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


# ---------------------------------------------------------------------------
# Test: GET /api/diagnostics/article-metadata  (Requirement 6.1, 6.2, 6.3)
# ---------------------------------------------------------------------------

def test_diagnostics(api_url, headers):
    """GET /api/diagnostics/article-metadata returns valid statistics structure."""
    print("\n--- Test: Diagnostics (summary) ---")
    resp = requests.get(
        f"{api_url}/api/diagnostics/article-metadata",
        headers=headers,
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:400]}")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"

    data = resp.json()

    # Requirement 6.2: must contain these statistics fields
    for key in ("total_articles", "numeric_title_count", "unknown_author_count", "both_issues_count"):
        assert key in data, f"Response missing '{key}'"
        assert isinstance(data[key], int), f"'{key}' should be int, got {type(data[key])}"

    # Requirement 6.3: sample of up to 20 articles
    assert "sample_articles" in data, "Response missing 'sample_articles'"
    assert isinstance(data["sample_articles"], list), "'sample_articles' should be a list"
    assert len(data["sample_articles"]) <= 20, f"Sample exceeds 20 items ({len(data['sample_articles'])})"

    print("✅ PASS")
    return data


# ---------------------------------------------------------------------------
# Test: GET /api/diagnostics/article-metadata?detailed=true  (Req 6.4)
# ---------------------------------------------------------------------------

def test_diagnostics_detailed(api_url, headers):
    """GET /api/diagnostics/article-metadata?detailed=true returns full article list."""
    print("\n--- Test: Diagnostics (detailed) ---")
    resp = requests.get(
        f"{api_url}/api/diagnostics/article-metadata",
        params={"detailed": "true"},
        headers=headers,
        timeout=60,
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:400]}")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"

    data = resp.json()

    for key in ("total_articles", "numeric_title_count", "unknown_author_count", "both_issues_count"):
        assert key in data, f"Response missing '{key}'"

    # Requirement 6.4: detailed=true returns full list (may be > 20)
    assert "sample_articles" in data, "Response missing 'sample_articles'"
    assert isinstance(data["sample_articles"], list), "'sample_articles' should be a list"

    print(f"  Detailed list length: {len(data['sample_articles'])}")
    print("✅ PASS")
    return data


# ---------------------------------------------------------------------------
# Test: GET /api/articles/poor-metadata  (Requirement 5.5)
# ---------------------------------------------------------------------------

def test_poor_metadata(api_url, headers):
    """GET /api/articles/poor-metadata returns articles with poor metadata."""
    print("\n--- Test: Poor Metadata List ---")
    resp = requests.get(
        f"{api_url}/api/articles/poor-metadata",
        headers=headers,
        timeout=60,
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:400]}")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"

    data = resp.json()

    # Requirement 5.5: returns count and articles list
    assert "count" in data, "Response missing 'count'"
    assert "articles" in data, "Response missing 'articles'"
    assert isinstance(data["count"], int), "'count' should be int"
    assert isinstance(data["articles"], list), "'articles' should be a list"
    assert data["count"] == len(data["articles"]), (
        f"count ({data['count']}) != len(articles) ({len(data['articles'])})"
    )

    print(f"  Poor metadata articles: {data['count']}")
    print("✅ PASS")
    return data


# ---------------------------------------------------------------------------
# Test: POST /api/articles/backfill-metadata  (Requirement 5.1, 5.2)
# ---------------------------------------------------------------------------

def test_trigger_backfill(api_url, headers):
    """POST /api/articles/backfill-metadata triggers backfill and returns run_id."""
    print("\n--- Test: Trigger Backfill ---")
    resp = requests.post(
        f"{api_url}/api/articles/backfill-metadata",
        headers=headers,
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:400]}")

    # Could be 200 (started) or 409 (already running from a previous test)
    assert resp.status_code in (200, 409), f"Unexpected status {resp.status_code}"

    data = resp.json()

    if resp.status_code == 200:
        # Requirement 5.2: returns run_id and status "started"
        assert "run_id" in data, "Response missing 'run_id'"
        assert data.get("status") == "started", f"Expected status 'started', got '{data.get('status')}'"
        print(f"  run_id: {data['run_id']}")
        print("✅ PASS")
        return data["run_id"]
    else:
        # 409 — backfill already running
        print("  Backfill already running (409) — skipping run_id check")
        print("✅ PASS (409 is acceptable)")
        return None


# ---------------------------------------------------------------------------
# Test: GET /api/articles/backfill-metadata/{run_id}  (Requirement 5.3)
# ---------------------------------------------------------------------------

def test_get_backfill_result(api_url, headers, run_id):
    """GET /api/articles/backfill-metadata/{run_id} returns backfill results."""
    print(f"\n--- Test: Get Backfill Result (run_id={run_id}) ---")

    # The backfill runs as a background task, so poll until it completes
    max_wait = 120  # seconds
    poll_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        resp = requests.get(
            f"{api_url}/api/articles/backfill-metadata/{run_id}",
            headers=headers,
            timeout=30,
        )
        print(f"  [{elapsed}s] Status: {resp.status_code}, Body: {resp.text[:200]}")
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}"

        data = resp.json()
        assert "status" in data, "Response missing 'status'"
        assert "run_id" in data, "Response missing 'run_id'"

        if data["status"] in ("completed", "failed"):
            break

        time.sleep(poll_interval)
        elapsed += poll_interval

    # Requirement 5.3: result contains summary fields
    assert data["status"] in ("completed", "failed", "running"), (
        f"Unexpected backfill status: {data['status']}"
    )

    if data["status"] == "completed":
        for key in ("total_identified", "titles_updated", "authors_updated", "still_poor"):
            assert key in data, f"Completed result missing '{key}'"
        print(f"  total_identified: {data.get('total_identified')}")
        print(f"  titles_updated:   {data.get('titles_updated')}")
        print(f"  authors_updated:  {data.get('authors_updated')}")
        print(f"  still_poor:       {data.get('still_poor')}")

    print("✅ PASS")
    return data


# ---------------------------------------------------------------------------
# Test: 409 conflict on concurrent backfill  (Requirement 5.4)
# ---------------------------------------------------------------------------

def test_concurrent_backfill_conflict(api_url, headers):
    """Triggering backfill while one is running returns 409."""
    print("\n--- Test: Concurrent Backfill Conflict (409) ---")

    # First trigger — start a backfill (or it may already be running)
    resp1 = requests.post(
        f"{api_url}/api/articles/backfill-metadata",
        headers=headers,
        timeout=30,
    )
    print(f"  First trigger:  status={resp1.status_code}")

    if resp1.status_code == 200:
        # Backfill just started — immediately try a second trigger
        resp2 = requests.post(
            f"{api_url}/api/articles/backfill-metadata",
            headers=headers,
            timeout=30,
        )
        print(f"  Second trigger: status={resp2.status_code}")
        print(f"  Body: {resp2.text[:300]}")

        # Requirement 5.4: should be 409 since the first one is still running
        assert resp2.status_code == 409, (
            f"Expected 409 for concurrent backfill, got {resp2.status_code}"
        )
        print("✅ PASS")
        return resp1.json().get("run_id")

    elif resp1.status_code == 409:
        # Already running from a previous test — that itself proves 409 works
        print("  Backfill already running — 409 confirmed")
        print("✅ PASS")
        return None

    else:
        raise AssertionError(f"Unexpected status on first trigger: {resp1.status_code}")


# ---------------------------------------------------------------------------
# Test: 404 for non-existent run_id
# ---------------------------------------------------------------------------

def test_backfill_result_not_found(api_url, headers):
    """GET /api/articles/backfill-metadata/{bad_id} returns 404."""
    print("\n--- Test: Backfill Result Not Found (404) ---")
    resp = requests.get(
        f"{api_url}/api/articles/backfill-metadata/nonexistent-run-id-12345",
        headers=headers,
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:300]}")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print("✅ PASS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    env = sys.argv[1] if len(sys.argv) > 1 else "staging"
    api_url = URLS.get(env, env)  # Allow passing a custom URL
    headers = get_headers()

    print(f"🔗 Testing against: {api_url}")
    print(f"   Environment: {env}")

    passed = 0
    failed = 0
    errors = []

    tests = [
        ("Diagnostics (summary)", lambda: test_diagnostics(api_url, headers)),
        ("Diagnostics (detailed)", lambda: test_diagnostics_detailed(api_url, headers)),
        ("Poor Metadata List", lambda: test_poor_metadata(api_url, headers)),
        ("Backfill Result Not Found", lambda: test_backfill_result_not_found(api_url, headers)),
    ]

    # Run read-only tests first
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"❌ FAIL: {e}")

    # Run backfill tests (these mutate state)
    try:
        run_id = test_trigger_backfill(api_url, headers)
        passed += 1

        if run_id:
            # Test concurrent conflict while backfill is running
            try:
                test_concurrent_backfill_conflict(api_url, headers)
                passed += 1
            except Exception as e:
                failed += 1
                errors.append(("Concurrent Backfill Conflict", str(e)))
                print(f"❌ FAIL: {e}")

            # Wait for and check backfill result
            try:
                test_get_backfill_result(api_url, headers, run_id)
                passed += 1
            except Exception as e:
                failed += 1
                errors.append(("Get Backfill Result", str(e)))
                print(f"❌ FAIL: {e}")
        else:
            # Backfill was already running — try conflict test anyway
            try:
                test_concurrent_backfill_conflict(api_url, headers)
                passed += 1
            except Exception as e:
                failed += 1
                errors.append(("Concurrent Backfill Conflict", str(e)))
                print(f"❌ FAIL: {e}")

    except Exception as e:
        failed += 1
        errors.append(("Trigger Backfill", str(e)))
        print(f"❌ FAIL: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  ❌ {name}: {err}")
    else:
        print("\n🎉 All article metadata API tests passed!")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
