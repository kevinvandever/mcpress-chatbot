"""
Unit Tests for Appstle Customer Tag Authentication
Feature: appstle-customer-tag-auth

Covers:
- Tag extraction from real-shaped Appstle API responses
- Default config values when no env vars are set
- Customer with both customerTags and tags fields (first one wins)
- Empty string tags in the list are preserved correctly
- Malformed tags structure logs warning and returns empty list
- _parse_tags_response with various API response shapes
- Login flow with mocked Appstle API returning tagged customer

Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.2, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4
"""

import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import module-level functions and models
try:
    from backend.subscription_auth import (
        TagConfig,
        load_tag_config,
        _derive_status_from_tags,
        AppstleSubscriptionResponse,
        SubscriptionAuthService,
    )
except ImportError:
    from subscription_auth import (
        TagConfig,
        load_tag_config,
        _derive_status_from_tags,
        AppstleSubscriptionResponse,
        SubscriptionAuthService,
    )

# Real Appstle tag names
ACTIVE_TAG = "appstle_subscription_active_customer"
PAUSED_TAG = "appstle_subscription_paused_customer"
INACTIVE_TAG = "appstle_subscription_inactive_customer"


# ---------------------------------------------------------------------------
# Helper: create a SubscriptionAuthService with all deps mocked
# ---------------------------------------------------------------------------
def _make_service(tag_config=None):
    """Create a SubscriptionAuthService with mocked dependencies."""
    with patch.dict(os.environ, {
        "APPSTLE_API_URL": "https://fake-appstle.example.com",
        "APPSTLE_API_KEY": "fake-key",
        "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
        "SUBSCRIPTION_SIGNUP_URL": "https://example.com/signup",
    }):
        with patch("backend.subscription_auth.PasswordService", autospec=True):
            svc = SubscriptionAuthService()
    if tag_config:
        svc.tag_config = tag_config
    return svc


# ===================================================================
# 1. Tag extraction from real-shaped Appstle API response
# ===================================================================
# Validates: Requirements 1.1

class TestTagExtractionRealShape:
    """Extract tags from a realistic Appstle API customer record."""

    def test_extract_tags_from_customer_tags_field(self):
        svc = _make_service()
        customer = {
            "email": "user@example.com",
            "customerTags": [ACTIVE_TAG, "premium"],
            "activeSubscriptions": 1,
            "subscriptionContracts": {"edges": []},
        }
        tags = svc._extract_customer_tags(customer)
        assert tags == [ACTIVE_TAG, "premium"]

    def test_extract_tags_from_dict_items(self):
        """Tags as list-of-dicts with 'name' key."""
        svc = _make_service()
        customer = {
            "customerTags": [
                {"name": "active-subscriber"},
                {"value": "vip"},
                {"tag": "beta-tester"},
            ]
        }
        tags = svc._extract_customer_tags(customer)
        assert tags == ["active-subscriber", "vip", "beta-tester"]


# ===================================================================
# 2. Default config values when no env vars are set
# ===================================================================
# Validates: Requirements 3.2

