# Appstle payload fixtures

Sanitized Appstle API payloads for the `subscription-multi-contract-access`
bugfix spec. They let the property tests run entirely offline — no staging, no
database, no Appstle credentials. Payloads are injected at the `_appstle_get()`
seam by the harness's URL-keyed router (Task 4).

Two kinds of fixture live here:

- **Real** — derived from a live Appstle capture (`inspect_appstle_contracts.py
  --save`, Task 1). Dates, statuses, `billingPolicy`, `customerId`, contract
  `id`, `lastPaymentStatus`, and every `pageInfo` block are **verbatim**. These
  are the evidence that the bug is real, so fidelity to the capture matters more
  than convenience.
- **Synthetic** — hand-built, clearly labelled. Dates were generated at
  fixture-build time as offsets from `FIXTURE_NOW` so their intent is readable.
  Synthetic fixtures exist for the cases the capture did not contain.

## FIXTURE_NOW — the pinned clock

```
FIXTURE_NOW = 2026-08-09T01:31:12Z
```

Exported from `fixture_clock.py` in this directory, along with `fixture_now()`
(a drop-in for the production clock helper), `at_offset(**kwargs)`, and
`SYNTHETIC_OFFSETS` (the offsets baked into each synthetic fixture).

### Why it is required, not a convenience

The captured dates are absolute. Dave's granting contract has
`nextBillingDate` `2026-08-27T19:00:00Z`, which is in the **future** relative to
the capture instant and in the **past** after that date passes. If the fixtures
keep absolute dates and the production code reads `datetime.now()` directly,
then every date-dependent test silently inverts its verdict once wall-clock time
crosses those dates, and the suite starts failing for reasons that have nothing
to do with the code. Property 3 — Dave's exact payload — would begin asserting
the opposite of what it means to assert: that his newest contract is expired.

The alternative, rewriting the captured dates to be relative, was rejected. It
would destroy the fidelity that makes these fixtures evidence.

So: keep the real dates, pin the clock instead.

### The clock seam this depends on

`backend/subscription_auth.py` gets a module-level `_utcnow() -> datetime`
returning `datetime.now(timezone.utc)`, and `_paid_through()` and
`_contract_grants()` call it rather than calling `datetime.now()` inline. Tests
monkeypatch that single function to return `FIXTURE_NOW`:

```python
monkeypatch.setattr(subscription_auth, "_utcnow", fixture_clock.fixture_now)
```

One patch point, no `now=` parameter threaded through every signature. This is
recorded as required production work in the spec's `design.md`, under "Changes
Required" for `backend/subscription_auth.py` (item 2b), and Tasks 4, 8.3, and
8.4 depend on it. It is **not** implemented by Task 2.

Fixtures whose dates are offsets from `FIXTURE_NOW` are meaningless without that
patch. Fixtures with no date-dependent behavior (`step1_*`, `no_subscription`,
`empty_nodes`, `missing_product_subscriber_status`, `paused_unrecognized_interval`,
`paused_absent_billing_policy`) do not need it.

## Sanitization

Applied to the three real-data fixtures. The synthetic fixtures were written
from scratch and never contained any of it.

### Stripped, not redacted

| Removed | Where | Why |
|---|---|---|
| `customerPaymentMethod` | every contract node | One captured payload (`lapsed.thirtyday@example.com`) carried a real cardholder name, card brand, `firstDigits`, `lastDigits`, `maskedNumber`, `expiryMonth`, and `expiryYear`. Redaction leaves a shape inviting someone to refill it with real values; the whole block is gone instead. Removed from all three payloads for consistency, including the two whose instrument was a `CustomerShopPayAgreement` with no card data. |
| `originOrder` | every contract node | Real Shopify order IDs and order names (`"MC Press Bookstore #NNNN"`), which identify a purchase. |
| `variantImage` | every `lines[].nodes[]` entry | Shopify CDN URLs. No PII, but no test value either, and they bloat the diff. |

Nothing in the codebase reads any of these three, so removing them cannot change
a decision.

### Replaced

