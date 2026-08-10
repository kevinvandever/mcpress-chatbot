# Implementation Plan

## Overview

This plan fixes the multi-contract subscription lockout in `backend/subscription_auth.py`. It opens with a hard blocker: Task 1 captures real Appstle payloads from three live customers and lands four findings in `design.md`, because the renewal anchor field, the `billingPolicy` shape, whether `nextBillingDate` survives on cancelled contracts, and the pagination parameter are all provisional until observed. Tasks 2-4 turn that capture into sanitized fixtures, extract the `_appstle_get()` test seam, and build the offline harness with a URL-keyed payload router.

Tasks 5-7 establish the pre-fix baseline. The bug condition exploration test (Property 1) and the remaining fix-checking properties are written and run on UNFIXED code, so their failures document which root cause each counterexample confirms. The preservation suite (Property 2) records its goldens mechanically from the unfixed code, with the three Preservation Exceptions asserted separately so no golden encodes behavior that is being deliberately changed.

Task 8 builds the pure decision layer — `ContractView`, `_parse_iso8601()`, `_add_calendar_interval()`, `_paid_through()`, `_contract_grants()`, aligned `DENIAL_MESSAGES`, and the I/O-free `decide_access()` — none of which changes observable behavior on its own. Task 9 rewrites the callers onto it: multi-node contract parsing, multi-customer-record and paginated collection, `login()` and `refresh()` reduced to a single `decide_access()` call, and deletion of the tag-based fallback plus the duplicate test endpoint.

Tasks 10-12 are the verification passes: re-run the same pre-fix suites to confirm the bug condition test now passes and preservation still holds, verify against real Appstle data on staging after deploy, then a final checkpoint before promoting `staging` → `main`.

### Blocking prerequisite

Task 1 is a hard blocker. Every task marked **[BLOCKED ON TASK 1]** touches `_paid_through`, `_add_calendar_interval`, or contract pagination, and cannot be started until the payload capture in Task 1 has landed its four findings in `design.md`. Nothing else in the plan may reorder around it.

## Tasks

- [x] 1. Capture real Appstle payloads and finalize the provisional design decisions
  - **HARD BLOCKER** — no task marked [BLOCKED ON TASK 1] may start before this is complete
  - With `APPSTLE_API_URL` / `APPSTLE_API_KEY` exported, run `python3 inspect_appstle_contracts.py dave@shireyllc.com <renewed-subscriber-email> <cancelled-subscriber-email> --save` (project root, already written; emails are positional args) — three customers: Dave (the multi-contract lockout case), one recurring subscriber that has renewed at least once (the only way to tell whether a `lastBillingDate`-style field exists and advances on renewal), and one cancelled subscriber
  - Record these four findings into the **provisional** sections of `.kiro/specs/subscription-multi-contract-access/design.md` (Glossary "Renewal anchor", `paidThrough` pseudocode, and Fix Implementation items 3, 4, 9, 11), replacing the `lastBillingDate` placeholder:
    1. The renewal anchor field name(s) Appstle actually returns and their priority order
    2. The `billingPolicy` shape — exact key names for interval unit and `intervalCount`, plus the observed value set
    3. Whether `nextBillingDate` survives on CANCELLED contracts (determines how often the fallback fires at all)
    4. The pagination parameter name accepted by `/api/external/v2/subscription-customers/{customerId}`, if any
  - Keep the raw `appstle-payload-*.json` files out of git (they contain customer PII); they are the input to Task 2 only
  - _Requirements: 2.6, 2.7, 2.8, 2.11_

