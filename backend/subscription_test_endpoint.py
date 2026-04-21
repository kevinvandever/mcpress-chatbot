"""
Test endpoint for subscription status bug exploration.

This endpoint exercises the login decision logic in SubscriptionAuthService
with controlled AppstleSubscriptionResponse inputs, bypassing the actual
Appstle API. This allows us to test how the login method's step 4 handles
different subscription statuses (PAUSED, CANCELLED, ACTIVE, etc.) without
needing real Appstle API responses.

The endpoint constructs an AppstleSubscriptionResponse from the provided
contract data (productSubscriberStatus + nextBillingDate) and then runs
the EXACT same step 4 decision logic from the login method.

This endpoint is for TESTING ONLY and should be removed after the bugfix
is verified.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

try:
    from backend.subscription_auth import (
        SubscriptionAuthService,
        AppstleSubscriptionResponse,
        _normalize_status,
        LoginSuccessResponse,
        LoginDeniedResponse,
    )
except ImportError:
    from subscription_auth import (
        SubscriptionAuthService,
        AppstleSubscriptionResponse,
        _normalize_status,
        LoginSuccessResponse,
        LoginDeniedResponse,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])

# Instantiate the service to access its methods and config
_service = SubscriptionAuthService()


class SubscriptionTestRequest(BaseModel):
    """Request body for the subscription decision test endpoint.

    Simulates contract data from the Appstle API so we can test
    the login step 4 decision logic in isolation.
    """
    email: str = "test@example.com"
    product_subscriber_status: Optional[str] = None  # "ACTIVE", "PAUSED", "CANCELLED", or None
    next_billing_date: Optional[str] = None  # ISO 8601 datetime string, or null
    has_subscription: bool = True  # Whether the user has an Appstle record at all


class SubscriptionTestResponse(BaseModel):
    """Response from the subscription decision test endpoint."""
    status_code: int
    body: dict
    debug: dict  # Extra debug info about what the decision logic saw


@router.post("/subscription-decision")
async def test_subscription_decision(req: SubscriptionTestRequest):
    """
    Test the login method's step 4 subscription decision logic
    with controlled contract data.

    This bypasses:
    - Rate limiting
    - Appstle API calls (steps 1-3)
    - Password verification (steps 5-7)
    - Token creation (step 8)

    It constructs an AppstleSubscriptionResponse from the provided
    contract data and then runs the EXACT same step 4 logic from
    the login method to determine subscription_status.

    The contract data (product_subscriber_status, next_billing_date)
    represents what the Appstle API step 2 response contains. The
    current code ignores this data and uses tags instead — that's
    the bug we're testing.
    """
    # Parse next_billing_date if provided
    parsed_billing_date = None
    if req.next_billing_date:
        try:
            parsed_billing_date = datetime.fromisoformat(req.next_billing_date)
        except (ValueError, TypeError):
            parsed_billing_date = None

    # Build an AppstleSubscriptionResponse that represents what
    # _parse_tags_response CURRENTLY returns for the given contract data.
    #
    # This is the crux of the bug: _parse_tags_response uses customer tags
    # (which are unreliable) instead of productSubscriberStatus and
    # nextBillingDate from the contract data.
    #
    # Current _parse_tags_response behavior:
    # - If tags contain "active" or "paused" pattern → is_valid=True, status="ACTIVE"
    # - If tags contain "inactive" pattern → is_valid=False, status="CANCELLED"
    # - No recognized tags → is_valid=False, status=None
    #
    # Since we're simulating with contract data, we map:
    # - ACTIVE → tags would show "active" → is_valid=True, status="ACTIVE"
    # - PAUSED → tags would show "paused" → is_valid=True, status="ACTIVE" (BUG!)
    # - CANCELLED → tags would show "inactive" → is_valid=False, status="CANCELLED"
    # - None/no subscription → is_valid=False, status=None

    if not req.has_subscription:
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status=None,
            expiration_date=None,
            customer_email=req.email,
        )
    elif req.product_subscriber_status and req.product_subscriber_status.upper() == "ACTIVE":
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=True,
            subscription_status="ACTIVE",
            expiration_date=None,
            customer_email=req.email,
        )
    elif req.product_subscriber_status and req.product_subscriber_status.upper() == "PAUSED":
        # BUG: _parse_tags_response treats PAUSED same as ACTIVE via tags
        # The tag "appstle_subscription_paused_customer" maps to is_valid=True, status="ACTIVE"
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=True,
            subscription_status="ACTIVE",
            expiration_date=None,
            customer_email=req.email,
        )
    elif req.product_subscriber_status and req.product_subscriber_status.upper() == "CANCELLED":
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status="CANCELLED",
            expiration_date=None,
            customer_email=req.email,
        )
    else:
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status=req.product_subscriber_status,
            expiration_date=None,
            customer_email=req.email,
        )

    # ---------------------------------------------------------------
    # Run the EXACT same step 4 logic from the login method
    # This is copied verbatim from SubscriptionAuthService.login()
    # ---------------------------------------------------------------
    raw_status = appstle_resp.subscription_status
    normalized = _normalize_status(raw_status)

    if appstle_resp.is_valid and normalized == "active":
        subscription_status = "active"
    else:
        subscription_status = "free"

    # Build the response exactly as the login method would
    result_body = LoginSuccessResponse(
        token="test-token-not-real",
        email=req.email,
        subscription_status=subscription_status,
        expires_at=None,
    ).model_dump()
    result_status_code = 200

    # Note: The current code NEVER returns 403 from step 4.
    # There is no denial path. This is the bug.

    debug_info = {
        "input_product_subscriber_status": req.product_subscriber_status,
        "input_next_billing_date": req.next_billing_date,
        "input_has_subscription": req.has_subscription,
        "parsed_billing_date": str(parsed_billing_date) if parsed_billing_date else None,
        "appstle_resp_is_valid": appstle_resp.is_valid,
        "appstle_resp_subscription_status": appstle_resp.subscription_status,
        "normalized_status": normalized,
        "final_subscription_status": subscription_status,
        "final_status_code": result_status_code,
        "note": (
            "This endpoint runs the EXACT step 4 logic from login(). "
            "The current code has no 403 denial path — all non-active "
            "statuses map to 'free'. PAUSED is treated as ACTIVE via tags."
        ),
    }

    logger.info(
        "Subscription decision test: input_status=%s, next_billing=%s → result=%d/%s",
        req.product_subscriber_status,
        req.next_billing_date,
        result_status_code,
        subscription_status,
    )

    return SubscriptionTestResponse(
        status_code=result_status_code,
        body=result_body,
        debug=debug_info,
    )
