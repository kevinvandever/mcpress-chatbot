"""
Appstle Subscription Authentication Service

Verifies customer subscriptions via the Appstle API and manages
JWT-based session tokens for authenticated users.

This module handles CUSTOMER authentication only.
Admin authentication (backend/auth.py) remains completely separate.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import aiohttp
import jwt
from dataclasses import dataclass, field

from pydantic import BaseModel, EmailStr

# Import RateLimiter from existing auth module
try:
    from backend.auth import RateLimiter
except ImportError:
    from auth import RateLimiter

# Import PasswordService for password authentication
try:
    from backend.password_service import PasswordService
except ImportError:
    from password_service import PasswordService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CustomerLoginRequest(BaseModel):
    """Request body for customer login with email and password."""
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot-password endpoint."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset-password endpoint."""
    token: str
    new_password: str


class AppstleSubscriptionResponse(BaseModel):
    """Parsed response from the Appstle subscription API."""
    is_valid: bool
    subscription_status: Optional[str] = None  # "ACTIVE", "CANCELLED", "EXPIRED", "PAUSED", or None
    expiration_date: Optional[datetime] = None
    customer_email: Optional[str] = None


class LoginSuccessResponse(BaseModel):
    """Returned on successful login with an active subscription."""
    success: bool = True
    token: str
    email: str
    subscription_status: str
    expires_at: Optional[str] = None  # ISO datetime


class LoginDeniedResponse(BaseModel):
    """Returned when login is denied due to subscription issues."""
    success: bool = False
    error: str
    subscription_status: Optional[str] = None
    redirect_url: Optional[str] = None


class RefreshResponse(BaseModel):
    """Returned from the token refresh endpoint."""
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None
    redirect_url: Optional[str] = None


@dataclass(frozen=True)
class TagConfig:
    active_patterns: list[str] = field(default_factory=lambda: ["appstle_subscription_active_customer"])
    paused_patterns: list[str] = field(default_factory=lambda: ["appstle_subscription_paused_customer"])
    inactive_patterns: list[str] = field(default_factory=lambda: ["appstle_subscription_inactive_customer"])


def load_tag_config() -> TagConfig:
    """Read tag patterns from environment variables and return a TagConfig."""
    def _parse_env(var_name: str, default: list[str]) -> list[str]:
        raw = os.getenv(var_name, "")
        patterns = [p.strip().lower() for p in raw.split(",") if p.strip()]
        return patterns if patterns else [d.lower() for d in default]

    return TagConfig(
        active_patterns=_parse_env("SUBSCRIPTION_TAG_ACTIVE", ["appstle_subscription_active_customer"]),
        paused_patterns=_parse_env("SUBSCRIPTION_TAG_PAUSED", ["appstle_subscription_paused_customer"]),
        inactive_patterns=_parse_env("SUBSCRIPTION_TAG_INACTIVE", ["appstle_subscription_inactive_customer"]),
    )


def _derive_status_from_tags(tags: list[str], config: TagConfig) -> str:
    """Derive subscription status from customer tags.

    Returns one of: active, paused, inactive, not_found.
    Priority: active > paused > inactive > not_found.
    """
    lower_tags = [t.lower() for t in tags]

    for tag in lower_tags:
        if tag in config.active_patterns:
            return "active"

    for tag in lower_tags:
        if tag in config.paused_patterns:
            return "paused"

    for tag in lower_tags:
        if tag in config.inactive_patterns:
            return "inactive"

    return "not_found"


# ---------------------------------------------------------------------------
# Status-specific denial messages
# ---------------------------------------------------------------------------

DENIAL_MESSAGES: Dict[str, str] = {
    "EXPIRED": "Your subscription has expired",
    "PAUSED": "Your subscription is paused",
    "CANCELLED": "Your subscription has been cancelled",
}

# Default message for not_found, unknown, empty, or any other status
DEFAULT_DENIAL_MESSAGE = "No subscription found"


def _get_denial_message(status: Optional[str]) -> str:
    """Return the user-facing denial message for a given subscription status."""
    if not status:
        return DEFAULT_DENIAL_MESSAGE
    return DENIAL_MESSAGES.get(status.upper(), DEFAULT_DENIAL_MESSAGE)


