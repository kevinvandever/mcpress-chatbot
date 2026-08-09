# Bugfix Requirements Document

## Introduction

`backend/subscription_auth.py` evaluates only the FIRST subscription contract returned by Appstle for a customer. Any customer whose access-granting contract is not first is wrongly denied login.

The real case: customer Dave (`dave@shireyllc.com`) has two PAUSED contracts — the oldest expired, the newest still valid with paid time remaining. Appstle returns contracts oldest-first, so `nodes[0]` is the expired one and Dave was locked out despite having paid. He currently has access only because he was added to `BYPASS_EMAILS`.

There are two distinct truncations, both verified in the code:

1. `_parse_contract_response()` reads only `subscriptionContracts.nodes[0].nextBillingDate`. Every other contract is silently ignored.
2. `_extract_customer_id()` returns only the FIRST `customerId` from step 1. If an email maps to multiple Appstle customer records, the remaining records are never fetched. Same bug class, one level up.

Also verified: the per-contract `status` field inside each contract node is never read anywhere in the codebase. Only the customer-level `productSubscriberStatus` is consulted.

The fix replaces the current five-scenario, status-label-driven decision with a single paid-through rule: a customer gets access if ANY of their contracts still has paid time remaining. Cancelling a subscription means "don't bill me again", not "revoke what I already paid for" — cutting off a customer who paid through a period invites chargebacks. Status labels have already misled twice on this system (tags read "active" on a paused subscription; PAUSED turned out to mean "one-time purchase, still valid" rather than "suspended"), so the new rule deliberately makes the status label almost irrelevant.

### Prerequisite that gates one requirement

Clause 2.6 (the `paid_through` fallback formula) CANNOT be finalized until real Appstle payloads are captured. The `createdAt + interval` fallback computes the end of the FIRST billing period only. For a contract that has renewed N times, real paid-through is approximately `lastBillingDate + one interval`. A customer in year three of an annual plan who cancels would get `createdAt + 1 year` — roughly two years in the past — and be wrongly denied. The fallback fails hardest for the longest-tenured, highest-value customers, reintroducing the exact lockout bug being fixed.

`billingPolicy`, `intervalCount`, `lastBillingDate`, `lastOrderDate`, and `billingAttempt` have zero references anywhere in the codebase today, so which date fields Appstle actually returns is unknown. The diagnostic script `inspect_appstle_contracts.py` (project root) must be run first against Dave, a recurring subscriber that has renewed at least once, and a cancelled subscriber. No work that depends on the fallback formula may be sequenced before that capture.

### Known limitations, explicitly out of scope

- **`expiration_date` is never populated**, so `expires_at` in the login response and `subscription_expires_at` in the JWT are always null. Cosmetic, touches JWT semantics, no access impact. Deferred — not fixed here.
- **Refund handling.** A refund should revoke access immediately, but refunds are a separate Shopify action absent from contract data. Not built at current volume; handled manually or via a future deny-list if it becomes real.

## Bug Analysis

### Current Behavior (Defect)

Multi-contract and multi-customer truncation:

1.1 WHEN a customer has more than one subscription contract THEN the system evaluates only `subscriptionContracts.nodes[0]` and ignores every other contract

1.2 WHEN a customer's access-granting contract is not first in `nodes[]` (Appstle returns contracts oldest-first) THEN the system denies login even though the customer has paid time remaining

1.3 WHEN an email maps to more than one Appstle `customerId` THEN the system fetches contracts for only the first customer record and never evaluates the others

1.4 WHEN `subscriptionContracts.pageInfo.hasNextPage` is true THEN the system ignores the additional pages, so contracts beyond the first page are never seen

Decision-signal defects:

1.5 WHEN evaluating access THEN the system never reads the per-contract `status` field and relies solely on the customer-level `productSubscriberStatus`

1.6 WHEN a contract has no `nextBillingDate` THEN the system treats the customer as expired with no attempt to derive a paid-through date from `createdAt` and the billing policy interval

