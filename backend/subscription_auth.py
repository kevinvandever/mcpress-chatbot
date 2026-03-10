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
from pydantic import BaseModel, EmailStr

# Import RateLimiter from existing auth module
try:
    from backend.auth import RateLimiter
except ImportError:
    from auth import RateLimiter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CustomerLoginRequest(BaseModel):
    """Request body for customer login (email-only, no password)."""
    email: EmailStr


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


    # ------------------------------------------------------------------
    # verify_subscription
    # ------------------------------------------------------------------
    async def verify_subscription(self, email: str) -> AppstleSubscriptionResponse:
        """
        Call the Appstle API to check subscription status for the given email.

        GET {APPSTLE_API_URL}/api/external/v2/subscription-contract-details/customers?email={email}
        Headers: X-API-Key: {APPSTLE_API_KEY}
        Timeout: 10 seconds

        The endpoint returns a paginated list of customers with subscription contracts.
        If the response contains any customer data with subscription contracts, the
        customer has a valid subscription. We look for contracts with ACTIVE status.

        Returns an AppstleSubscriptionResponse with parsed fields.
        Raises:
            aiohttp.ClientError on network issues
            asyncio.TimeoutError on timeout
            ValueError on malformed response
        """
        url = f"{self.appstle_api_url}/api/external/v2/subscription-contract-details/customers"
        headers = {"X-API-Key": self.appstle_api_key}
        params = {"email": email}
        timeout = aiohttp.ClientTimeout(total=self.appstle_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logger.error(
                        "Appstle API returned status %d for email=%s",
                        resp.status, email,
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=f"Appstle API returned {resp.status}",
                    )

                try:
                    data = await resp.json()
                except Exception as exc:
                    logger.error("Malformed JSON from Appstle API: %s", exc)
                    raise ValueError(f"Malformed Appstle response: {exc}") from exc

                logger.info(
                    "Appstle API response for email=%s: %s",
                    email,
                    str(data)[:500],  # Log first 500 chars for debugging
                )

                # Parse the response to determine subscription status.
                # The endpoint returns customer data with subscription contracts.
                # We need to find if any contract has an ACTIVE status.
                return self._parse_subscription_response(data, email)

    # ------------------------------------------------------------------
    # _parse_subscription_response
    # ------------------------------------------------------------------
    def _parse_subscription_response(
        self, data: Any, email: str
    ) -> AppstleSubscriptionResponse:
        """
        Parse the Appstle /subscription-contract-details/customers response.

        The response may be:
        - A paginated object with a "content" list of customers
        - A list of customers directly
        - An empty list/object if no customer found

        Each customer may have "subscriptionContracts" with "edges" containing
        contract nodes with a "status" field (ACTIVE, PAUSED, CANCELLED, EXPIRED, FAILED).

        We consider the customer to have a valid subscription if ANY contract
        has an ACTIVE status.
        """
        # Normalize: extract the customer list from the response
        customers = []
        if isinstance(data, list):
            customers = data
        elif isinstance(data, dict):
            # Paginated response: {"content": [...], "pageable": {...}, ...}
            customers = data.get("content", [])
            # If "content" is not present, maybe the response IS the customer
            if not customers and data.get("email"):
                customers = [data]

        if not customers:
            logger.info("No customers found in Appstle response for email=%s", email)
            return AppstleSubscriptionResponse(
                is_valid=False,
                subscription_status=None,
                expiration_date=None,
                customer_email=email,
            )

        # Look through all customers (should typically be 1 for an email filter)
        best_status = None
        best_expiration = None
        found_active = False

        for customer in customers:
            customer_email = customer.get("email") or customer.get("customerEmail")

            # ----- Strategy 1: Check summary-level activeSubscriptions field -----
            # The Appstle customer-list endpoint returns a summary with
            # "activeSubscriptions" (int) instead of nested contract objects.
            active_count = customer.get("activeSubscriptions")
            if active_count is not None and int(active_count) > 0:
                found_active = True
                best_status = "ACTIVE"
                # Use nextOrderDate as expiration proxy when available
                next_order = customer.get("nextOrderDate")
                if next_order and not best_expiration:
                    try:
                        best_expiration = datetime.fromisoformat(
                            str(next_order).replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass
                break  # Found active, done

            # ----- Strategy 2: Check nested subscription contracts -----
            contracts = self._extract_contracts(customer)

            for contract in contracts:
                status = contract.get("status", "").upper()

                if status == "ACTIVE":
                    found_active = True
                    best_status = "ACTIVE"
                    # Try to get next billing date as expiration proxy
                    next_billing = contract.get("nextBillingDate")
                    if next_billing and not best_expiration:
                        try:
                            best_expiration = datetime.fromisoformat(
                                str(next_billing).replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass
                    break  # Found active, no need to check more contracts
                elif not best_status or status in ("PAUSED", "CANCELLED", "EXPIRED"):
                    best_status = status

            if found_active:
                break

            # ----- Strategy 3: Infer from inActiveSubscriptions if no contracts -----
            # If no contracts found and no activeSubscriptions, check if
            # inActiveSubscriptions > 0 to determine a non-active status.
            if not contracts and not best_status:
                inactive_count = customer.get("inActiveSubscriptions", 0)
                if inactive_count and int(inactive_count) > 0:
                    best_status = "EXPIRED"  # Best guess for inactive

        return AppstleSubscriptionResponse(
            is_valid=found_active,
            subscription_status=best_status,
            expiration_date=best_expiration,
            customer_email=email,
        )

    # ------------------------------------------------------------------
    # _extract_contracts
    # ------------------------------------------------------------------
    def _extract_contracts(self, customer: dict) -> list:
        """
        Extract subscription contracts from a customer object.

        Handles multiple possible response shapes:
        - customer["subscriptionContracts"]["edges"][*]["node"]
        - customer["subscriptionContracts"][*]  (flat list)
        - customer["contracts"][*]
        """
        contracts = []

        sub_contracts = customer.get("subscriptionContracts")
        if sub_contracts:
            if isinstance(sub_contracts, dict):
                # GraphQL-style: {"edges": [{"node": {...}}, ...]}
                edges = sub_contracts.get("edges", [])
                for edge in edges:
                    node = edge.get("node") if isinstance(edge, dict) else None
                    if node:
                        contracts.append(node)
            elif isinstance(sub_contracts, list):
                contracts.extend(sub_contracts)

        # Fallback: check "contracts" key
        if not contracts:
            alt_contracts = customer.get("contracts", [])
            if isinstance(alt_contracts, list):
                contracts.extend(alt_contracts)

        return contracts


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
        self, email: str, client_ip: str
    ) -> Dict[str, Any]:
        """
        Full login flow:
        1. Check configuration
        2. Check rate limit for client_ip
        3. Call Appstle API to verify subscription by email
        4. Return success with token, or denial with status-specific message

        Returns a dict with keys:
          - status_code: int (200, 403, 429, 500, 503)
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

        # 3. Call Appstle API
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

        # 4. Evaluate subscription status
        raw_status = appstle_resp.subscription_status
        normalized = _normalize_status(raw_status)

        if appstle_resp.is_valid and normalized == "active":
            # Success — reset rate limiter and issue token
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
        else:
            # Denied — subscription not active
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
