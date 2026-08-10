"""Bug condition exploration test — Property 1: Any Granting Contract Grants Access.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.8, 2.1, 2.2, 2.3, 2.5, 2.10, 2.11, 2.12**

Spec: ``.kiro/specs/subscription-multi-contract-access/`` (bugfix.md, design.md).

THIS SUITE IS EXPECTED TO FAIL ON UNFIXED CODE. Each failure is a counterexample
that confirms one of the root causes. The same assertions become the fix check in
Task 11.1, so nothing here asserts current (buggy) behavior — every assertion
states the required behavior, and the observed failures are recorded below.

Property 1 (design.md, "Correctness Properties"):

    FOR ALL X WHERE isBugCondition(X) clause (a) holds DO
      result <- login(X)
      ASSERT result.status_code == 200
      ASSERT result.body.subscription_status == "active"

Clause (a), ``isMultiContractBug``: some contract in the union of all contracts
across all customer records and all pages grants, while ``nodes[0]`` of the first
customer record's first page — the only contract the unfixed parser reads — does
not.

Everything is asserted on ``login()``'s returned ``status_code`` and ``body``.
Nothing touches parser internals: the shipped bug was hidden precisely by tests
that asserted on fields the decision path never reads (clause 1.12). Payloads
enter at the ``_appstle_get()`` seam (Task 3) through the harness's URL-keyed
router (Task 4), so the parser, the multi-record traversal, and the pagination
loop all stay inside the system under test. The clock is pinned to
``FIXTURE_NOW`` (2026-08-09T01:31:12Z) so the verbatim captured dates keep the
meaning they had at capture time.

Run offline::

    python3 -m pytest tests/test_subscription_bug_condition.py -v


OBSERVED COUNTEREXAMPLES (run on UNFIXED code)
----------------------------------------------

``python3 -m pytest tests/test_subscription_bug_condition.py -v``
→ **4 failed, 1 xfailed** in ~6s. Every failure matches the root cause analysis
in design.md; nothing was refuted, so no re-hypothesizing was needed.

1. ``test_daves_two_paused_contracts_grant_access`` — **FAILED**, confirms
   **root cause 1** (``nodes[0]`` truncation in ``_parse_contract_response()``)::

       expected 200 / "active"
       got      403 {"error": "Your subscription has expired. Resubscribe to continue.",
                     "subscription_status": "paused",
                     "redirect_url": "https://mcpress.test/subscribe"}

   Dave's real payload, ``customerId`` 2788838535: ``nodes[0]`` PAUSED
   ``nextBillingDate`` 2026-07-02T22:00:00Z (past), ``nodes[1]`` PAUSED
   ``nextBillingDate`` 2026-08-27T19:00:00Z (future). This is the exact
   403 + copy predicted by the spec, from real captured data, with
   ``BYPASS_EMAILS`` empty.

2. ``test_second_customer_record_grants_access`` — **FAILED**, confirms
   **root cause 2** (first-``customerId`` truncation in
   ``_extract_customer_id()``)::

       expected 200 / "active"
       got      403 "Your subscription has expired. Resubscribe to continue." / "paused"
       router   step-2 requests issued for [3289420039] only

   ``c2`` = 7000000021, which holds the CANCELLED-with-21-days-paid contract,
   was **never requested**. That router evidence is the direct observation the
   task asked for: the second customer record is not merely mis-evaluated, it is
   never fetched.

3. ``test_granting_contract_on_second_page_grants_access`` — **XFAIL**, confirms
   **root cause 3** (no pagination). Under ``--runxfail``::

       expected 200 / "active"
       got      403 "Your subscription has expired. Resubscribe to continue." / "paused"
       router   1 step-2 request for customerId 7000000018, cursors [None]

   ``pageInfo.hasNextPage`` is true on page 1 and page 2 was never requested.
   Marked xfail rather than a hard failure — see "Documented deviations" below.

4. ``test_any_granting_contract_grants_access_scoped`` (Hypothesis, 60 examples)
   — **FAILED** with two distinct minimal counterexamples, both with a granting
   ACTIVE contract present:

   a. ``records=[7000200001, 7000200002]``, granting contract under the second
      record, first record's ``productSubscriberStatus`` ``EXPIRED``
      → **200 / ``"free"``** (not 403). Root cause 2, plus root cause 4: an
      unrecognized customer-level status silently drops a customer who holds a
      granting contract into free tier (clause 1.15).
   b. single record, ``nodes[0]`` PAUSED with a past billing date and an ACTIVE
      contract at ``nodes[1]``
      → **403 "Your subscription has expired. Resubscribe to continue." /
      ``"paused"``**. Root cause 1.

5. ``test_any_granting_contract_grants_access_broad`` (Hypothesis, 150 examples
   over the full contract domain, filtered to clause (a)) — **FAILED** with the
   same two shapes as 4a and 4b, reached from the unconstrained strategy. The
   two observable failure modes are therefore ``403 expired`` and
   ``200 "free"``, depending on the first record's ``productSubscriberStatus``.

Two alternative hypotheses listed in design.md under "Exploratory Bug Condition
Checking" are refuted by these runs:

* *"Appstle may order contracts newest-first for some customers."* Dave's
  captured payload is oldest-first, and the fixture asserts it: ``nodes[0]`` is
  the 2026-06-02 contract, ``nodes[1]`` the 2026-07-28 one.
* *"``productSubscriberStatus`` already reflects the newest contract."* Dave's
  customer-level status is PAUSED while his newest contract still has paid time,
  and the ladder denies him on ``nodes[0]``'s date regardless. The
  customer-level field carries no information about which contract grants.


Documented deviations from the task text
----------------------------------------

Both exist so this module can serve its second job — the Task 11.1 fix check —
without asserting behavior the fix is meant to remove.

* **The two-customer-record case asserts the required behavior, not the bug.**
  The task asks it to "assert via the router that no step-2 request was made for
  the second ``customerId`` on unfixed code". A passing assertion on the buggy
  behavior would invert once the fix lands. Instead the test asserts
  ``router.fetched_customer(c2)`` — the required behavior under clause 2.10 —
  and its failure message reports the ``customerId``s actually fetched, which is
  the same evidence stated in the direction that stays correct after the fix.
  Observed: ``[3289420039]``.

* **The pagination case is ``xfail(strict=False)``.** Design **Finding 4**
  records that cursor-following is not implementable yet: ``pageInfo`` is
  cursor-based with opaque base64 cursors, ``hasNextPage`` was false for all
  three captured customers, and the query-parameter name the step-2 endpoint
  accepts for a cursor is unknown. Task 9.3 is scoped to
  detection-plus-ERROR-log only, so this case is expected to stay red after the
  fix. A hard failure would make the suite permanently red and hide real
  regressions; ``strict=False`` also means it will not fail the suite if
  page-following is implemented later and it starts passing. The counterexample
  is recorded above and reproducible with ``--runxfail``.

Also worth recording: the Hypothesis properties generate **single-page** plans
only, for the same Finding 4 reason. Multi-page distribution is a legitimate
clause (a) input, but generating it would leave these properties red forever. The
pagination gap is carried by the one xfail'd case above, where it is visible,
rather than buried inside a generator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest
from dateutil.relativedelta import relativedelta
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from tests.subscription_harness import (
    DEFAULT_CLIENT_IP,
    FIXTURE_NOW,
    KNOWN_PASSWORD,
    PayloadPlan,
    contract_dicts,
    future_dates,
    harness,
    load_fixture,
    past_dates,
    payload_plans,
    step1_payload,
)

# ---------------------------------------------------------------------------
# Fixture coordinates (see tests/fixtures/appstle/README.md)
# ---------------------------------------------------------------------------

DAVE_EMAIL = "multi.contract@example.com"
DAVE_CUSTOMER_ID = 2788838535

TWO_RECORDS_EMAIL = "two.records@example.com"
PAGINATED_EMAIL = "paginated@example.com"
PAGINATED_CUSTOMER_ID = 7000000018

EXPIRED_DENIAL = "Your subscription has expired. Resubscribe to continue."


# ---------------------------------------------------------------------------
# Test-side oracle: contractGrants / paidThrough from design.md
# ---------------------------------------------------------------------------
#
# Implemented here over the *generated payload dicts* so the property can decide
# whether clause (a) holds without importing anything from the decision layer
# (which does not exist yet, and which is the thing under test). It is a
# transcription of the design pseudocode, deliberately kept independent of the
# production implementation.

GRANTING_STATUSES = {"PAUSED", "CANCELLED"}

_INTERVALS = {
    "DAY": "days",
    "WEEK": "weeks",
    "MONTH": "months",
    "YEAR": "years",
}


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
    if status_upper in GRANTING_STATUSES:
        paid_through = oracle_paid_through(node)
        return paid_through is not None and paid_through > FIXTURE_NOW
    return False


def clause_a_holds(all_contracts: List[dict], first_contract: Optional[dict]) -> bool:
    """``isMultiContractBug(X)``: some contract grants, ``nodes[0]`` does not."""
    any_grants = any(oracle_contract_grants(node) for node in all_contracts)
    first_grants = first_contract is not None and oracle_contract_grants(first_contract)
    return any_grants and not first_grants


# ---------------------------------------------------------------------------
# Shared assertion
# ---------------------------------------------------------------------------

def assert_grants_access(result: Dict[str, Any], *, evidence: str) -> None:
    """Property 1's two assertions, on ``login()``'s status code and body only.

    ``evidence`` is folded into the failure message so the counterexample is
    legible in the run log rather than having to be reconstructed from it.
    """
    body = result["body"]
    assert result["status_code"] == 200, (
        f"Property 1 violated: expected 200, got {result['status_code']} "
        f"with error={body.get('error')!r} subscription_status="
        f"{body.get('subscription_status')!r}. {evidence}"
    )
    assert body.get("subscription_status") == "active", (
        f"Property 1 violated: expected subscription_status='active', got "
        f"{body.get('subscription_status')!r}. {evidence}"
    )


# ---------------------------------------------------------------------------
# Concrete case 1 — Dave's captured payload (root cause 1: nodes[0] truncation)
# ---------------------------------------------------------------------------

def test_daves_two_paused_contracts_grant_access():
    """Dave's real captured payload: ``nodes[1]`` grants, ``nodes[0]`` does not.

    Two PAUSED contracts returned oldest-first. ``nodes[0]`` has
    ``nextBillingDate`` 2026-07-02 (past at ``FIXTURE_NOW``); ``nodes[1]`` has
    2026-08-27 (future). ``BYPASS_EMAILS`` is empty, so nothing masks the
    decision — which is the point: in production Dave only has access because he
    is on the bypass list.

    Confirms root cause 1 when it fails.
    """
    step2 = load_fixture("dave_two_paused_contracts")
    nodes = step2["subscriptionContracts"]["nodes"]
    assert not oracle_contract_grants(nodes[0]), "fixture drift: nodes[0] should not grant"
    assert oracle_contract_grants(nodes[1]), "fixture drift: nodes[1] should grant"

    with harness(
        step1=load_fixture("step1_single_customer"),
        step2={DAVE_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={DAVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(DAVE_EMAIL, KNOWN_PASSWORD)

        assert_grants_access(
            result,
            evidence=(
                "Dave, customerId 2788838535: nodes[0] PAUSED nextBillingDate "
                "2026-07-02T22:00:00Z (past), nodes[1] PAUSED nextBillingDate "
                "2026-08-27T19:00:00Z (future) — a granting contract exists. "
                "Root cause 1: _parse_contract_response() reads nodes[0] only."
            ),
        )


# ---------------------------------------------------------------------------
# Concrete case 2 — two customer records (root cause 2: first-customerId truncation)
# ---------------------------------------------------------------------------

def test_second_customer_record_grants_access():
    """One email, two Appstle ``customerId``s: only the second one grants.

    ``c1`` (3289420039) is the lapsed 30-day purchaser — PAUSED, billing date in
    the past, does not grant. ``c2`` (7000000021) is CANCELLED with 21 days of
    paid time left, so it grants.

    Two assertions carry this case, both stated as required behavior:

    1. ``login()`` returns 200 / ``"active"``.
    2. The router shows a step-2 request was issued for ``c2``.

    The task text asks this case to assert that **no** step-2 request was made
    for ``c2`` on unfixed code. Asserting the buggy behavior directly would make
    this module fail once the fix lands, contradicting its second job as the
    Task 11.1 fix check. So the observation is captured the other way round: the
    assertion states the required behavior, and its failure message reports the
    ``customerId``s actually fetched — which is exactly the evidence that ``c2``
    was never requested. Deviation recorded in the module docstring.
    """
    step1 = load_fixture("step1_two_customers")
    c1, c2 = [record["customerId"] for record in step1]

    with harness(
        step1=step1,
        step2={
            c1: load_fixture("lapsed_paused_subscriber"),
            c2: load_fixture("cancelled_with_paid_time"),
        },
        bypass_emails="",
        known_passwords={TWO_RECORDS_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(TWO_RECORDS_EMAIL, KNOWN_PASSWORD)
        fetched = h.router.requested_customer_ids

        assert_grants_access(
            result,
            evidence=(
                f"two customer records {[c1, c2]}: nothing under c1={c1} grants, "
                f"the CANCELLED-with-paid-time contract under c2={c2} does. "
                f"Step-2 requests were issued for {fetched}. "
                "Root cause 2: _extract_customer_id() returns the first customerId only."
            ),
        )
        assert h.router.fetched_customer(c2), (
            f"Required behavior (clause 2.10): a step-2 request must be issued for "
            f"c2={c2}. Step-2 requests observed: {fetched} — c2 was never fetched, "
            f"so its granting contract could not have been seen. Root cause 2."
        )


# ---------------------------------------------------------------------------
# Concrete case 3 — granting contract on page 2 (root cause 3: no pagination)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=False,
    reason=(
        "Root cause 3 (no pagination) is confirmed by this failure, but design "
        "Finding 4 records that cursor-following is NOT implementable yet: "
        "pageInfo is cursor-based and hasNextPage was false for every captured "
        "customer, so the request parameter name Appstle accepts is unknown. "
        "Task 9.3 therefore ships detection-plus-ERROR-log only, and this case "
        "is expected to remain red after the fix. xfail(strict=False) so it "
        "reports either way without gating the suite."
    ),
)
def test_granting_contract_on_second_page_grants_access():
    """``pageInfo.hasNextPage`` is true and the granting contract sits on page 2.

    Page 1 carries a PAUSED contract with a past billing date; page 2 carries a
    PAUSED contract with ``nextBillingDate`` 14 days out. Under "grant if any
    contract grants", a granting contract stranded on an unread page is a false
    denial of a paying customer (clause 2.11).

    The page pair uses a synthetic placeholder cursor parameter, since Appstle's
    real one is unknown (Finding 4). The harness router *can* serve page 2; that
    it is never requested is the counterexample.
    """
    page1 = load_fixture("contracts_page1")
    page2 = load_fixture("contracts_page2")
    assert page1["subscriptionContracts"]["pageInfo"]["hasNextPage"] is True
    assert not oracle_contract_grants(page1["subscriptionContracts"]["nodes"][0])
    assert oracle_contract_grants(page2["subscriptionContracts"]["nodes"][0])

    with harness(
        step1=step1_payload([PAGINATED_CUSTOMER_ID], email=PAGINATED_EMAIL),
        step2={PAGINATED_CUSTOMER_ID: [page1, page2]},
        bypass_emails="",
        known_passwords={PAGINATED_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(PAGINATED_EMAIL, KNOWN_PASSWORD)
        pages_requested = h.router.page_count(PAGINATED_CUSTOMER_ID)

        assert_grants_access(
            result,
            evidence=(
                f"customerId {PAGINATED_CUSTOMER_ID}: page 1 advertises "
                f"hasNextPage=true and does not grant; page 2 holds a PAUSED "
                f"contract with nextBillingDate FIXTURE_NOW+14d, which grants. "
                f"Step-2 requests issued for this customer: {pages_requested} "
                f"(cursors {h.router.cursors_requested(PAGINATED_CUSTOMER_ID)}). "
                "Root cause 3: pageInfo is never read."
            ),
        )


# ---------------------------------------------------------------------------
# Widening: Hypothesis over contract sets where clause (a) holds
# ---------------------------------------------------------------------------
#
# Both properties below generate SINGLE-PAGE plans on purpose. Distributing a
# granting contract onto page 2 is a genuine clause (a) input, but per design
# Finding 4 the fix cannot follow pages yet, so generating it here would leave
# these properties red forever and destroy their second job as the Task 11.1 fix
# check. The pagination counterexample is carried by the xfail'd concrete case
# above instead, which is where that deviation is visible rather than hidden
# inside a generator.

NON_GRANTING_STATUSES = (
    "PAUSED", "CANCELLED", "EXPIRED", "", "SUSPENDED", "NOT_A_STATUS",
    "paused", "active ", "0", None,
)
GRANTING_ON_PAID_TIME = ("PAUSED", "CANCELLED", "paused", "cancelled")

# ACTIVE is excluded: the unfixed decision path grants on a customer-level
# ACTIVE status without reading a contract at all, which would let an example
# pass for a reason that has nothing to do with the contract set.
NON_ACTIVE_FALLBACK_STATUSES = ("PAUSED", "CANCELLED", "EXPIRED", None)


def non_granting_contracts() -> st.SearchStrategy[dict]:
    """A contract that cannot grant: non-ACTIVE status, billing date in the past.

    ``paid_through`` is ``nextBillingDate`` whenever it is present, so a past
    billing date settles it and the anchor and interval axes stay free.
    """
    return contract_dicts(
        status=st.sampled_from(NON_GRANTING_STATUSES),
        next_billing_date=past_dates(),
    )


def granting_contracts() -> st.SearchStrategy[dict]:
    """A contract that grants: ACTIVE outright, or paid time still remaining."""
    return st.one_of(
        contract_dicts(status=st.just("ACTIVE")),
        contract_dicts(
            status=st.sampled_from(GRANTING_ON_PAID_TIME),
            next_billing_date=future_dates(),
        ),
    )


@st.composite
def clause_a_plans(draw) -> PayloadPlan:
    """Generate payload plans where bug-condition clause (a) holds by construction.

    ``nodes[0]`` of the first customer record never grants; exactly one granting
    contract is hidden either later in that same ``nodes[]`` list (root cause 1)
    or under a second customer record (root cause 2). Constructing the shape
    rather than filtering for it keeps every example on-target — a plain filter
    over the full domain throws most of its work away and shrinks toward
    uninteresting inputs.
    """
    first = draw(non_granting_contracts())
    visible_extra = draw(st.lists(non_granting_contracts(), min_size=0, max_size=2))
    granting = draw(granting_contracts())
    hide_under_second_record = draw(st.booleans())
    second_record_filler = draw(st.lists(non_granting_contracts(), min_size=0, max_size=2))

    visible = [first, *visible_extra]
    if hide_under_second_record:
        second = [*second_record_filler, granting]
    else:
        # Anywhere after nodes[0], which is all the unfixed parser reads.
        position = draw(st.integers(min_value=1, max_value=len(visible)))
        visible.insert(position, granting)
        second = second_record_filler

    customer_ids = [7_000_200_001]
    pages_by_customer = {customer_ids[0]: [visible]}
    if hide_under_second_record or second:
        customer_ids.append(7_000_200_002)
        pages_by_customer[customer_ids[1]] = [second]

    # Unique, deterministic contract ids: the denial-message tiebreak (clause
    # 2.16) compares contract_id, and duplicates would make it ambiguous.
    for index, node in enumerate(
        node for cid in customer_ids for page in pages_by_customer[cid] for node in page
    ):
        node["id"] = f"gid://shopify/SubscriptionContract/{9_000_020_000 + index}"
        node["lines"]["nodes"][0]["id"] = f"gid://shopify/SubscriptionLine/{9_000_020_000 + index}"

    return PayloadPlan(
        email="clause.a@example.com",
        customer_ids=customer_ids,
        pages_by_customer=pages_by_customer,
        fallback_status_by_customer={
            cid: draw(st.sampled_from(NON_ACTIVE_FALLBACK_STATUSES)) for cid in customer_ids
        },
    )


def _run_plan(plan: PayloadPlan) -> Dict[str, Any]:
    with harness(
        **plan.router_kwargs(),
        bypass_emails="",
        known_passwords={plan.email: KNOWN_PASSWORD},
    ) as h:
        return h.login(plan.email, KNOWN_PASSWORD, DEFAULT_CLIENT_IP)


def _plan_evidence(plan: PayloadPlan) -> str:
    def describe(node: dict) -> str:
        return (
            f"{node['id'].rsplit('/', 1)[-1]}:{node.get('status')!r}"
            f" created={node.get('createdAt')} next={node.get('nextBillingDate')}"
            f" grants={oracle_contract_grants(node)}"
        )

    return (
        f"records={plan.customer_ids} "
        f"nodes[0]={describe(plan.first_contract) if plan.first_contract else None} "
        f"all_contracts=[{'; '.join(describe(n) for n in plan.all_contracts)}] "
        f"fallback={plan.fallback_status_by_customer}"
    )


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(clause_a_plans())
def test_any_granting_contract_grants_access_scoped(plan):
    """Property 1 over generated clause-(a) inputs: a hidden granting contract wins.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.8, 2.1, 2.2, 2.3, 2.10**
    """
    assert clause_a_holds(plan.all_contracts, plan.first_contract), (
        "generator invariant broken: clause (a) must hold for every example"
    )
    assert_grants_access(_run_plan(plan), evidence=_plan_evidence(plan))


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(payload_plans(min_pages=1, max_pages=1))
def test_any_granting_contract_grants_access_broad(plan):
    """Property 1 over the full contract domain, filtered to clause (a).

    Same assertion as the scoped property, reached from the unconstrained
    strategy: statuses over ``{ACTIVE, PAUSED, CANCELLED, EXPIRED, junk, None}``,
    ``nextBillingDate`` over ``{past, future, null}``, anchors past and future,
    intervals over ``{DAY, WEEK, MONTH, YEAR, unrecognized, absent}``, and
    ``intervalCount`` 1..12, distributed across 1-3 customer records. This is the
    pass that would catch a granting combination the scoped generator does not
    think to build — including grants derived from ``createdAt`` + interval
    rather than from ``nextBillingDate``.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.8, 2.1, 2.2, 2.3, 2.5, 2.10, 2.12**
    """
    assume(clause_a_holds(plan.all_contracts, plan.first_contract))
    assert_grants_access(_run_plan(plan), evidence=_plan_evidence(plan))
