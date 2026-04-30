# Appstle Subscription Logic Investigation

Date: April 15, 2026

## Background

We use the Appstle API to determine whether a customer has an active subscription to MC ChatMaster. The original implementation relied on customer tags returned by the API to determine subscription status. During testing, we discovered that tags are not reliably updated when subscription status changes, leading to incorrect access decisions.

## API Flow (Two-Step)

### Step 1: Look up customer by email
```
GET {APPSTLE_API_URL}/api/external/v2/subscription-contract-details/customers?email={email}
Header: X-API-Key: {APPSTLE_API_KEY}
```
Returns a list of customer records. We extract `customerId` from the first result.

### Step 2: Get customer details (including tags and contracts)
```
GET {APPSTLE_API_URL}/api/external/v2/subscription-customers/{customerId}
Header: X-API-Key: {APPSTLE_API_KEY}
```
Returns full customer record with tags, productSubscriberStatus, and subscription contracts.

## What the API Returns (Actual Data — April 15, 2026)

### Customer 1: kevin.vandever@mac.com (should have access — within 30-day period)
- **customerId**: 8252308979777
- **productSubscriberStatus**: PAUSED
- **tags**: `["appstle_subscription_active_customer", "Login with Shop", "Shop"]`
- **Contract status**: PAUSED
- **Contract createdAt**: 2026-03-23
- **nextBillingDate**: 2026-04-22 (still in the future)
- **billingPolicy**: 30 DAY interval
- **Issue**: Tag still says `active_customer` even though subscription is PAUSED

### Customer 2: dmu@mcpressonline.com (should NOT have access — 30 days expired)
- **customerId**: 2788747591
- **productSubscriberStatus**: PAUSED
- **tags**: `["appstle_subscription_paused_customer"]`
- **Contract status**: PAUSED
- **Contract createdAt**: 2026-03-10
- **nextBillingDate**: 2026-04-09 (already passed)
- **billingPolicy**: 30 DAY interval
- **Issue**: Tag correctly says `paused_customer`, but this user can still access the app as free-tier

## Current Logic (Tag-Based)

File: `backend/subscription_auth.py`

The current code checks customer tags to determine status:

```python
def _derive_status_from_tags(tags, config):
    # Priority: active > paused > inactive > not_found
    if any tag matches "appstle_subscription_active_customer" → return "active"
    if any tag matches "appstle_subscription_paused_customer" → return "paused"
    if any tag matches "appstle_subscription_inactive_customer" → return "inactive"
    return "not_found"
```

Then in the login flow:
```python
if appstle_resp.is_valid and normalized == "active":
    subscription_status = "active"    # unlimited access
else:
    subscription_status = "free"      # limited questions via usage gate
```

### Problems with Current Logic

1. **Tags are unreliable**: Customer 1 has `active_customer` tag despite being PAUSED. Appstle doesn't consistently update tags when subscription status changes.

2. **Nobody is ever denied**: The login flow maps everything that isn't "active" to "free" tier. Paused, inactive, cancelled — they all get in with limited questions. There is no "denied" path.

3. **No billing period check**: A paused subscription with paid time remaining (nextBillingDate in the future) should still grant access. The current logic doesn't consider this.

## Proposed Logic (Contract-Based)

Instead of relying on tags, use `productSubscriberStatus` and `nextBillingDate` from the subscription contract:

```
ACTIVE contract status → access granted (subscription_status = "active")

PAUSED contract status + nextBillingDate in the future → access granted
  (user has paid time remaining)

PAUSED contract status + nextBillingDate in the past or null → access denied
  (paid period has expired)

CANCELLED contract status → access denied

No subscription found → fall through to free-tier logic
```

### Why This Is Better

- `productSubscriberStatus` and contract `status` are always accurate (they reflect the actual Shopify subscription state)
- `nextBillingDate` tells us exactly when the paid period ends
- No dependency on tags being updated correctly
- Clear distinction between "paid time remaining" and "expired"

### Fields to Use from Step 2 Response

| Field | Location | Purpose |
|-------|----------|---------|
| `productSubscriberStatus` | Top-level | Overall subscriber status (ACTIVE, PAUSED, CANCELLED) |
| `status` | `subscriptionContracts.nodes[0].status` | Individual contract status |
| `nextBillingDate` | `subscriptionContracts.nodes[0].nextBillingDate` | End of current paid period |
| `createdAt` | `subscriptionContracts.nodes[0].createdAt` | When subscription started |

### Code Changes Needed

File: `backend/subscription_auth.py`

1. Modify `_parse_tags_response()` (or create new method) to extract `productSubscriberStatus` and `nextBillingDate` from the API response
2. Update `verify_subscription()` to return these fields in `AppstleSubscriptionResponse`
3. Update the login flow (step 4) to use contract-based logic instead of tag-based
4. Add datetime comparison for `nextBillingDate` vs current UTC time

## Appstle Support Ticket

Submitted April 15, 2026. Asked about:
- Why tags aren't updated consistently when subscriptions are paused
- Whether `productSubscriberStatus` + `nextBillingDate` is the recommended approach
- Awaiting response (typically 1-2 days)

## Decision

Pending Appstle's response. If they confirm tags are unreliable or can't guarantee sync, we proceed with the contract-based approach. If they provide a fix for tag syncing, we may keep the tag-based approach but add `nextBillingDate` as a secondary check.

Either way, the login flow needs to be updated to actually deny access for expired subscriptions instead of falling through to free tier.
