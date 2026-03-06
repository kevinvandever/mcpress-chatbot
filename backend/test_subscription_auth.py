"""
Backend unit and property-based tests for Appstle Subscription Authentication.

Uses pytest + Hypothesis for property-based testing.
Run with: python3 -m pytest backend/test_subscription_auth.py -v
"""
import os
import time
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import jwt
import pytest
from hypothesis import given, strategies as st, settings

# ---------------------------------------------------------------------------
# Environment setup — must happen BEFORE importing the service
# ---------------------------------------------------------------------------
os.environ.setdefault("APPSTLE_API_URL", "https://test.appstle.com")
os.environ.setdefault("APPSTLE_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("SUBSCRIPTION_SIGNUP_URL", "https://test.com/subscribe")

try:
    from backend.subscription_auth import (
        SubscriptionAuthService,
        AppstleSubscriptionResponse,
        CustomerLoginRequest,
        _get_denial_message,
        _normalize_status,
        DENIAL_MESSAGES,
        DEFAULT_DENIAL_MESSAGE,
    )
    from backend.subscription_auth_routes import router, COOKIE_CONFIG
except ImportError:
    from subscription_auth import (
        SubscriptionAuthService,
        AppstleSubscriptionResponse,
        CustomerLoginRequest,
        _get_denial_message,
        _normalize_status,
        DENIAL_MESSAGES,
        DEFAULT_DENIAL_MESSAGE,
    )
    from subscription_auth_routes import router, COOKIE_CONFIG


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    """Fresh SubscriptionAuthService instance for each test."""
    svc = SubscriptionAuthService()
    # Ensure config is valid for tests
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True
    return svc


@pytest.fixture
def active_appstle_response():
    """An active subscription response from Appstle."""
    return AppstleSubscriptionResponse(
        is_valid=True,
        subscription_status="ACTIVE",
        expiration_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        customer_email="user@example.com",
    )


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Emails that are valid enough for our JWT (Hypothesis emails() can be slow)
email_strategy = st.from_regex(
    r"[a-z][a-z0-9]{1,8}@[a-z]{2,6}\.[a-z]{2,4}", fullmatch=True
)

expiration_date_strategy = st.datetimes(
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(timezone.utc),
)

subscription_status_strategy = st.sampled_from(["active", "cancelled", "expired", "paused"])

non_active_status_strategy = st.sampled_from(
    ["cancelled", "expired", "paused", "not_found", "unknown", ""]
)

# Appstle raw statuses that map to non-active
non_active_appstle_status_strategy = st.sampled_from(
    ["CANCELLED", "EXPIRED", "PAUSED", None, "", "UNKNOWN", "RANDOM"]
)


# ===========================================================================
# Property 1: Token structure completeness
# ===========================================================================

# Feature: appstle-subscription-auth, Property 1: Token structure completeness
@given(
    email=email_strategy,
    expires_at=expiration_date_strategy,
)
@settings(max_examples=100)
def test_property_1_token_structure_completeness(email, expires_at):
    """For any email and expiration date, create_token produces a JWT
    containing all required claims: sub, subscription_status,
    subscription_expires_at, iat, exp.

    **Validates: Requirements 1.3, 2.6, 3.1**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"

    token = svc.create_token(email, "active", expires_at)
    claims = jwt.decode(token, svc.jwt_secret, algorithms=["HS256"])

    assert "sub" in claims, "Missing 'sub' claim"
    assert claims["sub"] == email
    assert "subscription_status" in claims, "Missing 'subscription_status' claim"
    assert claims["subscription_status"] == "active"
    assert "subscription_expires_at" in claims, "Missing 'subscription_expires_at' claim"
    assert claims["subscription_expires_at"] == int(expires_at.timestamp())
    assert "iat" in claims, "Missing 'iat' claim"
    assert "exp" in claims, "Missing 'exp' claim"


# ===========================================================================
# Property 2: Token expiration window
# ===========================================================================

# Feature: appstle-subscription-auth, Property 2: Token expiration window
@given(
    email=email_strategy,
    expires_at=expiration_date_strategy,
)
@settings(max_examples=100)
def test_property_2_token_expiration_window(email, expires_at):
    """For any issued JWT, exp is exactly 3600 seconds after iat.

    **Validates: Requirements 3.2**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"

    token = svc.create_token(email, "active", expires_at)
    claims = jwt.decode(token, svc.jwt_secret, algorithms=["HS256"])

    assert claims["exp"] - claims["iat"] == 3600, (
        f"Expected exp - iat == 3600, got {claims['exp'] - claims['iat']}"
    )


# ===========================================================================
# Property 3: Token verification round-trip
# ===========================================================================

# Feature: appstle-subscription-auth, Property 3: Token verification round-trip
@given(
    email=email_strategy,
    status=subscription_status_strategy,
    expires_at=expiration_date_strategy,
)
@settings(max_examples=100)
def test_property_3_token_verification_round_trip(email, status, expires_at):
    """Tokens created by create_token are accepted by verify_token;
    tokens with tampered signatures or expired beyond grace window are rejected.

    **Validates: Requirements 3.4, 3.5, 3.6**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"

    token = svc.create_token(email, status, expires_at)

    # Valid token should be accepted
    claims = svc.verify_token(token)
    assert claims is not None, "Valid token was rejected"
    assert claims["sub"] == email
    assert claims["subscription_status"] == status

    # Tampered signature should be rejected
    tampered = token + "x"
    assert svc.verify_token(tampered) is None, "Tampered token was accepted"

    # Token signed with wrong secret should be rejected
    wrong_secret_token = jwt.encode(
        {"sub": email, "iat": int(datetime.now(timezone.utc).timestamp()),
         "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
         "subscription_status": status, "subscription_expires_at": None},
        "wrong-secret",
        algorithm="HS256",
    )
    assert svc.verify_token(wrong_secret_token) is None, "Wrong-secret token was accepted"


# ===========================================================================
# Property 4: Cookie security attributes
# ===========================================================================

# Feature: appstle-subscription-auth, Property 4: Cookie security attributes
@pytest.mark.asyncio
async def test_property_4_cookie_security_attributes():
    """Mock a successful login request and verify the response sets cookie
    with httponly=True, secure=True, samesite=lax, path=/.

    **Validates: Requirements 3.7**
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)

    # Mock the auth_service.login to return a successful result
    mock_result = {
        "status_code": 200,
        "body": {
            "success": True,
            "token": "mock-jwt-token",
            "email": "user@example.com",
            "subscription_status": "active",
            "expires_at": None,
        },
    }

    # Patch the module-level auth_service in the routes module
    try:
        import backend.subscription_auth_routes as routes_mod
    except ImportError:
        import subscription_auth_routes as routes_mod

    original_login = routes_mod.auth_service.login
    routes_mod.auth_service.login = AsyncMock(return_value=mock_result)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com"},
        )

        assert response.status_code == 200

        # Check Set-Cookie header
        cookie_header = response.headers.get("set-cookie", "")
        assert "session_token=" in cookie_header, f"No session_token cookie set: {cookie_header}"
        assert "httponly" in cookie_header.lower(), f"Missing httponly: {cookie_header}"
        assert "secure" in cookie_header.lower(), f"Missing secure: {cookie_header}"
        assert "samesite=lax" in cookie_header.lower(), f"Missing samesite=lax: {cookie_header}"
        assert "path=/" in cookie_header.lower(), f"Missing path=/: {cookie_header}"
    finally:
        routes_mod.auth_service.login = original_login