- [x] 2. Create sanitized Appstle fixtures from the Task 1 capture
  - Depends on Task 1; must precede every property test that consumes fixtures
  - Create `tests/fixtures/appstle/` and commit sanitized payloads derived from the Task 1 capture. Sanitization: strip the entire `customerPaymentMethod` block from every contract node (one capture carries a real cardholder name, card brand, first/last digits, masked number, and expiry — strip, do not redact), strip `originOrder` (real order names and IDs) and `lines[].variantImage` URLs, and replace emails with placeholders (`multi.contract@example.com`, `renewed.monthly@example.com`, `lapsed.thirtyday@example.com`). Keep `lines[].sellingPlanName` — it is load-bearing evidence that Appstle's PAUSED means "one-time purchase, not auto-renewing" and contains no PII. Preserve verbatim: all dates, all per-contract `status` values, `productSubscriberStatus`, `billingPolicy`, `customerId`, contract `id`, `lastPaymentStatus`, and every `pageInfo` block including the opaque cursors
  - **Time dependence — resolved, not worked around.** The captured dates are absolute, and Dave's granting contract (`nextBillingDate` 2026-08-27) is in the future relative to the capture but in the past afterwards. Real fixtures keep the captured dates verbatim (fidelity is what makes them evidence); the clock is pinned instead at `FIXTURE_NOW = 2026-08-09T01:31:12Z`, exported from `tests/fixtures/appstle/fixture_clock.py` along with `fixture_now()`, `at_offset()`, and `SYNTHETIC_OFFSETS`. This requires the `_utcnow()` clock seam now recorded as **design change 2b** for `backend/subscription_auth.py` — a single monkeypatch point, no `now=` signature churn — which Tasks 4, 8.3, and 8.4 depend on. Task 2 records the requirement only; it implements no production code
  - Real-data fixtures (dates verbatim):
    - `dave_two_paused_contracts.json` — step-2 payload, `customerId` 2788838535, `nodes[0]` expired (2026-07-02), `nodes[1]` with paid time remaining (2026-08-27). The Property 3 fixture
    - `renewed_subscriber.json` — the ACTIVE monthly subscriber, `customerId` 2788845447 (`createdAt` 2026-06-16, `nextBillingDate` 2026-08-16, MONTH × 1, `lastPaymentStatus` SUCCEEDED). Preserved 200 / `"active"` case (3.1)
    - `lapsed_paused_subscriber.json` — the lapsed 30-day purchaser, `customerId` 3289420039 (PAUSED, `nextBillingDate` 2026-05-23 past, DAY × 30). Preserved 403 case (3.3)
  - **Correction to the original fixture list: there is no `cancelled_subscriber.json`.** No CANCELLED contract was captured — the customer expected to be cancelled is reported by Appstle as PAUSED, which design Finding 3 records as an open risk. Fabricating a real-data cancelled fixture would invent an answer to an open question, so the real one is named `lapsed_paused_subscriber.json` and the cancelled cases are clearly-labelled synthetic fixtures instead
  - Synthetic fixtures, hand-built with dates as offsets from `FIXTURE_NOW`, each serving a specific property:
    - `step1_single_customer.json` — step-1 customer-lookup payload, one `customerId`
    - `step1_two_customers.json` — step-1 payload with two `customerId`s (Property 7; no real-data counterpart, the capture showed one `customerId` per email)
    - `contracts_page1.json` / `contracts_page2.json` — `pageInfo.hasNextPage` true on page 1, granting contract on page 2 (Property 1 via pagination). **Correction: Finding 4 records NO pagination parameter** — the endpoint documents none and `hasNextPage` was false for all three captured customers — so these use a synthetic placeholder cursor parameter, describe hypothetical pagination, and Task 9.3 stays scoped to detection-plus-ERROR-log only
    - `empty_nodes.json` — `subscriptionContracts.nodes == []` with `productSubscriberStatus` present (clause 2.12)
    - `no_subscription.json` — step-1 payload yielding no `customerId` (preserved 200 / `"free"`, clause 3.2)
    - `cancelled_with_paid_time.json` — single CANCELLED contract, `nextBillingDate` `FIXTURE_NOW` + 21 days (Property 5, a Preservation Exception)
    - `active_past_billing_dunning.json` — ACTIVE contract, `nextBillingDate` `FIXTURE_NOW` − 5 days (Property 6, must grant via the ACTIVE short-circuit)
    - `paused_null_nextbilling_derivable.json` — PAUSED, `nextBillingDate` null, `createdAt` `FIXTURE_NOW` − 8 days, MONTH × 1, so the `createdAt` fallback derives a future `paid_through` (Property 11 and a Preservation Exception)
    - `paused_unrecognized_interval.json` — PAUSED, `nextBillingDate` null, `billingPolicy.interval` `"FORTNIGHT"` (Property 12, must not grant, ERROR logged)
    - `paused_absent_billing_policy.json` — PAUSED, `nextBillingDate` null, `billingPolicy` absent entirely (Property 12)
    - `denial_newest_cancelled_older_paused.json` — two contracts, neither granting: newest by `createdAt` is CANCELLED, older is PAUSED with a past `nextBillingDate` (Property 8 — the denial message must come from the newest)
    - `missing_product_subscriber_status.json` — `productSubscriberStatus` absent with empty nodes (Property 13, 200 / `"free"` plus an ERROR record)
  - `tests/fixtures/appstle/README.md` records which live customer each real fixture derives from (by placeholder email and `customerId`, never the real email), exactly what was stripped and why, `FIXTURE_NOW` and why the pinned clock is required, which fixtures are real versus synthetic, and a coverage map from each fixture to the property or clause it serves
  - Verified: the raw `appstle-payload-*.json` files remain uncommitted (`git check-ignore` confirms the `/*.json` rule covers all three), no real email / cardholder name / card digits / masked number / order name appears anywhere under `tests/fixtures/appstle/`, every stripped key is absent from all fixtures, and the three real fixtures are byte-faithful to the capture apart from exactly those stripped keys
  - _Requirements: 2.1, 2.10, 2.11, 2.12_

