"""Fix-checking property tests — Properties 3, 4, 5, 6, 7, 8, 9, 10, 13.

**Validates: Requirements 1.6, 1.7, 1.9, 1.10, 1.14, 1.15, 1.16, 2.2, 2.3, 2.9,
2.10, 2.13, 2.14, 2.16, 2.17, 2.19, 2.20**

Spec: ``.kiro/specs/subscription-multi-contract-access/`` (bugfix.md, design.md).

THIS SUITE IS EXPECTED TO FAIL ON UNFIXED CODE, except Property 6. Every
assertion states the REQUIRED behavior, never the current behavior, so the same
file becomes the fix check in Task 10.2 without a single assertion flipping
direction. Property 6 is included because it already passes: the ACTIVE
short-circuit is the one branch where a non-paying account keeps access
(clause 2.2, the dunning retry window), and the point of including it is to lock
that grace window in place so the fix cannot quietly remove it.

Everything is asserted on ``login()``'s / ``refresh()``'s returned
``status_code`` and ``body`` — plus ``caplog`` records and the router's call log
where the property is explicitly about logging or about which URL was fetched.
Nothing touches parser internals. That discipline is not stylistic: the shipped
bug was hidden by tests that asserted on fields the decision path never reads
(clause 1.12).

Payloads enter at the ``_appstle_get()`` seam (Task 3) through the harness's
URL-keyed router (Task 4). The clock is pinned to ``FIXTURE_NOW``
(2026-08-09T01:31:12Z) via the ``_utcnow()`` seam (design change 2b) so the
verbatim captured dates keep the meaning they had at capture time.

Property 11 was added by Task 8.3, scoped to ``_add_calendar_interval()`` — the
only half of that property assertable before ``_paid_through()`` exists. It is
one of the properties here that calls a helper directly instead of driving
``login()``, because the helper is pure, module-level, and has no payload or
response body involved in "what is Jan 31 plus one month"; the anchor-selection
half arrives with Property 12.

Property 12 was added by Task 8.4 and likewise runs against ``_paid_through()``
and ``_contract_grants()`` directly. It has to: those two helpers exist as of
Task 8.4 but are deliberately NOT wired into any caller yet (Tasks 9.1 and 9.5
do that), so there is no path from ``login()`` to the behavior it asserts. Once
the wiring lands, the same underivable-paid-through inputs reach ``login()``
through the ``paused_unrecognized_interval`` and ``paused_absent_billing_policy``
fixtures, and the response-level assertion is carried by Property 8's denial
cases.

Run offline::

    python3 -m pytest tests/test_subscription_fix_checking.py -v


OBSERVED RESULTS (run on UNFIXED code)
--------------------------------------

``python3 -m pytest tests/test_subscription_fix_checking.py -v``
→ **14 failed, 3 passed** in ~2s. Transcribed from the run, not predicted.

That count is the Task 6 run, before Properties 11 and 12 were written. The same
command now reports **14 failed, 9 passed** — the identical 14 failures, plus the
6 helper-level cases added by Tasks 8.3 and 8.4. Those pass because they assert
against helpers that did not exist when the failures were recorded and that are
not yet wired into ``login()``; nothing about the pre-fix behavior of the callers
has changed, which is the whole point of Task 8 landing separately from Task 9.

Summary against the expected outcome (Properties 3, 4, 5, 7, 8, 9, 10, 13 FAIL;
Property 6 PASSES): matched, with one caveat — one of Property 8's three cases
passes coincidentally. Detail under Property 8 below.

**Property 3 — Dave's Exact Payload: FAILED** (as expected). Confirms the
``nodes[0]`` truncation on real captured data::

    expected 200 / "active"
    got      403 {"error": "Your subscription has expired. Resubscribe to continue.",
                  "subscription_status": "paused",
                  "redirect_url": "https://mcpress.test/subscribe"}
    contracts 84206911553 PAUSED created=2026-06-02T22:27:41Z next=2026-07-02T22:00:00Z grants=False
              87268229185 PAUSED created=2026-07-28T19:33:13Z next=2026-08-27T19:00:00Z grants=True

**Property 4 — Order Independence: FAILED** (as expected), both cases.

*Generated* (40 examples), minimal counterexample — two ACTIVE contracts under a
customer whose ``productSubscriberStatus`` is PAUSED::

    permutation (0, 1) → (403, 'paused', 'Your subscription has expired. Resubscribe to continue.')
    permutation (1, 0) → (200, 'active', None)
    contracts 9100000000 ACTIVE created=None next=2026-08-08T01:31:12Z grants=True
              9100000001 ACTIVE created=2026-08-08T01:31:12Z next=2026-08-10T01:31:12Z grants=True

Worth noting what Hypothesis shrank to: *both* contracts grant under the new
rule, and both are ACTIVE, yet the outcome still flips on ordering — because the
unfixed ladder reads the customer-level PAUSED label and then ``nodes[0]``'s
date, and never looks at either contract's own ACTIVE status (clause 1.5).

*Real data* (Dave's two nodes, as-captured versus reversed)::

    as-captured (oldest-first) → (403, 'paused', 'Your subscription has expired. Resubscribe to continue.')
    reversed                   → (200, 'active', None)

Same payload, same instant, opposite verdicts. That asymmetry is clause 1.8 with
nothing generated about it.

**Property 5 — Cancelled With Paid Time Remaining: FAILED** (as expected), both
cases. Fixture case::

    expected 200 / "active"
    got      403 "Your subscription has been cancelled. Resubscribe to continue." / "cancelled"
    contract 9000000211 CANCELLED created=2026-07-31T01:31:12Z next=2026-08-30T01:31:12Z
             (21 days of paid time remaining at FIXTURE_NOW)

Generated case (30 examples) reaches the identical 403 from
``next=2026-08-10T01:31:12Z``. Confirms clause 1.7: CANCELLED denies
unconditionally, three weeks of paid time notwithstanding.

**Property 6 — Active Grants Regardless Of Paid-Through: PASSED** (as expected),
both cases. The dunning grace window (clause 2.2) is present in the unfixed code
and is now pinned by assertion so the fix cannot drop it. Note *why* it passes
today: the fixture's customer-level status is ACTIVE, so the unfixed ladder
short-circuits on the label. After the fix it passes on the contract's own
ACTIVE status instead — same verdict, different route.

**Property 7 — Second Customer Record Counts: FAILED** (as expected)::

    expected 200 / "active"
    got      403 "Your subscription has expired. Resubscribe to continue." / "paused"
    router   step-2 requests issued for [3289420039]

``c2`` = 7000000021, which holds the CANCELLED-with-21-days-paid contract, was
**never requested**. The router evidence is the direct observation: the second
customer record is not mis-evaluated, it is never fetched (clause 1.3).

**Property 8 — Denial Message From The Most Recent Contract: FAILED** on two of
three cases; the third passes coincidentally.

*Generated* (40 examples) — **FAILED**. Minimal counterexample is a single
CANCELLED contract one day past its billing date, under a customer whose
``productSubscriberStatus`` is PAUSED::

    expected "Your subscription has been cancelled. Resubscribe to continue."
    got      "Your subscription has expired. Resubscribe to continue."
    contract 9100000000 CANCELLED created=2026-08-08T01:31:12Z next=2026-08-08T01:31:12Z

The 403 itself is right; the copy is wrong, and it is wrong because it is derived
from the customer-level label rather than from any contract (clauses 1.13, 1.14).

*Identical ``createdAt`` tiebreak* — **FAILED**::

    both contracts createdAt=2026-07-10T01:31:12Z, both past
    expected "Your subscription has expired. Resubscribe to continue."
             (tiebreak picks contract id 9100000502, PAUSED)
    got      "Your subscription has been cancelled. Resubscribe to continue."

*Fixture case* (``denial_newest_cancelled_older_paused``) — **PASSED, for the
wrong reason.** That fixture's customer-level ``productSubscriberStatus`` is also
CANCELLED, so the unfixed ladder emits the cancelled message from the
customer-level label and coincidentally agrees with the newest contract's status.
Not weakened and not removed: it states the required behavior and still holds
after the fix. The two failures above are what actually expose clause 1.14.

**Property 9 — Bypass Survives Refresh: FAILED** (as expected), both cases.
Fixture case::

    expected 200 / body.success == true, no Appstle call
    got      403 {"success": false, "token": null,
                  "error": "Your subscription has expired. Resubscribe to continue.",
                  "redirect_url": "https://mcpress.test/subscribe"}

Generated case (4 fallback statuses) failed two distinct ways, which together
name both halves of the defect::

    fallback='PAUSED'  → 403, denied outright
    fallback='EXPIRED' → 200, but Appstle was consulted:
        ['.../subscription-contract-details/customers',
         '.../subscription-customers/7000400001']

The second is the more interesting one: with an unrecognized customer-level
status the bypass user is *not* denied, but only by luck of falling into the
free-tier branch — ``refresh()`` still made two live Appstle calls it had no
business making. Clause 1.10, both symptoms.

**Property 10 — login And refresh Agree: FAILED** (as expected), both cases.

*Generated* (40 examples), minimal counterexample with the bypass axis true::

    login  : granted=True  status='active' error=None                    (HTTP 200)
    refresh: granted=False status=None     error='...has expired...'     (HTTP 403)
    bypass=True fallback='PAUSED'
    contract 9100000000 ACTIVE created=None next=2026-08-08T01:31:12Z grants=True

A bypass user logs in successfully and is bounced one hour later when the token
refreshes. That is the drift three copies of step 4 made inevitable (clause 1.9).

*Real data* — the two callers **agree** on Dave's payload (both deny with the
expired message), and the case fails on the second assertion instead: they agree
on the *wrong* answer. Recorded as-is, because "consistent" and "correct" are
different properties and this suite has to assert both::

    login=(False, None, 'Your subscription has expired. Resubscribe to continue.')
    refresh=(False, None, 'Your subscription has expired. Resubscribe to continue.')

**Property 13 — Silent Downgrades Become Loud: FAILED** (as expected), both
halves.

*Missing ``productSubscriberStatus``* — the outcome is already right (200 /
``"free"``, which clause 2.19 keeps); the volume is not. Highest level observed
was **INFO**, no ERROR record::

    INFO  No productSubscriberStatus in response for email=... , falling back to tags
    INFO  Derived status for email=...: not_found (matched from tags)
    INFO  Free-tier login for email=...: product_subscriber_status=None

Also visible here: the dead tag path (clause 1.12) running and its verdict being
discarded, exactly as the spec describes.

*Multi-contract logging* — the entire log for Dave's two-contract login is three
lines, and only ``nodes[0]`` appears anywhere in it::

    INFO  Contract data for email=...: productSubscriberStatus=PAUSED,
          nextBillingDate=2026-07-02 22:00:00+00:00
    INFO  Subscription expired for email=...: status=PAUSED,
          nextBillingDate=2026-07-02 22:00:00+00:00 (past)

The contract count is absent, and so is every field of the contract that would
have explained the lockout. Failed on the contract-count assertion first; the
per-contract status/date assertions that follow would also fail.

One thing this suite structurally **cannot** observe: the ``str(data)[:500]``
truncation itself. It lives inside ``_appstle_get()``, which is the method the
harness router replaces, so that line never runs here. The two raw-repr markers
are kept as a guard against a *parser* logging a payload repr, but the
load-bearing assertion for clause 2.20 is the positive one — count, statuses,
dates. The truncation's removal is verified against real Appstle data on staging
in Task 11.

Nothing observed here refutes the root cause analysis in design.md, so no
re-hypothesizing was needed.


Documented deviations from the task text
----------------------------------------

* **Property 7 asserts the required behavior, not the bug.** The task asks for a
  router assertion that ``c2`` was fetched; that is what is asserted, and its
  failure message reports the ``customerId``s actually requested
  (``[3289420039]``), which is the same evidence in the direction that stays
  correct after the fix. An assertion phrased as "no request for c2" would have
  to be inverted in Task 10.2.

* **Property 10 generates the ``BYPASS_EMAILS`` flag as an input axis.** Without
  it the property passes on unfixed code, because ``login()`` and ``refresh()``
  run identical ladders over an identical ``appstle_resp``; the bypass check is
  the one place they have actually diverged (clause 1.10). Appstle *failure*
  injection is deliberately excluded from the same generator: clause 3.8
  preserves a real divergence there (login falls through to free tier, refresh
  keeps the JWT claim), so generating it would assert against a requirement.

* **Property 8's generated statuses are scoped to ``{PAUSED, CANCELLED,
  EXPIRED}``.** Junk statuses are valid inputs and reach
  ``DEFAULT_DENIAL_MESSAGE`` by the same rule, but pinning exact user-facing copy
  for ``"SUSPENDED"`` or ``"0"`` would assert strings the requirements never
  name. Message stability across the full status domain is carried by Property 4.

* **Expected denial copy is transcribed, not imported.** ``EXPIRED_DENIAL`` and
  ``CANCELLED_DENIAL`` are written out here rather than read from
  ``DENIAL_MESSAGES``, whose current values omit the ``"Resubscribe to
  continue."`` sentence. Importing them would make the assertion agree with
  whatever the dict says and quietly permit the copy change clause 2.21 exists to
  prevent.
"""