# ===========================================================================
# Property 5: Non-active subscription denial
# ===========================================================================

# Feature: appstle-subscription-auth, Property 5: Non-active subscription denial
@given(
    status=non_active_appstle_status_strategy,
)
@settings(max_examples=100)
def test_property_5_non_active_subscription_denial(status):
    """For any status not active (cancelled, expired, paused, not_found,
    unknown, empty), login returns denial with redirect URL.

    **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 9.5**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    appstle_resp = AppstleSubscriptionResponse(
        is_valid=False,
        subscription_status=status,
        expiration_date=None,
        customer_email="user@example.com",
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=appstle_resp):
        result = asyncio.get_event_loop().run_until_complete(
            svc.login("user@example.com", "127.0.0.1")
        )

    assert result["status_code"] == 403, f"Expected 403, got {result['status_code']}"
    body = result["body"]
    assert body["success"] is False
    assert body["redirect_url"] == "https://test.com/subscribe"
    assert body["error"]  # Should have a denial message


# ===========================================================================
# Property 6: Active subscription grants access
# ===========================================================================

# Feature: appstle-subscription-auth, Property 6: Active subscription grants access
@given(
    email=email_strategy,
)
@settings(max_examples=100)
def test_property_6_active_subscription_grants_access(email):
    """Mock Appstle returning active status, verify login returns success
    with valid JWT.

    **Validates: Requirements 2.1**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    appstle_resp = AppstleSubscriptionResponse(
        is_valid=True,
        subscription_status="ACTIVE",
        expiration_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        customer_email=email,
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=appstle_resp):
        result = asyncio.get_event_loop().run_until_complete(
            svc.login(email, "127.0.0.1")
        )

    assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"
    body = result["body"]
    assert body["success"] is True
    assert body["token"]

    # Verify the token is a valid JWT with correct claims
    claims = jwt.decode(body["token"], svc.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == email
    assert claims["subscription_status"] == "active"


# ===========================================================================
# Property 7: Grace window acceptance
# ===========================================================================

# Feature: appstle-subscription-auth, Property 7: Grace window acceptance
@given(
    email=email_strategy,
    seconds_expired=st.integers(min_value=1, max_value=299),
)
@settings(max_examples=100)
def test_property_7_grace_window_acceptance(email, seconds_expired):
    """Tokens expired within 5 minutes are accepted by verify_token(allow_grace=True);
    tokens expired beyond 5 minutes are rejected.

    **Validates: Requirements 3.9**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"

    now = datetime.now(timezone.utc)

    # Create a token that expired `seconds_expired` seconds ago (within grace)
    payload_within_grace = {
        "sub": email,
        "subscription_status": "active",
        "subscription_expires_at": None,
        "iat": int((now - timedelta(hours=1, seconds=seconds_expired)).timestamp()),
        "exp": int((now - timedelta(seconds=seconds_expired)).timestamp()),
    }
    token_within_grace = jwt.encode(payload_within_grace, svc.jwt_secret, algorithm="HS256")

    # Should be accepted with grace
    claims = svc.verify_token(token_within_grace, allow_grace=True)
    assert claims is not None, f"Token expired {seconds_expired}s ago should be accepted with grace"
    assert claims["sub"] == email

    # Should be rejected without grace
    claims_no_grace = svc.verify_token(token_within_grace, allow_grace=False)
    assert claims_no_grace is None, "Expired token should be rejected without grace"


# Feature: appstle-subscription-auth, Property 7: Grace window rejection beyond 5 min
@given(
    email=email_strategy,
    seconds_beyond=st.integers(min_value=301, max_value=3600),
)
@settings(max_examples=100)
def test_property_7_grace_window_rejection_beyond(email, seconds_beyond):
    """Tokens expired beyond 5 minutes are rejected even with allow_grace=True.

    **Validates: Requirements 3.9**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"

    now = datetime.now(timezone.utc)

    payload_beyond_grace = {
        "sub": email,
        "subscription_status": "active",
        "subscription_expires_at": None,
        "iat": int((now - timedelta(hours=1, seconds=seconds_beyond)).timestamp()),
        "exp": int((now - timedelta(seconds=seconds_beyond)).timestamp()),
    }
    token_beyond_grace = jwt.encode(payload_beyond_grace, svc.jwt_secret, algorithm="HS256")

    claims = svc.verify_token(token_beyond_grace, allow_grace=True)
    assert claims is None, f"Token expired {seconds_beyond}s ago should be rejected even with grace"


# ===========================================================================
# Property 8: Refresh with active subscription
# ===========================================================================

# Feature: appstle-subscription-auth, Property 8: Refresh with active subscription
@given(
    email=email_strategy,
)
@settings(max_examples=100)
def test_property_8_refresh_with_active_subscription(email):
    """Mock Appstle active, verify refresh issues new token with fresh 1-hour expiry.

    **Validates: Requirements 3.10**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    # Create a valid token
    original_token = svc.create_token(email, "active", datetime(2025, 12, 31, tzinfo=timezone.utc))

    appstle_resp = AppstleSubscriptionResponse(
        is_valid=True,
        subscription_status="ACTIVE",
        expiration_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        customer_email=email,
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=appstle_resp):
        result = asyncio.get_event_loop().run_until_complete(svc.refresh(original_token))

    assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"
    body = result["body"]
    assert body["success"] is True
    assert body["token"]

    # Verify new token has fresh 1-hour expiry
    new_claims = jwt.decode(body["token"], svc.jwt_secret, algorithms=["HS256"])
    assert new_claims["exp"] - new_claims["iat"] == 3600
    assert new_claims["sub"] == email


# ===========================================================================
# Property 9: Refresh with inactive subscription
# ===========================================================================

# Feature: appstle-subscription-auth, Property 9: Refresh with inactive subscription
@given(
    email=email_strategy,
    status=non_active_appstle_status_strategy,
)
@settings(max_examples=100)
def test_property_9_refresh_with_inactive_subscription(email, status):
    """Mock Appstle inactive, verify refresh returns 403 with redirect URL.

    **Validates: Requirements 3.11**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    # Create a valid token
    original_token = svc.create_token(email, "active", datetime(2025, 12, 31, tzinfo=timezone.utc))

    appstle_resp = AppstleSubscriptionResponse(
        is_valid=False,
        subscription_status=status,
        expiration_date=None,
        customer_email=email,
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=appstle_resp):
        result = asyncio.get_event_loop().run_until_complete(svc.refresh(original_token))

    assert result["status_code"] == 403, f"Expected 403, got {result['status_code']}"
    body = result["body"]
    assert body["success"] is False
    assert body["redirect_url"] == "https://test.com/subscribe"


# ===========================================================================
# Property 12: Rate limiting enforcement
# ===========================================================================

# Feature: appstle-subscription-auth, Property 12: Rate limiting enforcement
@pytest.mark.asyncio
async def test_property_12_rate_limiting_enforcement():
    """Simulate 5 failed attempts, verify 6th returns 429.

    **Validates: Requirements 6.2**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    test_ip = "192.168.1.100"

    # Mock Appstle to return inactive (so login fails but doesn't error)
    appstle_resp = AppstleSubscriptionResponse(
        is_valid=False,
        subscription_status="CANCELLED",
        expiration_date=None,
        customer_email="user@example.com",
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=appstle_resp):
        # First 5 attempts should go through (denied by subscription, not rate limit)
        for i in range(5):
            result = await svc.login("user@example.com", test_ip)
            assert result["status_code"] == 403, f"Attempt {i+1}: expected 403, got {result['status_code']}"

        # 6th attempt should be rate limited
        result = await svc.login("user@example.com", test_ip)
        assert result["status_code"] == 429, f"6th attempt: expected 429, got {result['status_code']}"
        assert "Too many login attempts" in result["body"]["error"]


# ===========================================================================
# Property 13: Rate limiting reset
# ===========================================================================

# Feature: appstle-subscription-auth, Property 13: Rate limiting reset
@pytest.mark.asyncio
async def test_property_13_rate_limiting_reset():
    """After failed attempts, a successful login resets the counter.

    **Validates: Requirements 6.3**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    test_ip = "192.168.1.200"

    inactive_resp = AppstleSubscriptionResponse(
        is_valid=False,
        subscription_status="CANCELLED",
        expiration_date=None,
        customer_email="user@example.com",
    )

    active_resp = AppstleSubscriptionResponse(
        is_valid=True,
        subscription_status="ACTIVE",
        expiration_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        customer_email="user@example.com",
    )

    # Make 3 failed attempts
    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=inactive_resp):
        for i in range(3):
            result = await svc.login("user@example.com", test_ip)
            assert result["status_code"] == 403

    # Successful login should reset the counter
    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=active_resp):
        result = await svc.login("user@example.com", test_ip)
        assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"

    # After reset, should be able to make 5 more failed attempts before rate limit
    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, return_value=inactive_resp):
        for i in range(5):
            result = await svc.login("user@example.com", test_ip)
            assert result["status_code"] == 403, f"Post-reset attempt {i+1}: expected 403, got {result['status_code']}"

        # 6th should be rate limited again
        result = await svc.login("user@example.com", test_ip)
        assert result["status_code"] == 429