- [x] 3. Extract the `_appstle_get()` test seam (behavior-preserving, before any property test)
  - In `backend/subscription_auth.py`, add `_appstle_get(self, session, url, params=None) -> Any` wrapping the status check, JSON parse, and error raising that step 1 and step 2 of `verify_subscription()` currently duplicate inline
  - Route both existing Appstle calls through it with no change to status codes, exception types, or fall-through behavior — this task must not alter any response
  - This is the single patch point for all property tests; without it, tests can only reach the parser by stubbing `verify_subscription()`, which is how this bug shipped
  - _Requirements: 2.13_
  - _Preservation: Preservation Requirements from design (3.1-3.14) — this refactor changes no observable behavior_

- [x] 4. Build the offline test harness with a URL-keyed payload router
  - Create `tests/subscription_harness.py`: builds a `SubscriptionAuthService` with valid `APPSTLE_*`, `JWT_SECRET_KEY`, and `SUBSCRIPTION_SIGNUP_URL` env values, monkeypatches `_appstle_get` with a payload router keyed by URL (step-1 lookup, per-`customerId` step-2, per-page step-2), stubs `password_service` for deterministic password checks, and resets the rate limiter between cases
  - The router records every requested URL so tests can assert that a second `customerId` or a second page was actually fetched
  - Include a `normalize_body()` helper that reduces `token` to its decoded claim key set so bodies compare across calls
  - Add Hypothesis composite strategies for contract dicts (`status` over `{ACTIVE, PAUSED, CANCELLED, EXPIRED, junk, None}`, `nextBillingDate` over `{past, future, null}`, anchors past and future, intervals over `{DAY, WEEK, MONTH, YEAR, unrecognized, absent}`, `intervalCount` 1..12) and for distributing contracts across 1-3 customer records and 1-3 pages
  - `pytest`, `pytest-asyncio`, and `hypothesis` are already in `requirements.txt`; the harness must run offline with no staging or database dependency
  - _Requirements: 2.9, 2.13_

- [x] 5. Write the bug condition exploration test
  - **Property 1: Bug Condition** - Any Granting Contract Grants Access
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it validates the fix when it passes in Task 11.1
  - **GOAL**: Surface counterexamples that demonstrate the bug and confirm or refute the root cause analysis
  - Create `tests/test_subscription_bug_condition.py` using the Task 4 harness and Task 2 fixtures
  - **Scoped PBT Approach**: the bug is deterministic, so scope the property to the concrete failing payloads from the capture — Dave's two PAUSED contracts, the two-customer-record pair, and the paginated pair — then widen with the Hypothesis contract-set strategy where `isBugCondition` clause (a) holds
  - Property: for every generated contract set where some contract grants but `nodes[0]` of the first customer record does not, `login()` returns `status_code == 200` and `body.subscription_status == "active"`
  - Assert on `login()`'s returned `status_code` and `body` only — never on parser internals
  - For the two-customer-record case, additionally assert via the router that no step-2 request was made for the second `customerId` on unfixed code
  - Run on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with 403 `"Your subscription has expired. Resubscribe to continue."` (this is correct — it proves the bug exists)
  - Document the counterexamples in the test module docstring: which root cause each failure confirms (1 = `nodes[0]` truncation, 2 = first-`customerId` truncation, 3 = no pagination). If the failures do not match, stop and re-hypothesize before any implementation
  - Mark complete when the test is written, run, and the failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.8, 2.1, 2.2, 2.3, 2.5, 2.10, 2.11, 2.12_