class TestDefaultConfig:
    """load_tag_config returns sensible defaults when env vars are absent."""

    def test_defaults_when_no_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove the specific vars if present
            for var in ("SUBSCRIPTION_TAG_ACTIVE", "SUBSCRIPTION_TAG_PAUSED", "SUBSCRIPTION_TAG_INACTIVE"):
                os.environ.pop(var, None)
            cfg = load_tag_config()

        assert cfg.active_patterns == [ACTIVE_TAG]
        assert cfg.paused_patterns == [PAUSED_TAG]
        assert cfg.inactive_patterns == [INACTIVE_TAG]

    def test_whitespace_only_env_falls_back_to_default(self):
        env = {
            "SUBSCRIPTION_TAG_ACTIVE": "   ,  , ",
            "SUBSCRIPTION_TAG_PAUSED": "",
            "SUBSCRIPTION_TAG_INACTIVE": "  ",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = load_tag_config()

        assert cfg.active_patterns == [ACTIVE_TAG]
        assert cfg.paused_patterns == [PAUSED_TAG]
        assert cfg.inactive_patterns == [INACTIVE_TAG]


# ===================================================================
# 3. Customer with both customerTags and tags fields (first one wins)
# ===================================================================
# Validates: Requirements 1.1

class TestCustomerTagsPriority:
    """When both customerTags and tags exist, customerTags takes precedence."""

    def test_customer_tags_wins_over_tags(self):
        svc = _make_service()
        customer = {
            "customerTags": [ACTIVE_TAG],
            "tags": [PAUSED_TAG],
        }
        tags = svc._extract_customer_tags(customer)
        assert tags == [ACTIVE_TAG]

    def test_falls_back_to_tags_when_customer_tags_empty(self):
        svc = _make_service()
        # customerTags is empty list → falsy, so falls back to tags
        customer = {
            "customerTags": [],
            "tags": [PAUSED_TAG],
        }
        tags = svc._extract_customer_tags(customer)
        assert tags == [PAUSED_TAG]

    def test_falls_back_to_tags_when_customer_tags_missing(self):
        svc = _make_service()
        customer = {"tags": [INACTIVE_TAG]}
        tags = svc._extract_customer_tags(customer)
        assert tags == [INACTIVE_TAG]


# ===================================================================
# 4. Empty string tags in the list are preserved correctly
# ===================================================================
# Validates: Requirements 1.1

class TestEmptyStringTags:
    """Empty strings in the tag list are preserved (they are valid strings)."""

    def test_empty_string_tags_preserved(self):
        svc = _make_service()
        customer = {"customerTags": [ACTIVE_TAG, "", "premium"]}
        tags = svc._extract_customer_tags(customer)
        assert tags == [ACTIVE_TAG, "", "premium"]


# ===================================================================
# 5. Malformed tags structure logs warning and returns empty list
# ===================================================================
# Validates: Requirements 1.4

class TestMalformedTags:
    """Non-list tags structures log a warning and return []."""

    def test_tags_as_string_returns_empty(self, caplog):
        svc = _make_service()
        customer = {"customerTags": "not-a-list"}
        with caplog.at_level(logging.WARNING):
            tags = svc._extract_customer_tags(customer)
        assert tags == []
        assert "Unexpected tags structure" in caplog.text

    def test_tags_as_int_returns_empty(self, caplog):
        svc = _make_service()
        customer = {"customerTags": 42}
        with caplog.at_level(logging.WARNING):
            tags = svc._extract_customer_tags(customer)
        assert tags == []
        assert "Unexpected tags structure" in caplog.text

    def test_tags_as_dict_returns_empty(self, caplog):
        svc = _make_service()
        customer = {"customerTags": {"key": "value"}}
        with caplog.at_level(logging.WARNING):
            tags = svc._extract_customer_tags(customer)
        assert tags == []
        assert "Unexpected tags structure" in caplog.text

    def test_no_tags_fields_returns_empty(self):
        svc = _make_service()
        customer = {"email": "user@example.com"}
        tags = svc._extract_customer_tags(customer)
        assert tags == []

    def test_unexpected_item_type_in_list_skipped(self, caplog):
        svc = _make_service()
        customer = {"customerTags": ["valid-tag", 123, "another-tag"]}
        with caplog.at_level(logging.WARNING):
            tags = svc._extract_customer_tags(customer)
        assert tags == ["valid-tag", "another-tag"]
        assert "Unexpected tag item type" in caplog.text


# ===================================================================
# 6. _parse_tags_response with various API response shapes
# ===================================================================
# Validates: Requirements 4.2, 4.3, 4.4, 4.5

class TestParseTagsResponse:
    """_parse_tags_response handles list, paginated dict, single customer dict, and empty."""

    def setup_method(self):
        self.svc = _make_service()

    def test_paginated_dict_active(self):
        """Paginated response with content list → active customer."""
        data = {
            "content": [
                {"email": "user@example.com", "customerTags": [ACTIVE_TAG]}
            ]
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is True
        assert resp.subscription_status == "ACTIVE"
        assert resp.customer_email == "user@example.com"

    def test_list_response_paused(self):
        """Plain list response → paused customer."""
        data = [
            {"email": "user@example.com", "customerTags": [PAUSED_TAG]}
        ]
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status == "PAUSED"

    def test_single_customer_dict_inactive(self):
        """Single customer dict (has email key, no content key) → inactive."""
        data = {"email": "user@example.com", "customerTags": [INACTIVE_TAG]}
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status == "CANCELLED"

    def test_empty_content_list(self):
        """Empty content list → not_found."""
        data = {"content": []}
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status is None

    def test_empty_list(self):
        """Empty list → not_found."""
        data = []
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status is None

    def test_no_recognized_tags(self):
        """Customer with unrecognized tags → not_found."""
        data = [{"email": "user@example.com", "customerTags": ["random-tag", "other"]}]
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status is None

    def test_case_insensitive_matching(self):
        """Tags are matched case-insensitively."""
        data = [{"email": "user@example.com", "customerTags": [ACTIVE_TAG.upper()]}]
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is True
        assert resp.subscription_status == "ACTIVE"


# ===================================================================
# 7. Login flow with mocked Appstle API returning tagged customer
# ===================================================================
# Validates: Requirements 5.1, 5.2, 5.3, 5.4

class TestLoginFlowWithTags:
    """End-to-end login flow with verify_subscription mocked."""

    def _make_login_service(self):
        """Create a service with password_service and rate_limiter mocked."""
        svc = _make_service()
        # Mock password_service to simulate existing user with valid password
        svc.password_service = MagicMock()
        svc.password_service.get_customer = AsyncMock(return_value={
            "email": "user@example.com",
            "password_hash": "$2b$12$fakehashvalue",
        })
        svc.password_service.verify_password = MagicMock(return_value=True)
        return svc

    @pytest.mark.asyncio
    async def test_login_active_subscriber_success(self):
        """Active tag → 200 with token and subscription_status='active'."""
        svc = self._make_login_service()
        svc.verify_subscription = AsyncMock(return_value=AppstleSubscriptionResponse(
            is_valid=True,
            subscription_status="ACTIVE",
            customer_email="user@example.com",
        ))

        result = await svc.login("user@example.com", "ValidPass1!", "127.0.0.1")
        assert result["status_code"] == 200
        assert result["body"]["success"] is True
        assert result["body"]["subscription_status"] == "active"
        assert "token" in result["body"]

    @pytest.mark.asyncio
    async def test_login_paused_subscriber_denied(self):
        """Paused tag → 403 with 'Your subscription is paused'."""
        svc = self._make_login_service()
        svc.verify_subscription = AsyncMock(return_value=AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status="PAUSED",
            customer_email="user@example.com",
        ))

        result = await svc.login("user@example.com", "ValidPass1!", "127.0.0.1")
        assert result["status_code"] == 403
        assert result["body"]["success"] is False
        assert result["body"]["error"] == "Your subscription is paused"

    @pytest.mark.asyncio
    async def test_login_inactive_subscriber_denied(self):
        """Inactive tag → 403 with 'Your subscription has been cancelled'."""
        svc = self._make_login_service()
        svc.verify_subscription = AsyncMock(return_value=AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status="CANCELLED",
            customer_email="user@example.com",
        ))

        result = await svc.login("user@example.com", "ValidPass1!", "127.0.0.1")
        assert result["status_code"] == 403
        assert result["body"]["success"] is False
        assert result["body"]["error"] == "Your subscription has been cancelled"

    @pytest.mark.asyncio
    async def test_login_no_tags_denied(self):
        """No recognized tags → 403 with 'No subscription found'."""
        svc = self._make_login_service()
        svc.verify_subscription = AsyncMock(return_value=AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status=None,
            customer_email="user@example.com",
        ))

        result = await svc.login("user@example.com", "ValidPass1!", "127.0.0.1")
        assert result["status_code"] == 403
        assert result["body"]["success"] is False
        assert result["body"]["error"] == "No subscription found"