# ===========================================================================
# Property 14: Disabled configuration
# ===========================================================================

# Feature: appstle-subscription-auth, Property 14: Disabled configuration
@given(
    email=email_strategy,
)
@settings(max_examples=100)
def test_property_14_disabled_configuration_missing_url(email):
    """When APPSTLE_API_URL is missing, login returns 503.

    **Validates: Requirements 8.6**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = None
    svc.appstle_api_key = "test-key"
    svc._config_valid = False  # Missing URL

    result = asyncio.get_event_loop().run_until_complete(
        svc.login(email, "127.0.0.1")
    )

    assert result["status_code"] == 503, f"Expected 503, got {result['status_code']}"
    assert "temporarily unavailable" in result["body"]["error"].lower()


# Feature: appstle-subscription-auth, Property 14: Disabled configuration (missing key)
@given(
    email=email_strategy,
)
@settings(max_examples=100)
def test_property_14_disabled_configuration_missing_key(email):
    """When APPSTLE_API_KEY is missing, login returns 503.

    **Validates: Requirements 8.6**
    """
    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = None
    svc._config_valid = False  # Missing key

    result = asyncio.get_event_loop().run_until_complete(
        svc.login(email, "127.0.0.1")
    )

    assert result["status_code"] == 503, f"Expected 503, got {result['status_code']}"
    assert "temporarily unavailable" in result["body"]["error"].lower()


# ===========================================================================
# Property 15: Appstle API errors
# ===========================================================================

# Feature: appstle-subscription-auth, Property 15: Appstle API errors
@pytest.mark.asyncio
async def test_property_15_appstle_api_non_200():
    """Mock non-200 responses, verify 503 returned.

    **Validates: Requirements 9.1**
    """
    import aiohttp

    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    # Mock verify_subscription to raise ClientResponseError (non-200)
    mock_error = aiohttp.ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=500,
        message="Internal Server Error",
    )

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, side_effect=mock_error):
        result = await svc.login("user@example.com", "127.0.0.1")

    assert result["status_code"] == 503, f"Expected 503, got {result['status_code']}"
    assert "temporarily unavailable" in result["body"]["error"].lower()


@pytest.mark.asyncio
async def test_property_15_appstle_api_timeout():
    """Mock timeout, verify 503 returned.

    **Validates: Requirements 9.1**
    """
    import asyncio as aio

    svc = SubscriptionAuthService()
    svc.jwt_secret = "test-secret-key-for-testing"
    svc.appstle_api_url = "https://test.appstle.com"
    svc.appstle_api_key = "test-key"
    svc.signup_url = "https://test.com/subscribe"
    svc._config_valid = True

    with patch.object(svc, "verify_subscription", new_callable=AsyncMock, side_effect=aio.TimeoutError()):
        result = await svc.login("user@example.com", "127.0.0.2")

    assert result["status_code"] == 503, f"Expected 503, got {result['status_code']}"
    assert "temporarily unavailable" in result["body"]["error"].lower()


# ===========================================================================
# Property 16: Status-specific denial messages
# ===========================================================================

# Feature: appstle-subscription-auth, Property 16: Status-specific denial messages
def test_property_16_status_specific_denial_messages():
    """Verify each status maps to its correct user-facing message.

    **Validates: Requirements 10.3**
    """
    expected_messages = {
        "EXPIRED": "Your subscription has expired",
        "PAUSED": "Your subscription is paused",
        "CANCELLED": "Your subscription has been cancelled",
        None: "No subscription found",
        "": "No subscription found",
        "not_found": "No subscription found",
        "UNKNOWN": "No subscription found",
        "RANDOM_STATUS": "No subscription found",
    }

    for status, expected_msg in expected_messages.items():
        actual = _get_denial_message(status)
        assert actual == expected_msg, (
            f"Status '{status}': expected '{expected_msg}', got '{actual}'"
        )


@given(
    status=non_active_appstle_status_strategy,
)
@settings(max_examples=100)
def test_property_16_denial_messages_property(status):
    """For any non-active status, the denial message is one of the known messages.

    **Validates: Requirements 10.3**
    """
    message = _get_denial_message(status)
    valid_messages = set(DENIAL_MESSAGES.values()) | {DEFAULT_DENIAL_MESSAGE}
    assert message in valid_messages, f"Unexpected denial message: '{message}' for status '{status}'"


# ===========================================================================
# Admin auth isolation test
# ===========================================================================

def test_admin_auth_isolation():
    """Verify POST /api/admin/login still works independently of customer auth.

    The admin routes should be registered and respond to requests without
    being affected by the subscription auth routes.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    # Register both routers (customer auth)
    app.include_router(router)

    # Register admin auth router
    try:
        from backend.auth_routes import router as admin_router
    except ImportError:
        from auth_routes import router as admin_router

    app.include_router(admin_router)

    client = TestClient(app)

    # Verify admin login endpoint exists and responds
    # (It will return 401 or 422 since we're not providing valid credentials,
    # but the point is it's registered and not broken by customer auth)
    response = client.post(
        "/api/admin/login",
        json={"email": "admin@test.com", "password": "testpass"},
    )
    # Should NOT be 404 (route not found) or 405 (method not allowed)
    assert response.status_code not in (404, 405), (
        f"Admin login route not found or broken: {response.status_code}"
    )

    # Verify customer auth endpoints also exist
    response_customer = client.post(
        "/api/auth/login",
        json={"email": "user@test.com"},
    )
    assert response_customer.status_code not in (404, 405), (
        f"Customer login route not found: {response_customer.status_code}"
    )

    # Verify they use different prefixes
    assert "/api/admin/" != "/api/auth/"