Emails map to placeholders. As it happens the step-2 payloads contain **no email
field at all** — Appstle keys the customer record by `customerId` — so the
substitution was a no-op on the real payloads. The placeholders are what appear
in this README, in the synthetic `step1_*` fixtures, and in test case names:

| Real customer | Placeholder | `customerId` |
|---|---|---|
| the multi-contract lockout case (Dave) | `multi.contract@example.com` | `2788838535` |
| the renewed monthly subscriber | `renewed.monthly@example.com` | `2788845447` |
| the lapsed 30-day purchaser | `lapsed.thirtyday@example.com` | `3289420039` |

### Preserved verbatim

All `createdAt` and `nextBillingDate` values; per-contract `status`;
customer-level `productSubscriberStatus`; `billingPolicy` (`interval` and
`intervalCount`); `customerId`; contract `id`; `lastPaymentStatus`; `tags`; and
every `pageInfo` block including the opaque base64 cursors, at both the
contract-connection and line-connection level.

`lines[].sellingPlanName` is deliberately kept. It contains no PII and it is
load-bearing evidence: Dave's two PAUSED contracts are named
`"One-time Purchase"` and `"30-Day Access — $10.95"`, which is what establishes
that **Appstle's `PAUSED` means "not set to auto-renew", not "suspended"**. That
finding is the reason the fix keys on a derived `paid_through` date rather than
on the status label. Deleting the field would delete the proof.

`customerId` is preserved on purpose. It is an internal Appstle/Shopify
identifier, it is the router key the harness dispatches step-2 requests on, and
the spec lists it as preserve-verbatim data.

## Real-data fixtures

All three are **step-2** payloads:
`GET /api/external/v2/subscription-customers/{customerId}`.

### `dave_two_paused_contracts.json`

From `multi.contract@example.com`, `customerId` `2788838535`. The canonical
counterexample and the Property 3 fixture. `productSubscriberStatus` `PAUSED`,
two contracts returned oldest-first:

| node | `status` | `createdAt` | `nextBillingDate` | vs `FIXTURE_NOW` | grants? |
|---|---|---|---|---|---|
| `nodes[0]` | `PAUSED` | 2026-06-02T22:27:41Z | 2026-07-02T22:00:00Z | past | no |
| `nodes[1]` | `PAUSED` | 2026-07-28T19:33:13Z | 2026-08-27T19:00:00Z | **future** | **yes** |

Both `billingPolicy` `DAY` × `30`. Unfixed code reads `nodes[0]` only and returns
403 `"Your subscription has expired. Resubscribe to continue."`; correct
behavior is 200 / `"active"`.

Serves: **Property 3** (Dave's exact payload), **Property 1** (bug condition
clause (a), the `nodes[0]` truncation), **Property 4** (order independence — the
harness permutes `nodes`).

### `renewed_subscriber.json`

From `renewed.monthly@example.com`, `customerId` `2788845447`. One contract,
`status` `ACTIVE`, `createdAt` 2026-06-16T16:16:18Z, `nextBillingDate`
2026-08-16T16:00:00Z, `billingPolicy` `MONTH` × `1`, `lastPaymentStatus`
`"SUCCEEDED"`. Grants on the `ACTIVE` short-circuit → 200 / `"active"`, before
and after the fix.

This is also the fixture that proves the `createdAt` fallback is weak with real
data: the store owner confirms a renewal billed 2026-07-16, and that date appears
nowhere in the payload. `createdAt` + one `MONTH` yields 2026-07-16 — a full
interval behind the true paid-through of 2026-08-16 (design Finding 1).

Serves: **preservation clause 3.1** (ACTIVE subscriber, 200 / `"active"`).

### `lapsed_paused_subscriber.json`

From `lapsed.thirtyday@example.com`, `customerId` `3289420039`. One contract,
`status` `PAUSED`, `createdAt` 2026-04-23T06:25:11Z, `nextBillingDate`
2026-05-23T06:00:00Z (past), `billingPolicy` `DAY` × `30`, `sellingPlanName`
`"One-time Purchase"`. Correctly denied → 403 with the expired message and a
non-null `redirect_url`, before and after the fix.

Serves: **preservation clause 3.3** (every contract expired — the byte-identical
denial copy that clause 2.21 and Task 8.5 protect), and the non-granting first
customer record for **Property 7**.