1.7 WHEN a customer's `productSubscriberStatus` is CANCELLED THEN the system denies access unconditionally, even if the customer has paid time remaining on a contract

1.8 WHEN the access decision is made THEN the result depends on the order in which Appstle returns contracts

Duplication and drift:

1.9 WHEN the step-4 access decision runs THEN the system executes one of three separately maintained copies of the same logic — `login()`, `refresh()`, and `backend/subscription_test_endpoint.py` — which have already drifted apart

1.10 WHEN a `BYPASS_EMAILS` user's token is refreshed THEN the system re-checks their subscription and can deny them, because the bypass check exists only in `login()` and not in `refresh()`

1.11 WHEN `backend/subscription_test_endpoint.py` is deployed THEN the system exposes an unauthenticated POST endpoint at `/api/test/subscription-decision` that instantiates the auth service and echoes a fourth copy of the decision logic

Dead and unreachable code:

1.12 WHEN `_parse_tags_response()` determines a subscription status from customer tags THEN the system populates `is_valid` and `subscription_status` but never sets `product_subscriber_status`, which is the only field the decision path reads — so the tag fallback's verdict is silently discarded and those users land in free tier

1.13 WHEN a denial message is produced THEN the system uses hardcoded inline strings in `login()` and `refresh()`, leaving `DENIAL_MESSAGES`, `DEFAULT_DENIAL_MESSAGE`, `_get_denial_message()`, and `_normalize_status()` defined but never called

1.14 WHEN a customer has multiple contracts and is denied THEN the system derives the denial message from the first contract, so a customer whose most recent subscription was cancelled but who also has an older paused contract is told "expired" rather than the more accurate and actionable "cancelled"

Observability defects:

1.15 WHEN `productSubscriberStatus` is missing from the Appstle response THEN the system silently downgrades the customer to free tier at `logger.info`, making the downgrade invisible in normal log review

1.16 WHEN the Appstle step-1 and step-2 responses are logged THEN the system truncates them to 500 characters, which hides multi-contract payloads and therefore hides exactly the data needed to diagnose this class of bug

### Expected Behavior (Correct)

Access rule — grant if ANY contract has paid time remaining:

2.1 WHEN a customer has one or more subscription contracts THEN the system SHALL evaluate EVERY contract and SHALL grant access if ANY single contract qualifies as granting

2.2 WHEN a contract's per-contract `status` is ACTIVE THEN the system SHALL treat that contract as granting WITHOUT checking `paid_through`. This is a deliberate decision, not an emergent side effect: if a renewal payment fails, Appstle may hold status ACTIVE with `nextBillingDate` in the past while retrying, and granting access during that dunning window is intended. This is the one branch where a non-paying account retains access.

2.3 WHEN a contract's per-contract `status` is PAUSED or CANCELLED THEN the system SHALL treat that contract as granting if and only if its `paid_through` date is in the future

2.4 WHEN a contract's per-contract `status` is any other value THEN the system SHALL treat that contract as not granting

2.5 WHEN no contract qualifies as granting THEN the system SHALL deny access

`paid_through` derivation:

2.6 WHEN deriving a contract's `paid_through` date THEN the system SHALL use `nextBillingDate` when present; otherwise it SHALL compute the date from the strongest available renewal anchor plus one billing interval — preferring a `lastBillingDate`-style field if the payload capture confirms one exists, and falling back to `createdAt` plus one interval only when no such field is available. When the weaker `createdAt` path fires, the system SHALL log at ERROR level, because that path is only correct for a contract that has never renewed. The exact field names in this clause SHALL be finalized from the `inspect_appstle_contracts.py` capture before any dependent work begins.

2.7 WHEN adding a billing interval to an anchor date THEN the system SHALL use calendar-aware date arithmetic (`relativedelta`-style) for MONTH and YEAR intervals rather than approximating them as 30 or 365 days, and SHALL honour `intervalCount`

