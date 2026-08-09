# Subscription Multi-Contract Access Bugfix Design

## Overview

`backend/subscription_auth.py` decides customer access from a single data point: the customer-level `productSubscriberStatus` plus `subscriptionContracts.nodes[0].nextBillingDate` of the first Appstle customer record. Everything else Appstle returns is discarded. Customers whose access-granting contract is not first are denied login even though they have paid time remaining. Dave (`dave@shireyllc.com`) is the live counterexample: two PAUSED contracts, oldest expired, newest still paid — Appstle returns oldest-first, so the code reads the expired one and returns 403. He has access today only because he is in `BYPASS_EMAILS`.

The fix has four moving parts:

1. **Collect all the data.** Traverse every Appstle `customerId` for the email, every contract under each record, and every page of `subscriptionContracts`.
2. **Replace the decision rule.** Drop the five-scenario status-label ladder in favour of one rule: grant access if ANY contract still has paid time remaining. Status labels have misread reality twice on this system, so the new rule deliberately makes the label almost irrelevant — `ACTIVE` short-circuits to grant, `PAUSED`/`CANCELLED` are decided by a derived `paid_through` date, everything else does not grant.
3. **Consolidate to one decision path.** `login()`, `refresh()`, and `backend/subscription_test_endpoint.py` each carry a separately maintained copy of step 4, and they have already drifted. One module-level `decide_access()` function replaces all three; the test endpoint is deleted rather than kept as a fourth copy.
4. **Make the failure modes loud.** Silent `logger.info` downgrades and 500-character payload truncation are exactly what hid this bug class. Both become structured, ERROR-level where a customer could be wrongly denied.

One piece of the fix could not be finalized from the code alone: the `paid_through` fallback for a contract with no `nextBillingDate` needs a renewal anchor, and `lastBillingDate`, `lastOrderDate`, `billingAttempt`, `billingPolicy`, and `intervalCount` had zero references in the codebase, so nobody knew which of them Appstle returns. That capture has now been run (see **Prerequisite** below) and the answer is blunt: **Appstle returns no renewal anchor at all.** A contract carries exactly two dates, `createdAt` and `nextBillingDate`. The anchor is therefore `createdAt` or nothing, and the renewed subscriber in the capture confirms the weakness with real data — `createdAt` + one interval lands a full month behind that customer's true paid-through. The fallback is kept anyway because it errs toward denial, never toward a false grant, and it is kept loud. Two secondary questions came back only partly answered: no CANCELLED contract was captured, and pagination was never triggered. Both are recorded as open risks rather than settled decisions.

Out of scope, carried over from the requirements: `expiration_date` stays unpopulated (so `expires_at` and `subscription_expires_at` remain null), and refund-driven revocation is not built.

## Glossary

- **Bug_Condition (C)**: The predicate identifying inputs where the current code's access decision or denial message differs from the correct one — principally, some contract grants access but the one `nodes[0]` of the first customer record does not.
- **Property (P)**: The required behavior on bug-condition inputs — `login()` returns HTTP 200 with `subscription_status="active"` when any contract grants.
- **Preservation**: The observable `status_code` and response body of `login()` / `refresh()` for all inputs outside the bug condition, which the fix must leave byte-identical (modulo the JWT string itself).
- **Granting contract**: A contract that entitles its owner to access — `status == ACTIVE`, or `status IN {PAUSED, CANCELLED}` with `paid_through` in the future.
- **`paid_through`**: The instant a contract's already-paid period ends. `nextBillingDate` when present; otherwise a renewal anchor plus one billing interval.
- **Renewal anchor**: The date a contract's current paid period started. **`createdAt` — there is no alternative.** The payload capture (see Prerequisite below) established that Appstle returns exactly two date fields per contract, `createdAt` and `nextBillingDate`; no `lastBillingDate`-style field exists, so the provisional two-step priority collapses to a single field. `createdAt` is exact for a never-renewed contract and one or more full intervals too early for a renewed one, which errs toward denial and can never wrongly grant. Its use is logged at ERROR level.
- **`productSubscriberStatus`**: The customer-level status field, currently the primary access signal. Demoted to a fallback used only when `subscriptionContracts.nodes[]` is empty.
- **`ContractView`**: New normalized, timezone-aware, per-contract record produced by the parser and consumed by the decision function. The unit the decision rule operates on.
- **`decide_access()`**: New module-level pure function holding the single copy of the access decision. Consumed by `login()`, `refresh()`, and any future caller.
- **`BYPASS_EMAILS`**: Env-var allowlist that skips the subscription check. Present in `login()` only today, which is why a bypass user can be bounced on refresh.
- **F / F'**: The current (unfixed) and fixed code, respectively.

## Bug Details

### Bug Condition

The bug manifests whenever the access decision computed from *all* of a customer's contracts differs from the decision the current code reaches from `subscriptionContracts.nodes[0]` of the first `customerId`. Three independent code paths produce that divergence:

- `_parse_contract_response()` reads `nodes[0].nextBillingDate` and discards every other node (clauses 1.1, 1.2, 1.4, 1.8).
- `_extract_customer_id()` returns the first `customerId` and never fetches the rest (clause 1.3).
- The five-scenario ladder in `login()` / `refresh()` denies `CANCELLED` unconditionally and treats a null `nextBillingDate` as expired without attempting derivation, so it can misjudge even the single contract it does read (clauses 1.6, 1.7).

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X of type LoginInput (email, password, appstlePayloads)
  OUTPUT: boolean

  RETURN isMultiContractBug(X) OR isDecisionRuleBug(X) OR isDenialMessageBug(X)
END FUNCTION


// (a) Truncation and ordering — the bug as stated in bugfix.md
FUNCTION isMultiContractBug(X)
  allContracts   ← FLATTEN(contracts(c) FOR EACH c IN allCustomerRecords(X.email))
  firstContract  ← firstContractOfFirstCustomerRecord(X.email)   // what F reads

  anyGrants      ← EXISTS k IN allContracts WHERE contractGrants(k)
  firstGrants    ← firstContract IS NOT NULL AND contractGrants(firstContract)

  RETURN anyGrants AND NOT firstGrants
END FUNCTION


// (b) Decision-rule change on the very contract F already reads.
//     Covers clauses 1.6 (null nextBillingDate) and 1.7 (CANCELLED with paid time).
//     Single-contract customers land here, not in (a).
FUNCTION isDecisionRuleBug(X)
  firstContract ← firstContractOfFirstCustomerRecord(X.email)
  RETURN firstContract IS NOT NULL
         AND contractGrants(firstContract) ≠ legacyFiveScenarioGrants(firstContract)