> **This fixture is why there is no real-data cancelled fixture.**
> `tasks.md` asks for a `cancelled_subscriber.json` derived from the capture.
> **No CANCELLED contract was captured.** This customer — the one expected to be
> cancelled — is reported by Appstle as `PAUSED`, because a lapsed one-time /
> 30-day purchase is `PAUSED` in Appstle's vocabulary. Design **Finding 3**
> records the open risk: whether `nextBillingDate` survives cancellation is
> **unknown**. Fabricating a "real" cancelled payload would invent an answer to
> an open question, so the cancelled cases are synthetic and labelled as such
> (`cancelled_with_paid_time.json`,
> `denial_newest_cancelled_older_paused.json`). Capture a genuinely CANCELLED
> contract before relying on clause 2.3 for cancelled customers in production.

## Synthetic fixtures

Hand-built. All dates were generated at build time as offsets from
`FIXTURE_NOW`; the offsets are listed below and in `SYNTHETIC_OFFSETS` in
`fixture_clock.py`. Synthetic `customerId`s are in the `70000000xx` range and
synthetic contract `id`s in the `90000001xx`–`90000002xx` range, so they can
never be mistaken for captured values. Synthetic cursors are the literal string
`SYNTHETIC_PLACEHOLDER_CURSOR_*` rather than base64, for the same reason.

### Step-1 customer-lookup payloads

`GET /api/external/v2/subscription-contract-details/customers?email={email}`.
Shape is a bare list of customer records; the code also normalizes
`{"content": [...]}` and a single-record dict, and those variants are covered by
`_extract_customer_ids` unit tests (Task 9.2) rather than by fixtures.

| Fixture | Contents | Serves |
|---|---|---|
| `step1_single_customer.json` | one record: `customerId` `2788838535`, `multi.contract@example.com` | routes straight to `dave_two_paused_contracts.json` for Property 3 |
| `step1_two_customers.json` | two records under one email `two.records@example.com`: `c1` = `3289420039`, `c2` = `7000000021` | **Property 7** |
| `no_subscription.json` | `[]` | **clause 3.2** — no Appstle record, preserved 200 / `"free"` |

`step1_two_customers.json` has **no real-data counterpart**. Each of the three
captured emails mapped to exactly one `customerId`, so the multi-customer-record
path is fixture-only (design Finding under change 9). Its two records are wired
so that no contract under `c1` grants and one under `c2` does — the harness
routes `c1` (`3289420039`) to `lapsed_paused_subscriber.json` and `c2`
(`7000000021`) to `cancelled_with_paid_time.json`, whose `customerId` is
`7000000021` for exactly this reason. `c1` reuses a real payload with its real
`customerId` under a synthetic email; that mismatch is intentional and harmless,
because the parser takes `customer_id` from the request loop variable, not from
the payload body.

### Pagination pair

| Fixture | Contents |
|---|---|
| `contracts_page1.json` | `customerId` `7000000018`, `pageInfo.hasNextPage` **true**; one `PAUSED` contract, `createdAt` −70d, `nextBillingDate` −40d → does **not** grant |
| `contracts_page2.json` | same `customerId`, `hasPreviousPage` true / `hasNextPage` false; one `PAUSED` contract, `createdAt` −16d, `nextBillingDate` **+14d** → **grants** |

