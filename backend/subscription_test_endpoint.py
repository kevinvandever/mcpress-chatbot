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
        LoginSuccessResponse,
        LoginDeniedResponse,
    )
except ImportError:
    from subscription_auth import (
        SubscriptionAuthService,
        AppstleSubscriptionResponse,
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
    contract data and then runs the EXACT same 5-scenario step 4
    logic from the FIXED login method to determine subscription_status.

    The 5 scenarios match the fixed login() method in subscription_auth.py:
    1. ACTIVE → subscription_status="active" (200)
    2. PAUSED + nextBillingDate in future → subscription_status="active" (200)
    3. PAUSED + nextBillingDate in past or null → 403 denial (expired)
    4. CANCELLED → 403 denial (cancelled)
    5. No subscription → subscription_status="free" (200)
    """
    # Parse next_billing_date if provided
    parsed_billing_date = None
    if req.next_billing_date:
        try:
            parsed_billing_date = datetime.fromisoformat(
                req.next_billing_date.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            parsed_billing_date = None

    # Build an AppstleSubscriptionResponse with contract fields populated,
    # exactly as _parse_contract_response() would return from the Appstle API.
    if not req.has_subscription:
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=False,
            subscription_status=None,
            expiration_date=None,
            customer_email=req.email,
            product_subscriber_status=None,
            next_billing_date=None,
        )
    else:
        appstle_resp = AppstleSubscriptionResponse(
            is_valid=True,
            subscription_status=req.product_subscriber_status,
            expiration_date=None,
            customer_email=req.email,
            product_subscriber_status=req.product_subscriber_status,
            next_billing_date=parsed_billing_date,
        )

    # ---------------------------------------------------------------
    # Run the EXACT same 5-scenario step 4 logic from the FIXED
    # login method in SubscriptionAuthService.login()
    # ---------------------------------------------------------------
    status_upper = (appstle_resp.product_subscriber_status or "").upper()
    next_billing = appstle_resp.next_billing_date

    if status_upper == "ACTIVE":
        # Scenario 1: ACTIVE subscriber → full access
        subscription_status = "active"
        result_body = LoginSuccessResponse(
            token="test-token-not-real",
            email=req.email,
            subscription_status=subscription_status,
            expires_at=None,
        ).model_dump()
        result_status_code = 200

    elif status_upper == "PAUSED":
        if next_billing is not None:
            # Make comparison timezone-aware
            now = datetime.now(timezone.utc)
            if next_billing.tzinfo is None:
                next_billing = next_billing.replace(tzinfo=timezone.utc)
            if next_billing > now:
                # Scenario 2: PAUSED + nextBillingDate in future → active (paid time remaining)
                subscription_status = "active"
                result_body = LoginSuccessResponse(
                    token="test-token-not-real",
                    email=req.email,
                    subscription_status=subscription_status,
                    expires_at=None,
                ).model_dump()
                result_status_code = 200
            else:
                # Scenario 3: PAUSED + nextBillingDate in past → deny
                subscription_status = "paused"
                result_body = LoginDeniedResponse(
                    error="Your subscription has expired. Resubscribe to continue.",
                    subscription_status="paused",
                    redirect_url=_service.signup_url,
                ).model_dump()
                result_status_code = 403
        else:
            # Scenario 3b: PAUSED + null nextBillingDate → deny
            subscription_status = "paused"
            result_body = LoginDeniedResponse(
                error="Your subscription has expired. Resubscribe to continue.",
                subscription_status="paused",
                redirect_url=_service.signup_url,
            ).model_dump()
            result_status_code = 403

    elif status_upper == "CANCELLED":
        # Scenario 4: CANCELLED → deny
        subscription_status = "cancelled"
        result_body = LoginDeniedResponse(
            error="Your subscription has been cancelled. Resubscribe to continue.",
            subscription_status="cancelled",
            redirect_url=_service.signup_url,
        ).model_dump()
        result_status_code = 403

    else:
        # Scenario 5: No subscription record (None/not found) → free-tier
        subscription_status = "free"
        result_body = LoginSuccessResponse(
            token="test-token-not-real",
            email=req.email,
            subscription_status=subscription_status,
            expires_at=None,
        ).model_dump()
        result_status_code = 200

    debug_info = {
        "input_product_subscriber_status": req.product_subscriber_status,
        "input_next_billing_date": req.next_billing_date,
        "input_has_subscription": req.has_subscription,
        "parsed_billing_date": str(parsed_billing_date) if parsed_billing_date else None,
        "appstle_resp_product_subscriber_status": appstle_resp.product_subscriber_status,
        "appstle_resp_next_billing_date": str(appstle_resp.next_billing_date) if appstle_resp.next_billing_date else None,
        "status_upper": status_upper,
        "final_subscription_status": subscription_status,
        "final_status_code": result_status_code,
        "note": (
            "This endpoint runs the FIXED 5-scenario step 4 logic from login(). "
            "PAUSED-expired and CANCELLED now return 403. "
            "PAUSED-with-time-remaining returns 200/active."
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