from __future__ import annotations

import calendar
import itertools
import logging
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from dateutil.relativedelta import relativedelta
from hypothesis import HealthCheck, assume, event, given, settings
from hypothesis import strategies as st

from backend import subscription_auth
from backend.subscription_auth import (
    ContractView,
    _add_calendar_interval,
    _contract_grants,
    _paid_through,
)
from tests.subscription_harness import (
    DEFAULT_CLIENT_IP,
    FIXTURE_NOW,
    KNOWN_PASSWORD,
    UNRECOGNIZED_INTERVALS,
    build_contract_node,
    build_step2_payload,
    contract_dicts,
    fixture_now,
    future_dates,
    harness,
    load_fixture,
    past_dates,
    step1_payload,
)

LOGGER_NAME = "backend.subscription_auth"

# ---------------------------------------------------------------------------
# Fixture coordinates (see tests/fixtures/appstle/README.md)
# ---------------------------------------------------------------------------

DAVE_EMAIL = "multi.contract@example.com"
DAVE_CUSTOMER_ID = 2788838535

TWO_RECORDS_EMAIL = "two.records@example.com"
CANCELLED_PAID_CUSTOMER_ID = 7000000021
DUNNING_CUSTOMER_ID = 7000000011
DENIAL_NEWEST_CUSTOMER_ID = 7000000015
MISSING_STATUS_CUSTOMER_ID = 7000000017


# ---------------------------------------------------------------------------
# Expected denial copy
# ---------------------------------------------------------------------------
#
# The ALIGNED values from clause 2.21 / Task 8.5, transcribed here rather than
# imported from ``DENIAL_MESSAGES``. Importing would make the assertion vacuous:
# the dict's current values omit the "Resubscribe to continue." sentence that
# ``login()`` actually emits, and the whole point of 2.21 is that adopting the
# dict must not change the byte-identical expired copy preserved by clause 3.3.

EXPIRED_DENIAL = "Your subscription has expired. Resubscribe to continue."
CANCELLED_DENIAL = "Your subscription has been cancelled. Resubscribe to continue."
DEFAULT_DENIAL = "No subscription found"

EXPECTED_DENIAL_MESSAGES = {
    "ACTIVE": EXPIRED_DENIAL,   # pathological: label says ACTIVE, contract did not grant
    "EXPIRED": EXPIRED_DENIAL,
    "PAUSED": EXPIRED_DENIAL,
    "CANCELLED": CANCELLED_DENIAL,
}


def expected_denial_message(status: Optional[str]) -> str:
    """``_get_denial_message(status)`` as clause 2.17 + 2.21 require it to behave."""
    if not status:
        return DEFAULT_DENIAL
    return EXPECTED_DENIAL_MESSAGES.get(status.upper(), DEFAULT_DENIAL)


# ---------------------------------------------------------------------------
# Test-side oracle: contractGrants / paidThrough from design.md
# ---------------------------------------------------------------------------
#
# Transcribed from the design pseudocode and evaluated over the generated
# payload dicts, so a property can decide whether a contract set should grant
# without importing the decision layer (which does not exist yet, and which is
# the thing under test).

GRANTING_ON_PAID_TIME_STATUSES = {"PAUSED", "CANCELLED"}

