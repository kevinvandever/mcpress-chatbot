#!/usr/bin/env python3
"""
verify_subscription_access_staging.py
-------------------------------------
API-based staging verification for the multi-contract subscription fix.

Tests three captured customers against the staging login endpoint and checks
that the deleted test endpoint returns 404 and /health is green.

Usage:
    # Set environment variables for customer credentials:
    export CUSTOMER_1_EMAIL="..."   # Dave (multi-contract, customerId 2788838535)
    export CUSTOMER_1_PASSWORD="..."
    export CUSTOMER_2_EMAIL="..."   # Renewed monthly (customerId 2788845447)
    export CUSTOMER_2_PASSWORD="..."
    export CUSTOMER_3_EMAIL="..."   # Lapsed 30-day (customerId 3289420039)
    export CUSTOMER_3_PASSWORD="..."

    python3 verify_subscription_access_staging.py

Environment:
    API_URL - Override staging URL (default: https://mcpress-chatbot-staging.up.railway.app)
"""

import os
import sys
import requests

API_URL = os.getenv("API_URL", "https://mcpress-chatbot-staging.up.railway.app")

# --- Customer definitions (emails come from env vars, never committed) ---

CUSTOMERS = [
    {
        "label": "Dave (multi-contract, customerId 2788838535)",
        "email_env": "CUSTOMER_1_EMAIL",
        "password_env": "CUSTOMER_1_PASSWORD",
        "expected_status_code": 200,
        "expected_subscription_status": "active",
    },
    {
        "label": "Renewed monthly (customerId 2788845447)",
        "email_env": "CUSTOMER_2_EMAIL",
        "password_env": "CUSTOMER_2_PASSWORD",
        "expected_status_code": 200,
        "expected_subscription_status": "active",
    },
    {
        "label": "Lapsed 30-day (customerId 3289420039)",
        "email_env": "CUSTOMER_3_EMAIL",
        "password_env": "CUSTOMER_3_PASSWORD",
        "expected_status_code": 403,
        "expected_subscription_status": None,  # denied, check error field
    },
]


def check_health():
    """Verify /health is green."""
    print("\n" + "=" * 60)
    print("CHECK: GET /health")
    print("=" * 60)
    resp = requests.get(f"{API_URL}/health", timeout=15)
    print(f"  Status: {resp.status_code}")
    data = resp.json()
    print(f"  Body:   {data}")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
    assert data.get("status") == "healthy", f"Unhealthy: {data}"
    print("  ✅ PASS: Health is green")


def check_test_endpoint_removed():
    """Verify POST /api/test/subscription-decision returns 404."""
    print("\n" + "=" * 60)
    print("CHECK: POST /api/test/subscription-decision (expect 404)")
    print("=" * 60)
    resp = requests.post(
        f"{API_URL}/api/test/subscription-decision",
        json={"email": "nobody@example.com"},
        timeout=15,
    )
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 404, (
        f"Test endpoint still alive! Got {resp.status_code}: {resp.text[:200]}"
    )
    print("  ✅ PASS: Test endpoint correctly returns 404 (removed)")


def check_customer_login(customer):
    """POST /api/auth/login for a customer and print results."""
    label = customer["label"]
    email = os.getenv(customer["email_env"])
    password = os.getenv(customer["password_env"])

    print(f"\n{'=' * 60}")
    print(f"CHECK: Login — {label}")
    print(f"{'=' * 60}")

    if not email or not password:
        print(f"  ⚠️  SKIP: {customer['email_env']} or {customer['password_env']} not set")
        return None

    resp = requests.post(
        f"{API_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

    print(f"  Status Code:         {resp.status_code}")
    print(f"  subscription_status: {data.get('subscription_status', 'N/A')}")
    print(f"  error:               {data.get('error', 'N/A')}")
    print(f"  redirect_url:        {data.get('redirect_url', 'N/A')}")

    expected_code = customer["expected_status_code"]
    expected_sub = customer["expected_subscription_status"]

    if resp.status_code == expected_code:
        print(f"  ✅ Status code matches expected ({expected_code})")
    else:
        print(f"  ❌ FAIL: Expected status {expected_code}, got {resp.status_code}")

    if expected_sub and data.get("subscription_status") == expected_sub:
        print(f"  ✅ subscription_status matches expected ('{expected_sub}')")
    elif expected_sub:
        print(f"  ❌ FAIL: Expected subscription_status '{expected_sub}', got '{data.get('subscription_status')}'")

    return resp.status_code


def main():
    print(f"Staging URL: {API_URL}")
    print(f"{'=' * 60}")

    # Infrastructure checks
    check_health()
    check_test_endpoint_removed()

    # Customer login checks
    results = []
    for customer in CUSTOMERS:
        code = check_customer_login(customer)
        results.append((customer["label"], code))

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for label, code in results:
        status = "✅" if code else "⚠️ SKIPPED"
        print(f"  {status} {label}: {code or 'no credentials'}")

    # Check if any customers were skipped
    skipped = [r for r in results if r[1] is None]
    if skipped:
        print(f"\n⚠️  {len(skipped)} customer(s) skipped due to missing env vars.")
        print("   Set CUSTOMER_N_EMAIL and CUSTOMER_N_PASSWORD for each.")

    print("\nDone.")


if __name__ == "__main__":
    main()
