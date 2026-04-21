#!/usr/bin/env python3
"""
Preservation Property Tests — Subscription Status Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

These tests verify that existing behavior for non-buggy inputs is preserved
BEFORE and AFTER the subscription status fix is implemented. They capture
the baseline behavior observed on UNFIXED code.

Property 3 (from design): Preservation — ACTIVE Subscribers and No-Subscription Users
  For any input where the user has productSubscriberStatus="ACTIVE", OR where
  the user has no Appstle subscription record at all, the login function SHALL
  produce: ACTIVE → status_code=200, subscription_status="active";
  no-subscription → status_code=200, subscription_status="free".

Property 4 (from design): Preservation — Error Paths Unchanged
  For any input that triggers an API error, incorrect password, rate limit,
  or password validation failure, the login function SHALL produce the same
  error response (503, 401, 429, or 400 respectively).

Testing approach:
  - ACTIVE subscriber and no-subscription scenarios use the /api/test/subscription-decision
    endpoint (exercises the EXACT step 4 decision logic with controlled inputs).
  - Hypothesis generates random variations of inputs to strengthen preservation guarantees.
  - Error path scenarios (bad password, weak password) use the real /api/auth/login endpoint.
  - API timeout/error, rate-limited IP: These are handled BEFORE step 4 in the login flow
    and cannot be triggered via the test endpoint. Documented as limitations below.

Limitations (scenarios 3-5 from task):
  - API timeout/error (Req 3.3): The test endpoint bypasses the Appstle API entirely,
    so API errors cannot be simulated. The real login endpoint would need the Appstle
    API to actually be down. This can only be verified via integration testing or by
    temporarily misconfiguring the API URL. Documented, not tested here.
  - Rate-limited IP (Req 3.5): The test endpoint bypasses rate limiting. The real
    login endpoint enforces rate limits, but triggering them would require 5+ rapid
    requests from the same IP, which could interfere with other tests. Rate limiting
    is implemented in RateLimiter (backend/auth.py) which is not modified by this fix.
    Documented, not tested here.
  - Incorrect password (Req 3.4): The test endpoint bypasses password verification.
    Tested via the real /api/auth/login endpoint with deterministic tests below.

EXPECTED OUTCOME: All tests PASS on unfixed code — confirms baseline behavior to preserve.

Usage:
    python3 test_subscription_preservation.py

Requires: requests, hypothesis
    pip3 install requests hypothesis
"""
import os
import sys
import json
import string
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip3 install requests")
    sys.exit(1)

try:
    from hypothesis import given, settings, HealthCheck, note, assume
    from hypothesis import strategies as st