- [x] 6. Write the remaining fix-checking property tests (BEFORE implementing the fix)
  - Create `tests/test_subscription_fix_checking.py`, all cases driven through `login()` / `refresh()` with `_appstle_get` patched. Every property below is expected to FAIL on unfixed code except Property 6, which already passes and is included to lock the dunning grace window in place
  - **Property 3: Bug Condition** - Dave's Exact Payload: `dave_two_paused_contracts.json` with `BYPASS_EMAILS` empty → 200 / `"active"` (_Requirements: 2.1, 2.3_)
  - **Property 4: Bug Condition** - Order Independence: `permutations()` over each generated contract set → identical `status_code`, `body.subscription_status`, and denial message (_Requirements: 2.9, 2.16_)
  - **Property 5: Bug Condition** - Cancelled With Paid Time Remaining Grants: single CANCELLED contract, `nextBillingDate` in the future → 200 / `"active"` (_Requirements: 2.3_)
  - **Property 6: Bug Condition** - Active Grants Regardless Of Paid-Through: ACTIVE contract with `paid_through` in the past → 200 / `"active"` (_Requirements: 2.2_)
  - **Property 7: Bug Condition** - Contracts Under A Second Customer Record Count: `step1_two_customers.json`, no contract under `c1` grants, one under `c2` does → 200 / `"active"`, and the router shows a step-2 call for `c2` (_Requirements: 2.10_)
  - **Property 8: Bug Condition** - Denial Message Comes From The Most Recent Contract: all-denied sets → 403, non-null `body.redirect_url`, `body.error` equal to the message for the newest contract by `createdAt` with the `contract_id` tiebreak (_Requirements: 2.16, 2.17_)
  - **Property 9: Bug Condition** - Bypass Survives Refresh: email in `BYPASS_EMAILS`, valid token, Appstle returning an all-expired payload → `refresh()` returns 200 / `body.success == true` with no Appstle call (_Requirements: 2.14_)
  - **Property 10: Bug Condition** - login And refresh Agree: for every generated input, `login()` and `refresh()` on a token for the same email reach the same access decision and the same denial message (_Requirements: 2.13, 2.15_)
  - **Property 13: Bug Condition** - Silent Downgrades Become Loud: payload missing `productSubscriberStatus` → 200 / `"free"` plus an ERROR-level record via `caplog`; and a multi-contract payload logs the contract count and each contract's `status` and dates with no 500-character truncation (_Requirements: 2.19, 2.20_)
  - Run on UNFIXED code and record each observed failure in the module docstring
  - **EXPECTED OUTCOME**: Properties 3, 4, 5, 7, 8, 9, 10, 13 FAIL; Property 6 PASSES
  - Properties 11 and 12 target helpers that do not exist yet and are written in Tasks 8.3 and 8.4
  - _Requirements: 1.6, 1.7, 1.9, 1.10, 1.14, 1.15, 1.16, 2.2, 2.3, 2.9, 2.10, 2.13, 2.14, 2.16, 2.17, 2.19, 2.20_

- [x] 7. Write preservation property tests and record the unfixed-code goldens (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Bug Inputs Behave Identically
  - **IMPORTANT**: Follow observation-first methodology — the goldens are recorded mechanically from the UNFIXED code, never transcribed by hand
  - Create `tests/test_subscription_preservation_properties.py` plus goldens at `tests/fixtures/appstle/goldens/preservation_baseline.json`
  - Run the suite against unfixed code with the Task 4 router in record mode, serializing each case's `(status_code, normalized_body)` — `token` reduced to its decoded claim key set — then assert against those goldens
  - Property: for every generated input where `isBugCondition` is false (clauses (a), (b), and (c) all false), the response matches the recorded golden
  - **The three Preservation Exceptions are excluded from Property 2** and asserted separately with their intended NEW values, so the goldens never encode behavior being deliberately changed: single CANCELLED contract with paid time (2.3 / 1.7), PAUSED with null `nextBillingDate` and a future anchor + interval (2.6 / 1.6), and denied-with-newest-status ≠ `nodes[0]`-status (2.16 / 1.14)
  - Cases to record, all through `login()` / `refresh()`: ACTIVE subscriber (3.1); no Appstle record (3.2); every contract expired, byte-identical denial copy plus non-null `redirect_url` (3.3); empty `nodes[]` decided by `productSubscriberStatus` (2.12, 3.2); wrong password with an active subscription (3.4); 6 rapid attempts from one IP → 429 on the 6th (3.5); missing Appstle config → 503 (3.6); Appstle timeout, HTTP 500, and malformed JSON → free-tier fall-through (3.7); Appstle unavailable at refresh → status preserved from JWT claims (3.8); new user with a weak password → 400 + `failed_rules` (3.9); `BYPASS_EMAILS` at login with no Appstle call (3.10); token 2 minutes expired accepted and 10 minutes expired → 401 (3.11); JWT claim key set and 1-hour `exp - iat` (3.12); `expires_at` and `subscription_expires_at` null on every success path (3.13)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms the baseline behavior to preserve)
  - Mark complete when the goldens are committed and the suite passes on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13_