2.8 WHEN a contract's interval unit is unrecognized, the billing policy is absent, or the renewal anchor itself is null (neither a `lastBillingDate`-style field nor `createdAt` is present) THEN the system SHALL treat that contract's `paid_through` as underivable, SHALL treat the contract as not granting, and SHALL log at ERROR level rather than attempting interval arithmetic on a null anchor

Order independence:

2.9 WHEN the same set of contracts is presented in any order THEN the system SHALL produce the same access decision, the same `subscription_status`, and the same denial message

Complete data collection:

2.10 WHEN an email maps to multiple Appstle `customerId` values THEN the system SHALL fetch and evaluate contracts across ALL customer records, not just the first

2.11 WHEN `subscriptionContracts.pageInfo.hasNextPage` is true THEN the system SHALL follow the additional pages so that no contract is missed, and SHALL log at ERROR level if pages cannot be followed. Under the "grant if any contract grants" rule, a granting contract stranded on an unread page produces a FALSE DENIAL of a paying customer, so incomplete data now biases toward lockout.

2.12 WHEN `subscriptionContracts.nodes[]` is empty THEN the system SHALL fall back to the customer-level `productSubscriberStatus`. That field SHALL be used as a fallback only, never as the primary access signal.

Single decision path:

2.13 WHEN any caller needs an access decision THEN the system SHALL call ONE shared decision function, and `login()`, `refresh()`, and any future caller SHALL all use it so that the logic cannot drift again

2.14 WHEN `refresh()` is called for an email listed in `BYPASS_EMAILS` THEN the system SHALL skip the subscription check and issue a token with active status, mirroring the bypass check in `login()`, so a bypass user survives a full token refresh cycle without being bounced

2.15 WHEN this bugfix is complete THEN `backend/subscription_test_endpoint.py` SHALL be deleted rather than maintained as a fourth copy of the decision logic

Denial messages:

2.16 WHEN a customer is denied and has one or more contracts THEN the system SHALL select the denial message from the customer's MOST RECENT contract by `createdAt`, with a deterministic tiebreak for identical timestamps

2.17 WHEN a denial message is produced THEN the system SHALL obtain it from `DENIAL_MESSAGES` / `_get_denial_message()` (extended as needed to host the selection rule in 2.16) rather than from hardcoded inline strings

2.18 WHEN the tag-based fallback path is retained THEN the system SHALL populate `product_subscriber_status` so its verdict actually reaches the decision path; otherwise the tag path SHALL be deleted entirely rather than left silently discarded

Observability:

2.19 WHEN `productSubscriberStatus` is missing from the Appstle response THEN the system SHALL log at ERROR level while still granting free-tier access, keeping the safer free-tier behavior but making the downgrade loud

2.20 WHEN Appstle responses are logged THEN the system SHALL record the contract count and, for each contract, its `status` and relevant dates, rather than a 500-character truncation of the raw payload

Denial message strings (numbered after the observability clauses to leave 2.16-2.18 intact):

2.21 WHEN `DENIAL_MESSAGES` is adopted as the live source of denial copy per clause 2.17 THEN the system SHALL first align its values to the EXACT strings the inline code emits today. The dict values currently omit the `"Resubscribe to continue."` sentence that `login()` and `refresh()` actually send, so adopting the dict as-is would silently change denial copy on the preserved expired-subscriber path (3.3): `EXPIRED` and `PAUSED` SHALL read `"Your subscription has expired. Resubscribe to continue."` and `CANCELLED` SHALL read `"Your subscription has been cancelled. Resubscribe to continue."`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a customer has an ACTIVE subscription THEN the system SHALL CONTINUE TO grant full active access with `subscription_status="active"` and HTTP 200

3.2 WHEN a customer has no Appstle subscription record at all THEN the system SHALL CONTINUE TO grant free-tier access with `subscription_status="free"` and HTTP 200, limited by `FREE_QUESTION_LIMIT` via the usage gate

3.3 WHEN every one of a customer's contracts has expired THEN the system SHALL CONTINUE TO deny access with HTTP 403 and a resubscribe redirect URL

