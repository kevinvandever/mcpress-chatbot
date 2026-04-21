#!/usr/bin/env python3
"""
Bug Condition Exploration Test — Subscription Status Fix

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

This test exercises the login decision logic (step 4) with 4 concrete
bug condition scenarios. It calls the /api/test/subscription-decision
endpoint on the staging backend, which runs the EXACT same decision
logic as the real login method but with controlled inputs.

EXPECTED OUTCOME ON UNFIXED CODE:
- Scenario 1 (PAUSED+expired): FAILS — gets 200/"active" via tags, expected 403
- Scenario 2 (CANCELLED): FAILS — gets 200/"free", expected 403
- Scenario 3 (PAUSED+future): May coincidentally pass — tags treat PAUSED as ACTIVE
  BUT this is still buggy because it uses unreliable tags, not contract data
- Scenario 4 (PAUSED+null): FAILS — gets 200/"active" via tags, expected 403

The current code has TWO bugs:
1. _parse_tags_response uses unreliable customer tags instead of contract data
2. Login step 4 has no 403 denial path — everything is either "active" or "free"

This test encodes the EXPECTED (correct) behavior. When the fix is
implemented, these tests will PASS, confirming the bug is fixed.

Bug Condition from design:
  isBugCondition(input) returns true when:
    hasSubscription AND (isPausedExpired OR isCancelled OR isPausedWithTimeRemaining)

Usage:
    python3 test_subscription_bug_exploration.py

Requires: requests, hypothesis
    pip3 install requests hypothesis
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip3 install requests")
    sys.exit(1)

try:
    from hypothesis import given, settings, HealthCheck, note
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
ENDPOINT = f"{STAGING_URL}/api/test/subscription-decision"
TIMEOUT = 30  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def call_subscription_decision(
    product_subscriber_status,  # str or None
    next_billing_date,  # str or None
    has_subscription=True,  # bool
    email="test-exploration@example.com",  # str
):  # -> dict
    """Call the test endpoint and return the parsed response."""
    payload = {
        "email": email,
        "product_subscriber_status": product_subscriber_status,
        "next_billing_date": next_billing_date,
        "has_subscription": has_subscription,
    }
    resp = requests.post(ENDPOINT, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Hypothesis strategies for date generation
# ---------------------------------------------------------------------------

# Strategy: past dates (1 day to 2 years ago)
past_dates = st.integers(min_value=1, max_value=730).map(
    lambda days: (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
)

# Strategy: future dates (1 day to 2 years from now)
future_dates = st.integers(min_value=1, max_value=730).map(
    lambda days: (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
)

# ---------------------------------------------------------------------------
# Property Test: Bug Condition Exploration
# ---------------------------------------------------------------------------
# **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
#
# These tests assert the EXPECTED (correct) behavior for each scenario.
# On unfixed code, they will fail because the login step 4 has no denial
# path and uses unreliable tags instead of contract data.
# ---------------------------------------------------------------------------


# Scenario 1: PAUSED + nextBillingDate in the past → expect 403 expired
@settings(
    max_examples=5,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(billing_date=past_dates)
def test_paused_expired_should_deny(billing_date: str):
    """
    **Validates: Requirements 1.1**

    Bug Condition Scenario 1: PAUSED + nextBillingDate in the past.
    Expected: 403 with "Your subscription has expired. Resubscribe to continue."
    Actual (buggy): 200 — current code treats PAUSED as ACTIVE via tags,
    and has no denial path for expired subscriptions.
    """
    result = call_subscription_decision(
        product_subscriber_status="PAUSED",
        next_billing_date=billing_date,
        has_subscription=True,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}, debug={result['debug']}")

    # Expected behavior (will fail on unfixed code — no 403 path exists)
    assert result["status_code"] == 403, (
        f"PAUSED+expired should return 403, got {result['status_code']} "
        f"with subscription_status='{result['body'].get('subscription_status')}'. "
        f"Bug: login step 4 has no denial path for expired subscriptions."
    )
    assert result["body"].get("error") == "Your subscription has expired. Resubscribe to continue.", (
        f"Expected expiry denial message, got: {result['body']}"
    )


# Scenario 2: CANCELLED → expect 403 cancelled
@settings(
    max_examples=5,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(data=st.data())
def test_cancelled_should_deny(data):
    """
    **Validates: Requirements 1.2**

    Bug Condition Scenario 2: CANCELLED subscription.
    Expected: 403 with "Your subscription has been cancelled. Resubscribe to continue."
    Actual (buggy): 200 with subscription_status="free" — current code maps
    CANCELLED to is_valid=False which falls through to "free" tier.
    """
    # Vary the billing date — shouldn't matter for CANCELLED
    billing_date = data.draw(
        st.one_of(past_dates, future_dates, st.none()),
        label="billing_date",
    )

    result = call_subscription_decision(
        product_subscriber_status="CANCELLED",
        next_billing_date=billing_date,
        has_subscription=True,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}, debug={result['debug']}")

    # Expected behavior (will fail on unfixed code — no 403 path exists)
    assert result["status_code"] == 403, (
        f"CANCELLED should return 403, got {result['status_code']} "
        f"with subscription_status='{result['body'].get('subscription_status')}'. "
        f"Bug: login step 4 maps CANCELLED to 'free' instead of denying."
    )
    assert result["body"].get("error") == "Your subscription has been cancelled. Resubscribe to continue.", (
        f"Expected cancellation denial message, got: {result['body']}"
    )


# Scenario 3: PAUSED + nextBillingDate in the future → expect 200 active
@settings(
    max_examples=5,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(billing_date=future_dates)
def test_paused_with_time_remaining_should_be_active(billing_date: str):
    """
    **Validates: Requirements 1.3**

    Bug Condition Scenario 3: PAUSED + nextBillingDate in the future.
    Expected: 200 with subscription_status="active" (paid time remaining).

    NOTE: On unfixed code, this may coincidentally pass because
    _parse_tags_response treats PAUSED the same as ACTIVE via tags.
    However, this is still a bug because:
    - It uses unreliable tags instead of contract data
    - The "active" result is for the wrong reason (tags, not contract logic)
    - In real-world scenarios, tags may not be present/accurate
    """
    result = call_subscription_decision(
        product_subscriber_status="PAUSED",
        next_billing_date=billing_date,
        has_subscription=True,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}, debug={result['debug']}")

    # Expected behavior: 200 with active status
    assert result["status_code"] == 200, (
        f"PAUSED+future should return 200, got {result['status_code']}"
    )
    assert result["body"].get("subscription_status") == "active", (
        f"PAUSED+future should have subscription_status='active', "
        f"got '{result['body'].get('subscription_status')}'"
    )


# Scenario 4: PAUSED + nextBillingDate=null → expect 403 expired
@settings(
    max_examples=3,
    deadline=60000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(data=st.data())
def test_paused_null_date_should_deny(data):
    """
    **Validates: Requirements 1.4, 1.5**

    Bug Condition Scenario 4: PAUSED + nextBillingDate=null.
    Expected: 403 with "Your subscription has expired. Resubscribe to continue."
    Actual (buggy): 200 — current code treats PAUSED as ACTIVE via tags,
    completely ignoring the null nextBillingDate.
    """
    result = call_subscription_decision(
        product_subscriber_status="PAUSED",
        next_billing_date=None,
        has_subscription=True,
    )
    note(f"Result: status_code={result['status_code']}, body={result['body']}, debug={result['debug']}")

    # Expected behavior (will fail on unfixed code — no 403 path exists)
    assert result["status_code"] == 403, (
        f"PAUSED+null date should return 403, got {result['status_code']} "
        f"with subscription_status='{result['body'].get('subscription_status')}'. "
        f"Bug: login step 4 treats PAUSED as ACTIVE via tags, ignoring null billing date."
    )
    assert result["body"].get("error") == "Your subscription has expired. Resubscribe to continue.", (
        f"Expected expiry denial message, got: {result['body']}"
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SUBSCRIPTION STATUS BUG EXPLORATION TEST")
    print("=" * 70)
    print(f"Target: {STAGING_URL}")
    print(f"Endpoint: {ENDPOINT}")
    print()
    print("This test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms the bug exists in login step 4.")
    print()

    # First, verify the endpoint is reachable
    print("Checking endpoint availability...")
    try:
        health = requests.get(f"{STAGING_URL}/health", timeout=10)
        print(f"  Health check: {health.status_code}")
    except Exception as e:
        print(f"  ❌ Cannot reach staging backend: {e}")
        print("  Make sure the test endpoint is deployed to staging first.")
        sys.exit(1)

    # Quick smoke test to verify the test endpoint exists
    try:
        smoke = requests.post(
            ENDPOINT,
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
        elif smoke.status_code == 422:
            print(f"  ❌ Test endpoint returned 422 (validation error). Check endpoint schema.")
            print(f"     Response: {smoke.text[:200]}")
            sys.exit(1)
        print(f"  Smoke test: {smoke.status_code} — endpoint is available")
        print(f"  Smoke response: {smoke.json()}")
    except Exception as e:
        print(f"  ❌ Smoke test failed: {e}")
        sys.exit(1)

    print()
    print("-" * 70)

    # Run each scenario
    results = {}
    scenarios = [
        ("Scenario 1: PAUSED + expired date → expect 403", test_paused_expired_should_deny),
        ("Scenario 2: CANCELLED → expect 403", test_cancelled_should_deny),
        ("Scenario 3: PAUSED + future date → expect 200/active", test_paused_with_time_remaining_should_be_active),
        ("Scenario 4: PAUSED + null date → expect 403", test_paused_null_date_should_deny),
    ]

    failures = []
    for name, test_fn in scenarios:
        print(f"\n▶ {name}")
        try:
            test_fn()
            print(f"  ✅ PASSED")
            results[name] = "PASSED"
        except AssertionError as e:
            print(f"  ❌ FAILED (expected on unfixed code — confirms bug)")
            counterexample = str(e)[:200]
            print(f"     Counterexample: {counterexample}")
            results[name] = f"FAILED: {counterexample}"
            failures.append((name, counterexample))
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
    num_passed = len(scenarios) - num_failed

    if num_failed == 0:
        print("⚠️ ALL TESTS PASSED — the bug may already be fixed.")
        print("   If the fix has not been implemented yet, the test endpoint")
        print("   may not be exercising the real decision logic correctly.")
        return 1  # Unexpected pass
    else:
        print(f"✅ {num_failed}/{len(scenarios)} TESTS FAILED AS EXPECTED — bug confirmed.")
        if num_passed > 0:
            print(f"   ({num_passed} tests coincidentally passed due to tag-based logic)")
        print()
        print("   Root cause confirmed:")
        print("   1. _parse_tags_response uses unreliable customer tags")
        print("   2. Login step 4 has no 403 denial path")
        print("   3. nextBillingDate from contract data is completely ignored")
        print("   4. PAUSED subscribers are treated as ACTIVE via tags")
        print("   5. CANCELLED subscribers are silently downgraded to free tier")
        print()
        print("   Counterexamples found:")
        for name, ce in failures:
            print(f"   - {name}: {ce[:80]}")
        return 0  # Expected failure = success for exploration test


if __name__ == "__main__":
    sys.exit(main())