# ===================================================================
# Bonus: _derive_status_from_tags unit examples
# ===================================================================
# Validates: Requirements 2.1, 2.2, 2.3, 2.4

class TestDeriveStatusFromTags:
    """Specific examples for the pure status derivation function."""

    def setup_method(self):
        self.config = TagConfig()

    def test_active_tag_returns_active(self):
        assert _derive_status_from_tags([ACTIVE_TAG], self.config) == "active"

    def test_paused_tag_returns_paused(self):
        assert _derive_status_from_tags([PAUSED_TAG], self.config) == "paused"

    def test_inactive_tag_returns_inactive(self):
        assert _derive_status_from_tags([INACTIVE_TAG], self.config) == "inactive"

    def test_no_tags_returns_not_found(self):
        assert _derive_status_from_tags([], self.config) == "not_found"

    def test_unrecognized_tags_returns_not_found(self):
        assert _derive_status_from_tags(["random", "other"], self.config) == "not_found"

    def test_active_wins_over_paused(self):
        """Active takes priority even when paused is also present."""
        assert _derive_status_from_tags(
            [PAUSED_TAG, ACTIVE_TAG], self.config
        ) == "active"

    def test_case_insensitive(self):
        assert _derive_status_from_tags([ACTIVE_TAG.upper()], self.config) == "active"
        assert _derive_status_from_tags([PAUSED_TAG.title()], self.config) == "paused"