Serves **Property 1** via pagination (bug condition clause (a): the granting
contract is stranded on an unread page, which under "grant if any contract
grants" is a false denial of a paying customer).

**These two fixtures describe hypothetical pagination.** `tasks.md` says to use
"the pagination parameter recorded in Task 1", but design **Finding 4** records
**no such parameter**: `pageInfo` is cursor-based (`hasPreviousPage`,
`hasNextPage`, `startCursor`, `endCursor`, opaque base64), yet `hasNextPage` was
`false` for all three captured customers, so no pagination request was ever
exercised and the query-parameter name that
`/api/external/v2/subscription-customers/{customerId}` accepts for a cursor
remains unknown. The endpoint documents none.

These fixtures therefore use a **synthetic placeholder cursor parameter**
(`?cursor=SYNTHETIC_PLACEHOLDER_CURSOR_PAGE1_END`, cursor values
`SYNTHETIC_PLACEHOLDER_CURSOR_PAGE{1,2}_{START,END}`). Consequently
**Task 9.3 is scoped to detection-plus-ERROR-log only** — production code logs
at ERROR that contracts may be missing when `hasNextPage` is true, and does not
attempt to follow the page. `contracts_page1.json` is what exercises that ERROR
path. `contracts_page2.json` is staged for the day Appstle's docs confirm the
parameter or a genuinely multi-page customer appears; until then no production
code requests it.

### Customer-level fallback cases

| Fixture | Contents | Serves |
|---|---|---|
| `empty_nodes.json` | `customerId` `7000000016`, `subscriptionContracts.nodes == []`, `productSubscriberStatus` `"ACTIVE"` | **clause 2.12** — empty `nodes[]` decided by the customer-level status; preservation case 4 |
| `missing_product_subscriber_status.json` | `customerId` `7000000017`, `nodes == []`, `productSubscriberStatus` key **absent entirely** | **Property 13** — 200 / `"free"` plus an ERROR-level record (clause 2.19) |

`empty_nodes.json` pins one value of the fallback field. The `PAUSED` and
`CANCELLED` fallback branches are reached by overwriting that single scalar in
the harness rather than by three near-identical files.

### Decision-rule cases

All step-2 payloads with a single `customerId`. Offsets are from `FIXTURE_NOW`.

| Fixture | `customerId` | Contract | Serves |
|---|---|---|---|
| `cancelled_with_paid_time.json` | `7000000021` | `CANCELLED`, `createdAt` −9d, `nextBillingDate` **+21d**, `MONTH` × 1 | **Property 5**, and **Preservation Exception 2.3 / 1.7** (F: 403 cancelled → F': 200 active). Also the granting `c2` for Property 7. |
| `active_past_billing_dunning.json` | `7000000011` | `ACTIVE`, `createdAt` −35d, `nextBillingDate` **−5d**, `MONTH` × 1 | **Property 6** — must grant via the `ACTIVE` short-circuit *without* consulting `paid_through`. The one branch where a non-paying account keeps access, deliberately, to cover the dunning retry window (clause 2.2). Passes on unfixed code too; it is here to lock that grace window in place. |
| `paused_null_nextbilling_derivable.json` | `7000000012` | `PAUSED`, `createdAt` −8d, `nextBillingDate` **null**, `MONTH` × 1 | **Property 11**, and **Preservation Exception 2.6 / 1.6**. The `createdAt` fallback derives `2026-09-01T01:31:12Z`, which is ~22 days past `FIXTURE_NOW`, so the contract grants and an ERROR is logged for using the weak anchor. Calendar-aware arithmetic matters here: a 30-day approximation gives a different answer. |
| `paused_unrecognized_interval.json` | `7000000013` | `PAUSED`, `nextBillingDate` **null**, `billingPolicy.interval` `"FORTNIGHT"` × 1, `createdAt` −8d | **Property 12** — `paid_through` underivable, contract must **not** grant, ERROR logged. No silent guess. |
| `paused_absent_billing_policy.json` | `7000000014` | `PAUSED`, `nextBillingDate` **null**, `billingPolicy` key **absent entirely**, `createdAt` −8d | **Property 12**, the other half — absent policy, not merely an unknown unit. |
| `denial_newest_cancelled_older_paused.json` | `7000000015` | two contracts, oldest-first: `nodes[0]` `PAUSED` `createdAt` −120d / `nextBillingDate` −90d; `nodes[1]` `CANCELLED` `createdAt` −40d / `nextBillingDate` −10d. Neither grants. | **Property 8**, and **Preservation Exception 2.16 / 1.14**. Both are past, so the outcome is 403 either way; what changes is the message. Unfixed code reads `nodes[0]` and says *expired*; the fix picks the newest by `createdAt` and says *cancelled*. |

`FORTNIGHT` is deliberately not a real Appstle value. Only `DAY` and `MONTH` were
observed (design Finding 2); `WEEK` and `YEAR` are supported but unobserved. The
point of the fixture is an unrecognized unit, and inventing one is the only way
to get it.

`intervalCount` is `30` on several fixtures, mirroring the capture. It is
routinely not `1`, so honouring it is load-bearing rather than a nicety.

## Coverage map

| Property / clause | Fixture(s) |
|---|---|
| Property 1 — any granting contract grants | `dave_two_paused_contracts`, `step1_two_customers` + `lapsed_paused_subscriber` + `cancelled_with_paid_time`, `contracts_page1` + `contracts_page2` |
| Property 3 — Dave's exact payload | `step1_single_customer` + `dave_two_paused_contracts` |
| Property 4 — order independence | `dave_two_paused_contracts`, `denial_newest_cancelled_older_paused` (harness permutes `nodes`) |
| Property 5 — cancelled with paid time grants | `cancelled_with_paid_time` |
| Property 6 — active grants regardless of paid-through | `active_past_billing_dunning` |
| Property 7 — second customer record counts | `step1_two_customers` (+ the two step-2 payloads above) |
| Property 8 — denial message from newest contract | `denial_newest_cancelled_older_paused` |
| Property 11 — calendar interval math | `paused_null_nextbilling_derivable` |
| Property 12 — underivable paid-through does not grant | `paused_unrecognized_interval`, `paused_absent_billing_policy` |
| Property 13 — silent downgrades become loud | `missing_product_subscriber_status`, `dave_two_paused_contracts` (multi-contract logging) |
| Clause 2.11 — `hasNextPage` detection + ERROR | `contracts_page1` |
| Clause 2.12 — empty `nodes[]` fallback | `empty_nodes` |
| Clause 3.1 — ACTIVE subscriber preserved | `renewed_subscriber` |
| Clause 3.2 — no Appstle record preserved | `no_subscription` |
| Clause 3.3 — all contracts expired preserved | `lapsed_paused_subscriber` |

Properties 2, 9, and 10 are driven by the harness across these fixtures rather
than by a fixture of their own: Property 2 records goldens over the non-bug
cases, and Properties 9 and 10 concern `refresh()` and `BYPASS_EMAILS`, which are
inputs to the service rather than Appstle payloads.

## Provenance and PII

The raw captures — `appstle-payload-*.json` in the project root — contain live
customer PII and are **not committed**. They are covered by the `/*.json` rule in
`.gitignore` (verified with `git check-ignore`) and were the input to Task 2 only.

Nothing under this directory contains a real email address, cardholder name, card
digit, masked card number, card expiry, or Shopify order name.

## `goldens/preservation_baseline.json`

The Property 2 preservation baseline, added by Task 7 and consumed by
`tests/test_subscription_preservation_properties.py`. Every entry is the literal
`(status_code, normalized_body)` that `login()` / `refresh()` returned on the
**unfixed** `backend/subscription_auth.py`, plus the issued token's decoded
claims with the moving `iat` / `exp` pair reduced to `exp_minus_iat_seconds`
(`normalize_body()` collapses `body.token` to its claim key set, since a fresh
JWT differs on every call).

Two case families, both deterministic:

- **`named`** — 24 cases, one per preserved clause (3.1 - 3.13) plus the
  empty-`nodes[]` fallback variants (2.12), each keyed by a stable `case_id`.
- **`corpus`** — 100 cases drawn by a seeded `random.Random(20260809)` over the
  same axes as the harness's Hypothesis strategies and filtered to non-bug
  inputs. Each carries a `fingerprint` over its decision-relevant payload, which
  the suite re-verifies so generator drift fails loudly instead of silently
  comparing a golden against a different input.

Recorded — never hand-written — with:

```bash
python3 -m tests.test_subscription_preservation_properties --record
```

The recorder refuses to run once the fixed decision layer exists in
`backend/subscription_auth.py`, because Task 10.3 re-asserts these goldens rather
than re-recording them. `_meta.git_commit` records the revision the current
baseline came from.

The three **Preservation Exceptions** (2.3 / 1.7, 2.6 / 1.6, 2.16 / 1.14) are
deliberately **absent** from this file: they are asserted separately with their
intended new values, so no golden encodes behavior the fix changes on purpose.