3.4 WHEN a customer provides an incorrect password THEN the system SHALL CONTINUE TO return HTTP 401 "Invalid email or password" regardless of subscription status

3.5 WHEN a client IP exceeds the rate limit THEN the system SHALL CONTINUE TO return HTTP 429 "Too many login attempts. Please try again later."

3.6 WHEN Appstle configuration is missing or invalid THEN the system SHALL CONTINUE TO return HTTP 503 "Subscription service temporarily unavailable"

3.7 WHEN the Appstle API times out, errors, or returns malformed JSON during login THEN the system SHALL CONTINUE TO fall through to free-tier access rather than blocking login

3.8 WHEN the Appstle API is unavailable during refresh THEN the system SHALL CONTINUE TO preserve the subscription status carried in the existing JWT claims

3.9 WHEN a new customer's password fails validation rules THEN the system SHALL CONTINUE TO return HTTP 400 with the list of failed rules

3.10 WHEN an email is listed in `BYPASS_EMAILS` and calls `login()` THEN the system SHALL CONTINUE TO skip the subscription check and grant active status

3.11 WHEN a token is presented within the 5-minute grace window THEN `refresh()` SHALL CONTINUE TO accept it, and SHALL CONTINUE TO return HTTP 401 for tokens expired beyond that window

3.12 WHEN a token is issued THEN the system SHALL CONTINUE TO emit the same JWT claim shape (`sub`, `subscription_status`, `subscription_expires_at`, `iat`, `exp`) with the same 1-hour expiry

3.13 WHEN a login or refresh response is returned THEN `expires_at` and `subscription_expires_at` SHALL CONTINUE TO be null, since `expiration_date` remains unpopulated (deferred, out of scope)

3.14 WHEN a free-tier customer exhausts their allotted questions THEN the frontend SHALL CONTINUE TO show the subscription prompt with a signup URL

---

## Bug Condition

### Bug Condition Function

The bug condition decomposes into three independent clauses. Clause (a) is the bug as
filed. Clauses (b) and (c) are included because requirements 2.3, 2.6, and 2.16 also
change outcomes for inputs clause (a) does not cover — single-contract customers, and
denied customers whose message source moves. Those inputs must be named here, or the
preservation property below would contradict the fix. See **Preservation Exceptions**.

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type LoginInput (email, password, appstlePayloads)
  OUTPUT: boolean

  RETURN isMultiContractBug(X) OR isDecisionRuleBug(X) OR isDenialMessageBug(X)
END FUNCTION


// (a) Truncation and ordering — the bug as filed.
//     Some contract that is NOT the one the old code looked at grants access,
//     while the one the old code looked at does not.
//     Covers clauses 1.1, 1.2, 1.3, 1.4, 1.8.
FUNCTION isMultiContractBug(X)
  allContracts ← FLATTEN(
    contracts(c) FOR EACH c IN allCustomerRecords(X.email)
  )
  firstContract ← firstContractOfFirstCustomerRecord(X.email)   // what F reads

  anyGrants   ← EXISTS k IN allContracts WHERE contractGrants(k)
  firstGrants ← firstContract IS NOT NULL AND contractGrants(firstContract)

  RETURN anyGrants AND NOT firstGrants
END FUNCTION


// (b) The new decision rule changes the outcome on the very contract F already
//     reads. Covers clause 1.6 (null nextBillingDate with a derivable
//     paid_through) and clause 1.7 (CANCELLED with paid time remaining).
//     Single-contract customers land here, not in (a).
FUNCTION isDecisionRuleBug(X)
  firstContract ← firstContractOfFirstCustomerRecord(X.email)
  RETURN firstContract IS NOT NULL
         AND contractGrants(firstContract) ≠ legacyFiveScenarioGrants(firstContract)
END FUNCTION