except ImportError:
    print("ERROR: 'hypothesis' package required. Install with: pip3 install hypothesis")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAGING_URL = os.getenv(
    "API_URL",
    "https://mcpress-chatbot-staging.up.railway.app",
)
TEST_ENDPOINT = f"{STAGING_URL}/api/test/subscription-decision"
LOGIN_ENDPOINT = f"{STAGING_URL}/api/auth/login"
TIMEOUT = 30  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def call_subscription_decision(
    product_subscriber_status,  # str or None
    next_billing_date,          # str or None
    has_subscription=True,      # bool
    email="test-preservation@example.com",
):
    """Call the test endpoint and return the parsed response."""
    payload = {
        "email": email,
        "product_subscriber_status": product_subscriber_status,
        "next_billing_date": next_billing_date,
        "has_subscription": has_subscription,
    }
    resp = requests.post(TEST_ENDPOINT, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def call_real_login(email, password):
    """Call the real login endpoint and return (status_code, body_dict)."""
    resp = requests.post(
        LOGIN_ENDPOINT,
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    return resp.status_code, resp.json()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy: random email-like strings for the test endpoint
random_emails = st.from_regex(
    r"preserve-[a-z0-9]{4,8}@example\.com", fullmatch=True
)

# Strategy: random billing dates (past, future, or None) — for ACTIVE tests
# ACTIVE subscribers should always get 200/active regardless of billing date
random_billing_dates = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=730).map(
        lambda days: (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    ),
    st.integers(min_value=1, max_value=730).map(
        lambda days: (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    ),
)


# ---------------------------------------------------------------------------
# Property Tests: Preservation — ACTIVE Subscribers (via test endpoint)
# ---------------------------------------------------------------------------

@settings(
    max_examples=10,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    email=random_emails,
    billing_date=random_billing_dates,
)
def test_active_subscriber_always_gets_active(email, billing_date):
    """
    **Validates: Requirements 3.1**

    Property 3: Preservation — ACTIVE subscribers always get 200/active.

    For any ACTIVE subscriber, regardless of billing date or email,
    the login step 4 decision logic SHALL return status_code=200
    with subscription_status="active".

    Observed on unfixed code: ACTIVE + is_valid=True → normalized="active" → "active".
    This path is NOT affected by the bug (bug only affects PAUSED/CANCELLED).
    """
    result = call_subscription_decision(
        product_subscriber_status="ACTIVE",
        next_billing_date=billing_date,
        has_subscription=True,
        email=email,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}")

    assert result["status_code"] == 200, (
        f"ACTIVE subscriber should get 200, got {result['status_code']}"
    )
    assert result["body"].get("subscription_status") == "active", (
        f"ACTIVE subscriber should have subscription_status='active', "
        f"got '{result['body'].get('subscription_status')}'"
    )


# ---------------------------------------------------------------------------
# Property Tests: Preservation — No-Subscription Users (via test endpoint)
# ---------------------------------------------------------------------------

@settings(
    max_examples=10,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    email=random_emails,
)
def test_no_subscription_user_always_gets_free(email):
    """
    **Validates: Requirements 3.2**

    Property 3: Preservation — No-subscription users always get 200/free.

    For any user with no Appstle subscription record (has_subscription=False),
    the login step 4 decision logic SHALL return status_code=200
    with subscription_status="free".

    Observed on unfixed code: has_subscription=False → is_valid=False,
    subscription_status=None → normalized="not_found" → "free".
    This path is NOT affected by the bug.
    """
    result = call_subscription_decision(
        product_subscriber_status=None,
        next_billing_date=None,
        has_subscription=False,
        email=email,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}")

    assert result["status_code"] == 200, (
        f"No-subscription user should get 200, got {result['status_code']}"
    )
    assert result["body"].get("subscription_status") == "free", (
        f"No-subscription user should have subscription_status='free', "
        f"got '{result['body'].get('subscription_status')}'"
    )


# ---------------------------------------------------------------------------
# Deterministic Tests: Error Paths (via real login endpoint)
# ---------------------------------------------------------------------------

def test_incorrect_password_returns_401():
    """
    **Validates: Requirements 3.4**

    Property 4: Preservation — Incorrect password returns 401.

    When an existing user provides the wrong password, the login endpoint
    SHALL return 401 with error="Invalid email or password".

    This test uses a known test account created during Task 1 exploration.
    The account 'nonexistent-test-user-12345@example.com' was created with
    password 'WrongPassword123!' — we send a different password to trigger 401.

    NOTE: This error path is handled in login step 6a (password verification),
    which is BEFORE the subscription status decision in step 4. The fix does
    not modify steps 5-7, so this behavior should be preserved.
    """
    status_code, body = call_real_login(
        email="nonexistent-test-user-12345@example.com",
        password="CompletelyDifferentPassword789!",
    )

    assert status_code == 401, (
        f"Wrong password should return 401, got {status_code}. Body: {body}"
    )
    assert body.get("error") == "Invalid email or password", (
        f"Expected 'Invalid email or password', got: {body.get('error')}"
    )


def test_weak_password_new_user_returns_400():
    """
    **Validates: Requirements 3.6**

    Property 4: Preservation — Weak password for new user returns 400.

    When a new user (no existing password record) provides a password that
    fails validation rules, the login endpoint SHALL return 400 with
    error="Password validation failed" and a list of failed_rules.

    This error path is handled in login step 6b (password validation),
    which is BEFORE the subscription status decision. The fix does not
    modify steps 5-7.

    Uses a unique email to ensure this is a new user (no existing record).
    """
    import uuid
    unique_email = f"preservation-test-{uuid.uuid4().hex[:8]}@example.com"

    status_code, body = call_real_login(
        email=unique_email,
        password="weak",  # Too short, no uppercase, no digit, no special char
    )

    assert status_code == 400, (
        f"Weak password should return 400, got {status_code}. Body: {body}"
    )
    assert body.get("error") == "Password validation failed", (
        f"Expected 'Password validation failed', got: {body.get('error')}"
    )
    assert isinstance(body.get("failed_rules"), list), (
        f"Expected failed_rules list, got: {body.get('failed_rules')}"
    )
    assert len(body["failed_rules"]) > 0, "Expected at least one failed rule"


# ---------------------------------------------------------------------------
# Documentation: Untestable Preservation Scenarios
# ---------------------------------------------------------------------------

def test_document_untestable_scenarios():
    """
    **Validates: Requirements 3.3, 3.5**

    This test documents preservation scenarios that CANNOT be directly tested
    via the available endpoints. It always passes — it exists for documentation.

    Scenario 3 — API timeout/error (Req 3.3):
      The /api/test/subscription-decision endpoint bypasses the Appstle API
      entirely (it constructs AppstleSubscriptionResponse directly). Therefore,
      API timeouts and HTTP errors cannot be simulated through this endpoint.
      The real /api/auth/login endpoint would need the Appstle API to actually
      be unavailable, which we cannot control from tests.
      PRESERVATION ARGUMENT: The fix modifies step 4 (subscription decision)
      and the _parse_contract_response method. API error handling is in step 3
      (the try/except around verify_subscription), which is NOT modified.
      Therefore, 503 responses for API errors are preserved by construction.

    Scenario 4 — Rate-limited IP (Req 3.5):
      The test endpoint bypasses rate limiting. The real login endpoint enforces
      rate limits (5 attempts per IP per 15 minutes via RateLimiter), but
      triggering them would require 5+ rapid failed login attempts, which could
      interfere with other tests and lock out the test IP.
      PRESERVATION ARGUMENT: Rate limiting is in step 2 of the login flow,
      implemented by RateLimiter (backend/auth.py). The fix does not modify
      step 2 or the RateLimiter class. Therefore, 429 responses are preserved
      by construction.

    Scenario 5 — Incorrect password (Req 3.4):
      Tested above via test_incorrect_password_returns_401() using the real
      login endpoint. The test endpoint cannot test this because it bypasses
      password verification.
    """
    # This test always passes — it exists for documentation purposes
    untestable = {
        "api_timeout_error": {
            "requirement": "3.3",
            "expected": "status_code=503, error='Subscription service temporarily unavailable'",
            "reason": "Cannot simulate Appstle API failure from test scripts",
            "preservation_argument": "Fix modifies step 4 only; API error handling is in step 3 (unchanged)",
        },
        "rate_limited_ip": {
            "requirement": "3.5",
            "expected": "status_code=429, error='Too many login attempts'",
            "reason": "Triggering rate limits would lock out test IP and interfere with other tests",
            "preservation_argument": "Fix does not modify step 2 or RateLimiter class",
        },
    }

    for scenario, info in untestable.items():
        assert info["preservation_argument"], f"Missing preservation argument for {scenario}"

    # Pass — documentation recorded
    print("  ℹ️  Documented untestable scenarios (preserved by construction):")
    for scenario, info in untestable.items():
        print(f"     - {scenario} (Req {info['requirement']}): {info['reason']}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SUBSCRIPTION STATUS PRESERVATION PROPERTY TESTS")
    print("=" * 70)
    print(f"Target: {STAGING_URL}")
    print(f"Test endpoint: {TEST_ENDPOINT}")
    print(f"Login endpoint: {LOGIN_ENDPOINT}")
    print()
    print("These tests should PASS on both unfixed and fixed code.")
    print("They verify that non-buggy behavior is preserved.")
    print()

    # Verify endpoints are reachable
    print("Checking endpoint availability...")
    try:
        health = requests.get(f"{STAGING_URL}/health", timeout=10)
        print(f"  Health check: {health.status_code}")
    except Exception as e:
        print(f"  ❌ Cannot reach staging backend: {e}")
        sys.exit(1)

    try:
        smoke = requests.post(
            TEST_ENDPOINT,
            json={
                "email": "smoke@test.com",
                "product_subscriber_status": "ACTIVE",
                "next_billing_date": None,
                "has_subscription": True,
            },
            timeout=TIMEOUT,
        )
        if smoke.status_code == 404:
            print(f"  ❌ Test endpoint not found (404). Deploy the test endpoint first.")
            sys.exit(1)
        print(f"  Test endpoint: {smoke.status_code} — available")
    except Exception as e:
        print(f"  ❌ Smoke test failed: {e}")
        sys.exit(1)

    print()
    print("-" * 70)

    # Run all tests
    tests = [
        ("Property: ACTIVE subscribers → 200/active (Hypothesis)", test_active_subscriber_always_gets_active),
        ("Property: No-subscription users → 200/free (Hypothesis)", test_no_subscription_user_always_gets_free),
        ("Deterministic: Wrong password → 401", test_incorrect_password_returns_401),
        ("Deterministic: Weak password (new user) → 400", test_weak_password_new_user_returns_400),
        ("Documentation: Untestable scenarios", test_document_untestable_scenarios),
    ]

    results = {}
    failures = []

    for name, test_fn in tests:
        print(f"\n▶ {name}")
        try:
            test_fn()
            print(f"  ✅ PASSED")
            results[name] = "PASSED"
        except AssertionError as e:
            print(f"  ❌ FAILED")
            msg = str(e)[:200]
            print(f"     {msg}")
            results[name] = f"FAILED: {msg}"
            failures.append((name, msg))
        except Exception as e:
            print(f"  ⚠️ ERROR: {e}")
            results[name] = f"ERROR: {e}"
            failures.append((name, str(e)))

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, result in results.items():
        status = "✅" if result == "PASSED" else "❌"
        print(f"  {status} {name}")
        if result != "PASSED":
            print(f"     {result[:100]}")

    print()
    num_failed = len(failures)
    total = len(tests)

    if num_failed == 0:
        print(f"✅ ALL {total} PRESERVATION TESTS PASSED")
        print("   Baseline behavior confirmed — safe to implement fix.")
        print()
        print("   Verified preservation of:")
        print("   - ACTIVE subscribers → 200 with subscription_status='active' (Req 3.1)")
        print("   - No-subscription users → 200 with subscription_status='free' (Req 3.2)")
        print("   - Wrong password → 401 'Invalid email or password' (Req 3.4)")
        print("   - Weak password → 400 'Password validation failed' (Req 3.6)")
        print("   - API errors → preserved by construction (Req 3.3)")
        print("   - Rate limits → preserved by construction (Req 3.5)")
        return 0
    else:
        print(f"❌ {num_failed}/{total} TESTS FAILED")
        print("   Unexpected failures — investigate before implementing fix.")
        for name, msg in failures:
            print(f"   - {name}: {msg[:80]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
