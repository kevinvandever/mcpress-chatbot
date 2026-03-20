#!/usr/bin/env python3
"""
API-based integration test for auto content ingestion endpoints.

Usage:
    python3 test_ingestion_api.py [staging|production]

Requires a valid admin JWT token in the ADMIN_TOKEN env var.
"""

import os
import sys
import requests

URLS = {
    "staging": "https://mcpress-chatbot-staging.up.railway.app",
    "production": "https://mcpress-chatbot-production.up.railway.app",
}


def get_headers():
    token = os.getenv("ADMIN_TOKEN", "")
    if not token:
        print("⚠️  ADMIN_TOKEN env var not set — auth-protected endpoints will fail")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def test_trigger(api_url, headers):
    """POST /api/ingestion/trigger — expect 200 (started) or 409 (already running)."""
    print("\n--- Test: Trigger Ingestion ---")
    resp = requests.post(f"{api_url}/api/ingestion/trigger", headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:300]}")
    assert resp.status_code in (200, 409), f"Unexpected status {resp.status_code}"
    print("✅ PASS")
    return resp.status_code


def test_status(api_url, headers):
    """GET /api/ingestion/status — expect 200 with status field."""
    print("\n--- Test: Get Status ---")
    resp = requests.get(f"{api_url}/api/ingestion/status", headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:300]}")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"
    data = resp.json()
    assert "status" in data or "run_id" in data, "Response missing status/run_id"
    print("✅ PASS")


def test_history(api_url, headers):
    """GET /api/ingestion/history — expect 200 with runs list."""
    print("\n--- Test: Get History ---")
    resp = requests.get(
        f"{api_url}/api/ingestion/history", params={"limit": 5}, headers=headers, timeout=30
    )
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:300]}")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"
    data = resp.json()
    assert "runs" in data, "Response missing 'runs' key"
    print("✅ PASS")


def test_duplicate_trigger(api_url, headers):
    """POST /api/ingestion/trigger again — expect 409 if first trigger started a run."""
    print("\n--- Test: Duplicate Trigger (expect 409) ---")
    resp = requests.post(f"{api_url}/api/ingestion/trigger", headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:300]}")
    # Could be 409 (already running) or 200 (previous run finished fast)
    assert resp.status_code in (200, 409), f"Unexpected status {resp.status_code}"
    print("✅ PASS")


def main():
    env = sys.argv[1] if len(sys.argv) > 1 else "staging"
    api_url = URLS.get(env, env)  # Allow passing a custom URL
    headers = get_headers()

    print(f"🔗 Testing against: {api_url}")

    first_status = test_trigger(api_url, headers)
    test_status(api_url, headers)
    test_history(api_url, headers)
    if first_status == 200:
        test_duplicate_trigger(api_url, headers)

    print("\n🎉 All ingestion API tests passed!")


if __name__ == "__main__":
    main()