# ===================================================================
# 8. _extract_customer_id from step 1 response
# ===================================================================

class TestExtractCustomerId:
    """Extract customerId from the step 1 Appstle API response."""

    def setup_method(self):
        self.svc = _make_service()

    def test_extract_from_list_response(self):
        data = [{"customerId": 3101473863, "name": "Test User", "email": "user@example.com"}]
        assert self.svc._extract_customer_id(data) == 3101473863

    def test_extract_from_paginated_dict(self):
        data = {"content": [{"customerId": 12345, "email": "user@example.com"}]}
        assert self.svc._extract_customer_id(data) == 12345

    def test_extract_from_single_dict(self):
        data = {"customerId": 99999, "email": "user@example.com"}
        assert self.svc._extract_customer_id(data) == 99999

    def test_returns_none_for_empty_list(self):
        assert self.svc._extract_customer_id([]) is None

    def test_returns_none_for_empty_content(self):
        assert self.svc._extract_customer_id({"content": []}) is None

    def test_returns_none_for_missing_customer_id(self):
        data = [{"email": "user@example.com", "name": "No ID"}]
        assert self.svc._extract_customer_id(data) is None

    def test_returns_first_customer_id(self):
        """When multiple customers, returns the first one."""
        data = [
            {"customerId": 111, "email": "a@example.com"},
            {"customerId": 222, "email": "b@example.com"},
        ]
        assert self.svc._extract_customer_id(data) == 111


# ===================================================================
# 9. Real Appstle step 2 response shape (tags field)
# ===================================================================

class TestRealAppstleStep2Response:
    """Test _parse_tags_response with the actual shape returned by
    /api/external/v2/subscription-customers/{customerId}."""

    def setup_method(self):
        self.svc = _make_service()

    def test_active_customer_with_extra_tags(self):
        """Real response has tags as flat string list with extra Shopify tags."""
        data = {
            "__typename": "Customer",
            "id": "gid://shopify/Customer/3101473863",
            "productSubscriberStatus": "ACTIVE",
            "tags": [ACTIVE_TAG, "newsletter", "prospect"],
            "subscriptionContracts": {"__typename": "SubscriptionContractConnection", "nodes": []},
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is True
        assert resp.subscription_status == "ACTIVE"

    def test_paused_customer(self):
        data = {
            "__typename": "Customer",
            "id": "gid://shopify/Customer/123",
            "tags": [PAUSED_TAG, "newsletter"],
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status == "PAUSED"

    def test_inactive_customer(self):
        data = {
            "__typename": "Customer",
            "id": "gid://shopify/Customer/456",
            "tags": [INACTIVE_TAG],
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status == "CANCELLED"

    def test_customer_with_no_subscription_tags(self):
        """Customer exists but has no Appstle subscription tags."""
        data = {
            "__typename": "Customer",
            "id": "gid://shopify/Customer/789",
            "tags": ["newsletter", "prospect"],
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is False
        assert resp.subscription_status is None

    def test_customer_with_active_and_paused_tags(self):
        """Active takes priority when both active and paused tags present."""
        data = {
            "tags": [PAUSED_TAG, ACTIVE_TAG, "newsletter"],
        }
        resp = self.svc._parse_tags_response(data, "user@example.com")
        assert resp.is_valid is True
        assert resp.subscription_status == "ACTIVE"
