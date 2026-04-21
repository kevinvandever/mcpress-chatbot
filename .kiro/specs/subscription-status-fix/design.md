# Subscription Status Fix — Bugfix Design

## Overview

The login flow in `backend/subscription_auth.py` uses unreliable customer tags from the Appstle API to determine subscription status, and maps every non-"active" status to free-tier access. This means paused-expired and cancelled subscribers are never denied — they silently get limited free questions instead of being blocked. Additionally, paused subscribers with paid time remaining (nextBillingDate in the future) are downgraded to free-tier instead of receiving full active access.

The fix replaces tag-based status derivation with contract-based logic using `productSubscriberStatus` and `nextBillingDate` from the Appstle API step 2 response. It introduces a 403 denial path for expired/cancelled subscriptions and correctly grants active access to paused subscribers with remaining paid time. The frontend is updated to handle 403 responses with specific denial messages and resubscribe links.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — when a user has a subscription record with status PAUSED (expired or with time remaining) or CANCELLED, and the system incorrectly maps them to free-tier instead of denying or granting active access
- **Property (P)**: The desired behavior — PAUSED-expired and CANCELLED users are denied with 403; PAUSED-with-time-remaining users get active access
- **Preservation**: Existing behavior for ACTIVE subscribers, no-subscription users, API errors, password failures, and rate limiting must remain unchanged
- **`_parse_tags_response()`**: The method in `subscription_auth.py` that currently extracts customer tags from the Appstle API step 2 response and derives subscription status from them
- **`verify_subscription()`**: The async method that performs the two-step Appstle API flow and returns an `AppstleSubscriptionResponse`
- **`productSubscriberStatus`**: Top-level field in the Appstle step 2 response indicating overall subscriber status (ACTIVE, PAUSED, CANCELLED)
- **`nextBillingDate`**: Field in `subscriptionContracts.nodes[0]` indicating when the current paid period ends
- **`AppstleSubscriptionResponse`**: Pydantic model that holds the parsed Appstle API result; currently lacks `next_billing_date` and `product_subscriber_status` fields
- **FREE_QUESTION_LIMIT**: Environment variable controlling how many questions free-tier users can ask before being prompted to subscribe

## Bug Details

### Bug Condition

The bug manifests when a user has an Appstle subscription record with a status other than ACTIVE. The login method's step 4 maps every non-"active" normalized status to `subscription_status = "free"`, so there is no denial path. Additionally, `_parse_tags_response()` relies on customer tags which Appstle does not consistently update when subscription status changes (e.g., a PAUSED customer may still have the `appstle_subscription_active_customer` tag).

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type LoginInput (email, password, appstleResponse)
  OUTPUT: boolean

  hasSubscription ← input.appstleResponse.customerId IS NOT NULL
  status ← input.appstleResponse.productSubscriberStatus
  nextBilling ← input.appstleResponse.nextBillingDate

  isPausedExpired ← (status = "PAUSED") AND (nextBilling IS NULL OR nextBilling < NOW())
  isCancelled ← (status = "CANCELLED")
  isPausedWithTimeRemaining ← (status = "PAUSED") AND (nextBilling IS NOT NULL AND nextBilling >= NOW())

  RETURN hasSubscription AND (isPausedExpired OR isCancelled OR isPausedWithTimeRemaining)