- [x] 8. Build the pure decision layer in `backend/subscription_auth.py`

  - [x] 8.1 Add `python-dateutil` to `requirements.txt`
    - Verified absent from `requirements.txt` today; it resolves only as a transitive dependency of pandas
    - Add `python-dateutil>=2.8.2` so `relativedelta` is a first-class pinned dependency before any access decision depends on it
    - No behavior change; nothing imports it until Task 8.3
    - _Requirements: 2.7_

  - [x] 8.2 Add `ContractView` and `_parse_iso8601()`
    - Module-level frozen dataclass `ContractView` with `customer_id: int`, `contract_id: Optional[str]`, `status: Optional[str]`, `next_billing_date: Optional[datetime]`, `created_at: Optional[datetime]`, `renewal_anchor: Optional[datetime]`, `renewal_anchor_field: Optional[str]`, `interval: Optional[str]`, `interval_count: int = 1`; all datetimes UTC-aware at construction
    - `renewal_anchor_field` records where the anchor came from so the log line can name it and Property 12's ERROR path is testable
    - Module-level `_parse_iso8601(value) -> Optional[datetime]`: handles the `Z` suffix, coerces naive datetimes to UTC, returns `None` and logs on parse failure — replacing the `.replace("Z", "+00:00")` and `tzinfo is None` patch-ups repeated in four places
    - Unit tests in `tests/test_subscription_helpers.py`: `Z` suffix, explicit offset, naive input, garbage, `None`
    - Nothing consumes these yet, so no observable behavior changes
    - _Requirements: 2.1, 2.6_

  - [x] 8.3 Add `_add_calendar_interval()` **[BLOCKED ON TASK 1]**
    - **Property 11: Bug Condition** - Calendar Interval Math
    - Module-level `_add_calendar_interval(anchor, interval, count) -> Optional[datetime]` using `relativedelta(years=|months=|weeks=|days=)` keyed on `YEAR|MONTH|WEEK|DAY` multiplied by `count`; returns `None` for an unrecognized unit; no 30-day or 365-day approximations
    - Use the interval unit key names and value set recorded in Task 1 finding 2
    - Unit tests: month-end rollover (Jan 31 + 1 month), leap day (Feb 29 + 1 year), `intervalCount > 1`, each of `DAY|WEEK|MONTH|YEAR`, unrecognized unit → `None`
    - Property test in `tests/test_subscription_fix_checking.py`: for MONTH and YEAR over random anchors and `intervalCount` 1..12, the result equals calendar arithmetic and differs from the 30/365-day approximation wherever the two diverge
    - _Requirements: 2.7_

  - [x] 8.4 Add `_paid_through()` and `_contract_grants()` **[BLOCKED ON TASK 1]**
    - **Property 12: Bug Condition** - Underivable Paid-Through Does Not Grant
    - Module-level `_paid_through(c: ContractView) -> Optional[datetime]` implementing the design's `paidThrough`: `next_billing_date` when present; else `renewal_anchor` + one interval, logging ERROR when the anchor is the weak `created_at` path; `None` plus ERROR when the anchor is null, `billingPolicy` is absent, or the interval unit is unrecognized — never interval arithmetic on a null anchor
    - Anchor field name and priority order come from Task 1 finding 1; replace the provisional `lastBillingDate`
    - Module-level `_contract_grants(c: ContractView) -> bool` implementing `contractGrants`: `ACTIVE` short-circuits to `True` without touching `paid_through` (the deliberate dunning grace); `PAUSED`/`CANCELLED` grant iff `paid_through` is in the future; every other or null status does not grant; status comparison case-insensitive
    - Unit tests: `nextBillingDate` wins over the anchor; anchor priority order; `created_at` path emits ERROR; absent `billingPolicy` → `None` + ERROR; unrecognized interval → `None` + ERROR; ACTIVE grants with `paid_through` past and null; PAUSED/CANCELLED gated on `paid_through`; unknown and null status do not grant; case-insensitivity
    - Property test: for random unrecognized interval units and absent billing policies, `paid_through` is null, the contract does not grant, and an ERROR is logged
    - _Requirements: 2.2, 2.3, 2.4, 2.6, 2.7, 2.8_

  - [x] 8.5 Align `DENIAL_MESSAGES` to the live inline strings and make the dict the live source
    - Both halves land in this one task so denial copy never changes in an intermediate state: aligning the values (2.21) and switching the code onto the dict (2.17) must be simultaneous
    - Update `DENIAL_MESSAGES` values to exactly what `login()` and `refresh()` emit today: `EXPIRED` and `PAUSED` → `"Your subscription has expired. Resubscribe to continue."`, `CANCELLED` → `"Your subscription has been cancelled. Resubscribe to continue."`; add an `ACTIVE` key mapping to the expired message for the pathological "status says ACTIVE but the contract did not grant" case; leave `DEFAULT_DENIAL_MESSAGE` reachable for unknown/empty statuses
    - The current dict omits the `"Resubscribe to continue."` sentence, so adopting it unaligned would silently change the preserved expired-subscriber denial copy (3.3)
    - `_get_denial_message()` and `_normalize_status()` become live in Task 8.6; no inline denial strings remain after Task 8.10
    - Unit tests asserting the exact strings, including that the 3.3 expired copy is byte-identical to the recorded golden
    - _Requirements: 1.13, 2.17, 2.21, 3.3_

  - [x] 8.6 Add `AccessDecision` and `decide_access()` — the single decision path
    - Module-level frozen dataclass `AccessDecision` with `granted: bool`, `subscription_status: str`, `denial_message: Optional[str]`, `redirect_url_needed: bool`, `deciding_contract: Optional[ContractView]`
    - Module-level pure `decide_access(contracts, product_subscriber_status, email) -> AccessDecision`, no I/O: any contract grants → granted `"active"`; else contracts exist → denied, `newest = max(contracts, key=(created_at, contract_id))` with `created_at is None` sorting last and `contract_id` as the deterministic tiebreak, `denial_message = _get_denial_message(newest.status)`, `subscription_status = _normalize_status(newest.status)`; else empty contracts → fall back to `product_subscriber_status`, `ACTIVE` → granted `"active"`, `PAUSED`/`CANCELLED` → denied with the matching message, null/unknown → granted `"free"` with an ERROR log when the field was missing entirely
    - Unit-test `decide_access()` **directly** in `tests/test_decide_access.py` — no HTTP, no service instance, no env config: any-grants wins; newest-contract denial selection including the `contract_id` tiebreak and null `created_at`; each `productSubscriberStatus` fallback value; missing-status ERROR record; order independence by feeding permuted contract lists
    - _Requirements: 2.1, 2.5, 2.9, 2.12, 2.13, 2.16, 2.17, 2.19_