_INTERVALS = {"DAY": "days", "WEEK": "weeks", "MONTH": "months", "YEAR": "years"}


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def oracle_paid_through(node: Dict[str, Any]) -> Optional[datetime]:
    """``paidThrough(k)`` from design.md."""
    next_billing = _parse_iso(node.get("nextBillingDate"))
    if next_billing is not None:
        return next_billing

    anchor = _parse_iso(node.get("createdAt"))
    policy = node.get("billingPolicy")
    if anchor is None or not isinstance(policy, dict):
        return None

    unit = _INTERVALS.get(str(policy.get("interval")))
    if unit is None:
        return None
    count = policy.get("intervalCount")
    if not isinstance(count, int) or count < 1:
        return None
    return anchor + relativedelta(**{unit: count})


def oracle_contract_grants(node: Dict[str, Any]) -> bool:
    """``contractGrants(k)`` from design.md."""
    status = node.get("status")
    status_upper = status.upper() if isinstance(status, str) else ""
    if status_upper == "ACTIVE":
        return True
    if status_upper in GRANTING_ON_PAID_TIME_STATUSES:
        paid_through = oracle_paid_through(node)
        return paid_through is not None and paid_through > FIXTURE_NOW
    return False


def oracle_newest(nodes: List[dict]) -> dict:
    """``max(contracts, key=(created_at, contract_id))`` with null ``createdAt`` last.

    design.md change 6: newest by ``createdAt``, ``contract_id`` as the
    deterministic tiebreak. Contract ids in this module are built to equal
    length, so the lexicographic comparison a string ``contract_id`` gets and the
    numeric comparison an integer one would get agree.
    """
    def key(node: dict) -> Tuple[int, str, str]:
        created = _parse_iso(node.get("createdAt"))
        return (
            0 if created is None else 1,            # null createdAt sorts last
            "" if created is None else created.isoformat(),
            str(node.get("id") or ""),
        )

    return max(nodes, key=key)


def oracle_grants_anywhere(nodes: List[dict]) -> bool:
    return any(oracle_contract_grants(node) for node in nodes)


# ---------------------------------------------------------------------------
# Shared assertions
# ---------------------------------------------------------------------------

def assert_grants_access(result: Dict[str, Any], *, evidence: str) -> None:
    """200 / ``"active"`` on ``login()``'s status code and body only."""
    body = result["body"]
    assert result["status_code"] == 200, (
        f"expected 200, got {result['status_code']} with error={body.get('error')!r} "
        f"subscription_status={body.get('subscription_status')!r}. {evidence}"
    )
    assert body.get("subscription_status") == "active", (
        f"expected subscription_status='active', got "
        f"{body.get('subscription_status')!r}. {evidence}"
    )


def messages_of(caplog: pytest.LogCaptureFixture, *, level: Optional[int] = None) -> List[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if level is None or record.levelno >= level
    ]


def describe(node: dict) -> str:
    return (
        f"{str(node.get('id', '')).rsplit('/', 1)[-1]}:{node.get('status')!r}"
        f" created={node.get('createdAt')} next={node.get('nextBillingDate')}"
        f" grants={oracle_contract_grants(node)}"
    )


def describe_all(nodes: List[dict]) -> str:
    return "[" + "; ".join(describe(node) for node in nodes) + "]"