END FUNCTION
```

### Examples

- **PAUSED + expired**: Customer `dmu@mcpressonline.com` has `productSubscriberStatus = "PAUSED"` and `nextBillingDate = 2026-04-09` (in the past). Current behavior: gets free-tier access. Expected: 403 with "Your subscription has expired. Resubscribe to continue."
- **PAUSED + time remaining**: Customer `kevin.vandever@mac.com` has `productSubscriberStatus = "PAUSED"` and `nextBillingDate = 2026-04-22` (in the future). Current behavior: gets free-tier access. Expected: 200 with `subscription_status = "active"` (paid time remaining).
- **CANCELLED**: A customer with `productSubscriberStatus = "CANCELLED"`. Current behavior: gets free-tier access. Expected: 403 with "Your subscription has been cancelled. Resubscribe to continue."
- **PAUSED + null nextBillingDate**: A customer with `productSubscriberStatus = "PAUSED"` and no `nextBillingDate`. Current behavior: gets free-tier access. Expected: 403 with "Your subscription has expired. Resubscribe to continue."

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- ACTIVE subscribers continue to receive full access (`status_code=200`, `subscription_status="active"`)
- Users with no Appstle subscription record continue to receive free-tier access (`status_code=200`, `subscription_status="free"`, limited by `FREE_QUESTION_LIMIT` environment variable)
- Appstle API timeouts and errors continue to return 503 "Subscription service temporarily unavailable"
- Incorrect passwords continue to return 401 "Invalid email or password"
- Rate-limited IPs continue to return 429 "Too many login attempts"
- New user password validation failures continue to return 400 with specific failed rules
- Free-tier users who exhaust their questions continue to see the subscription prompt with signup URL on the frontend

**Scope:**
All inputs that do NOT involve a subscription record with status PAUSED or CANCELLED should be completely unaffected by this fix. This includes:
- ACTIVE subscribers (no change in access decision)
- Users with no Appstle record (no change — still free-tier)
- All error paths (API errors, bad passwords, rate limits)
- The token refresh flow (uses the same `verify_subscription` but the refresh method's step 4 logic also needs the same contract-based update)

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Tag-based status derivation is unreliable**: `_parse_tags_response()` uses `_derive_status_from_tags()` which checks customer tags like `appstle_subscription_active_customer`. Appstle does not consistently update these tags when subscription status changes. Customer 1 in the investigation doc has `active_customer` tag despite being PAUSED.

2. **`_parse_tags_response()` conflates PAUSED with ACTIVE**: When a tag matches either "active" or "paused", the method returns `is_valid=True, subscription_status="ACTIVE"`. This means paused subscribers are treated as active at the API parsing level, but then the login step 4 only checks for exact "active" match, so the nuance is lost.

3. **No denial path in login step 4**: The login method's step 4 has a simple binary: if `normalized == "active"` → active, else → free. There is no code path that returns a 403 denial. Every non-active subscriber gets free-tier access.

4. **`AppstleSubscriptionResponse` lacks contract fields**: The dataclass does not include `next_billing_date` or `product_subscriber_status`, so even if the API returns this data, it is not captured or passed to the login decision logic.

5. **`nextBillingDate` is never extracted or compared**: The step 2 API response contains `nextBillingDate` in the subscription contracts, but `_parse_tags_response()` ignores it entirely. There is no datetime comparison to determine whether a paused subscriber has paid time remaining.

## Correctness Properties

Property 1: Bug Condition — Paused-Expired and Cancelled Users Are Denied

_For any_ input where the user has a subscription with `productSubscriberStatus = "PAUSED"` and `nextBillingDate` in the past or null, OR `productSubscriberStatus = "CANCELLED"`, the fixed login function SHALL return a 403 response with the appropriate denial message ("Your subscription has expired. Resubscribe to continue." for paused-expired, "Your subscription has been cancelled. Resubscribe to continue." for cancelled) and a non-null `redirect_url` to the subscription signup page.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Paused With Time Remaining Get Active Access

_For any_ input where the user has a subscription with `productSubscriberStatus = "PAUSED"` and `nextBillingDate` in the future, the fixed login function SHALL return a 200 response with `subscription_status = "active"`, granting full unlimited access.

**Validates: Requirements 2.3, 2.5**

Property 3: Preservation — ACTIVE Subscribers and No-Subscription Users

_For any_ input where the user has `productSubscriberStatus = "ACTIVE"`, OR where the user has no Appstle subscription record at all, the fixed login function SHALL produce the same result as the original function: ACTIVE subscribers get `subscription_status = "active"` and no-subscription users get `subscription_status = "free"`.

**Validates: Requirements 3.1, 3.2**

Property 4: Preservation — Error Paths Unchanged

_For any_ input that triggers an API error (timeout, HTTP error), incorrect password, rate limit, or password validation failure, the fixed login function SHALL produce the same error response (503, 401, 429, or 400 respectively) as the original function.

**Validates: Requirements 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/subscription_auth.py`

**1. Update `AppstleSubscriptionResponse` model**:
- Add `next_billing_date: Optional[datetime] = None` field
- Add `product_subscriber_status: Optional[str] = None` field
- These fields carry the contract data from the API response through to the login decision logic

**2. Create `_parse_contract_response()` method** (or modify `_parse_tags_response()`):
- Extract `productSubscriberStatus` from the top-level of the step 2 response
- Extract `nextBillingDate` from `subscriptionContracts.nodes[0].nextBillingDate`
- Parse `nextBillingDate` string into a `datetime` object (ISO 8601 format)
- Populate the new fields on `AppstleSubscriptionResponse`
- Set `is_valid=True` when a customer record with contract data is found
- Set `subscription_status` to the raw `productSubscriberStatus` value (ACTIVE, PAUSED, CANCELLED)
- Fall back to tag-based logic if contract fields are missing (defensive)

**3. Update `verify_subscription()` to use the new parsing method**:
- Replace the call to `self._parse_tags_response(step2_data, email)` with `self._parse_contract_response(step2_data, email)`
- The method signature and return type remain the same (`AppstleSubscriptionResponse`)

**4. Rewrite login method step 4 with 5-scenario logic**:
- Extract `product_subscriber_status` and `next_billing_date` from `appstle_resp`
- Implement the decision tree:
  - **ACTIVE** → `subscription_status = "active"` (200)
  - **PAUSED + nextBillingDate in future** → `subscription_status = "active"` (200)
  - **PAUSED + nextBillingDate in past or null** → 403 with "Your subscription has expired. Resubscribe to continue." and `redirect_url = self.signup_url`
  - **CANCELLED** → 403 with "Your subscription has been cancelled. Resubscribe to continue." and `redirect_url = self.signup_url`
  - **No subscription record (None/not found)** → `subscription_status = "free"` (200)