- [x] 9. Wire the decision layer into data collection and the callers

  - [x] 9.1 Rewrite contract parsing into `_parse_contract_nodes()`
    - Replace `_parse_contract_response()` (`backend/subscription_auth.py`) with `_parse_contract_nodes(payload, customer_id, email) -> list[ContractView]` plus a thin assembler that keeps returning an `AppstleSubscriptionResponse`
    - Iterate EVERY node in `subscriptionContracts.nodes`, read the per-contract `status` (first use of that field anywhere in the codebase), and build one `ContractView` per node via `_parse_iso8601`
    - Extend `AppstleSubscriptionResponse` with `contracts: list[ContractView] = []`; keep `product_subscriber_status`, `next_billing_date`, `is_valid`, `subscription_status`, and `expiration_date` so no external consumer breaks; `expiration_date` stays `None`; populate the scalar `next_billing_date` from the deciding contract for logging continuity only
    - Replace the `str(data)[:500]` step-2 log with a structured line recording the contract count and each contract's `status` and dates
    - Unit tests: multi-node parsing, per-contract `status` extraction, naive-datetime coercion to UTC, unparseable dates, non-dict nodes
    - _Requirements: 1.5, 2.1, 2.20, 3.13_

  - [x] 9.2 Replace `_extract_customer_id()` with `_extract_customer_ids()`
    - `_extract_customer_ids(data) -> list[int]` keeps the existing payload normalization (bare list, `{"content": [...]}`, single-record dict) but collects ALL non-null `customerId` values, de-duplicated, order preserved
    - Verified no external callers — it is referenced only inside `verify_subscription()`, updated in Task 9.4
    - Unit tests: bare list, `{"content": [...]}`, single-record dict, duplicate IDs, null IDs, empty, malformed input
    - _Requirements: 2.10_

  - [x] 9.3 Add `_fetch_contract_pages()` pagination **[BLOCKED ON TASK 1]**
    - Follow `subscriptionContracts.pageInfo.hasNextPage` using the pagination parameter recorded in Task 1 finding 4, with a bounded page cap of 10, accumulating `ContractView`s across pages
    - Log at ERROR level when a next page is advertised but cannot be followed — under "grant if any contract grants", a granting contract stranded on an unread page is a false denial of a paying customer
    - Requests go through `_appstle_get()` so the property tests' router can serve `contracts_page1.json` / `contracts_page2.json`
    - _Requirements: 2.11_

  - [x] 9.4 Rewrite `verify_subscription()` for multi-record, multi-page collection **[BLOCKED ON TASK 1]**
    - Step 1 → `_extract_customer_ids()`; empty list → the existing no-subscription response, unchanged (3.2, 3.7)
    - For each `customerId`: step 2 via `_appstle_get()` → `_parse_contract_nodes()` → `_fetch_contract_pages()`; accumulate contracts across all customer records
    - Aggregate the fallback `product_subscriber_status` by fixed priority `ACTIVE > PAUSED > CANCELLED > other > None` rather than first-seen, so the result is order-independent
    - Remove the `str(...)[:500]` truncation from the step-1 log as well; keep the existing timeout / HTTP error / malformed-JSON handling exactly as-is so login still falls through to free tier
    - _Requirements: 2.9, 2.10, 2.11, 2.12, 2.20, 3.7_

  - [x] 9.5 Rewrite `login()` step 4 onto `decide_access()`
    - Bypass → `"active"` unchanged (3.10); `appstle_resp is None` → `"free"` unchanged (3.7); otherwise one `decide_access()` call and a single branch on `decision.granted`
    - Denials return `LoginDeniedResponse(error=decision.denial_message, subscription_status=decision.subscription_status, redirect_url=self.signup_url)` — no inline denial strings remain
    - Steps 1, 2, 5, 6a, 6b, 7, 8 (config check, rate limiting, password lookup and verification, new-user password rules, password-record creation, rate-limiter reset, token creation) are untouched
    - _Bug_Condition: isBugCondition(X) from design — isMultiContractBug OR isDecisionRuleBug OR isDenialMessageBug_
    - _Expected_Behavior: Correctness Properties 1, 3-8 from design_
    - _Preservation: Preservation Requirements from design, with the three Preservation Exceptions excluded_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.13, 2.16, 2.17, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 3.10, 3.12, 3.13_

  - [x] 9.6 Rewrite `refresh()` step 4 and add the missing bypass check
    - Extract `_is_bypass_email(email)` (handling whitespace, case, empty env var, trailing commas) and call it from both `login()` and `refresh()` so the two cannot drift again
    - Add the `BYPASS_EMAILS` check to `refresh()` before the Appstle call, issuing a token with active status
    - Replace `refresh()` step 4 with the same single `decide_access()` call; keep the JWT-claims-preserving path when Appstle is unavailable (3.8) and the 5-minute grace window behavior (3.11)
    - Unit tests for `_is_bypass_email`
    - _Bug_Condition: isBugCondition(X) from design; clause 1.10 (bypass absent from refresh)_
    - _Expected_Behavior: Correctness Properties 9, 10 from design_
    - _Preservation: Preservation Requirements 3.8, 3.11, 3.12 from design_
    - _Requirements: 2.13, 2.14, 3.8, 3.11, 3.12_

  - [x] 9.7 Delete the tag-based fallback
    - Remove `_parse_tags_response()`, `_extract_customer_tags()`, `TagConfig`, `load_tag_config()`, `_derive_status_from_tags()`, `self.tag_config`, and its `__init__` log line from `backend/subscription_auth.py`; drop `SUBSCRIPTION_TAG_ACTIVE|PAUSED|INACTIVE` from `.env.example`
    - Where the parser currently falls back to tags, return an empty-contracts response and let `decide_access()`'s `productSubscriberStatus` fallback decide
    - Deletion is the behavior-preserving option: the tag verdict is discarded today (it never sets `product_subscriber_status`), so those customers land in free tier before and after
    - _Requirements: 1.12, 2.18, 3.2_

  - [x] 9.8 Delete the fourth copy of the decision logic and retire its tests
    - Delete `backend/subscription_test_endpoint.py`
    - Remove its registration in `backend/main.py` — the `try` block importing `subscription_test_router` and printing `"✅ Subscription test endpoint enabled at /api/test/subscription-decision"` (around lines 365-374) — and confirm `backend/main.py` still imports cleanly
    - Retire `test_subscription_bug_exploration.py` and `test_subscription_preservation.py` (project root): both drive the deleted endpoint over HTTP against staging, so both break on deletion. Delete them; their coverage is replaced in-process by `tests/test_subscription_bug_condition.py`, `tests/test_subscription_fix_checking.py`, and `tests/test_subscription_preservation_properties.py`
    - _Requirements: 1.9, 1.11, 2.13, 2.15_