def _normalize_status(status: Optional[str]) -> str:
    """Normalize a subscription status string for response payloads."""
    if not status:
        return "not_found"
    mapping = {
        "ACTIVE": "active",
        "CANCELLED": "cancelled",
        "EXPIRED": "expired",
        "PAUSED": "paused",
    }
    return mapping.get(status.upper(), "not_found")


# ---------------------------------------------------------------------------
# SubscriptionAuthService
# ---------------------------------------------------------------------------

class SubscriptionAuthService:
    """
    Verifies customer credentials against the Appstle subscription API,
    issues and validates JWT session tokens, and handles token refresh.
    """

    def __init__(self):
        self.appstle_api_url: Optional[str] = os.getenv("APPSTLE_API_URL")
        self.appstle_api_key: Optional[str] = os.getenv("APPSTLE_API_KEY")
        self.jwt_secret: str = os.getenv("JWT_SECRET_KEY", "")
        self.signup_url: str = os.getenv("SUBSCRIPTION_SIGNUP_URL", "")

        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=1)
        self.grace_window = timedelta(minutes=5)
        self.appstle_timeout = 10  # seconds

        # Rate limiter: 5 attempts per IP per 15 minutes
        self.rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)

        # Password service for local password authentication
        try:
            self.password_service = PasswordService()
        except Exception as exc:
            logger.warning("⚠️ PasswordService initialization failed: %s — password auth disabled", exc)
            self.password_service = None

        # Configuration health check
        self._config_valid = True
        if not self.appstle_api_url:
            logger.warning("⚠️ APPSTLE_API_URL is not set — subscription verification disabled")
            self._config_valid = False
        if not self.appstle_api_key:
            logger.warning("⚠️ APPSTLE_API_KEY is not set — subscription verification disabled")
            self._config_valid = False
        if not self.jwt_secret:
            logger.warning("⚠️ JWT_SECRET_KEY is not set — token signing will fail")
            self._config_valid = False
        if not self.signup_url:
            logger.warning("⚠️ SUBSCRIPTION_SIGNUP_URL is not set — redirect URLs will be empty")

        # Tag-based subscription config
        self.tag_config = load_tag_config()

        logger.info("Loaded tag config: active=%s, paused=%s, inactive=%s",
                     self.tag_config.active_patterns, self.tag_config.paused_patterns,
                     self.tag_config.inactive_patterns)

    # ------------------------------------------------------------------
    # _extract_customer_tags
    # ------------------------------------------------------------------
    def _extract_customer_tags(self, customer: dict) -> list[str]:
        """Extract tag strings from a customer record."""
        raw_tags = customer.get("customerTags") or customer.get("tags")

        if raw_tags is None:
            return []

        if not isinstance(raw_tags, list):
            logger.warning("Unexpected tags structure: %s", type(raw_tags))
            return []

        tags = []
        for item in raw_tags:
            if isinstance(item, str):
                tags.append(item)
            elif isinstance(item, dict):
                tag_value = item.get("name") or item.get("value") or item.get("tag")
                if tag_value and isinstance(tag_value, str):
                    tags.append(tag_value)
            else:
                logger.warning("Unexpected tag item type: %s", type(item))

        return tags

    # ------------------------------------------------------------------
    # _parse_tags_response
    # ------------------------------------------------------------------
    def _parse_tags_response(self, data: Any, email: str) -> AppstleSubscriptionResponse:
        """Parse Appstle API response using customer tags to determine subscription status."""
        # Normalize: extract the customer list from the response
        customers = []
        if isinstance(data, list):
            customers = data
        elif isinstance(data, dict):
            customers = data.get("content", [])
            if not customers and (data.get("email") or data.get("tags") or data.get("id")):
                customers = [data]

        if not customers:
            logger.info("No customers found in Appstle response for email=%s", email)
            return AppstleSubscriptionResponse(
                is_valid=False, subscription_status=None, customer_email=email,
            )

        # Check each customer's tags
        for customer in customers:
            tags = self._extract_customer_tags(customer)
            logger.info("Extracted tags for email=%s: %s", email, tags)

            status = _derive_status_from_tags(tags, self.tag_config)
            logger.info("Derived status for email=%s: %s (matched from tags)", email, status)

            if status in ("active", "paused"):
                return AppstleSubscriptionResponse(
                    is_valid=True, subscription_status="ACTIVE", customer_email=email,
                )
            elif status == "inactive":
                return AppstleSubscriptionResponse(
                    is_valid=False, subscription_status="CANCELLED", customer_email=email,
                )

        # No recognized tags found in any customer
        return AppstleSubscriptionResponse(
            is_valid=False, subscription_status=None, customer_email=email,
        )

    # ------------------------------------------------------------------
    # verify_subscription
    # ------------------------------------------------------------------
    async def verify_subscription(self, email: str) -> AppstleSubscriptionResponse:
        """
        Two-step Appstle API flow to check subscription status via customer tags.

        Step 1: GET {APPSTLE_API_URL}/api/external/v2/subscription-contract-details/customers?email={email}
                → Extract customerId from the first customer record.

        Step 2: GET {APPSTLE_API_URL}/api/external/v2/subscription-customers/{customerId}
                → Get full customer details including tags array.

        Step 3: Pass the customer data (with tags) to _parse_tags_response.

        Both endpoints use the same base URL and API key.

        Returns an AppstleSubscriptionResponse with parsed fields.
        Raises:
            aiohttp.ClientError on network issues
            asyncio.TimeoutError on timeout
            ValueError on malformed response
        """
        headers = {"X-API-Key": self.appstle_api_key}
        timeout = aiohttp.ClientTimeout(total=self.appstle_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Step 1: Look up customerId by email
            step1_url = f"{self.appstle_api_url}/api/external/v2/subscription-contract-details/customers"
            params = {"email": email}

            async with session.get(step1_url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logger.error(
                        "Appstle API (step 1) returned status %d for email=%s",
                        resp.status, email,
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=f"Appstle API returned {resp.status}",
                    )

                try:
                    step1_data = await resp.json()
                except Exception as exc:
                    logger.error("Malformed JSON from Appstle API (step 1): %s", exc)
                    raise ValueError(f"Malformed Appstle response: {exc}") from exc

                logger.info(
                    "Appstle API step 1 response for email=%s: %s",
                    email, str(step1_data)[:500],
                )

            # Extract customerId from step 1 response
            customer_id = self._extract_customer_id(step1_data)
            if customer_id is None:
                logger.info("No customerId found for email=%s — no subscription", email)
                return AppstleSubscriptionResponse(
                    is_valid=False, subscription_status=None, customer_email=email,
                )

            # Step 2: Get full customer details (including tags) by customerId
            step2_url = f"{self.appstle_api_url}/api/external/v2/subscription-customers/{customer_id}"

            async with session.get(step2_url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(
                        "Appstle API (step 2) returned status %d for customerId=%s email=%s",
                        resp.status, customer_id, email,
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=f"Appstle API step 2 returned {resp.status}",
                    )

                try:
                    step2_data = await resp.json()
                except Exception as exc:
                    logger.error("Malformed JSON from Appstle API (step 2): %s", exc)
                    raise ValueError(f"Malformed Appstle response: {exc}") from exc

                logger.info(
                    "Appstle API step 2 response for email=%s: %s",
                    email, str(step2_data)[:500],
                )

                # Step 3: Parse the customer data (with tags) to determine status
                return self._parse_tags_response(step2_data, email)

    # ------------------------------------------------------------------
    # _extract_customer_id
    # ------------------------------------------------------------------
    def _extract_customer_id(self, data: Any) -> Optional[int]:
        """Extract the customerId from the step 1 Appstle API response.

        The response is typically a list of customer records like:
        [{"customerId": 123, "email": "...", ...}]

        Returns the customerId of the first customer, or None if not found.
        """
        customers = []
        if isinstance(data, list):
            customers = data
        elif isinstance(data, dict):
            customers = data.get("content", [])
            if not customers and data.get("customerId"):
                customers = [data]

        for customer in customers:
            if isinstance(customer, dict):
                cid = customer.get("customerId")
                if cid is not None:
                    return cid

        return None

    # ------------------------------------------------------------------
    # create_token
    # ------------------------------------------------------------------
    def create_token(
        self,
        email: str,
        subscription_status: str,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """
        Create a JWT with the following claims:
          - sub: user email
          - subscription_status: e.g. "active"
          - subscription_expires_at: unix timestamp (or None)
          - iat: issued-at unix timestamp
          - exp: iat + 1 hour
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": email,
            "subscription_status": subscription_status,
            "subscription_expires_at": (
                int(expires_at.timestamp()) if expires_at else None
            ),
            "iat": int(now.timestamp()),
            "exp": int((now + self.token_expiry).timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)

    # ------------------------------------------------------------------
    # verify_token
    # ------------------------------------------------------------------
    def verify_token(
        self, token: str, allow_grace: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Decode and verify a JWT.

        If allow_grace=True, tokens that expired within the last 5 minutes
        are still accepted (used for the refresh flow).

        Returns the decoded claims dict, or None if verification fails.
        """
        try:
            claims = jwt.decode(
                token, self.jwt_secret, algorithms=[self.algorithm]
            )
            return claims
        except jwt.ExpiredSignatureError:
            if not allow_grace:
                return None
            # Decode without verifying expiration to check grace window
            try:
                claims = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False},
                )
                exp = claims.get("exp", 0)
                now = datetime.now(timezone.utc).timestamp()
                if now - exp <= self.grace_window.total_seconds():
                    return claims
                return None
            except jwt.InvalidTokenError:
                return None
        except jwt.InvalidTokenError:
            return None


    # ------------------------------------------------------------------
    # login
    # ------------------------------------------------------------------
    async def login(
        self, email: str, password: str, client_ip: str
    ) -> Dict[str, Any]:
        """
        Full login flow — subscription check always comes first:
        1. Check configuration
        2. Check rate limit for client_ip
        3. Call Appstle API to verify subscription (always, for all users)
        4. If subscription not valid → deny immediately (no password check)
        5. Lookup customer_passwords record by email
        6a. If record exists: verify password → if mismatch, return 401
        6b. If no record (new user): validate password rules → if fail, return 400
        7. If new user + active subscription: create customer_passwords record
        8. Return success with token

        Returns a dict with keys:
          - status_code: int (200, 400, 401, 403, 429, 500, 503)
          - body: LoginSuccessResponse | LoginDeniedResponse (as dict)
        """
        import asyncio

        # 1. Configuration check
        if not self._config_valid:
            logger.warning("Login attempt with missing Appstle configuration")
            return {
                "status_code": 503,
                "body": LoginDeniedResponse(
                    error="Subscription service temporarily unavailable",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }

        # 2. Rate limit check
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for IP %s", client_ip)
            return {
                "status_code": 429,
                "body": LoginDeniedResponse(
                    error="Too many login attempts. Please try again later.",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }

        # 3. Call Appstle API to verify subscription FIRST (for all users)
        try:
            appstle_resp = await self.verify_subscription(email)
        except asyncio.TimeoutError:
            logger.error("Appstle API timeout for email=%s", email)
            return {
                "status_code": 503,
                "body": LoginDeniedResponse(
                    error="Subscription service temporarily unavailable",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }
        except aiohttp.ClientResponseError as exc:
            logger.error("Appstle API error: status=%s for email=%s", exc.status, email)
            return {
                "status_code": 503,
                "body": LoginDeniedResponse(
                    error="Subscription service temporarily unavailable",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }
        except ValueError as exc:
            logger.error("Malformed Appstle response for email=%s: %s", email, exc)
            return {
                "status_code": 500,
                "body": LoginDeniedResponse(
                    error="An unexpected error occurred",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }
        except Exception as exc:
            logger.error("Unexpected error calling Appstle API for email=%s: %s", email, exc)
            return {
                "status_code": 503,
                "body": LoginDeniedResponse(
                    error="Subscription service temporarily unavailable",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }

        # 4. Evaluate subscription status — deny immediately if not active
        raw_status = appstle_resp.subscription_status
        normalized = _normalize_status(raw_status)

        if not (appstle_resp.is_valid and normalized == "active"):
            message = _get_denial_message(raw_status)
            logger.info(
                "Login denied for email=%s: status=%s message=%s",
                email, raw_status, message,
            )
            return {
                "status_code": 403,
                "body": LoginDeniedResponse(
                    error=message,
                    subscription_status=normalized,
                    redirect_url=self.signup_url or None,
                ).model_dump(),
            }

        # 5. Subscription is active — now check password
        existing_record = None
        is_new_user = True
        if self.password_service:
            try:
                existing_record = await self.password_service.get_customer(email)
                is_new_user = existing_record is None
            except Exception as exc:
                logger.error("Error looking up password record for email=%s: %s", email, exc)
                # Continue without password check if DB is unavailable

        # 6a. Existing user: verify password against stored hash
        if existing_record:
            try:
                password_valid = self.password_service.verify_password(
                    password, existing_record["password_hash"]
                )
            except Exception as exc:
                logger.error("Error verifying password for email=%s: %s", email, exc)
                return {
                    "status_code": 500,
                    "body": LoginDeniedResponse(
                        error="An unexpected error occurred",
                        subscription_status=None,
                        redirect_url=None,
                    ).model_dump(),
                }

            if not password_valid:
                logger.info("Password mismatch for email=%s", email)
                return {
                    "status_code": 401,
                    "body": LoginDeniedResponse(
                        error="Invalid email or password",
                        subscription_status=None,
                        redirect_url=None,
                    ).model_dump(),
                }

        # 6b. New user: validate password rules
        if is_new_user and self.password_service:
            failed_rules = self.password_service.validate_password(password)
            if failed_rules:
                logger.info("Password validation failed for new user email=%s: %s", email, failed_rules)
                return {
                    "status_code": 400,
                    "body": {
                        "success": False,
                        "error": "Password validation failed",
                        "failed_rules": failed_rules,
                    },
                }

        # 7. New user with active subscription: create password record
        if is_new_user and self.password_service:
            try:
                await self.password_service.create_customer(email, password)
                logger.info("Created password record for new user email=%s", email)
            except Exception as exc:
                logger.error("Failed to create password record for email=%s: %s", email, exc)
                # Don't block login if record creation fails

        # 8. Success — reset rate limiter and issue token
        self.rate_limiter.reset(client_ip)

        token = self.create_token(
            email=email,
            subscription_status="active",
            expires_at=appstle_resp.expiration_date,
        )

        expires_at_iso = (
            appstle_resp.expiration_date.isoformat()
            if appstle_resp.expiration_date
            else None
        )

        logger.info("Successful login for email=%s", email)
        return {
            "status_code": 200,
            "body": LoginSuccessResponse(
                token=token,
                email=email,
                subscription_status="active",
                expires_at=expires_at_iso,
            ).model_dump(),
        }


    # ------------------------------------------------------------------
    # refresh
    # ------------------------------------------------------------------
    async def refresh(self, token: str) -> Dict[str, Any]:
        """
        Refresh flow:
        1. Verify existing token with grace window (allow 5 min expired)
        2. Re-verify subscription with Appstle API
        3. Issue new token if still active, or return 403

        Returns a dict with keys:
          - status_code: int (200, 401, 403, 503)
          - body: RefreshResponse (as dict)
        """
        import asyncio

        # 1. Verify token (with grace window)
        claims = self.verify_token(token, allow_grace=True)
        if claims is None:
            return {
                "status_code": 401,
                "body": RefreshResponse(
                    success=False,
                    error="Token expired beyond grace window",
                ).model_dump(),
            }

        email = claims.get("sub", "")

        # 2. Configuration check
        if not self._config_valid:
            return {
                "status_code": 503,
                "body": RefreshResponse(
                    success=False,
                    error="Subscription service temporarily unavailable",
                ).model_dump(),
            }

        # 3. Re-verify subscription
        try:
            appstle_resp = await self.verify_subscription(email)
        except asyncio.TimeoutError:
            logger.error("Appstle API timeout during refresh for email=%s", email)
            return {
                "status_code": 503,
                "body": RefreshResponse(
                    success=False,
                    error="Subscription service temporarily unavailable",
                ).model_dump(),
            }
        except Exception as exc:
            logger.error("Appstle API error during refresh for email=%s: %s", email, exc)
            return {
                "status_code": 503,
                "body": RefreshResponse(
                    success=False,
                    error="Subscription service temporarily unavailable",
                ).model_dump(),
            }

        # 4. Check if still active
        normalized = _normalize_status(appstle_resp.subscription_status)

        if appstle_resp.is_valid and normalized == "active":
            new_token = self.create_token(
                email=email,
                subscription_status="active",
                expires_at=appstle_resp.expiration_date,
            )
            logger.info("Token refreshed for email=%s", email)
            return {
                "status_code": 200,
                "body": RefreshResponse(
                    success=True,
                    token=new_token,
                ).model_dump(),
            }
        else:
            logger.info("Refresh denied for email=%s: subscription no longer active", email)
            return {
                "status_code": 403,
                "body": RefreshResponse(
                    success=False,
                    error="Subscription no longer active",
                    redirect_url=self.signup_url or None,
                ).model_dump(),
            }