**5. Update the refresh method's step 4** with the same contract-based logic:
- The refresh flow currently has the same binary active/free logic
- Apply the same 5-scenario decision tree so refreshed tokens reflect accurate status

**6. Add `FREE_QUESTION_LIMIT` environment variable support**:
- Ensure the free-tier question limit is read from `os.getenv("FREE_QUESTION_LIMIT")` rather than being hardcoded
- This may already be handled by the usage gate; verify and document the configuration

**File**: `frontend/app/login/page.tsx`

**7. Handle 403 denial responses**:
- Add a `case 403:` block in the `handleSubmit` error switch
- Extract `error` message and `redirect_url` from the response body
- Display the denial message in a styled alert (distinct from generic errors)
- Show a "Resubscribe" link/button pointing to the `redirect_url`

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that mock the Appstle API to return PAUSED-expired, PAUSED-with-time-remaining, and CANCELLED contract data, then call the login method and assert the response. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Paused-Expired Test**: Mock API returning `productSubscriberStatus="PAUSED"`, `nextBillingDate` in the past → call login → expect 403 (will fail on unfixed code, returning 200 with "free")
2. **Cancelled Test**: Mock API returning `productSubscriberStatus="CANCELLED"` → call login → expect 403 (will fail on unfixed code, returning 200 with "free")
3. **Paused-With-Time-Remaining Test**: Mock API returning `productSubscriberStatus="PAUSED"`, `nextBillingDate` in the future → call login → expect 200 with "active" (will fail on unfixed code, returning 200 with "free")
4. **Paused-Null-Date Test**: Mock API returning `productSubscriberStatus="PAUSED"`, `nextBillingDate=null` → call login → expect 403 (will fail on unfixed code, returning 200 with "free")

**Expected Counterexamples**:
- All four test cases will return `status_code=200` with `subscription_status="free"` instead of the expected behavior
- Root cause confirmed: login step 4 has no denial path and no contract-based logic

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  status ← input.productSubscriberStatus
  nextBilling ← input.nextBillingDate

  result := login_fixed(input)

  IF status = "PAUSED" AND (nextBilling IS NULL OR nextBilling < NOW()) THEN
    ASSERT result.status_code = 403
    ASSERT result.body.error = "Your subscription has expired. Resubscribe to continue."
    ASSERT result.body.redirect_url IS NOT NULL
  ELSE IF status = "CANCELLED" THEN
    ASSERT result.status_code = 403
    ASSERT result.body.error = "Your subscription has been cancelled. Resubscribe to continue."
    ASSERT result.body.redirect_url IS NOT NULL
  ELSE IF status = "PAUSED" AND nextBilling >= NOW() THEN
    ASSERT result.status_code = 200
    ASSERT result.body.subscription_status = "active"
  END IF
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT login_original(input) = login_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (random ACTIVE statuses, random no-subscription inputs, random error conditions)
- It catches edge cases that manual unit tests might miss (e.g., unusual tag combinations, empty strings, unexpected API response shapes)
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for ACTIVE subscribers, no-subscription users, and error paths, then write property-based tests capturing that behavior.

**Test Cases**:
1. **ACTIVE Subscriber Preservation**: Verify that ACTIVE subscribers continue to get `status_code=200, subscription_status="active"` after the fix
2. **No-Subscription Preservation**: Verify that users with no Appstle record continue to get `status_code=200, subscription_status="free"` after the fix
3. **API Error Preservation**: Verify that API timeouts and HTTP errors continue to return 503 after the fix
4. **Password Error Preservation**: Verify that incorrect passwords continue to return 401 regardless of subscription status

### Unit Tests

- Test `_parse_contract_response()` with various API response shapes (complete data, missing fields, null values, empty contracts list)
- Test the 5-scenario decision logic in login step 4 with mocked `AppstleSubscriptionResponse` objects
- Test `nextBillingDate` parsing with various date formats and edge cases (exactly now, one second ago, one second in the future)
- Test that `AppstleSubscriptionResponse` correctly carries `next_billing_date` and `product_subscriber_status` fields
- Test frontend 403 handling renders denial message and resubscribe link

### Property-Based Tests

- Generate random `productSubscriberStatus` values (ACTIVE, PAUSED, CANCELLED) with random `nextBillingDate` values (past, future, null) and verify the login method returns the correct status code and subscription status for each combination
- Generate random inputs for non-buggy scenarios (ACTIVE, no-subscription) and verify the fixed function produces identical results to the original
- Generate random API error conditions and verify error responses are unchanged

### Integration Tests

- Test full login flow with mocked Appstle API returning each of the 5 scenarios end-to-end
- Test token refresh flow with contract-based logic for each scenario
- Test frontend login page submitting credentials and receiving a 403 response, verifying the denial UI appears with the correct message and resubscribe link