- [x] 10. Verify the fix against the pre-fix suites

  - [x] 10.1 Verify the bug condition exploration test now passes
    - **Property 1: Bug Condition** - Any Granting Contract Grants Access
    - **IMPORTANT**: Re-run the SAME test from Task 5 — do NOT write a new test
    - Run `python3 -m pytest tests/test_subscription_bug_condition.py`
    - **EXPECTED OUTCOME**: Test PASSES (confirms the bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.10, 2.11, 2.12_

  - [x] 10.2 Verify the remaining fix-checking properties now pass
    - **Properties 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13** from design
    - Re-run the SAME tests from Task 6 plus the property tests added in Tasks 8.3 and 8.4 — do NOT write new tests
    - Run `python3 -m pytest tests/test_subscription_fix_checking.py tests/test_subscription_helpers.py tests/test_decide_access.py`
    - **EXPECTED OUTCOME**: All properties PASS, including Property 6, which passed before the fix and must still pass
    - _Requirements: 2.2, 2.3, 2.7, 2.8, 2.9, 2.10, 2.13, 2.14, 2.16, 2.17, 2.19, 2.20_

  - [x] 10.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Bug Inputs Behave Identically
    - **IMPORTANT**: Re-run the SAME tests from Task 7 against the SAME goldens — do NOT re-record the goldens and do NOT write new tests
    - Run `python3 -m pytest tests/test_subscription_preservation_properties.py`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions). The three Preservation Exceptions assert their intended new values and are excluded from Property 2
    - Pay particular attention to case 3 (all contracts expired): the denial copy must be byte-identical to the golden, which is what Task 8.5 protects
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13_