// (c) Denial-message selection. Covers clause 1.14.
//     No contract grants, at least one contract exists, and the newest
//     contract's status differs from nodes[0]'s status. The access outcome is
//     identical (403); only the message and body.subscription_status change.
FUNCTION isDenialMessageBug(X)
  allContracts ← FLATTEN(
    contracts(c) FOR EACH c IN allCustomerRecords(X.email)
  )
  IF EXISTS k IN allContracts WHERE contractGrants(k) THEN RETURN false END IF
  IF allContracts IS EMPTY THEN RETURN false END IF

  newest ← ARGMAX(k IN allContracts BY k.createdAt, tiebreak BY contractId ASC)
  RETURN UPPER(newest.status) ≠ UPPER(firstContractOfFirstCustomerRecord(X.email).status)
END FUNCTION


FUNCTION contractGrants(k)
  INPUT: k of type SubscriptionContract
  OUTPUT: boolean

  IF UPPER(k.status) = "ACTIVE" THEN
    RETURN true                       // unconditional — doubles as dunning grace
  END IF

  IF UPPER(k.status) IN {"PAUSED", "CANCELLED"} THEN
    pt ← paidThrough(k)
    RETURN pt IS NOT NULL AND pt > NOW()
  END IF

  RETURN false
END FUNCTION


FUNCTION paidThrough(k)
  INPUT: k of type SubscriptionContract
  OUTPUT: datetime OR NULL

  IF k.nextBillingDate IS NOT NULL THEN
    RETURN k.nextBillingDate
  END IF

  // Anchor selection is provisional — finalized by the payload capture.
  // Prefer a lastBillingDate-style renewal anchor if Appstle provides one.
  IF k.lastBillingDate IS NOT NULL THEN
    anchor ← k.lastBillingDate
  ELSE
    anchor ← k.createdAt
    LOG ERROR "paid_through derived from createdAt — wrong for renewed contracts"
  END IF

  // A NULL anchor (neither lastBillingDate nor createdAt present) makes interval
  // arithmetic meaningless — do not attempt it.
  IF anchor IS NULL
     OR k.billingPolicy IS NULL
     OR k.billingPolicy.interval NOT IN {DAY, WEEK, MONTH, YEAR} THEN
    LOG ERROR "paid_through underivable — null anchor, or absent or unrecognized billing policy"
    RETURN NULL
  END IF

  // Calendar-aware addition. MONTH and YEAR must NOT be approximated
  // as 30 or 365 days.
  RETURN addCalendarInterval(anchor, k.billingPolicy.interval, k.billingPolicy.intervalCount)
END FUNCTION
```

Dave is the canonical counterexample:

```pascal
// F(Dave) → 403 "expired"     (reads nodes[0], the expired PAUSED contract)
// F'(Dave) → 200 "active"     (nodes[1] is PAUSED with paid time remaining)
```

### Property Specification — Fix Checking

```pascal
// Property: Fix Checking — Any Granting Contract Grants Access
FOR ALL X WHERE isBugCondition(X) DO
  result ← login'(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR

// Property: Fix Checking — Dave's Exact Payload
FOR X = dave WHERE X HAS two PAUSED contracts, nodes[0] expired, nodes[1] paid_through > NOW() DO
  result ← login'(X)   // with BYPASS_EMAILS empty
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR

// Property: Fix Checking — Order Independence
FOR ALL X, FOR ALL permutations P of X.allContracts DO
  ASSERT login'(X WITH contracts ORDERED BY P) = login'(X)
END FOR

// Property: Fix Checking — Cancelled With Paid Time Remaining Grants
FOR ALL X WHERE EXISTS k IN X.allContracts
                WHERE UPPER(k.status) = "CANCELLED" AND paidThrough(k) > NOW() DO
  result ← login'(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR

// Property: Fix Checking — Active Grants Regardless Of Paid-Through (dunning grace)
FOR ALL X WHERE EXISTS k IN X.allContracts
                WHERE UPPER(k.status) = "ACTIVE" AND paidThrough(k) < NOW() DO
  result ← login'(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR

// Property: Fix Checking — Contracts Under A Second Customer Record Count
FOR ALL X WHERE X.email MAPS TO customerIds [c1, c2]
                AND NO contract UNDER c1 grants
                AND SOME contract UNDER c2 grants DO
  result ← login'(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR

// Property: Fix Checking — Denial Message Comes From The Most Recent Contract
FOR ALL X WHERE NOT EXISTS k IN X.allContracts WHERE contractGrants(k) DO
  newest ← ARGMAX(k IN X.allContracts BY k.createdAt, deterministic tiebreak)
  result ← login'(X)
  ASSERT result.status_code = 403
  ASSERT result.body.error = denialMessageFor(newest.status)
  ASSERT result.body.redirect_url IS NOT NULL
END FOR

// Property: Fix Checking — Bypass Survives Refresh
FOR ALL X WHERE X.email IN BYPASS_EMAILS DO
  result ← refresh'(tokenFor(X))
  ASSERT result.status_code = 200
  ASSERT result.body.success = true
END FOR

// Property: Fix Checking — login' And refresh' Agree
FOR ALL X DO
  ASSERT accessDecision(login'(X)) = accessDecision(refresh'(tokenFor(X)))
END FOR

// Property: Fix Checking — Calendar Interval Math
FOR ALL k WHERE k.nextBillingDate IS NULL
              AND k.billingPolicy.interval IN {MONTH, YEAR} DO
  ASSERT paidThrough(k) = addCalendarInterval(anchor(k), k.billingPolicy.interval,
                                              k.billingPolicy.intervalCount)
  ASSERT paidThrough(k) ≠ anchor(k) + (30 OR 365 days approximation)
END FOR
```

### Preservation Goal

```pascal
// Property: Preservation Checking — Non-buggy inputs behave identically
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT login(X) = login'(X)
END FOR

// Specifically preserved:
// - ACTIVE subscribers                 → 200, subscription_status = "active"
// - No Appstle record                  → 200, subscription_status = "free"
// - Every contract expired             → 403, resubscribe redirect_url present
// - Empty nodes[]                      → decided by customer-level productSubscriberStatus
// - Incorrect password                 → 401 "Invalid email or password"
// - Rate limit exceeded                → 429 "Too many login attempts..."
// - Missing/invalid Appstle config     → 503 "Subscription service temporarily unavailable"
// - Appstle timeout/error during login → free-tier fall-through, not a block
// - Appstle unavailable during refresh → status preserved from JWT claims
// - New-user password rule failure     → 400 with failed_rules
// - BYPASS_EMAILS user at login        → 200, active
// - Token within 5-minute grace window → accepted; beyond it → 401
// - JWT claim shape and 1-hour expiry  → unchanged
// - expires_at / subscription_expires_at → still null (deferred)
```

#### Preservation Exceptions

Three clauses deliberately change behavior for inputs that clause (a) of the bug condition does not cover. They are exceptions to preservation, not regressions, and each is named here so the preservation property can exclude it explicitly rather than contradict the fix. Clauses (b) and (c) of `isBugCondition` are exactly the predicates that route these inputs to fix checking instead:

| Clause | Input | F | F' |
|---|---|---|---|
| 2.3 / 1.7 | Single CANCELLED contract, paid time remaining | 403 cancelled | 200 active |
| 2.6 / 1.6 | PAUSED, null `nextBillingDate`, anchor + interval in the future | 403 expired | 200 active |
| 2.16 / 1.14 | Denied, newest contract's status ≠ `nodes[0]`'s status | message from `nodes[0]` | message from newest contract |

Everything else, including every non-subscription response path, is preserved unchanged. The expired-subscriber denial copy in 3.3 in particular SHALL remain byte-identical, which is what clause 2.21 protects.

```pascal
// Property: Preservation Checking — with the three exceptions excluded
FOR ALL X WHERE NOT isBugCondition(X) DO      // (a) OR (b) OR (c) all false
  ASSERT login(X) = login'(X)
END FOR
```

### Verification Note

Preservation and fix checking MUST be asserted on `login()`'s and `refresh()`'s actual returned `status_code` and `body`, never on parser internals. The existing tag tests pass while checking fields the decision path never reads (clause 1.12) — that is precisely how this bug shipped.