def single_record_login(
    nodes: List[dict],
    *,
    customer_id: int = 7_000_300_001,
    email: str = "fixcheck@example.com",
    product_subscriber_status: Optional[str] = "PAUSED",
) -> Dict[str, Any]:
    """Serve ``nodes`` as one customer record's single page and run ``login()``."""
    with harness(
        step1=step1_payload([customer_id], email=email),
        step2={
            customer_id: build_step2_payload(
                customer_id=customer_id,
                nodes=nodes,
                product_subscriber_status=product_subscriber_status,
            )
        },
        bypass_emails="",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        return h.login(email, KNOWN_PASSWORD, DEFAULT_CLIENT_IP)


@st.composite
def pinned_contracts(
    draw,
    *,
    status: Optional[str] = None,
    next_billing_date: Optional[st.SearchStrategy] = None,
    created_at: Optional[str] = None,
) -> dict:
    """A contract drawn across the full domain, with named axes pinned afterwards.

    The harness's ``contract_dicts(status=...)`` narrowing would do the same job,
    but it selects strategies with ``strategy or default``, and a single-value
    ``st.just(...)`` in a boolean context makes Hypothesis warn on every draw.
    Drawing the full domain and overwriting the pinned keys is equivalent and
    keeps the run log readable.
    """
    node = draw(contract_dicts())
    if status is not None:
        node["status"] = status
    if next_billing_date is not None:
        node["nextBillingDate"] = draw(next_billing_date)
    if created_at is not None:
        node["createdAt"] = created_at
    return node


def with_unique_ids(nodes: List[dict], *, base: int = 9_100_000_000) -> List[dict]:
    """Give every node a unique, equal-length contract id.

    The denial-message tiebreak (clause 2.16) compares ``contract_id``, so
    duplicate ids would make the "deterministic tiebreak" assertion vacuous.
    """
    for index, node in enumerate(nodes):
        node["id"] = f"gid://shopify/SubscriptionContract/{base + index}"
        node["lines"]["nodes"][0]["id"] = f"gid://shopify/SubscriptionLine/{base + index}"
    return nodes


# ===========================================================================
# Property 3 — Dave's Exact Payload
# ===========================================================================

def test_property_3_daves_exact_payload_grants_access():
    """Dave's captured payload with ``BYPASS_EMAILS`` empty → 200 / ``"active"``.

    **Validates: Requirements 2.1, 2.3**

    ``customerId`` 2788838535, ``productSubscriberStatus`` PAUSED, two PAUSED
    contracts returned oldest-first: ``nodes[0]`` ``nextBillingDate``
    2026-07-02T22:00:00Z (past at ``FIXTURE_NOW``), ``nodes[1]``
    2026-08-27T19:00:00Z (future). Real data, not a construction.

    ``BYPASS_EMAILS`` is empty on purpose. In production Dave has access only
    because he is on the bypass list, so leaving him on it here would test the
    bypass rather than the access decision.
    """
    step2 = load_fixture("dave_two_paused_contracts")
    nodes = step2["subscriptionContracts"]["nodes"]
    assert not oracle_contract_grants(nodes[0]), "fixture drift: nodes[0] must not grant"
    assert oracle_contract_grants(nodes[1]), "fixture drift: nodes[1] must grant"

    with harness(
        step1=load_fixture("step1_single_customer"),
        step2={DAVE_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={DAVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(DAVE_EMAIL, KNOWN_PASSWORD)

    assert_grants_access(
        result,
        evidence=f"Dave, customerId {DAVE_CUSTOMER_ID}: {describe_all(nodes)}",
    )


# ===========================================================================
# Property 4 — Order Independence
# ===========================================================================

@st.composite
def order_sensitive_contract_sets(draw) -> Tuple[List[dict], Optional[str]]:
    """Contract sets whose per-contract data differs enough for order to matter.

    Sets are 2-3 contracts wide, drawn across the full status / date / interval
    domain, with the customer-level fallback status drawn alongside. Two or three
    contracts keep ``permutations()`` at 2 or 6 runs per example; a 4-wide set
    would be 24 logins, which buys nothing the narrower set does not already
    expose.
    """
    size = draw(st.integers(min_value=2, max_value=3))
    nodes = with_unique_ids([draw(contract_dicts()) for _ in range(size)])
    fallback = draw(st.sampled_from(("ACTIVE", "PAUSED", "CANCELLED", "EXPIRED", None)))
    return nodes, fallback


def _decision_signature(result: Dict[str, Any]) -> Tuple[int, Any, Any]:
    """``(status_code, subscription_status, error)`` — what clause 2.9 fixes."""
    body = result["body"]
    return (
        result["status_code"],
        body.get("subscription_status"),
        body.get("error"),
    )


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(order_sensitive_contract_sets())
def test_property_4_order_independence(case):
    """Every permutation of a contract set reaches the identical response.

    **Validates: Requirements 2.9, 2.16**

    ``status_code``, ``body.subscription_status``, and the denial message must all
    be identical across permutations. Appstle returns contracts oldest-first
    today, but "oldest-first" is an observation about one API's current behavior,
    not a guarantee, and the decision must not depend on it either way.
    """
    nodes, fallback = case

    signatures = {}
    for order in itertools.permutations(range(len(nodes))):
        permuted = [nodes[i] for i in order]
        result = single_record_login(permuted, product_subscriber_status=fallback)
        signatures[order] = _decision_signature(result)

    baseline_order, baseline = next(iter(signatures.items()))
    for order, signature in signatures.items():
        assert signature == baseline, (
            f"order dependence: permutation {order} returned {signature} but "
            f"permutation {baseline_order} returned {baseline}. "
            f"fallback={fallback!r} contracts={describe_all(nodes)}"
        )


def test_property_4_order_independence_on_daves_real_payload():
    """The same assertion on real captured data, both orderings of Dave's nodes.

    **Validates: Requirements 2.9**

    This is the concrete case behind the generated property: Appstle happens to
    return Dave's contracts oldest-first, which is the ordering that loses him
    his access. Reversed, the unfixed code grants. That asymmetry *is* the
    order-dependence defect (clause 1.8).
    """
    step2 = load_fixture("dave_two_paused_contracts")
    nodes = step2["subscriptionContracts"]["nodes"]

    as_captured = single_record_login(
        list(nodes),
        customer_id=DAVE_CUSTOMER_ID,
        email=DAVE_EMAIL,
        product_subscriber_status="PAUSED",
    )
    reversed_order = single_record_login(
        list(reversed(nodes)),
        customer_id=DAVE_CUSTOMER_ID,
        email=DAVE_EMAIL,
        product_subscriber_status="PAUSED",
    )

    assert _decision_signature(as_captured) == _decision_signature(reversed_order), (
        f"order dependence on real data: as-captured (oldest-first) returned "
        f"{_decision_signature(as_captured)}, reversed returned "
        f"{_decision_signature(reversed_order)}. contracts={describe_all(nodes)}"
    )


# ===========================================================================
# Property 5 — Cancelled With Paid Time Remaining Grants
# ===========================================================================

def test_property_5_cancelled_with_paid_time_grants_access():
    """A single CANCELLED contract with a future ``nextBillingDate`` grants.

    **Validates: Requirements 2.3**

    Cancelling means "stop billing me", not "revoke what I already paid for".
    Cutting off a customer who has paid through a period invites a chargeback.
    This is Preservation Exception 2.3 / 1.7: F returns 403 cancelled, F' returns
    200 active, and that change is intended rather than a regression.
    """
    step2 = load_fixture("cancelled_with_paid_time")
    node = step2["subscriptionContracts"]["nodes"][0]
    assert node["status"] == "CANCELLED"
    assert oracle_contract_grants(node), "fixture drift: paid time must remain"

    email = "cancelled.paid@example.com"
    with harness(
        step1=step1_payload([CANCELLED_PAID_CUSTOMER_ID], email=email),
        step2={CANCELLED_PAID_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        result = h.login(email, KNOWN_PASSWORD)

    assert_grants_access(
        result,
        evidence=(
            f"single CANCELLED contract with paid time remaining: {describe(node)} "
            f"(FIXTURE_NOW={FIXTURE_NOW.isoformat()})"
        ),
    )


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(pinned_contracts(status="CANCELLED", next_billing_date=future_dates()))
def test_property_5_cancelled_with_paid_time_grants_access_generated(node):
    """The same rule over generated CANCELLED contracts with paid time remaining.

    **Validates: Requirements 2.3**
    """
    nodes = with_unique_ids([node])
    result = single_record_login(nodes, product_subscriber_status="CANCELLED")
    assert_grants_access(result, evidence=f"generated CANCELLED: {describe(node)}")


# ===========================================================================
# Property 6 — Active Grants Regardless Of Paid-Through (dunning grace)
# ===========================================================================
#
# The one property here expected to PASS on unfixed code. It is included to lock
# the behavior in place: clause 2.2 grants access to an ACTIVE contract whose
# paid-through has passed, because Appstle can hold a contract ACTIVE with
# nextBillingDate in the past while a renewal payment retries. That is the single
# branch where a non-paying account keeps access, and it is deliberate.

def test_property_6_active_grants_regardless_of_paid_through():
    """An ACTIVE contract with ``paid_through`` in the past still grants.

    **Validates: Requirements 2.2**

    Expected to PASS before the fix as well as after. If it ever fails, the
    dunning grace window has been removed.
    """
    step2 = load_fixture("active_past_billing_dunning")
    node = step2["subscriptionContracts"]["nodes"][0]
    assert node["status"] == "ACTIVE"
    paid_through = oracle_paid_through(node)
    assert paid_through is not None and paid_through < FIXTURE_NOW, (
        "fixture drift: the dunning fixture's paid_through must be in the past"
    )

    email = "dunning@example.com"
    with harness(
        step1=step1_payload([DUNNING_CUSTOMER_ID], email=email),
        step2={DUNNING_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        result = h.login(email, KNOWN_PASSWORD)

    assert_grants_access(
        result,
        evidence=(
            f"ACTIVE contract past its paid_through (dunning retry window): "
            f"{describe(node)}"
        ),
    )


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(pinned_contracts(status="ACTIVE", next_billing_date=past_dates()))
def test_property_6_active_grants_regardless_of_paid_through_generated(node):
    """The dunning grace window over generated ACTIVE contracts with past dates.

    **Validates: Requirements 2.2**
    """
    nodes = with_unique_ids([node])
    result = single_record_login(nodes, product_subscriber_status="ACTIVE")
    assert_grants_access(result, evidence=f"generated ACTIVE past-due: {describe(node)}")


# ===========================================================================
# Property 7 — Contracts Under A Second Customer Record Count
# ===========================================================================

def test_property_7_second_customer_record_counts():
    """One email, two ``customerId``s: the granting contract is under the second.

    **Validates: Requirements 2.10**

    ``c1`` (3289420039) is the lapsed 30-day purchaser — PAUSED, billing date in
    the past, does not grant. ``c2`` (7000000021) is CANCELLED with 21 days of
    paid time left, so it grants.

    Two assertions, both stated as required behavior: ``login()`` returns
    200 / ``"active"``, and the router shows a step-2 request was issued for
    ``c2``. Asserting the *bug* ("no request for c2") would have to be inverted
    once the fix lands, which would defeat this module's second job as the Task
    10.2 fix check — so the same observation is made in the direction that stays
    correct, and the failure message reports which ``customerId``s were actually
    fetched.
    """
    step1 = load_fixture("step1_two_customers")
    c1, c2 = [record["customerId"] for record in step1]

    c1_payload = load_fixture("lapsed_paused_subscriber")
    c2_payload = load_fixture("cancelled_with_paid_time")
    assert not oracle_grants_anywhere(c1_payload["subscriptionContracts"]["nodes"])
    assert oracle_grants_anywhere(c2_payload["subscriptionContracts"]["nodes"])

    with harness(
        step1=step1,
        step2={c1: c1_payload, c2: c2_payload},
        bypass_emails="",
        known_passwords={TWO_RECORDS_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(TWO_RECORDS_EMAIL, KNOWN_PASSWORD)
        fetched = h.router.requested_customer_ids
        fetched_c2 = h.router.fetched_customer(c2)

    assert_grants_access(
        result,
        evidence=(
            f"two customer records {[c1, c2]}: nothing under c1={c1} grants, the "
            f"CANCELLED-with-paid-time contract under c2={c2} does. Step-2 "
            f"requests were issued for {fetched}."
        ),
    )
    assert fetched_c2, (
        f"clause 2.10 requires a step-2 request for c2={c2}. Step-2 requests "
        f"observed: {fetched} — c2 was never fetched, so its granting contract "
        f"could not have been seen."
    )


# ===========================================================================
# Property 8 — Denial Message Comes From The Most Recent Contract
# ===========================================================================
#
# Scoped to the three recognized non-granting statuses. Junk statuses are
# legitimate inputs and DO reach DEFAULT_DENIAL_MESSAGE by the same rule, but
# pinning an exact user-facing string for "SUSPENDED" or "0" would assert copy
# the requirements never name. Order-independence of the message across the full
# domain, junk included, is already carried by Property 4.

RECOGNIZED_NON_GRANTING = ("PAUSED", "CANCELLED", "EXPIRED")


@st.composite
def all_denied_contract_sets(draw) -> List[dict]:
    """1-3 contracts, none granting, each with a distinct ``createdAt``.

    ``nextBillingDate`` is always in the past, which settles ``paid_through``
    outright, so nothing can grant regardless of what the interval axis draws.
    ``createdAt`` values are forced distinct so "newest" is unambiguous — the
    identical-timestamp tiebreak is a separate, deliberate case below.
    """
    size = draw(st.integers(min_value=1, max_value=3))
    created_offsets = draw(
        st.lists(
            st.integers(min_value=1, max_value=900),
            min_size=size,
            max_size=size,
            unique=True,
        )
    )
    nodes = []
    for offset in created_offsets:
        node = draw(
            pinned_contracts(
                status=draw(st.sampled_from(RECOGNIZED_NON_GRANTING)),
                next_billing_date=past_dates(),
                created_at=(FIXTURE_NOW - relativedelta(days=offset)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            )
        )
        nodes.append(node)
    return with_unique_ids(nodes)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(all_denied_contract_sets())
def test_property_8_denial_message_comes_from_the_newest_contract(nodes):
    """All-denied sets: 403, a redirect URL, and the newest contract's message.

    **Validates: Requirements 2.16, 2.17**

    A customer whose most recent subscription was cancelled but who also holds an
    older paused contract is told "expired" today, because the message is derived
    from ``nodes[0]``. "Cancelled" is both more accurate and more actionable
    (clause 1.14).
    """
    assume(not oracle_grants_anywhere(nodes))

    newest = oracle_newest(nodes)
    expected = expected_denial_message(newest.get("status"))
    result = single_record_login(nodes, product_subscriber_status="PAUSED")
    body = result["body"]

    assert result["status_code"] == 403, (
        f"expected 403 for an all-denied set, got {result['status_code']} "
        f"with body={body!r}. contracts={describe_all(nodes)}"
    )
    assert body.get("redirect_url"), (
        f"clause 2.16 requires a non-null redirect_url on denial, got "
        f"{body.get('redirect_url')!r}. contracts={describe_all(nodes)}"
    )
    assert body.get("error") == expected, (
        f"denial message must come from the newest contract "
        f"({describe(newest)}, status={newest.get('status')!r} → {expected!r}), "
        f"got {body.get('error')!r}. contracts={describe_all(nodes)}"
    )


def test_property_8_denial_message_on_the_captured_shaped_fixture():
    """Newest CANCELLED, older PAUSED-expired → the *cancelled* message.

    **Validates: Requirements 2.16, 2.17**

    Preservation Exception 2.16 / 1.14. Both contracts are past, so the status
    code is 403 either way; only the message and ``subscription_status`` change.

    **This case PASSES on unfixed code, coincidentally.** The fixture's
    customer-level ``productSubscriberStatus`` is also CANCELLED, so the unfixed
    ladder — which reads that field and never looks at a contract's own status —
    emits the cancelled message for an unrelated reason and happens to agree.
    Left in place because it states the required behavior and still holds after
    the fix; the counterexamples that actually expose clause 1.14 are the
    generated property above and the tiebreak case below. Recorded in the module
    docstring, because a green test that is green for the wrong reason is the
    hazard this whole spec exists to correct.
    """
    step2 = load_fixture("denial_newest_cancelled_older_paused")
    nodes = step2["subscriptionContracts"]["nodes"]
    assert not oracle_grants_anywhere(nodes), "fixture drift: nothing may grant"
    newest = oracle_newest(nodes)
    assert newest["status"] == "CANCELLED", "fixture drift: the newest must be CANCELLED"

    email = "denial.newest@example.com"
    with harness(
        step1=step1_payload([DENIAL_NEWEST_CUSTOMER_ID], email=email),
        step2={DENIAL_NEWEST_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        result = h.login(email, KNOWN_PASSWORD)

    body = result["body"]
    assert result["status_code"] == 403, f"expected 403, got {result}"
    assert body.get("redirect_url"), f"expected a redirect_url, got {body!r}"
    assert body.get("error") == CANCELLED_DENIAL, (
        f"the newest contract is CANCELLED ({describe(newest)}), so the message "
        f"must be {CANCELLED_DENIAL!r}; got {body.get('error')!r}. "
        f"contracts={describe_all(nodes)}"
    )


def test_property_8_identical_created_at_uses_the_contract_id_tiebreak():
    """Identical ``createdAt`` → the greatest ``contract_id`` decides the message.

    **Validates: Requirements 2.16**

    design.md change 6 fixes the selection as ``max(contracts, key=(created_at,
    contract_id))``. Without a tiebreak, two contracts stamped the same instant
    would make the denial copy depend on dict/list ordering, which is the same
    class of defect as clause 1.8. Ids here are equal length, so the comparison
    is unambiguous whichever type ``contract_id`` ends up holding.
    """
    stamp = (FIXTURE_NOW - relativedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past = (FIXTURE_NOW - relativedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    lower_id_cancelled = build_contract_node(
        contract_id=9_100_000_501, status="CANCELLED",
        created_at=stamp, next_billing_date=past, interval="MONTH", interval_count=1,
    )
    higher_id_paused = build_contract_node(
        contract_id=9_100_000_502, status="PAUSED",
        created_at=stamp, next_billing_date=past, interval="MONTH", interval_count=1,
    )
    nodes = [lower_id_cancelled, higher_id_paused]
    assert not oracle_grants_anywhere(nodes)
    assert oracle_newest(nodes) is higher_id_paused

    result = single_record_login(nodes, product_subscriber_status="CANCELLED")
    body = result["body"]

    assert result["status_code"] == 403, f"expected 403, got {result}"
    assert body.get("error") == EXPIRED_DENIAL, (
        f"both contracts share createdAt={stamp}; the tiebreak picks contract id "
        f"9100000502 (PAUSED) over 9100000501 (CANCELLED), so the message must be "
        f"{EXPIRED_DENIAL!r}; got {body.get('error')!r}"
    )


# ===========================================================================
# Property 9 — Bypass Survives Refresh
# ===========================================================================

def test_property_9_bypass_survives_refresh():
    """A ``BYPASS_EMAILS`` user refreshing an all-expired account keeps access.

    **Validates: Requirements 2.14**

    The bypass check exists in ``login()`` only (clause 1.10), so a bypass user
    is granted at login and can be bounced one hour later when the token
    refreshes — the drift that three copies of the decision logic made
    inevitable. ``refresh()`` must skip the subscription check the same way, and
    must not consult Appstle at all.
    """
    email = "bypass.refresh@example.com"
    expired = load_fixture("lapsed_paused_subscriber")
    assert not oracle_grants_anywhere(expired["subscriptionContracts"]["nodes"])

    with harness(
        step1=step1_payload([3289420039], email=email),
        step2={3289420039: expired},
        bypass_emails=email,
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        token = h.service.create_token(email, "active")
        h.router.reset()
        result = h.refresh(token)
        appstle_calls = list(h.router.urls)

    assert result["status_code"] == 200, (
        f"clause 2.14: refresh() must skip the subscription check for a bypass "
        f"email, got {result['status_code']} body={result['body']!r}"
    )
    assert result["body"].get("success") is True, (
        f"expected body.success == true, got {result['body']!r}"
    )
    assert appstle_calls == [], (
        f"a bypass refresh must not consult Appstle; calls observed: {appstle_calls}"
    )


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.sampled_from(("PAUSED", "CANCELLED", "EXPIRED", None)))
def test_property_9_bypass_survives_refresh_for_any_denied_payload(fallback):
    """Bypass wins over every non-granting Appstle payload shape.

    **Validates: Requirements 2.14**
    """
    email = "bypass.any@example.com"
    customer_id = 7_000_400_001
    past = (FIXTURE_NOW - relativedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    nodes = with_unique_ids([
        build_contract_node(
            contract_id=9_100_000_601, status="PAUSED",
            created_at=past, next_billing_date=past, interval="DAY", interval_count=30,
        )
    ])

    with harness(
        step1=step1_payload([customer_id], email=email),
        step2={
            customer_id: build_step2_payload(
                customer_id=customer_id, nodes=nodes, product_subscriber_status=fallback
            )
        },
        bypass_emails=email,
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        token = h.service.create_token(email, "active")
        h.router.reset()
        result = h.refresh(token)
        appstle_calls = list(h.router.urls)

    assert result["status_code"] == 200, (
        f"bypass refresh denied with fallback={fallback!r}: {result!r}"
    )
    assert result["body"].get("success") is True, f"got {result['body']!r}"
    assert appstle_calls == [], f"Appstle consulted for a bypass refresh: {appstle_calls}"


# ===========================================================================
# Property 10 — login And refresh Agree
# ===========================================================================

def _login_decision(result: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """``(granted, granted_status, denial_message)`` as ``login()`` reports it."""
    body = result["body"]
    granted = result["status_code"] == 200
    return (
        granted,
        body.get("subscription_status") if granted else None,
        body.get("error"),
    )


def _refresh_decision(
    result: Dict[str, Any], claims_of
) -> Tuple[bool, Optional[str], Optional[str]]:
    """The same triple from ``refresh()``.

    ``RefreshResponse`` carries no ``subscription_status`` field, so on the
    granted path the status is read out of the reissued token's claims. That is
    the same value ``login()`` puts in its body, and it is where the decision
    actually lands for a refreshed session. Comparing body *shapes* instead would
    fail on a field-list difference that has nothing to do with the access
    decision.
    """
    body = result["body"]
    granted = result["status_code"] == 200 and body.get("success") is True
    status = None
    if granted and body.get("token"):
        status = claims_of(body["token"]).get("subscription_status")
    return (granted, status, body.get("error"))


@st.composite
def agreement_cases(draw):
    """A contract set, a customer-level fallback status, and a bypass flag.

    The bypass flag is a generated axis rather than a fixed ``False`` because it
    is where the two callers have actually drifted: ``login()`` checks
    ``BYPASS_EMAILS``, ``refresh()`` does not (clause 1.10). Leaving it out would
    make the property agree with the implementation instead of with requirement
    2.13.

    Appstle failure injection is deliberately absent. Clause 3.8 *preserves* a
    real divergence there — ``login()`` falls through to free tier while
    ``refresh()`` keeps the status carried in the JWT claims — so generating it
    would assert against a documented requirement.
    """
    size = draw(st.integers(min_value=1, max_value=3))
    nodes = with_unique_ids([draw(contract_dicts()) for _ in range(size)])
    fallback = draw(st.sampled_from(("ACTIVE", "PAUSED", "CANCELLED", "EXPIRED", None)))
    bypass = draw(st.booleans())
    return nodes, fallback, bypass


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(agreement_cases())
def test_property_10_login_and_refresh_agree(case):
    """``login()`` and ``refresh()`` reach the same decision and the same message.

    **Validates: Requirements 2.13, 2.15**

    Both grant with the same status, or both deny with the same copy. Three
    separately maintained copies of step 4 is what allowed them to diverge; one
    shared ``decide_access()`` is what makes this property hold by construction
    rather than by vigilance.
    """
    nodes, fallback, bypass = case
    email = "agree@example.com"
    customer_id = 7_000_500_001

    with harness(
        step1=step1_payload([customer_id], email=email),
        step2={
            customer_id: build_step2_payload(
                customer_id=customer_id, nodes=nodes, product_subscriber_status=fallback
            )
        },
        bypass_emails=email if bypass else "",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        login_result = h.login(email, KNOWN_PASSWORD, DEFAULT_CLIENT_IP)
        h.reset()
        refresh_result = h.refresh(h.service.create_token(email, "active"))
        login_decision = _login_decision(login_result)
        refresh_decision = _refresh_decision(refresh_result, h.claims)

    assert login_decision == refresh_decision, (
        f"login() and refresh() disagree.\n"
        f"  login  : granted={login_decision[0]} status={login_decision[1]!r} "
        f"error={login_decision[2]!r} (HTTP {login_result['status_code']})\n"
        f"  refresh: granted={refresh_decision[0]} status={refresh_decision[1]!r} "
        f"error={refresh_decision[2]!r} (HTTP {refresh_result['status_code']})\n"
        f"  bypass={bypass} fallback={fallback!r} contracts={describe_all(nodes)}"
    )


def test_property_10_login_and_refresh_agree_on_daves_payload():
    """The concrete agreement case on real data, with the bypass list empty.

    **Validates: Requirements 2.13**
    """
    email = DAVE_EMAIL
    with harness(
        step1=load_fixture("step1_single_customer"),
        step2={DAVE_CUSTOMER_ID: load_fixture("dave_two_paused_contracts")},
        bypass_emails="",
        known_passwords={email: KNOWN_PASSWORD},
    ) as h:
        login_result = h.login(email, KNOWN_PASSWORD)
        h.reset()
        refresh_result = h.refresh(h.service.create_token(email, "active"))
        login_decision = _login_decision(login_result)
        refresh_decision = _refresh_decision(refresh_result, h.claims)

    assert login_decision == refresh_decision, (
        f"login() and refresh() disagree on Dave's captured payload: "
        f"login={login_decision} refresh={refresh_decision}"
    )
    assert login_decision[0] is True, (
        f"Dave holds a contract with paid time remaining, so both callers must "
        f"grant; got login={login_decision} refresh={refresh_decision}"
    )


# ===========================================================================
# Property 11 — Calendar Interval Math
# ===========================================================================
#
# Scoped to ``_add_calendar_interval()`` (Task 8.3). Property 11's full statement
# is about ``paid_through``, but ``_paid_through()`` does not exist until Task
# 8.4, which is where the anchor-selection half of the property is asserted. The
# arithmetic itself is the part that can be pinned now, and it is the part where a
# wrong answer is invisible: a 30-day month is right often enough to survive a
# spot check and drifts a little every month, a full day every leap year.
#
# Unlike every other property in this module these two run against the helper
# directly rather than through ``login()``. The helper is pure and module-level
# precisely so that it can be: there is no payload, no customer, and no response
# body involved in "what is Jan 31 plus one month".


def calendar_oracle(anchor: datetime, unit: str, count: int) -> datetime:
    """Month/year arithmetic computed independently of ``relativedelta``.

    Deliberately NOT written with ``relativedelta``: asserting the implementation
    against the library it is built on would only restate the call. Month index
    arithmetic with an explicit clamp to the target month's length is the same
    rule stated a different way, so a disagreement means one of the two is wrong.
    """
    if unit == "YEAR":
        year, month = anchor.year + count, anchor.month
    else:
        zero_based = (anchor.month - 1) + count
        year = anchor.year + zero_based // 12
        month = zero_based % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


APPROXIMATION_DAYS = {"MONTH": 30, "YEAR": 365}


@settings(max_examples=200, deadline=None)
@given(
    anchor=st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2035, 12, 31, 23, 59, 59),
    ),
    unit=st.sampled_from(("MONTH", "YEAR")),
    count=st.integers(min_value=1, max_value=12),
)
def test_property_11_calendar_interval_math(anchor, unit, count):
    """MONTH and YEAR advance by calendar units, never by 30 or 365 days.

    **Validates: Requirements 2.7**

    Two assertions, and the second is the one with teeth. The result must equal
    independently computed calendar arithmetic; and wherever calendar arithmetic
    and the fixed-day approximation disagree, the result must follow the calendar.
    The approximation is not a strawman — it is the obvious implementation, and it
    is wrong for 7 of 12 months and for every leap year.
    """
    anchor_utc = anchor.replace(tzinfo=timezone.utc)

    result = _add_calendar_interval(anchor_utc, unit, count)
    expected = calendar_oracle(anchor_utc, unit, count)
    approximation = anchor_utc + timedelta(days=APPROXIMATION_DAYS[unit] * count)

    assert result == expected, (
        f"calendar arithmetic mismatch: {anchor_utc.isoformat()} + {count} "
        f"{unit} gave {result.isoformat() if result else None}, expected "
        f"{expected.isoformat()}"
    )

    if expected != approximation:
        event(f"{unit}: diverges from the {APPROXIMATION_DAYS[unit]}-day approximation")
        assert result != approximation, (
            f"{anchor_utc.isoformat()} + {count} {unit} returned the "
            f"{APPROXIMATION_DAYS[unit]}-day approximation "
            f"{approximation.isoformat()} where the calendar says "
            f"{expected.isoformat()} — a "
            f"{abs((approximation - expected).days)}-day error in paid time"
        )
    else:
        event(f"{unit}: coincides with the {APPROXIMATION_DAYS[unit]}-day approximation")


@settings(max_examples=50, deadline=None)
@given(year=st.integers(min_value=2000, max_value=2035))
def test_property_11_january_31_plus_one_month_never_equals_30_days(year):
    """Jan 31 + 1 MONTH is the end of February, and never Jan 31 + 30 days.

    **Validates: Requirements 2.7**

    The generated property above reports how often the calendar and the
    approximation happen to coincide; this one pins a region where they cannot,
    in every year, leap or not. Feb 28 versus Mar 2 is two days of paid time
    invented from nothing, in the direction that grants access.

    Scoped narrowly and deliberately. "Month-end anchors always diverge" is false
    and was worth discovering: Mar 31 + 1 month and Mar 31 + 30 days both land on
    Apr 30, and Jan 31 + 2 months coincides with +60 days in a leap year. The
    divergence is guaranteed only where the clamp is large, which is a landing in
    February — so that is what is asserted, rather than a broader claim that
    would be false.
    """
    anchor = datetime(year, 1, 31, 12, 0, tzinfo=timezone.utc)
    february_last_day = calendar.monthrange(year, 2)[1]

    result = _add_calendar_interval(anchor, "MONTH", 1)

    assert result == anchor.replace(month=2, day=february_last_day), (
        f"{anchor.isoformat()} + 1 MONTH must clamp to February "
        f"{february_last_day}, got {result.isoformat() if result else None}"
    )
    assert result != anchor + timedelta(days=30), (
        f"{anchor.isoformat()} + 1 MONTH returned the 30-day approximation "
        f"{(anchor + timedelta(days=30)).isoformat()}"
    )


# ===========================================================================
# Property 12 — Underivable Paid-Through Does Not Grant
# ===========================================================================
#
# Clause 2.8. When the paid-through date cannot be derived — no
# ``nextBillingDate``, and a billing policy that is absent or carries a unit
# Appstle has never sent — the contract must NOT grant, and the failure must be
# loud. Three assertions per example, and they are three different claims:
# ``paid_through`` is null (the derivation refused rather than guessed), the
# contract does not grant (the refusal reaches the decision), and an ERROR is
# logged (the refusal is visible).
#
# Direction matters here. This is the one place where the fix deliberately errs
# toward DENIAL: a contract we cannot price out in time is treated as not paid
# for. Guessing an interval would invent access, so the safe failure is a denial
# the customer can resolve by resubscribing.
#
# Like Property 11 these run against the helpers directly rather than through
# ``login()``, because Task 8.4 adds the helpers without wiring them into any
# caller — no observable behavior changes in that subtask, by design.


@contextmanager
def pinned_clock():
    """Pin ``_utcnow()`` to ``FIXTURE_NOW`` outside a full ``harness()`` context.

    ``harness()`` already does this for every property that drives ``login()``.
    Property 12 calls the helpers directly, so it pins the same seam (design
    change 2b) the same way — otherwise a paid-through expressed as an offset from
    ``FIXTURE_NOW`` would be compared against the real clock and the verdict would
    flip once wall-clock time crosses 2026-08-09.
    """
    original = subscription_auth._utcnow
    subscription_auth._utcnow = fixture_now
    try:
        yield
    finally:
        subscription_auth._utcnow = original


@contextmanager
def captured_errors(logger_name: str = LOGGER_NAME):
    """Collect ERROR-and-above records from a logger without ``caplog``.

    ``caplog`` is function-scoped, and a function-scoped fixture used from a
    Hypothesis ``@given`` test either trips ``HealthCheck.function_scoped_fixture``
    or silently accumulates records across examples. Attaching a handler inside
    the test body gives one clean collection per example.
    """
    records: List[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Collector(level=logging.ERROR)
    logger = logging.getLogger(logger_name)
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


# ``None`` is the absent-``billingPolicy`` case and the strings are unrecognized
# units; clause 2.8 names them separately and both must be underivable. Shared
# with the harness so the generators and the oracle cannot drift apart.
UNDERIVABLE_INTERVALS = (*UNRECOGNIZED_INTERVALS, None)


@st.composite
def underivable_contract_views(draw) -> ContractView:
    """A ``ContractView`` whose ``paid_through`` cannot be derived.

    ``next_billing_date`` is always null — with it present there is nothing to
    derive and the property does not apply. The status is drawn from PAUSED and
    CANCELLED, the two that gate on paid time (clause 2.3); ACTIVE is excluded
    because it grants without consulting ``paid_through`` at all (clause 2.2,
    Property 6), so including it would assert against a requirement.

    The anchor is drawn including future and null values. A future ``createdAt``
    is nonsense from Appstle but it is the input that would produce a future
    paid-through if the interval were readable, so it is exactly where a
    charitable reading of an unknown unit would leak a grant.
    """
    status = draw(st.sampled_from(("PAUSED", "CANCELLED", "paused", "cancelled")))
    anchor_offset = draw(st.one_of(st.none(), st.integers(min_value=-900, max_value=900)))
    anchor = None if anchor_offset is None else FIXTURE_NOW + timedelta(days=anchor_offset)

    return ContractView(
        customer_id=draw(st.integers(min_value=1_000_000, max_value=9_999_999_999)),
        contract_id=f"gid://shopify/SubscriptionContract/{draw(st.integers(9_200_000_000, 9_200_009_999))}",
        status=status,
        next_billing_date=None,
        created_at=anchor,
        renewal_anchor=anchor,
        renewal_anchor_field=None if anchor is None else "createdAt",
        interval=draw(st.sampled_from(UNDERIVABLE_INTERVALS)),
        interval_count=draw(st.integers(min_value=1, max_value=12)),
    )


@settings(max_examples=200, deadline=None)
@given(underivable_contract_views())
def test_property_12_underivable_paid_through_does_not_grant(view):
    """Unrecognized or absent billing policy → null, no grant, ERROR logged.

    **Validates: Requirements 2.8**

    The interesting half is that this holds for a FUTURE anchor too. With a
    readable unit, an anchor 900 days out would derive a paid-through well ahead
    of now and grant; the whole point of clause 2.8 is that an unreadable unit
    must not get there by guessing which unit was meant.
    """
    with pinned_clock(), captured_errors() as records:
        paid_through = _paid_through(view)
        grants = _contract_grants(view)

    event(f"interval={view.interval!r}")

    assert paid_through is None, (
        f"clause 2.8: paid_through must be underivable for interval="
        f"{view.interval!r} intervalCount={view.interval_count!r}, got "
        f"{paid_through.isoformat() if paid_through else None} from anchor="
        f"{view.renewal_anchor}"
    )
    assert grants is False, (
        f"clause 2.8: a contract with an underivable paid_through must not grant. "
        f"status={view.status!r} interval={view.interval!r} anchor={view.renewal_anchor}"
    )
    messages = [record.getMessage() for record in records]
    assert any("underivable" in message for message in messages), (
        f"clause 2.8 requires an ERROR record naming the failure; got "
        f"{messages or '<no ERROR records>'} for interval={view.interval!r}"
    )
    assert any(str(view.customer_id) in message for message in messages), (
        f"the ERROR must identify the customer, otherwise it is unactionable. "
        f"records={messages}"
    )


@pytest.mark.parametrize(
    "fixture_name",
    ["paused_unrecognized_interval", "paused_absent_billing_policy"],
)
def test_property_12_on_the_underivable_fixtures(fixture_name, caplog):
    """The same property on the two fixtures built for it.

    **Validates: Requirements 2.8**

    ``paused_unrecognized_interval`` carries ``billingPolicy.interval``
    ``"FORTNIGHT"``; ``paused_absent_billing_policy`` omits ``billingPolicy``
    entirely. Clause 2.8 names those as distinct inputs, so both are checked
    rather than assuming one stands for the other.

    The node → ``ContractView`` mapping is done here by hand because the parser
    that will do it (``_parse_contract_nodes``, Task 9.1) does not exist yet. It
    is deliberately minimal, and the anchor it sets is ``createdAt``, which per
    design Finding 1 is the only anchor Appstle exposes.
    """
    step2 = load_fixture(fixture_name)
    node = step2["subscriptionContracts"]["nodes"][0]
    assert node["nextBillingDate"] is None, "fixture drift: nextBillingDate must be null"

    policy = node.get("billingPolicy") or {}
    created_at = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
    view = ContractView(
        customer_id=7_000_000_013,
        contract_id=node["id"],
        status=node["status"],
        next_billing_date=None,
        created_at=created_at,
        renewal_anchor=created_at,
        renewal_anchor_field="createdAt",
        interval=policy.get("interval"),
        interval_count=policy.get("intervalCount", 1),
    )

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME), pinned_clock():
        paid_through = _paid_through(view)
        grants = _contract_grants(view)

    assert paid_through is None, (
        f"{fixture_name}: expected an underivable paid_through, got "
        f"{paid_through.isoformat() if paid_through else None}"
    )
    assert grants is False, f"{fixture_name}: must not grant"
    assert any(
        "underivable" in message for message in messages_of(caplog, level=logging.ERROR)
    ), (
        f"{fixture_name}: clause 2.8 requires an ERROR record. "
        f"records={messages_of(caplog)}"
    )


def test_property_12_recognized_interval_still_derives_and_grants(caplog):
    """The contrast case, so the property above cannot pass by denying everything.

    **Validates: Requirements 2.6, 2.7**

    Same shape of input — PAUSED, null ``nextBillingDate``, anchor eight days back
    — but with a unit Appstle actually sends. It must derive a paid-through and
    grant, which is Preservation Exception 2.6 / 1.6. Without this, an
    implementation that returned ``None`` unconditionally would satisfy
    Property 12.

    The ERROR is asserted here too: per design Finding 1 the ``createdAt`` anchor
    is the only one available and is exact only for a contract that has never
    renewed, so every use of this path is worth a record even when it succeeds.
    """
    anchor = FIXTURE_NOW - timedelta(days=8)
    view = ContractView(
        customer_id=7_000_000_012,
        contract_id="gid://shopify/SubscriptionContract/9000000121",
        status="PAUSED",
        next_billing_date=None,
        created_at=anchor,
        renewal_anchor=anchor,
        renewal_anchor_field="createdAt",
        interval="MONTH",
        interval_count=1,
    )

    with pinned_clock(), captured_errors() as records:
        paid_through = _paid_through(view)
        grants = _contract_grants(view)

    assert paid_through == anchor + relativedelta(months=1)
    assert paid_through > FIXTURE_NOW
    assert grants is True, (
        f"a derivable future paid_through must grant; paid_through="
        f"{paid_through.isoformat()} FIXTURE_NOW={FIXTURE_NOW.isoformat()}"
    )
    messages = [record.getMessage() for record in records]
    assert any("createdAt" in message for message in messages), (
        f"clause 2.6 requires an ERROR when the weak createdAt anchor is used; "
        f"got {messages or '<no ERROR records>'}"
    )


# ===========================================================================
# Property 13 — Silent Downgrades Become Loud
# ===========================================================================
#
# Two halves, both from clause 1.16 / 1.15: the observability that hid this bug
# class in the first place. A missing productSubscriberStatus downgrades a
# customer to free tier at logger.info, invisible in normal log review; and both
# Appstle payloads are logged as str(data)[:500], which truncates before the
# interesting contracts in exactly the multi-contract payloads needed to diagnose
# this.

# Signatures of a raw payload dict/list being logged. Requirement 2.20 replaces
# those with structured per-contract lines, so after the fix neither marker may
# appear anywhere in the log.
#
# Note on what this can and cannot observe: the ``str(data)[:500]`` truncation
# lives inside ``_appstle_get()``, which is the very method the harness router
# replaces, so that particular line never executes here and these markers cannot
# fire through this suite. They are kept as a guard against a *parser* logging a
# raw payload repr. The load-bearing half of this test is therefore the positive
# one below: the contract count and each contract's status and dates must be
# present.
RAW_STEP2_REPR_MARKER = "{'__typename'"
RAW_STEP1_REPR_MARKER = "[{'customerId'"


def mentions_contract_count(text: str, count: int) -> bool:
    """Does the log state how many contracts were seen, in any reasonable wording?

    Matches "2 contracts", "contract count=2", "contracts=2" and similar rather
    than pinning one phrasing, since requirement 2.20 fixes the information, not
    the sentence.
    """
    pattern = (
        rf"(?i)(\b{count}\b[^\n]{{0,40}}contract|contract[^\n]{{0,40}}\b{count}\b)"
    )
    return re.search(pattern, text) is not None


def test_property_13_missing_product_subscriber_status_logs_an_error(caplog):
    """A missing ``productSubscriberStatus`` still grants free tier, but loudly.

    **Validates: Requirements 2.19**

    Free tier is the right outcome — the safer of the two, and clause 3.2 keeps
    it. What changes is the volume: an ``ERROR`` record, not a ``logger.info``
    line nobody reads. A customer silently dropped to free tier is a support
    ticket that arrives without a trace.
    """
    step2 = load_fixture("missing_product_subscriber_status")
    assert "productSubscriberStatus" not in step2, "fixture drift: the key must be absent"

    email = "missing.status@example.com"
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        with harness(
            step1=step1_payload([MISSING_STATUS_CUSTOMER_ID], email=email),
            step2={MISSING_STATUS_CUSTOMER_ID: step2},
            bypass_emails="",
            known_passwords={email: KNOWN_PASSWORD},
        ) as h:
            result = h.login(email, KNOWN_PASSWORD)

    body = result["body"]
    assert result["status_code"] == 200, f"expected 200, got {result!r}"
    assert body.get("subscription_status") == "free", (
        f"expected subscription_status='free', got {body.get('subscription_status')!r}"
    )

    errors = messages_of(caplog, level=logging.ERROR)
    assert errors, (
        "clause 2.19 requires an ERROR-level record when productSubscriberStatus "
        "is missing; the highest level observed was "
        f"{max((r.levelname for r in caplog.records), default='<no records>')}. "
        f"records={messages_of(caplog)}"
    )


def test_property_13_multi_contract_payload_is_logged_untruncated(caplog):
    """Every contract's status and dates reach the log; no 500-char truncation.

    **Validates: Requirements 2.20**

    Dave's payload is the case that matters: the contract that would have
    explained his lockout is the second one, and a 500-character truncation of
    the raw payload cuts off before it. The log has to carry the contract count
    and, per contract, the status and the dates — the fields the decision
    actually turns on.
    """
    step2 = load_fixture("dave_two_paused_contracts")
    nodes = step2["subscriptionContracts"]["nodes"]

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        with harness(
            step1=load_fixture("step1_single_customer"),
            step2={DAVE_CUSTOMER_ID: step2},
            bypass_emails="",
            known_passwords={DAVE_EMAIL: KNOWN_PASSWORD},
        ) as h:
            h.login(DAVE_EMAIL, KNOWN_PASSWORD)

    log_text = "\n".join(messages_of(caplog))

    for marker in (RAW_STEP2_REPR_MARKER, RAW_STEP1_REPR_MARKER):
        assert marker not in log_text, (
            f"clause 2.20: the raw payload is still being logged (marker {marker!r} "
            f"found), which is the 500-character truncation that hides "
            f"multi-contract payloads. log:\n{log_text}"
        )

    assert mentions_contract_count(log_text, len(nodes)), (
        f"clause 2.20 requires the contract count ({len(nodes)}) in the log. "
        f"log:\n{log_text}"
    )

    for node in nodes:
        status = node["status"]
        assert status in log_text, (
            f"contract {node['id']} status {status!r} is absent from the log. "
            f"log:\n{log_text}"
        )
        for field in ("createdAt", "nextBillingDate"):
            # Compare on the YYYY-MM-DD prefix: a structured line may render a
            # datetime as "2026-07-02 22:00:00+00:00" rather than the ISO "Z"
            # form, and the requirement is about the dates being present, not
            # about how they are formatted.
            day = str(node[field])[:10]
            assert day in log_text, (
                f"contract {node['id']} {field} {node[field]!r} (day {day}) is "
                f"absent from the log. log:\n{log_text}"
            )