END FUNCTION


// (c) Denial-message selection. Covers clause 1.14.
//     Access outcome is identical (403); only the message and
//     body.subscription_status change.
FUNCTION isDenialMessageBug(X)
  allContracts ← FLATTEN(contracts(c) FOR EACH c IN allCustomerRecords(X.email))
  IF EXISTS k IN allContracts WHERE contractGrants(k) THEN RETURN false END IF
  IF allContracts IS EMPTY THEN RETURN false END IF

  newest ← ARGMAX(k IN allContracts BY k.createdAt, tiebreak BY contractId ASC)
  RETURN UPPER(newest.status) ≠ UPPER(firstContractOfFirstCustomerRecord(X.email).status)
END FUNCTION


FUNCTION contractGrants(k)
  INPUT: k of type ContractView
  OUTPUT: boolean

  IF UPPER(k.status) = "ACTIVE" THEN
    RETURN true                       // unconditional — doubles as dunning grace (2.2)
  END IF

  IF UPPER(k.status) IN {"PAUSED", "CANCELLED"} THEN
    pt ← paidThrough(k)
    RETURN pt IS NOT NULL AND pt > NOW()
  END IF

  RETURN false                        // unrecognized status does not grant (2.4)
END FUNCTION


FUNCTION paidThrough(k)
  INPUT: k of type ContractView
  OUTPUT: datetime OR NULL

  IF k.nextBillingDate IS NOT NULL THEN
    RETURN k.nextBillingDate
  END IF

  // Anchor is createdAt, full stop. The capture confirmed Appstle exposes no
  // lastBillingDate / lastOrderDate / billingAttempt field — createdAt and
  // nextBillingDate are the ONLY two dates on a contract (2.6).
  // Wrong by one or more intervals for a renewed contract, which under-grants
  // rather than over-grants, so it is still strictly better than returning NULL.
  anchor ← k.createdAt
  LOG ERROR "paid_through derived from createdAt — understates paid time for renewed contracts"

  IF anchor IS NULL
     OR k.billingPolicy IS NULL
     OR k.billingPolicy.interval NOT IN {DAY, WEEK, MONTH, YEAR} THEN
    LOG ERROR "paid_through underivable — absent or unrecognized billing policy"
    RETURN NULL                       // → contract does not grant (2.8)
  END IF

  // Calendar-aware. MONTH and YEAR must NOT be approximated as 30 or 365 days (2.7)
  RETURN addCalendarInterval(anchor, k.billingPolicy.interval, k.billingPolicy.intervalCount)
