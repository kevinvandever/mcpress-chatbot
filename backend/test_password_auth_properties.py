"""
Property-Based Tests for ChatMaster Password Authentication
Feature: chatmaster-password-auth

Uses hypothesis library with pytest for property-based testing.
Tests cover: password validation completeness, hash irreversibility,
reset token single use, reset token expiry, and password rule specificity.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Import PasswordService with try/except pattern
try:
    from backend.password_service import PasswordService
except ImportError:
    from password_service import PasswordService

# Import ResetTokenService with try/except pattern
try:
    from backend.reset_token_service import ResetTokenService
except ImportError:
    from reset_token_service import ResetTokenService


# --- Constants ---

SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
MIN_LENGTH = 8

KNOWN_RULE_MESSAGES = [
    "Password must be at least 8 characters long",
    "Password must contain at least one uppercase letter",
    "Password must contain at least one lowercase letter",
    "Password must contain at least one digit",
    "Password must contain at least one special character",
]


# --- Helpers ---

def _count_violated_rules(password: str) -> int:
    """Count how many password rules a given string violates."""
    count = 0
    if len(password) < MIN_LENGTH:
        count += 1
    if not any(c.isupper() for c in password):
        count += 1
    if not any(c.islower() for c in password):
        count += 1
    if not any(c.isdigit() for c in password):
        count += 1
    if not any(c in SPECIAL_CHARS for c in password):
        count += 1
    return count


def _all_rules_satisfied(password: str) -> bool:
    """Check if a password satisfies ALL rules."""
    return _count_violated_rules(password) == 0


# --- Property Test 11.1: Password Validation Completeness (Property 2) ---
# Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

class TestPasswordValidationCompleteness:
    """
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

    For any string, validate_password() returns an empty list if and only if
    ALL rules are satisfied (length >= 8, has uppercase, has lowercase, has digit,
    has special char). For any string that violates k rules, the returned list
    has exactly k entries.
    """

    def setup_method(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            self.service = PasswordService(database_url="postgresql://fake:5432/test")

    @given(st.text())
    @settings(max_examples=200)
    def test_validation_completeness(self, password: str):
        failures = self.service.validate_password(password)
        expected_count = _count_violated_rules(password)
        all_satisfied = _all_rules_satisfied(password)

        # Empty list iff all rules satisfied
        assert (len(failures) == 0) == all_satisfied, (
            f"Expected empty={all_satisfied} but got {len(failures)} failures "
            f"for password: {password!r}"
        )

        # Number of failures equals number of violated rules
        assert len(failures) == expected_count, (
            f"Expected {expected_count} failures but got {len(failures)} "
            f"for password: {password!r}"
        )


# --- Property Test 11.2: Password Hash Irreversibility (Property 1) ---
# Validates: Requirements 1.2

class TestPasswordHashIrreversibility:
    """
    **Validates: Requirements 1.2**

    For any password, hash_password() produces a hash that:
    - Differs from the plaintext password
    - bcrypt.checkpw(password, hash) returns True (the hash is valid)
    """

    def setup_method(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            self.service = PasswordService(database_url="postgresql://fake:5432/test")

    @given(st.text(min_size=1, max_size=72))
    @settings(max_examples=50, deadline=None)
    def test_hash_irreversibility(self, password: str):
        hashed = self.service.hash_password(password)

        # Hash differs from plaintext
        assert hashed != password, (
            f"Hash should differ from plaintext for: {password!r}"
        )

        # bcrypt.checkpw confirms the hash is valid for this password
        assert bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")), (
            f"bcrypt.checkpw should return True for password: {password!r}"
        )


# --- Property Test 11.3: Reset Token Single Use (Property 5) ---
# Validates: Requirements 7.3

class TestResetTokenSingleUse:
    """
    **Validates: Requirements 7.3**

    After a token is marked as used via mark_token_used(), validate_token()
    returns None for that token.
    """

    @pytest.mark.asyncio
    async def test_token_single_use(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            service = ResetTokenService(database_url="postgresql://fake:5432/test")

        test_token = "test-token-abc123"
        test_email = "user@example.com"
        future_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        # Mock the pool and connection
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        service.pool = mock_pool

        # --- Phase 1: validate_token returns email (token is valid) ---
        mock_conn.fetchrow.return_value = {
            "email": test_email,
            "expires_at": future_expiry,
            "used": False,
        }
        result = await service.validate_token(test_token)
        assert result == test_email, (
            f"Expected email {test_email!r} but got {result!r}"
        )

        # --- Phase 2: mark_token_used ---
        mock_conn.execute.return_value = "UPDATE 1"
        marked = await service.mark_token_used(test_token)
        assert marked is True, "mark_token_used should return True"

        # --- Phase 3: validate_token returns None (token is used) ---
        mock_conn.fetchrow.return_value = {
            "email": test_email,
            "expires_at": future_expiry,
            "used": True,
        }
        result_after = await service.validate_token(test_token)
        assert result_after is None, (
            f"Expected None after marking used, but got {result_after!r}"
        )


# --- Property Test 11.4: Reset Token Expiry (Property 6) ---
# Validates: Requirements 7.4

class TestResetTokenExpiry:
    """
    **Validates: Requirements 7.4**

    Tokens older than 1 hour are rejected by validate_token().
    Mock the database to return a token record with expires_at in the past.
    Verify validate_token() returns None.
    """

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            service = ResetTokenService(database_url="postgresql://fake:5432/test")

        test_token = "expired-token-xyz789"
        test_email = "expired@example.com"
        # Token expired 5 minutes ago
        past_expiry = datetime.now(timezone.utc) - timedelta(minutes=5)

        # Mock the pool and connection
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        service.pool = mock_pool

        # Database returns a token record with expired timestamp
        mock_conn.fetchrow.return_value = {
            "email": test_email,
            "expires_at": past_expiry,
            "used": False,
        }

        result = await service.validate_token(test_token)
        assert result is None, (
            f"Expected None for expired token, but got {result!r}"
        )

    @pytest.mark.asyncio
    async def test_non_expired_token_accepted(self):
        """Complementary: a token that hasn't expired should return the email."""
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            service = ResetTokenService(database_url="postgresql://fake:5432/test")

        test_token = "valid-token-abc456"
        test_email = "valid@example.com"
        future_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)

        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        service.pool = mock_pool

        mock_conn.fetchrow.return_value = {
            "email": test_email,
            "expires_at": future_expiry,
            "used": False,
        }

        result = await service.validate_token(test_token)
        assert result == test_email, (
            f"Expected {test_email!r} for valid token, but got {result!r}"
        )


# --- Property Test 11.5: Password Rule Specificity (Property 13) ---
# Validates: Requirements 2.6

class TestPasswordRuleSpecificity:
    """
    **Validates: Requirements 2.6**

    When a password fails validation, the error response contains exactly the
    failed rules, not generic messages. Each failure message must be one of the
    5 specific rule messages.
    """

    def setup_method(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake:5432/test"}):
            self.service = PasswordService(database_url="postgresql://fake:5432/test")

    @given(st.text())
    @settings(max_examples=200)
    def test_rule_specificity(self, password: str):
        failures = self.service.validate_password(password)

        # Every failure message must be one of the known specific rule messages
        for msg in failures:
            assert msg in KNOWN_RULE_MESSAGES, (
                f"Unexpected failure message: {msg!r}. "
                f"Must be one of: {KNOWN_RULE_MESSAGES}"
            )

        # No duplicates in the failure list
        assert len(failures) == len(set(failures)), (
            f"Duplicate failure messages found: {failures}"
        )
