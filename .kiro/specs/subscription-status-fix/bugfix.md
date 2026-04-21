# Bugfix Requirements Document

## Introduction

The subscription status logic in the login flow (`backend/subscription_auth.py`) never denies access to anyone. When a user's Appstle subscription is paused, cancelled, or expired, they are silently downgraded to free-tier (limited questions per FREE_QUESTION_LIMIT) instead of being blocked. This means former subscribers with expired or cancelled subscriptions receive the same treatment as brand-new users who never subscribed, undermining the subscription model.

The root cause is in the login method's step 4, where every non-"active" status maps to `"free"` — there is no denial path. Additionally, the `_parse_tags_response()` method relies on customer tags which are unreliable (tags are not consistently updated by Appstle when subscription status changes). The fix should use `productSubscriberStatus` and `nextBillingDate` from the Appstle contract data to make accurate access decisions.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user has a PAUSED subscription with `nextBillingDate` in the past (paid period expired) THEN the system grants free-tier access (limited by FREE_QUESTION_LIMIT) instead of denying access

1.2 WHEN a user has a CANCELLED subscription THEN the system grants free-tier access (limited by FREE_QUESTION_LIMIT) instead of denying access

1.3 WHEN a user has a PAUSED subscription with `nextBillingDate` in the future (paid time remaining) THEN the system grants free-tier access (limited by FREE_QUESTION_LIMIT) instead of granting full active access

1.4 WHEN the login flow evaluates subscription status THEN the system uses unreliable customer tags (`_parse_tags_response`) instead of the accurate `productSubscriberStatus` and contract `nextBillingDate` fields from the Appstle API

1.5 WHEN a user is denied access (paused-expired or cancelled) THEN the system does not return a 403 status code with a specific denial message and resubscribe redirect URL

### Expected Behavior (Correct)

2.1 WHEN a user has a PAUSED subscription with `nextBillingDate` in the past or null THEN the system SHALL deny access with a 403 response containing the message "Your subscription has expired. Resubscribe to continue." and a redirect URL to the subscription signup page

2.2 WHEN a user has a CANCELLED subscription THEN the system SHALL deny access with a 403 response containing the message "Your subscription has been cancelled. Resubscribe to continue." and a redirect URL to the subscription signup page

2.3 WHEN a user has a PAUSED subscription with `nextBillingDate` in the future THEN the system SHALL grant full active access (unlimited questions) because the user has paid time remaining

2.4 WHEN the login flow evaluates subscription status THEN the system SHALL use `productSubscriberStatus` and `nextBillingDate` from the Appstle subscription contract data to determine access, rather than relying solely on customer tags

2.5 WHEN a user has an ACTIVE subscription THEN the system SHALL grant full active access (unlimited questions)

2.6 WHEN a user has no Appstle subscription record at all (never subscribed) THEN the system SHALL grant free-tier access (limited questions as configured by the FREE_QUESTION_LIMIT environment variable, via usage gate)

2.7 WHEN the frontend receives a 403 denial response THEN the system SHALL display the denial message from the response and provide a link to the resubscribe URL

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user has an ACTIVE subscription THEN the system SHALL CONTINUE TO grant full active access with unlimited questions

3.2 WHEN a user has no Appstle subscription record (never subscribed) THEN the system SHALL CONTINUE TO grant free-tier access with questions limited by the FREE_QUESTION_LIMIT environment variable via the usage gate

3.3 WHEN the Appstle API is unavailable or times out THEN the system SHALL CONTINUE TO return a 503 "Subscription service temporarily unavailable" response

3.4 WHEN a user provides an incorrect password THEN the system SHALL CONTINUE TO return a 401 "Invalid email or password" response regardless of subscription status

3.5 WHEN a user exceeds the rate limit THEN the system SHALL CONTINUE TO return a 429 "Too many login attempts" response

3.6 WHEN a new user provides a password that fails validation rules THEN the system SHALL CONTINUE TO return a 400 response with the specific failed rules

3.7 WHEN a free-tier user has exhausted their questions (as configured by FREE_QUESTION_LIMIT) THEN the system SHALL CONTINUE TO show the subscription prompt with a signup URL on the frontend

---

## Bug Condition

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type LoginInput (email, password, appstleResponse)
  OUTPUT: boolean

  // The bug triggers when a user has a subscription record that is
  // not ACTIVE — specifically PAUSED-expired or CANCELLED — because
  // these users are incorrectly given free-tier access instead of
  // being denied. Also triggers for PAUSED-with-time-remaining users
  // who should get active access but instead get free-tier.
  
  hasSubscription ← X.appstleResponse.customerId IS NOT NULL
  status ← X.appstleResponse.productSubscriberStatus
  nextBilling ← X.appstleResponse.nextBillingDate
  
  isPausedExpired ← (status = "PAUSED") AND (nextBilling IS NULL OR nextBilling < NOW())
  isCancelled ← (status = "CANCELLED")
  isPausedWithTimeRemaining ← (status = "PAUSED") AND (nextBilling IS NOT NULL AND nextBilling >= NOW())
  
  RETURN hasSubscription AND (isPausedExpired OR isCancelled OR isPausedWithTimeRemaining)
END FUNCTION
```

### Property Specification — Fix Checking

```pascal
// Property: Fix Checking — Paused-Expired Users Are Denied
FOR ALL X WHERE isBugCondition(X) AND X.status = "PAUSED" AND (X.nextBillingDate IS NULL OR X.nextBillingDate < NOW()) DO
  result ← login'(X)
  ASSERT result.status_code = 403
  ASSERT result.body.error = "Your subscription has expired. Resubscribe to continue."
  ASSERT result.body.redirect_url IS NOT NULL
END FOR

// Property: Fix Checking — Cancelled Users Are Denied
FOR ALL X WHERE isBugCondition(X) AND X.status = "CANCELLED" DO
  result ← login'(X)
  ASSERT result.status_code = 403
  ASSERT result.body.error = "Your subscription has been cancelled. Resubscribe to continue."
  ASSERT result.body.redirect_url IS NOT NULL
END FOR

// Property: Fix Checking — Paused With Time Remaining Get Active Access
FOR ALL X WHERE isBugCondition(X) AND X.status = "PAUSED" AND X.nextBillingDate >= NOW() DO
  result ← login'(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR
```

### Preservation Goal

```pascal
// Property: Preservation Checking — Non-buggy inputs behave identically
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT login(X) = login'(X)
END FOR

// Specifically:
// - ACTIVE subscribers continue to get full access (status_code=200, subscription_status="active")
// - Users with no Appstle record continue to get free-tier (status_code=200, subscription_status="free")
// - API errors continue to return 503
// - Bad passwords continue to return 401
// - Rate-limited IPs continue to return 429
```