END FUNCTION
```

Clause (a) is the bug as filed. Clauses (b) and (c) are added here because requirements 2.3, 2.6, and 2.16 change single-contract outcomes too, and those inputs must be excluded from the preservation property or it would contradict the fix. See **Preservation Exceptions** below.

### Examples

- **Dave, two PAUSED contracts (the canonical case) — VERIFIED against his real captured payload, not just as filed.** `customerId 2788838535`, `productSubscriberStatus` PAUSED, two contracts returned oldest-first by `createdAt`:

  | node | `status` | `createdAt` | `nextBillingDate` | grants? |
  |---|---|---|---|---|
  | `nodes[0]` | PAUSED | 2026-06-02 | 2026-07-02 (past) | no |
  | `nodes[1]` | PAUSED | 2026-07-28 | 2026-08-27 (future) | **yes** |

  Current code reads `nodes[0]` only and returns 403 `"Your subscription has expired. Resubscribe to continue."` Correct behavior is 200 / `"active"`. **Oldest-first `nodes[]` ordering is now confirmed empirically**, which removes the "Appstle may order newest-first" alternative hypothesis listed under Exploratory Bug Condition Checking. Falls under (a).
- **Two Appstle customer records.** `c1` has only an expired contract, `c2` has a paid one. Expected 200 / `"active"`. Actual: `_extract_customer_id()` returns `c1`, `c2` is never fetched, 403. Falls under (a).
- **Paginated contracts.** `pageInfo.hasNextPage == true`, the granting contract sits on page 2. Expected 200 / `"active"`. Actual: page 2 never requested, 403. Falls under (a).
- **CANCELLED with paid time remaining.** One contract, `status=CANCELLED`, `nextBillingDate` three weeks out. Expected 200 / `"active"` — cancelling means "stop billing me", not "revoke what I paid for". Actual: unconditional 403 `"...has been cancelled..."`. Falls under (b).
- **PAUSED with null `nextBillingDate`, derivable.** Monthly contract, anchor eight days ago, no `nextBillingDate`. Expected 200 / `"active"` (paid through ~22 more days). Actual: 403 expired, no derivation attempted. Falls under (b).
- **ACTIVE with `nextBillingDate` in the past (dunning).** Renewal payment retrying. Expected 200 / `"active"` — deliberate grace window per 2.2. Current code also returns 200 here, so this is preserved, not fixed.
- **Newest contract CANCELLED, older contract PAUSED-expired.** Expected 403 with the cancelled message. Actual: 403 with the expired message, derived from `nodes[0]`. Falls under (c) — same status code, different message.
- **Edge case, unrecognized interval.** No `nextBillingDate`, `billingPolicy.interval == "FORTNIGHT"`. Expected: `paid_through` underivable, contract does not grant, ERROR logged. No silent guess.
- **Edge case, empty `nodes[]`.** Expected: fall back to customer-level `productSubscriberStatus`, unchanged from today.

The other two captured customers are the **preserved** cases, and both were verified from their real payloads:

- **Renewed monthly subscriber** (`customerId 2788845447`): one contract, `status` ACTIVE, `createdAt` 2026-06-16, `nextBillingDate` 2026-08-16, `billingPolicy` MONTH × 1, `lastPaymentStatus` `"SUCCEEDED"`. Grants unconditionally on the ACTIVE short-circuit → 200 / `"active"`, before and after the fix (3.1).
- **Lapsed 30-day purchaser** (`customerId 3289420039`): one contract, `status` PAUSED, `createdAt` 2026-04-23, `nextBillingDate` 2026-05-23 (past), `billingPolicy` DAY × 30. Correctly denied → 403 with the expired message, before and after the fix (3.3). This is the customer originally expected to be CANCELLED; Appstle reports a lapsed one-time purchase as PAUSED, which is why Finding 3 leaves the cancellation question open.

Each of the three emails mapped to exactly one `customerId`, so the two-customer-record example above (clause 2.10 / Property 7) has no real-data counterpart and is fixture-only.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- ACTIVE subscribers get 200 with `subscription_status="active"` (3.1).
- Customers with no Appstle record get 200 with `subscription_status="free"`, gated by `FREE_QUESTION_LIMIT` in the usage gate (3.2).
- Customers whose every contract has expired get 403 with a resubscribe `redirect_url` (3.3).
- Wrong password → 401 `"Invalid email or password"`, regardless of subscription state (3.4).
- Rate limit exceeded → 429 `"Too many login attempts. Please try again later."` (3.5).
- Missing/invalid Appstle config → 503 `"Subscription service temporarily unavailable"` (3.6).
- Appstle timeout, HTTP error, or malformed JSON during login → free-tier fall-through, never a block (3.7).
- Appstle unavailable during refresh → subscription status preserved from the existing JWT claims (3.8).
- New user with a non-compliant password → 400 with `failed_rules` (3.9).
- `BYPASS_EMAILS` at login → subscription check skipped, active status (3.10).
- Token inside the 5-minute grace window accepted; beyond it, 401 (3.11).
- JWT claim shape (`sub`, `subscription_status`, `subscription_expires_at`, `iat`, `exp`) and 1-hour expiry unchanged (3.12).
- `expires_at` / `subscription_expires_at` still null, since `expiration_date` stays unpopulated (3.13).
- Free-tier exhaustion still shows the frontend subscription prompt with a signup URL (3.14).

**Scope:**

Every input outside the bug condition must produce an identical `status_code` and body. That includes all of the pre-step-4 flow, which this fix does not touch at all: config check, rate limiting, bypass detection, password lookup, password verification, new-user password-rule validation, password-record creation, rate-limiter reset, and token creation. The change is confined to (i) how contracts are fetched and parsed, (ii) how the access decision is computed, and (iii) how it is logged.

### Preservation Exceptions

Three requirement clauses deliberately change behavior for inputs that clause (a) of the bug condition does not cover. They are exceptions to preservation, not regressions, and each is listed so the preservation property can exclude them explicitly:

| Clause | Input | F | F' |
|---|---|---|---|
| 2.3 / 1.7 | Single CANCELLED contract, paid time remaining | 403 cancelled | 200 active |
| 2.6 / 1.6 | PAUSED, null `nextBillingDate`, anchor + interval in the future | 403 expired | 200 active |
| 2.16 / 1.14 | Denied, newest contract's status ≠ `nodes[0]`'s status | message from `nodes[0]` | message from newest contract |

Everything else, including every non-subscription response path, is preserved unchanged.

**Note:** The required correct behavior on bug-condition inputs is specified in Correctness Properties below, not here.

## Hypothesized Root Cause

The root cause is not in doubt — it is read directly from the code, not inferred from symptoms. Four confirmed defects:

1. **Hardcoded `nodes[0]` in `_parse_contract_response()`.** The parser's contract extraction is literally `nodes[0].get("nextBillingDate")` inside a `try/except (IndexError, AttributeError, TypeError)`. Nothing loops. `AppstleSubscriptionResponse` has a single scalar `next_billing_date` field, so the model itself cannot represent more than one contract — the truncation is baked into the data shape, which is why the fix needs a new per-contract type rather than a loop bolted onto the old one.

2. **Single-value return from `_extract_customer_id()`.** It normalizes the step-1 payload into a customer list, then `return cid` on the first record with a non-null `customerId`. Same bug class one level up, and `verify_subscription()` is written around a single `customer_id` variable, so multi-record support requires restructuring the step-2 call into a loop.

3. **No pagination handling anywhere.** `subscriptionContracts.pageInfo` is never read. Under the old "first contract decides" rule an unread page was merely incomplete data; under "grant if any contract grants" a granting contract stranded on page 2 is a false denial of a paying customer, so incomplete data now biases toward lockout (2.11).

4. **The decision rule keys on labels, and the label is the wrong signal.** The five-scenario ladder branches on `productSubscriberStatus` — a customer-level field — and never reads the per-contract `status` field (clause 1.5, verified: no reference anywhere in the codebase). Two prior misreadings of this system's labels are on record: tags reported "active" for a paused subscription, and PAUSED turned out to mean "one-time purchase, still valid" rather than "suspended". `CANCELLED → 403` unconditionally is the most expensive instance: denying a customer who has paid through a period is a chargeback invitation.

Two contributing factors made the bug hard to see and easy to reintroduce:

5. **Three copies of the decision logic.** `login()` step 4, `refresh()` step 4, and `subscription_test_endpoint.py` all reimplement the ladder. They have drifted: `login()` has a `BYPASS_EMAILS` check, `refresh()` does not (clause 1.10), so a bypass user can be bounced one hour after a successful login. The test endpoint is registered unauthenticated in `backend/main.py` at `/api/test/subscription-decision` and instantiates its own `SubscriptionAuthService` (clause 1.11).

6. **Observability tuned to hide exactly this.** Step-1 and step-2 payloads are logged as `str(data)[:500]`, which truncates before the interesting contracts in a multi-contract payload. A missing `productSubscriberStatus` downgrades the customer to free tier at `logger.info`. And the existing test suite (`test_subscription_bug_exploration.py`, `test_subscription_preservation.py`) asserts against the test endpoint over HTTP, so it validated a copy of the logic rather than `login()` itself — while `_parse_tags_response()` populated `is_valid` and `subscription_status` but never `product_subscriber_status`, the only field the decision path reads (clause 1.12). Green tests, discarded verdict. That is how this shipped.

## Correctness Properties

Property 1: Bug Condition - Any Granting Contract Grants Access

_For any_ login input where the bug condition holds (`isBugCondition` returns true) and some contract grants, `login()` SHALL return `status_code == 200` with `body.subscription_status == "active"`, regardless of which customer record, which page, or which position in `nodes[]` that contract occupies.

**Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.10, 2.11, 2.12**

Property 2: Preservation - Non-Bug Inputs Behave Identically

_For any_ login input where the bug condition does NOT hold (`isBugCondition` returns false), `login()` SHALL return the same `status_code` and the same response body as the unfixed implementation, with the `token` field compared by decoded claim shape rather than by string. This covers ACTIVE subscribers, customers with no Appstle record, customers whose every contract has expired, empty `nodes[]` decided by `productSubscriberStatus`, wrong password, rate limiting, missing config, Appstle failure fall-through, new-user password validation, `BYPASS_EMAILS` at login, the refresh grace window, and JWT claim shape and expiry. The three documented Preservation Exceptions are excluded from this property.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14**

Property 3: Bug Condition - Dave's Exact Payload

_For any_ run with Dave's captured payload (two PAUSED contracts, `nodes[0]` expired, `nodes[1]` with `paid_through > NOW()`) and `BYPASS_EMAILS` empty, `login()` SHALL return `status_code == 200` with `body.subscription_status == "active"`.

**Validates: Requirements 2.1, 2.3**

Property 4: Bug Condition - Order Independence

_For any_ set of contracts and _for any_ permutation of that set, `login()` SHALL return the same `status_code`, the same `body.subscription_status`, and the same denial message.

**Validates: Requirements 2.9, 2.16**

Property 5: Bug Condition - Cancelled With Paid Time Remaining Grants

_For any_ input with a contract whose `status` is CANCELLED and whose `paid_through` is in the future, `login()` SHALL return `status_code == 200` with `body.subscription_status == "active"`.

**Validates: Requirements 2.3**

Property 6: Bug Condition - Active Grants Regardless Of Paid-Through

_For any_ input with a contract whose `status` is ACTIVE and whose `paid_through` is in the past, `login()` SHALL return `status_code == 200` with `body.subscription_status == "active"`, granting access through the dunning retry window.

**Validates: Requirements 2.2**

Property 7: Bug Condition - Contracts Under A Second Customer Record Count

_For any_ email mapping to customer records `[c1, c2]` where no contract under `c1` grants and some contract under `c2` does, `login()` SHALL return `status_code == 200` with `body.subscription_status == "active"`.

**Validates: Requirements 2.10**

Property 8: Bug Condition - Denial Message Comes From The Most Recent Contract

_For any_ input where no contract grants and at least one contract exists, `login()` SHALL return `status_code == 403`, a non-null `body.redirect_url`, and `body.error` equal to `_get_denial_message(newest.status)` where `newest` is the contract with the greatest `createdAt` under a deterministic tiebreak.

**Validates: Requirements 2.16, 2.17**

Property 9: Bug Condition - Bypass Survives Refresh

_For any_ email listed in `BYPASS_EMAILS`, `refresh()` on a valid token SHALL return `status_code == 200` with `body.success == true`, without consulting Appstle.

**Validates: Requirements 2.14**

Property 10: Bug Condition - login And refresh Agree

_For any_ input, the access decision reached by `login()` SHALL equal the access decision reached by `refresh()` on a token for the same email: both grant, or both deny with the same message.

**Validates: Requirements 2.13, 2.15**

Property 11: Bug Condition - Calendar Interval Math

_For any_ contract with a null `nextBillingDate` and a `billingPolicy.interval` of MONTH or YEAR, `paid_through` SHALL equal the renewal anchor advanced by `intervalCount` calendar months or years, and SHALL NOT equal the anchor advanced by a 30-day or 365-day approximation where the two differ.

**Validates: Requirements 2.7**

Property 12: Bug Condition - Underivable Paid-Through Does Not Grant

_For any_ contract with a null `nextBillingDate` and an absent `billingPolicy` or an unrecognized interval unit, `paid_through` SHALL be null, the contract SHALL NOT grant, and an ERROR SHALL be logged.

**Validates: Requirements 2.8**

Property 13: Bug Condition - Silent Downgrades Become Loud

_For any_ Appstle response missing `productSubscriberStatus`, the system SHALL still grant free-tier access (200, `"free"`) and SHALL emit an ERROR-level log record; and _for any_ Appstle response logged, the log SHALL record the contract count and each contract's `status` and dates rather than a 500-character truncation of the raw payload.

**Validates: Requirements 2.19, 2.20**

## Fix Implementation

### Prerequisite: capture real Appstle payloads — **COMPLETE**

`inspect_appstle_contracts.py --save` was run against three live customers: Dave (`2788838535`, the multi-contract lockout case), a recurring subscriber that has renewed once (`2788845447`), and the intended cancelled subscriber (`3289420039`). The four provisional decisions are now settled, two conclusively and two only partly. Findings below are read from the saved payloads, not inferred.

**Finding 1 — There is no renewal anchor field. The anchor is `createdAt` or nothing.**

The complete key set of a contract node, identical across all captured contracts, is:

```
__typename, billingPolicy, createdAt, customer, customerPaymentMethod,
deliveryPrice, id, lastPaymentStatus, lines, nextBillingDate, originOrder, status
```

Every candidate is **absent**: `lastBillingDate`, `lastOrderDate`, `lastPaymentDate`, `billingAttempt`, `startDate`, `endDate`, `cancelledAt`, `pausedAt`, `nextOrderDate`, `updatedAt`, `currentCycle`, `cycleIndex`. `createdAt` and `nextBillingDate` are the only two date fields on a contract. `lastPaymentStatus` does exist but is a status string (observed: `null`, `"SUCCEEDED"`), not a date, so it cannot serve as an anchor.

The renewed subscriber settles it with real data: `createdAt = 2026-06-16`, `nextBillingDate = 2026-08-16`, `billingPolicy` MONTH × 1, and the store owner confirms one renewal billed on `2026-07-16`. **That renewal date appears nowhere in the payload.** `createdAt` + one interval yields `2026-07-16` — one full interval behind the true paid-through of `2026-08-16`. The design's concern about the `createdAt` fallback is therefore confirmed, not hypothetical.

Consequence: the provisional two-step priority (`lastBillingDate` then `createdAt`) collapses to `createdAt` only. The fallback and its ERROR log are both kept. Rationale: for a never-renewed contract `createdAt` + interval is exactly correct; for a renewed contract it lands one or more intervals in the past, which errs toward **denial** and can never produce a false grant. Strictly better than returning `None`, and safe in the direction that matters.

**Finding 2 — `billingPolicy` shape confirmed, and `intervalCount` is load-bearing.**

Keys are `interval` (string) and `intervalCount` (integer), nested under `billingPolicy` with `__typename == "SubscriptionBillingPolicy"`. Observed values:

| `interval` | `intervalCount` | Selling plans observed |
|---|---|---|
| `DAY` | `30` | "One-time Purchase", "30-Day Access — $10.95" |
| `MONTH` | `1` | "Monthly Subscription" |

No `WEEK` or `YEAR` observed; support for all four units is retained anyway. Note that `intervalCount` is frequently **not** 1 — 30 is the common case here — so honouring `intervalCount` is load-bearing, not a theoretical nicety.

**Finding 3 — Partially answered. `nextBillingDate` was always present, but no CANCELLED contract was captured.**

`nextBillingDate` is present and non-null on *every* captured contract, including all three PAUSED ones. In observed data the `paid_through` fallback therefore **never fires** — every contract is decided directly by `nextBillingDate`. That substantially de-risks clause 2.6, but it also means the fallback path cannot be validated against real data and will only ever be exercised by synthetic fixtures.

**Open risk:** no CANCELLED contract exists in the capture. All three customers show per-contract status PAUSED or ACTIVE; the intended cancelled sample turned out to be a lapsed 30-day one-time purchase that Appstle reports as PAUSED. So "does `nextBillingDate` survive cancellation" remains **open**. If a CANCELLED contract drops `nextBillingDate`, the `createdAt` fallback becomes the sole signal for cancelled-with-paid-time customers, and per Finding 1 that signal is wrong by one or more intervals for any renewed contract. **Recommendation: capture a genuinely CANCELLED contract before relying on clause 2.3 for cancelled customers in production.**

Related discovery, worth stating plainly: **PAUSED is Appstle's status for one-time and 30-day purchases that are simply not set to auto-renew. It does not mean "suspended."** Dave's two contracts and the lapsed customer's contract are all PAUSED with selling plans named "One-time Purchase" and "30-Day Access — $10.95". This independently confirms the requirements' note that status labels have misled on this system, and it is precisely why the derived paid-through date rather than the label must drive the decision.

**Finding 4 — Unanswered. Pagination is cursor-based, but the request parameter name is still unknown.**

`subscriptionContracts.pageInfo` is present on every payload with keys `hasPreviousPage`, `hasNextPage`, `startCursor`, `endCursor` — cursor-based, with opaque base64 cursors. But `hasNextPage` was `false` for all three customers, so no pagination request was ever exercised and the query parameter name that `/api/external/v2/subscription-customers/{customerId}` accepts for a cursor remains unknown.

Design decision: **implement detection now, defer cursor-following.** If `hasNextPage` is `true`, log at ERROR level that contracts may be missing — per clause 2.11, incomplete data biases toward false denial of a paying customer. Actual page-following waits until either Appstle's API docs confirm the parameter or a customer with more than one page appears. Task 9.3 is therefore scoped to detection-plus-ERROR-log rather than blocked indefinitely.

**Fixtures.** Sanitized payloads still go under `tests/fixtures/appstle/` so the property tests run offline (Task 2). Payloads contain customer PII; sanitize emails and names, keep dates, statuses, `billingPolicy`, `customerId`, and `pageInfo`. One captured payload contains a cardholder name and masked card number, so the entire `customerPaymentMethod` block must be stripped, not just redacted. The raw `appstle-payload-*.json` files are covered by the `/*.json` rule in `.gitignore` and are not committed.

### Changes Required

Assuming the root cause analysis above (it is read from the code, so the risk here is low):

**File**: `backend/subscription_auth.py`

1. **New `ContractView` dataclass** (module level, frozen). Fields: `customer_id: int`, `contract_id: Optional[str]`, `status: Optional[str]`, `next_billing_date: Optional[datetime]`, `created_at: Optional[datetime]`, `renewal_anchor: Optional[datetime]`, `renewal_anchor_field: Optional[str]`, `interval: Optional[str]`, `interval_count: int = 1`. All datetimes UTC-aware at construction. `renewal_anchor_field` exists so the log line can name where the anchor came from, and so Property 12's ERROR path is testable.

2. **New `_parse_iso8601(value) -> Optional[datetime]`** (module level). Handles the `Z` suffix, coerces naive datetimes to UTC, returns `None` and logs on parse failure. The current code repeats the `.replace("Z", "+00:00")` dance and the `if tzinfo is None` patch-up in four places; centralize both.

2b. **New `_utcnow() -> datetime`** (module level) returning `datetime.now(timezone.utc)`, with `_paid_through()` and `_contract_grants()` calling it instead of reading the clock inline. Numbered `2b` rather than renumbered into the list because items 3-16 are cross-referenced by number elsewhere in this document and in `tasks.md`; it sits here because it is a small module-level helper of the same kind as `_parse_iso8601`.

    **Why it is required.** The sanitized fixtures in `tests/fixtures/appstle/` keep the captured dates verbatim, because that fidelity is what makes them evidence that the bug is real. Those dates are absolute: Dave's granting contract has `nextBillingDate` `2026-08-27T19:00:00Z`, in the future relative to the capture instant `2026-08-09T01:31:12Z` and in the past afterwards. With no clock seam, every date-dependent test silently inverts its verdict once wall-clock time crosses those dates and the suite begins failing for reasons unrelated to the code — Property 3 would start asserting the opposite of what it means to assert. Tests therefore pin the clock to `FIXTURE_NOW = 2026-08-09T01:31:12Z` (exported from `tests/fixtures/appstle/fixture_clock.py`) by monkeypatching this one function.

    **Why a module-level function rather than a `now=` parameter.** One patch point, and no signature churn across `_paid_through`, `_contract_grants`, `decide_access`, `verify_subscription`, `login`, and `refresh`.

    **This adds no second clock path.** The existing code already calls `datetime.now(timezone.utc)` inline in the step-4 ladder of both `login()` and `refresh()` (the `next_billing` comparison), and those two call sites disappear when both branches move onto `decide_access()` per changes 12 and 13. The remaining `datetime.now(timezone.utc)` calls in token creation and the refresh grace-window check are not access-decision reads and stay as they are.

    Depended on by Task 4 (harness), Task 8.3, and Task 8.4. Not implemented by Task 2, which only records the requirement.

3. **New `_add_calendar_interval(anchor, interval, count) -> Optional[datetime]`** (module level). `relativedelta(years=|months=|weeks=|days=)` keyed on `YEAR|MONTH|WEEK|DAY`, multiplied by `count`. Returns `None` for an unrecognized unit. No 30/365-day approximations. Per Finding 2 the source keys are `billingPolicy.interval` and `billingPolicy.intervalCount`, observed as `DAY`/`30` and `MONTH`/`1`; `intervalCount` is commonly 30, so multiplying by `count` is required for correctness on real data, and all four units stay supported even though only two were observed.

4. **New `_paid_through(c: ContractView) -> Optional[datetime]`** (module level). Implements `paidThrough` above: `next_billing_date` if present; else `created_at` + one interval with an ERROR log; `None` plus ERROR when `created_at` or the interval is unusable. Per Finding 1 there is **no anchor priority order to implement** — Appstle exposes no `lastBillingDate`-style field, so `created_at` is the only anchor and `renewal_anchor_field` is always either `"createdAt"` or unset. Keep the ERROR log: the renewed subscriber proves this path understates paid time by a full interval, which under-grants rather than over-grants but is still worth an alert. Per Finding 3 this whole fallback did not fire on any captured contract, so it is exercised by synthetic fixtures only.

5. **New `_contract_grants(c: ContractView) -> bool`** (module level). Implements `contractGrants` above. `ACTIVE` short-circuits without touching `paid_through`.

6. **New `AccessDecision` dataclass** and **`decide_access(contracts, product_subscriber_status, email) -> AccessDecision`** (module level, pure, no I/O). Fields: `granted: bool`, `subscription_status: str`, `denial_message: Optional[str]`, `redirect_url_needed: bool`, `deciding_contract: Optional[ContractView]`. Logic:
   - If any contract grants → granted, `"active"`.
   - Else if contracts exist → denied; pick `newest = max(contracts, key=(created_at, contract_id))` with `created_at is None` sorting last, `contract_id` as the deterministic tiebreak (2.16); `denial_message = _get_denial_message(newest.status)`, `subscription_status = _normalize_status(newest.status)`.
   - Else (empty `nodes[]`) → fall back to `product_subscriber_status` (2.12): `ACTIVE` → granted `"active"`; `PAUSED`/`CANCELLED` → denied with the corresponding message; null/unknown → granted `"free"` with an ERROR log when the field was missing entirely (2.19).
   - Being pure and module-level, this is directly unit-testable without HTTP, a service instance, or env config — the seam the current code lacks.

7. **Extend `AppstleSubscriptionResponse`** with `contracts: list[ContractView] = []`. Keep `product_subscriber_status`, `next_billing_date`, `is_valid`, `subscription_status`, `expiration_date` so no external consumer breaks; `expiration_date` stays `None` (3.13, out of scope). Populate the scalar `next_billing_date` from the deciding contract for logging continuity only — nothing reads it for decisions after this change.

8. **Rewrite `_parse_contract_response()`** into `_parse_contract_nodes(payload, customer_id, email) -> list[ContractView]` plus a thin assembler. Iterate every node in `subscriptionContracts.nodes`, read the per-contract `status` (clause 1.5 — first use of this field in the codebase), and build a `ContractView` each. Log contract count and a per-contract `status`/dates summary (2.20).

9. **Replace `_extract_customer_id()` with `_extract_customer_ids(data) -> list[int]`.** Same payload normalization (bare list, `{"content": [...]}`, single-record dict), but collect all non-null `customerId` values, de-duplicated, order preserved. No external callers exist — verified, it is referenced only inside `verify_subscription()`. Note from the capture: each of the three emails mapped to exactly **one** `customerId`, so the multi-customer-record path (clause 2.10 / Property 7) is unobserved in real data and will be **fixture-only**. It is still built, because a single unobserved case is not evidence the API cannot return two, and the failure mode is a false denial of a paying customer.

10. **New `_appstle_get(session, url, params=None) -> Any`** — one method wrapping the status check, JSON parse, and error raising that steps 1 and 2 currently duplicate inline. This is also the test seam: property tests patch this one method with a payload router keyed by URL, so the parser, the multi-customer traversal, and the pagination loop all stay under test while assertions are made on `login()`'s returned `status_code` and body. Without this seam, tests can only reach the parser by stubbing `verify_subscription()`, which is precisely the mistake that let this bug ship.

11. **Rewrite `verify_subscription()`** to: step 1 → `_extract_customer_ids`; empty → no-subscription response unchanged; then for each `customerId`, step 2 → parse contracts → inspect `pageInfo.hasNextPage` via `_fetch_contract_pages()` with a bounded page cap (10) and an ERROR log if a next page is advertised but cannot be followed (2.11); accumulate contracts across all records. Per Finding 4, `_fetch_contract_pages()` ships as **detection plus ERROR log only** — `pageInfo` is cursor-based (`hasPreviousPage`, `hasNextPage`, `startCursor`, `endCursor`, opaque base64 cursors) but `hasNextPage` was `false` on every captured customer, so the cursor request parameter name is unknown and cannot be guessed. `hasNextPage == true` is treated as "contracts may be missing" and logged at ERROR; actual cursor-following is added once Appstle's docs confirm the parameter or a multi-page customer appears. Aggregate the fallback `product_subscriber_status` by fixed priority `ACTIVE > PAUSED > CANCELLED > other > None` rather than "first seen", so the result is order-independent (2.9). Remove the `str(...)[:500]` truncation from both step logs (2.20).

12. **Rewrite `login()` step 4** as: bypass → `"active"` (unchanged, 3.10); `appstle_resp is None` → `"free"` (unchanged, 3.7); else one call to `decide_access()` and a single branch on `decision.granted`. Denials return `LoginDeniedResponse(error=decision.denial_message, subscription_status=decision.subscription_status, redirect_url=self.signup_url)`. Steps 1, 2, 5, 6a, 6b, 7, 8 are untouched. Roughly 70 lines of nested ladder collapse to about 10.

13. **Rewrite `refresh()` step 4** the same way, and **add the missing `BYPASS_EMAILS` check** before the Appstle call (2.14, clause 1.10). Keep the JWT-claims-preserving path when Appstle is unavailable (3.8). Extract the bypass list computation into a small `_is_bypass_email(email)` helper so the two callers cannot drift.

14. **Use the existing dead helpers instead of inline strings** (2.17, clause 1.13). `_get_denial_message()` and `_normalize_status()` become live via `decide_access()`. **Update `DENIAL_MESSAGES` values to the exact strings the inline code emits today** — `EXPIRED` and `PAUSED` → `"Your subscription has expired. Resubscribe to continue."`, `CANCELLED` → `"Your subscription has been cancelled. Resubscribe to continue."` The current dict values omit the `"Resubscribe to continue."` sentence; adopting the dict as-is would silently change denial copy for the preserved expired-subscriber path (3.3). Add an `ACTIVE` key mapping to the expired message for the pathological "status says ACTIVE but the contract did not grant" case.

15. **Delete the tag-based fallback entirely** (2.18, clause 1.12). Remove `_parse_tags_response()`, `_extract_customer_tags()`, `TagConfig`, `load_tag_config()`, `_derive_status_from_tags()`, `self.tag_config`, and its `__init__` log line; drop `SUBSCRIPTION_TAG_ACTIVE|PAUSED|INACTIVE` from `.env.example`. Clause 2.18 permits either wiring the verdict in or deleting it. Deletion is chosen because it is the behavior-preserving option: the tag verdict is discarded today, so those customers land in free tier, and after deletion they still land in free tier. Wiring it in would *change* live behavior on the strength of a signal already documented as wrong on this system (tags reported "active" for a paused subscription). Where `_parse_contract_response()` currently falls back to tags, return an empty-contracts response instead and let `decide_access()`'s `productSubscriberStatus` fallback handle it.

16. **Declare `python-dateutil` in `requirements.txt`** (e.g. `python-dateutil>=2.8.2`). It resolves at runtime today only as a transitive dependency of pandas; `relativedelta` becomes load-bearing for access decisions, so it needs to be a first-class pinned dependency rather than an accident of the dependency tree.

**File**: `backend/subscription_test_endpoint.py` — **delete** (2.15, clause 1.11). Its own docstring says it should be removed after the bugfix; it currently exposes unauthenticated `POST /api/test/subscription-decision`, instantiates a `SubscriptionAuthService` at import time, and carries a fourth drifted copy of the ladder.

**File**: `backend/main.py` — remove the `subscription_test_router` import/registration block (the `try` block ending in the `"✅ Subscription test endpoint enabled..."` print, around lines 361-370).

**Files**: `test_subscription_bug_exploration.py`, `test_subscription_preservation.py` (project root) — both drive the deleted endpoint over HTTP against staging, so both break on deletion. Replace with in-process tests against `login()` / `refresh()` as described below. Their failure mode is the cautionary tale for the new suite: they passed while asserting on a copy of the logic and on fields the decision path never reads.

**Not changed**: `backend/subscription_auth_routes.py` (the customer auth router; it passes `status_code` and `body` straight through and needs no edit), `backend/auth.py` and `backend/auth_routes.py` (admin auth, entirely separate), token creation, and the usage gate.

## Testing Strategy

### Validation Approach

Two phases. First, surface counterexamples on the **unfixed** code to confirm the root cause and capture the preservation baseline. Then verify the fix grants access on every bug-condition input and leaves everything else byte-identical.

Every assertion is made on what `login()` and `refresh()` actually return — `result["status_code"]` and `result["body"]` — never on parser internals. Payloads are injected at the `_appstle_get` seam so the parser, multi-record traversal, and pagination stay inside the system under test. `token` is compared by decoded claim shape and key set, not string equality, since a fresh JWT differs per call.

Test harness, shared by all three suites: instantiate `SubscriptionAuthService` with valid `APPSTLE_*` / `JWT_SECRET_KEY` / `SUBSCRIPTION_SIGNUP_URL` env values, monkeypatch `_appstle_get` with a payload router keyed by URL, stub `password_service` so password checks are deterministic, and reset the rate limiter between cases. `pytest`, `pytest-asyncio`, and `hypothesis` are already in `requirements.txt`. Runs offline; no staging dependency.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix, and confirm or refute the root cause analysis. If refuted, re-hypothesize before writing any fix.

**Test Plan**: Feed canned Appstle payloads through `_appstle_get` and assert the *expected correct* outcome from `login()`. Run against unfixed code; the failures and their exact shape are the evidence.

**Test Cases**:
1. **Dave's captured payload**: two PAUSED contracts, `nodes[0]` expired, `nodes[1]` paid, `BYPASS_EMAILS` empty — expect 200/`"active"` (will fail on unfixed code: 403 expired).
2. **Reordered Dave**: same two contracts with `nodes` reversed — expect the same result as case 1 (will pass on unfixed code, and that asymmetry against case 1 is itself the order-dependence counterexample).
3. **Two customer records**: `c1` expired only, `c2` paid — expect 200/`"active"` (will fail: `c2` never fetched; assert via the payload router that no step-2 request for `c2` was made).
4. **Paginated contracts**: `hasNextPage=true`, granting contract on page 2 — expect 200/`"active"` (will fail: page 2 never requested).
5. **CANCELLED with paid time**: single contract, `nextBillingDate` in the future — expect 200/`"active"` (will fail: 403 cancelled).
6. **PAUSED with null `nextBillingDate`, derivable**: monthly, anchor 8 days ago — expect 200/`"active"` (will fail: 403 expired).
7. **Denial message from newest contract**: newest CANCELLED, older PAUSED-expired — expect 403 with the cancelled message (will fail: expired message).
8. **Bypass through refresh**: bypass email, valid token, Appstle returning an all-expired payload — expect 200/`success=true` (will fail: 403).
9. **Edge case, unrecognized interval**: no `nextBillingDate`, `interval="FORTNIGHT"` — expect 403 plus an ERROR log record (may pass on unfixed code for the wrong reason; assert the ERROR record so the pass is meaningful).

**Expected Counterexamples**:
- Cases 1, 3, 4 return 403 with `"Your subscription has expired. Resubscribe to continue."` where 200/`"active"` is required — confirming root causes 1, 2, and 3.
- Case 3 additionally shows no step-2 HTTP call for the second `customerId`.
- Cases 5 and 6 confirm root cause 4 (label-driven decision).
- Case 8 confirms the `login()`/`refresh()` drift.
- Possible causes if the failures do NOT match: Appstle orders contracts newest-first for some customers (would weaken but not remove the bug), or `productSubscriberStatus` already reflects the newest contract (would change which clause dominates). Either outcome sends us back to re-hypothesize before implementation.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed code produces the expected behavior.

**Pseudocode:**
```
FOR ALL X WHERE isBugCondition(X) DO
  result := login_fixed(X)
  ASSERT result.status_code = 200
  ASSERT result.body.subscription_status = "active"
END FOR
```

Generation strategy for the property tests: Hypothesis composite strategies build lists of contract dicts over `status ∈ {ACTIVE, PAUSED, CANCELLED, EXPIRED, junk, None}`, `nextBillingDate ∈ {past, future, null}`, anchors past and future, intervals over `{DAY, WEEK, MONTH, YEAR, unrecognized, absent}`, and `intervalCount ∈ 1..12`; those contracts are then distributed across 1-3 customer records and 1-3 pages. `isBugCondition` is computed on the generated set to route each case to the fix-checking or preservation assertion. Order independence is tested by `permutations()` over the generated list.

Covers Properties 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13.

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed code produces the same result as the original.

**Pseudocode:**
```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT login_original(X) = login_fixed(X)
END FOR
```

**Testing Approach**: Property-based testing carries the weight here. The preserved surface is wide (fourteen clauses across subscription, password, rate-limit, config, and token paths), the input space is combinatorial, and the failure mode being guarded against is exactly the one that shipped: a hand-picked set of examples that agrees with the implementation rather than with the requirement. Hypothesis generating across the full contract domain, with bug-condition inputs routed away, catches the edge cases a fixed example list would not.

Baselines are captured mechanically rather than transcribed by hand: run the preservation suite on the unfixed code with the `_appstle_get` router in record mode, serialize each `(status_code, normalized_body)` to a golden file, then assert against those goldens after the fix. `token` is normalized to its decoded claim key set before comparison. The three documented Preservation Exceptions are asserted separately, with their intended new values, so the goldens never encode the behavior being deliberately changed.

**Test Plan**: Observe behavior on UNFIXED code for all non-bug inputs, freeze it, then re-assert after the fix.

**Test Cases**:
1. **ACTIVE subscriber**: observe 200/`"active"` on unfixed code, verify unchanged (3.1).
2. **No Appstle record**: observe 200/`"free"`, verify unchanged (3.2).
3. **All contracts expired**: observe 403 + expired message + non-null `redirect_url`, verify unchanged (3.3). This is the case most at risk from change 14 — verify the denial copy is byte-identical.
4. **Empty `nodes[]`, `productSubscriberStatus` present**: observe the decision, verify unchanged (2.12, 3.2).
5. **Wrong password with an active subscription**: observe 401 `"Invalid email or password"`, verify unchanged (3.4).
6. **Rate limit exceeded**: 6 rapid attempts from one IP, observe 429 on the 6th, verify unchanged (3.5).
7. **Missing Appstle config**: observe 503, verify unchanged (3.6).
8. **Appstle timeout / HTTP 500 / malformed JSON at login**: observe free-tier fall-through, verify unchanged for all three failure modes (3.7).
9. **Appstle unavailable at refresh**: observe status preserved from JWT claims, verify unchanged (3.8).
10. **New user, weak password**: observe 400 + `failed_rules`, verify unchanged (3.9).
11. **`BYPASS_EMAILS` at login**: observe 200/`"active"` with no Appstle call, verify unchanged (3.10).
12. **Grace window**: token 2 minutes expired accepted, 10 minutes expired → 401, verify unchanged (3.11).
13. **JWT claim shape**: exact claim key set and 1-hour `exp - iat`, verify unchanged (3.12).
14. **Null expiry fields**: `expires_at` and `subscription_expires_at` null on every success path, verify unchanged (3.13).

Covers Property 2.

### Unit Tests

- `_add_calendar_interval`: month-end rollover (Jan 31 + 1 month), leap day (Feb 29 + 1 year), `intervalCount > 1`, each of `DAY|WEEK|MONTH|YEAR`, unrecognized unit → `None`.
- `_paid_through`: `nextBillingDate` present wins over the `createdAt` anchor; the `createdAt` path emits ERROR (there is no anchor priority to test — per Finding 1 `createdAt` is the only anchor); null `createdAt` → `None` + ERROR, never interval arithmetic on a null anchor; absent `billingPolicy` → `None` + ERROR; unrecognized interval → `None` + ERROR.
- `_contract_grants`: `ACTIVE` grants with `paid_through` in the past and with `paid_through` null; `PAUSED`/`CANCELLED` gated on `paid_through`; unknown status and null status do not grant; status case-insensitivity.
- `decide_access`: any-grants wins; newest-contract denial selection including the `contract_id` tiebreak and null `created_at`; empty-contracts fallback for each `productSubscriberStatus` value; missing-status ERROR.
- `_extract_customer_ids`: bare list, `{"content": [...]}`, single-record dict, duplicate IDs, null IDs, empty, malformed input.
- `_parse_contract_nodes`: multi-node parsing, per-contract `status` extraction, naive-datetime coercion to UTC, unparseable dates, non-dict nodes.
- `_parse_iso8601`: `Z` suffix, explicit offset, naive input, garbage, `None`.
- `_is_bypass_email`: whitespace, case, empty env var, trailing commas.

### Property-Based Tests

- **Property 1 / 3-7**: generate contract sets across multiple customer records and pages; where any contract grants, `login()` returns 200/`"active"`.
- **Property 4**: `permutations()` of every generated contract set produce identical `status_code`, `subscription_status`, and denial message.
- **Property 8**: for all-denied sets, the denial message matches the newest contract by `createdAt` under the deterministic tiebreak.
- **Property 10**: for every generated input, `login()` and `refresh()` reach the same access decision.
- **Property 11**: for MONTH and YEAR intervals over random anchors, `paid_through` equals calendar arithmetic and diverges from the 30/365-day approximation where those differ.
- **Property 12**: for random unrecognized interval units and absent billing policies, the contract never grants and an ERROR is logged.
- **Property 2**: for every generated input where `isBugCondition` is false, the response matches the recorded golden.

### Integration Tests

- Full login → `/api/auth/me` → refresh cycle for a multi-contract customer, verifying the `session_token` cookie is set with the same flags and that `subscription_status` survives the round trip.
- Staging verification against Dave's real Appstle data with his entry removed from `BYPASS_EMAILS` — the end-to-end proof that the lockout is gone and that the bypass entry can be retired.
- `POST /api/test/subscription-decision` returns 404 after deletion, and `backend/main.py` still boots cleanly with the registration block removed.
- Contract-count and per-contract log lines appear untruncated for a multi-contract customer, and the ERROR-level records fire for a missing `productSubscriberStatus`, a `createdAt`-derived `paid_through`, an underivable `paid_through`, and an unfollowable next page.
- Free-tier customer exhausting `FREE_QUESTION_LIMIT` still gets the frontend subscription prompt with a signup URL (3.14).