- [-] 11. Verify against real Appstle data on staging
  - No local dev environment and no local database, so this step runs after deploy and never through `railway shell`
  - Deploy on the staging-first path: `feature/subscription-multi-contract-access` → `staging`, wait for the Railway staging deploy to finish
  - Create `verify_subscription_access_staging.py` (project root, API-based, `requests` only) that POSTs to `$API_URL/api/auth/login` against `https://mcpress-chatbot-staging.up.railway.app` for the three captured customers and prints each `status_code`, `subscription_status`, `error`, and `redirect_url`
  - The script must also assert `POST /api/test/subscription-decision` now returns 404 and that `GET /health` is green (proving `backend/main.py` boots with the registration block removed)
  - Remove `dave@shireyllc.com` from `BYPASS_EMAILS` in the staging environment and confirm he logs in with 200 / `"active"` on his real Appstle data — the end-to-end proof the lockout is gone and the bypass entry can be retired
  - Check `railway logs` for the untruncated contract-count and per-contract log lines, and for ERROR records on a missing `productSubscriberStatus`, a `created_at`-derived `paid_through`, an underivable `paid_through`, and an unfollowable next page
  - Confirm a free-tier customer exhausting `FREE_QUESTION_LIMIT` still gets the frontend subscription prompt with a signup URL
  - _Requirements: 2.11, 2.14, 2.15, 2.19, 2.20, 3.14_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Run the full offline suite: `python3 -m pytest tests/test_subscription_bug_condition.py tests/test_subscription_fix_checking.py tests/test_subscription_preservation_properties.py tests/test_subscription_helpers.py tests/test_decide_access.py`
  - Confirm all 13 design properties are green and the three Preservation Exceptions assert their intended new values
  - Confirm no root-level test file still targets the deleted `/api/test/subscription-decision` endpoint
  - Promote `staging` → `main` only after the staging verification in Task 11 is approved
  - Ensure all tests pass, ask the user if questions arise

## Notes

All property tests run offline: `pytest` in-process against `SubscriptionAuthService` with `_appstle_get` patched by a URL-keyed payload router reading fixtures from `tests/fixtures/appstle/`. There is no local dev environment and no local database, so real-Appstle verification (Task 11) is an API-based script run against staging after deploy — never `railway shell`.

Every assertion is made on `login()`'s / `refresh()`'s returned `status_code` and `body`. No test asserts on parser internals.
