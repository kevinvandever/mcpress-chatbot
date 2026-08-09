"""Preservation property tests — Property 2: Non-Bug Inputs Behave Identically.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10,
3.11, 3.12, 3.13**

Spec: ``.kiro/specs/subscription-multi-contract-access/`` (bugfix.md, design.md,
Task 7 in tasks.md).

Property 2 (design.md, "Correctness Properties")::

    FOR ALL X WHERE NOT isBugCondition(X) DO
      ASSERT login(X) = login'(X)
    END FOR

``login()`` and ``refresh()`` are driven in-process through the Task 4 harness,
with payloads injected at the ``_appstle_get()`` seam (Task 3) and the clock
pinned to ``FIXTURE_NOW`` (2026-08-09T01:31:12Z). Every assertion is made on the
returned ``status_code`` and ``body`` — never on parser internals, which is how
the original bug shipped past a green suite (clause 1.12).

This suite is expected to **PASS on unfixed code**: the goldens were recorded
from the unfixed code, so a red result here means the case or the harness is
wrong, not the production code.


How the goldens were generated
------------------------------

``tests/fixtures/appstle/goldens/preservation_baseline.json`` was recorded
**mechanically from the UNFIXED** ``backend/subscription_auth.py`` by running it,
never transcribed by hand. Every entry is the literal
``(status_code, normalized_body)`` that ``login()`` / ``refresh()`` returned,
plus the token's decoded claims with ``iat``/``exp`` reduced to
``exp_minus_iat_seconds`` (``normalize_body()`` collapses ``token`` to its claim
key set, because a fresh JWT string differs on every call).

Recorded with::

    python3 -m tests.test_subscription_preservation_properties --record

To regenerate: check out the pre-fix revision of
``backend/subscription_auth.py`` (the ``_meta.git_commit`` in the golden file
records the revision the current baseline came from), then run the command
above. The recorder **refuses to run** once the fixed decision layer is present
(it checks for ``decide_access``), because Task 10.3 must re-assert the same
goldens rather than re-record them — re-recording after the fix would turn this
suite into a tautology.

Two case families are recorded, both deterministic:

* **Named cases** — the fourteen preserved clauses from the task list, each with
  a stable ``case_id`` (see :data:`NAMED_CASES`).
* **A generated corpus** — :data:`CORPUS_SIZE` cases drawn by
  ``random.Random(CORPUS_SEED)`` over the same axes as the harness's Hypothesis
  strategies (status over ``{ACTIVE, PAUSED, CANCELLED, EXPIRED, junk, None}``,
  ``nextBillingDate`` over ``{past, future, null}``, anchors past/future/null,
  intervals over ``{DAY, WEEK, MONTH, YEAR, unrecognized, absent}``,
  ``intervalCount`` 1..12, distributed across 1-3 customer records and 1-2
  pages), filtered to non-bug inputs. A seeded ``Random`` rather than Hypothesis
  is deliberate: golden comparison needs the *same* inputs before and after the
  fix, and Hypothesis's example stream is not a stable key. Each corpus case
  carries a ``fingerprint`` (SHA-256 of its canonical payload plan) that is
  re-verified on every run, so generator drift fails loudly instead of silently
  comparing a golden to a different input.


Which inputs are excluded, and why
----------------------------------

An input is a preservation input only when all three ``isBugCondition`` clauses
are false **and** the legacy and fixed decisions agree:

* clause (a) ``isMultiContractBug`` — some contract grants, ``nodes[0]`` of the
  first customer record does not;
* clause (b) ``isDecisionRuleBug`` — the new rule changes the verdict on the very
  contract the unfixed parser reads (CANCELLED with paid time; null
  ``nextBillingDate`` with a derivable ``paid_through``);
* clause (c) ``isDenialMessageBug`` — all denied, and the newest contract's
  status differs from ``nodes[0]``'s.

The three named **Preservation Exceptions** (2.3 / 1.7, 2.6 / 1.6, 2.16 / 1.14)
are therefore excluded from Property 2 by construction, and are asserted
separately at the bottom of this module **with their intended NEW values**, so no
golden ever encodes behavior the fix deliberately changes. Those three
assertions failed on unfixed code and carried ``xfail(strict=True)`` until Task
9.5 moved ``login()``'s step 4 onto ``decide_access()``; all three XPASSed at
that point, so the markers were removed and each is now a plain assertion that
must hold for good.

**Discovered fourth exclusion, not named in the spec.** Requiring the legacy and
fixed decisions to agree is a strictly stronger filter than clauses (a)-(c), and
it has to be, because a literal reading of the three clauses admits inputs whose
behavior the fix legitimately changes:

    A customer whose ``productSubscriberStatus`` is ``EXPIRED``, ``None``, or an
    unrecognized value, who also has one non-granting contract in ``nodes[]``:

    * unfixed: the five-scenario ladder falls to its ``else`` branch → **200 /
      ``"free"``**;
    * fixed: contracts exist and none grant → **403** with the newest contract's
      denial message.

    Clause (a) is false (nothing grants), clause (b) is false under the
    "granted active access" reading of ``legacyFiveScenarioGrants``, and clause
    (c) is false for a single contract (newest *is* ``nodes[0]``). The mirror
    image also exists: ``productSubscriberStatus`` null with a **granting**
    ``nodes[0]`` moves 200 / ``"free"`` → 200 / ``"active"``.

Both shapes are excluded here rather than recorded, since a golden for either
would encode behavior that Task 10.3 is going to change and would fail that
task for the wrong reason. This is reported back as a spec gap: clause (b) of
``isBugCondition`` in bugfix.md / design.md arguably needs to compare full
legacy-vs-fixed *outcomes* (granted-active / free-tier / denied-with-message)
rather than a single "grants" boolean.

Two further notes on scope:

* Clause (a) can hold while behavior does *not* change (``productSubscriberStatus``
  ACTIVE with a non-granting ``nodes[0]`` returns 200 / ``"active"`` either way).
  Those inputs are excluded from this suite anyway, per the spec's framing, and
  they are covered by Property 1 in ``tests/test_subscription_bug_condition.py``.
* Per design **Finding 4** the fix will not follow contract pages (Task 9.3 is
  detection-plus-ERROR-log only). Corpus cases are therefore filtered so the
  legacy decision agrees with the fixed decision **both** over all generated
  contracts and over only the contracts on page 1 of each record, which keeps
  each golden valid whether or not page-following is added later.

Clause 3.14 (free-tier exhaustion still shows the frontend subscription prompt)
is a frontend/usage-gate behavior with no ``login()`` / ``refresh()`` surface, so
it is verified on staging in Task 11 rather than here.


Run offline
-----------

::

    python3 -m pytest tests/test_subscription_preservation_properties.py -q

No network, no database, no Railway, no Appstle credentials.


OBSERVED RESULT on UNFIXED code
-------------------------------

``python3 -m pytest tests/test_subscription_preservation_properties.py -q``
→ **143 passed, 3 xfailed** in ~0.5s (after Task 9.5: **146 passed**, the three
exceptions now asserting their intended new values). Property 2 holds on every
recorded case:
24 named cases and 100 corpus cases (login *and* refresh for each), plus the
corpus invariants and the clause-level assertions.

The three Preservation Exceptions fail exactly as the spec predicts. Under
``--runxfail``:

1. 2.3 / 1.7 — CANCELLED contract, ``nextBillingDate`` ``FIXTURE_NOW`` + 21 days::

       expected 200, got 403 error='Your subscription has been cancelled. Resubscribe to continue.'

2. 2.6 / 1.6 — PAUSED, ``nextBillingDate`` null, ``createdAt`` 2026-08-01 + MONTH × 1
   (22 days in the future)::

       expected 200, got 403 error='Your subscription has expired. Resubscribe to continue.'

3. 2.16 / 1.14 — newest contract CANCELLED (created 2026-06-30), ``nodes[0]``
   PAUSED-expired (created 2026-04-11)::

       expected 'Your subscription has been cancelled. Resubscribe to continue.'
       got      'Your subscription has expired. Resubscribe to continue.'

**Recorded while writing case 3: the fixture alone does not reach the exception.**
``denial_newest_cancelled_older_paused.json`` ships with customer-level
``productSubscriberStatus`` CANCELLED, and the unfixed ladder reads that field
rather than ``nodes[0]``, so it already emits the cancelled copy and the case
XPASSed — passing while proving nothing, which is the failure mode this whole
spec exists to avoid. The test overrides the customer-level status to PAUSED so
the label disagrees with the newest contract, which is the situation clause 1.14
actually describes. Worth noting for Property 8 in the fix-checking suite, which
consumes the same fixture.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest
from dateutil.relativedelta import relativedelta

from tests.subscription_harness import (
    APPSTLE_API_URL,
    CONTRACT_STATUSES,
    DEFAULT_CLIENT_IP,
    FIXTURE_DIR,
    FIXTURE_NOW,
    INTERVAL_UNITS,
    KNOWN_PASSWORD,
    PayloadPlan,
    WEAK_PASSWORD,
    WRONG_PASSWORD,
    appstle_http_error,
    appstle_malformed_json,
    appstle_timeout,
    at_offset,
    build_contract_node,
    build_step2_payload,
    decode_token_claims,
    harness,
    load_fixture,
    normalize_body,
    step1_payload,
)

# ---------------------------------------------------------------------------
# Golden file location and recorder entry point
# ---------------------------------------------------------------------------

GOLDEN_DIR = FIXTURE_DIR / "goldens"
GOLDEN_PATH = GOLDEN_DIR / "preservation_baseline.json"

RECORD_COMMAND = "python3 -m tests.test_subscription_preservation_properties --record"

# ---------------------------------------------------------------------------
# Fixture coordinates (see tests/fixtures/appstle/README.md)
# ---------------------------------------------------------------------------

ACTIVE_EMAIL = "renewed.monthly@example.com"
ACTIVE_CUSTOMER_ID = 2788845447

LAPSED_EMAIL = "lapsed.thirtyday@example.com"
LAPSED_CUSTOMER_ID = 3289420039

DUNNING_EMAIL = "dunning@example.com"
DUNNING_CUSTOMER_ID = 7000000011

EMPTY_NODES_EMAIL = "empty.nodes@example.com"
EMPTY_NODES_CUSTOMER_ID = 7000000016

MISSING_STATUS_EMAIL = "missing.status@example.com"
MISSING_STATUS_CUSTOMER_ID = 7000000017

NO_RECORD_EMAIL = "no.subscription@example.com"
NEW_USER_EMAIL = "brand.new@example.com"
BYPASS_EMAIL = "bypass.user@example.com"
MULTI_EXPIRED_EMAIL = "both.expired@example.com"
MULTI_EXPIRED_CUSTOMER_ID = 7000000031

# Preservation-exception fixtures (asserted separately, never recorded)
CANCELLED_PAID_EMAIL = "cancelled.paid@example.com"
CANCELLED_PAID_CUSTOMER_ID = 7000000021
DERIVABLE_EMAIL = "paused.derivable@example.com"
DERIVABLE_CUSTOMER_ID = 7000000012
DENIAL_NEWEST_EMAIL = "denial.newest@example.com"
DENIAL_NEWEST_CUSTOMER_ID = 7000000015

# ---------------------------------------------------------------------------
# Denial copy the unfixed code emits today (clause 2.21 keeps these byte-identical)
# ---------------------------------------------------------------------------

EXPIRED_DENIAL = "Your subscription has expired. Resubscribe to continue."
CANCELLED_DENIAL = "Your subscription has been cancelled. Resubscribe to continue."
DEFAULT_DENIAL = "No subscription found"

INVALID_CREDENTIALS = "Invalid email or password"
RATE_LIMITED = "Too many login attempts. Please try again later."
SERVICE_UNAVAILABLE = "Subscription service temporarily unavailable"

EXPECTED_DENIAL_MESSAGES = {
    "ACTIVE": EXPIRED_DENIAL,   # pathological: label ACTIVE, contract did not grant
    "EXPIRED": EXPIRED_DENIAL,
    "PAUSED": EXPIRED_DENIAL,
    "CANCELLED": CANCELLED_DENIAL,
}

TOKEN_CLAIM_KEYS = ["exp", "iat", "sub", "subscription_expires_at", "subscription_status"]
TOKEN_EXPIRY_SECONDS = 3600


def denial_message_for(status: Optional[str]) -> str:
    """``_get_denial_message(status)`` as clauses 2.17 + 2.21 require it to read."""
    if not status:
        return DEFAULT_DENIAL
    return EXPECTED_DENIAL_MESSAGES.get(status.upper(), DEFAULT_DENIAL)


def normalized_status_for(status: Optional[str]) -> str:
    """``_normalize_status(status)`` — unchanged by this fix, transcribed for the oracle."""
    if not status:
        return "not_found"
    return {
        "ACTIVE": "active",
        "CANCELLED": "cancelled",
        "EXPIRED": "expired",
        "PAUSED": "paused",
    }.get(status.upper(), "not_found")


# ---------------------------------------------------------------------------
# Test-side oracles: the legacy ladder, the fixed rule, and the bug clauses
# ---------------------------------------------------------------------------
#
# Both decisions are transcribed from the spec (the legacy ladder from the code
# in ``login()`` step 4, the fixed rule from design.md's ``contractGrants`` /
# ``paidThrough`` / ``decide_access``) and evaluated over the generated payload
# dicts. Nothing is imported from the decision layer: half of it does not exist
# yet, and the half that does is the thing under test.

GRANTING_ON_PAID_TIME = {"PAUSED", "CANCELLED"}

_INTERVALS = {"DAY": "days", "WEEK": "weeks", "MONTH": "months", "YEAR": "years"}


@dataclass(frozen=True)
class Outcome:
    """The observable part of an access decision, as ``login()`` reports it."""

    status_code: int
    subscription_status: Optional[str]
    error: Optional[str]


GRANTED_ACTIVE = Outcome(200, "active", None)
GRANTED_FREE = Outcome(200, "free", None)


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
    if status_upper in GRANTING_ON_PAID_TIME:
        paid_through = oracle_paid_through(node)
        return paid_through is not None and paid_through > FIXTURE_NOW
    return False


def oracle_newest(nodes: List[dict]) -> dict:
    """``max(contracts, key=(created_at, contract_id))``, null ``createdAt`` last."""

    def key(node: dict) -> Tuple[int, str, str]:
        created = _parse_iso(node.get("createdAt"))
        return (
            0 if created is None else 1,
            "" if created is None else created.isoformat(),
            str(node.get("id") or ""),
        )

    return max(nodes, key=key)


def legacy_outcome(product_subscriber_status: Optional[str], first_contract: Optional[dict]) -> Outcome:
    """The UNFIXED five-scenario ladder, over exactly what F reads.

    F reads the customer-level ``productSubscriberStatus`` of the **first**
    customer record and ``nodes[0].nextBillingDate`` of that record's first page.
    A missing or unrecognized status falls to the ``else`` branch and grants free
    tier — including the tag-fallback path, whose verdict never reaches
    ``product_subscriber_status`` (clause 1.12), so it lands here too.
    """
    status_upper = (product_subscriber_status or "").upper()
    next_billing = _parse_iso(first_contract.get("nextBillingDate")) if first_contract else None

    if status_upper == "ACTIVE":
        return GRANTED_ACTIVE
    if status_upper == "PAUSED":
        if next_billing is not None and next_billing > FIXTURE_NOW:
            return GRANTED_ACTIVE
        return Outcome(403, "paused", EXPIRED_DENIAL)
    if status_upper == "CANCELLED":
        return Outcome(403, "cancelled", CANCELLED_DENIAL)
    return GRANTED_FREE


def aggregate_fallback_status(statuses: List[Optional[str]]) -> Optional[str]:
    """``ACTIVE > PAUSED > CANCELLED > other > None`` (design change 11)."""
    upper = [(s or "").upper() for s in statuses]
    for candidate in ("ACTIVE", "PAUSED", "CANCELLED"):
        if candidate in upper:
            return candidate
    for original, up in zip(statuses, upper):
        if up:
            return original
    return None


def fixed_outcome(contracts: List[dict], fallback_statuses: List[Optional[str]]) -> Outcome:
    """``decide_access()`` from design.md change 6, as an outcome."""
    if any(oracle_contract_grants(node) for node in contracts):
        return GRANTED_ACTIVE

    if contracts:
        newest = oracle_newest(contracts)
        status = newest.get("status")
        return Outcome(403, normalized_status_for(status), denial_message_for(status))

    fallback = (aggregate_fallback_status(fallback_statuses) or "").upper()
    if fallback == "ACTIVE":
        return GRANTED_ACTIVE
    if fallback in ("PAUSED", "CANCELLED"):
        return Outcome(403, normalized_status_for(fallback), denial_message_for(fallback))
    return GRANTED_FREE


# -- the three isBugCondition clauses ---------------------------------------

def clause_a_multi_contract(all_contracts: List[dict], first_contract: Optional[dict]) -> bool:
    """``isMultiContractBug``: some contract grants, ``nodes[0]`` does not."""
    any_grants = any(oracle_contract_grants(node) for node in all_contracts)
    first_grants = first_contract is not None and oracle_contract_grants(first_contract)
    return any_grants and not first_grants


def clause_b_decision_rule(
    first_contract: Optional[dict],
    product_subscriber_status: Optional[str],
) -> bool:
    """``isDecisionRuleBug``: the new rule flips the verdict on the contract F reads.

    ``legacyFiveScenarioGrants`` is read as "did the legacy ladder grant *active*
    access", which is the reading that makes CANCELLED-with-paid-time (2.3) and
    PAUSED-with-derivable-``paid_through`` (2.6) land here as the spec intends.
    The free-tier-versus-denied divergence that this reading leaves uncovered is
    caught by :func:`outcomes_agree` — see the module docstring.
    """
    if first_contract is None:
        return False
    legacy_grants_active = legacy_outcome(product_subscriber_status, first_contract) == GRANTED_ACTIVE
    return oracle_contract_grants(first_contract) != legacy_grants_active


def clause_c_denial_message(all_contracts: List[dict], first_contract: Optional[dict]) -> bool:
    """``isDenialMessageBug``: all denied and the newest status ≠ ``nodes[0]``'s."""
    if not all_contracts or first_contract is None:
        return False
    if any(oracle_contract_grants(node) for node in all_contracts):
        return False
    newest = oracle_newest(all_contracts)
    return str(newest.get("status") or "").upper() != str(first_contract.get("status") or "").upper()


def outcomes_agree(plan: PayloadPlan) -> bool:
    """Does the fix leave this input's decision untouched?

    Checked against the fixed rule twice: over every generated contract, and over
    only the contracts on page 1 of each record. Design **Finding 4** says the fix
    detects but does not follow further pages, so requiring both keeps a recorded
    golden valid either way.
    """
    first_record = plan.customer_ids[0] if plan.customer_ids else None
    first_pss = plan.fallback_status_by_customer.get(first_record) if first_record else None
    legacy = legacy_outcome(first_pss, plan.first_contract)

    fallbacks = [plan.fallback_status_by_customer[cid] for cid in plan.customer_ids]
    reachable = [
        node
        for cid in plan.customer_ids
        for node in (plan.pages_by_customer[cid][0] if plan.pages_by_customer[cid] else [])
    ]
    return (
        legacy == fixed_outcome(plan.all_contracts, fallbacks)
        and legacy == fixed_outcome(reachable, fallbacks)
    )


def is_preservation_input(plan: PayloadPlan) -> bool:
    """``NOT isBugCondition(X)``, plus the discovered fourth exclusion."""
    first_record = plan.customer_ids[0] if plan.customer_ids else None
    first_pss = plan.fallback_status_by_customer.get(first_record) if first_record else None
    return (
        not clause_a_multi_contract(plan.all_contracts, plan.first_contract)
        and not clause_b_decision_rule(plan.first_contract, first_pss)
        and not clause_c_denial_message(plan.all_contracts, plan.first_contract)
        and outcomes_agree(plan)
    )


# ---------------------------------------------------------------------------
# Observation: what gets recorded and compared
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """One case's live result, plus the golden-comparable record derived from it."""

    result: Dict[str, Any]
    record: Dict[str, Any]
    requested_urls: List[str] = field(default_factory=list)

    @property
    def status_code(self) -> int:
        return self.result["status_code"]

    @property
    def body(self) -> Dict[str, Any]:
        return self.result["body"]

    @property
    def token_claims(self) -> Optional[Dict[str, Any]]:
        return self.record.get("token_claims")


def observe(result: Dict[str, Any], *, requested_urls: Optional[List[str]] = None) -> Observation:
    """Reduce a ``login()`` / ``refresh()`` result to its comparable form.

    ``normalize_body()`` collapses ``token`` to its decoded claim key set, since a
    fresh JWT differs on every call. The claims themselves are recorded
    separately with ``iat``/``exp`` reduced to ``exp_minus_iat_seconds`` — that is
    what makes clause 3.12 (claim shape and 1-hour expiry), clause 3.13
    (``subscription_expires_at`` null) and clause 3.8 (status preserved from the
    old claims) checkable from a golden rather than by eye.
    """
    record: Dict[str, Any] = {
        "status_code": result["status_code"],
        "body": normalize_body(result["body"]),
    }

    body = result["body"]
    token = body.get("token") if isinstance(body, dict) else None
    if isinstance(token, str) and token:
        claims = decode_token_claims(token)
        record["token_claims"] = {
            "claim_keys": sorted(claims.keys()),
            "sub": claims.get("sub"),
            "subscription_status": claims.get("subscription_status"),
            "subscription_expires_at": claims.get("subscription_expires_at"),
            "exp_minus_iat_seconds": int(claims["exp"]) - int(claims["iat"]),
        }

    return Observation(result=result, record=record, requested_urls=list(requested_urls or []))


def single_record_step1(customer_id: int, email: str) -> List[dict]:
    return step1_payload([customer_id], email=email)


# ===========================================================================
# Named preservation cases (the fourteen preserved clauses)
# ===========================================================================
#
# Each function builds its own harness, drives login() or refresh() once, and
# returns an Observation. They are registered in NAMED_CASES and are the unit
# both the recorder and the golden comparison work on, so the recorded baseline
# and the asserted behavior can never come from different code paths.


def case_login_active_subscriber() -> Observation:
    """3.1 — the real renewed monthly subscriber: ACTIVE contract → 200 / ``"active"``."""
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, ACTIVE_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(ACTIVE_EMAIL, KNOWN_PASSWORD)
        return observe(result, requested_urls=h.router.urls)


def case_login_active_contract_past_billing_dunning() -> Observation:
    """3.1 / 2.2 — ACTIVE with ``nextBillingDate`` 5 days past: the dunning grace window.

    Granted before the fix (the ladder branches on the customer-level ACTIVE) and
    after it (the per-contract ACTIVE short-circuit). Recorded so the grace window
    cannot be closed by accident.
    """
    with harness(
        step1=single_record_step1(DUNNING_CUSTOMER_ID, DUNNING_EMAIL),
        step2={DUNNING_CUSTOMER_ID: load_fixture("active_past_billing_dunning")},
        bypass_emails="",
        known_passwords={DUNNING_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(DUNNING_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def case_login_no_appstle_record() -> Observation:
    """3.2 — step 1 returns no ``customerId`` at all → 200 / ``"free"``."""
    with harness(
        step1=load_fixture("no_subscription"),
        step2={},
        bypass_emails="",
        known_passwords={NO_RECORD_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(NO_RECORD_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def case_login_all_contracts_expired() -> Observation:
    """3.3 — the real lapsed 30-day purchaser: PAUSED, billing date past → 403."""
    with harness(
        step1=single_record_step1(LAPSED_CUSTOMER_ID, LAPSED_EMAIL),
        step2={LAPSED_CUSTOMER_ID: load_fixture("lapsed_paused_subscriber")},
        bypass_emails="",
        known_passwords={LAPSED_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(LAPSED_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def _both_expired_nodes() -> List[dict]:
    """Two PAUSED contracts, both with billing dates in the past.

    Both statuses are PAUSED on purpose: clause (c) of the bug condition fires
    when the newest contract's status differs from ``nodes[0]``'s, and that input
    is a Preservation Exception. Equal statuses keep this case inside Property 2,
    where "every contract expired" belongs (3.3).
    """
    return [
        build_contract_node(
            contract_id=9_000_031_001,
            status="PAUSED",
            created_at=at_offset(days=-200).strftime("%Y-%m-%dT%H:%M:%SZ"),
            next_billing_date=at_offset(days=-170).strftime("%Y-%m-%dT%H:%M:%SZ"),
            interval="DAY",
            interval_count=30,
        ),
        build_contract_node(
            contract_id=9_000_031_002,
            status="PAUSED",
            created_at=at_offset(days=-60).strftime("%Y-%m-%dT%H:%M:%SZ"),
            next_billing_date=at_offset(days=-30).strftime("%Y-%m-%dT%H:%M:%SZ"),
            interval="DAY",
            interval_count=30,
        ),
    ]


def case_login_all_contracts_expired_multi_contract() -> Observation:
    """3.3 — two contracts, both PAUSED and both expired → 403, same copy."""
    with harness(
        step1=single_record_step1(MULTI_EXPIRED_CUSTOMER_ID, MULTI_EXPIRED_EMAIL),
        step2={
            MULTI_EXPIRED_CUSTOMER_ID: build_step2_payload(
                customer_id=MULTI_EXPIRED_CUSTOMER_ID,
                nodes=_both_expired_nodes(),
                product_subscriber_status="PAUSED",
            )
        },
        bypass_emails="",
        known_passwords={MULTI_EXPIRED_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(MULTI_EXPIRED_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def _empty_nodes_case(product_subscriber_status: Optional[str]) -> Observation:
    """2.12 — empty ``nodes[]``, decided by the customer-level status."""
    payload = load_fixture("empty_nodes")
    payload["productSubscriberStatus"] = product_subscriber_status
    with harness(
        step1=single_record_step1(EMPTY_NODES_CUSTOMER_ID, EMPTY_NODES_EMAIL),
        step2={EMPTY_NODES_CUSTOMER_ID: payload},
        bypass_emails="",
        known_passwords={EMPTY_NODES_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(EMPTY_NODES_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def case_login_empty_nodes_status_active() -> Observation:
    """2.12 / 3.1 — empty ``nodes[]`` + ACTIVE → 200 / ``"active"``."""
    return _empty_nodes_case("ACTIVE")


def case_login_empty_nodes_status_paused() -> Observation:
    """2.12 — empty ``nodes[]`` + PAUSED → 403 with the expired copy."""
    return _empty_nodes_case("PAUSED")


def case_login_empty_nodes_status_cancelled() -> Observation:
    """2.12 — empty ``nodes[]`` + CANCELLED → 403 with the cancelled copy."""
    return _empty_nodes_case("CANCELLED")


def case_login_empty_nodes_status_missing() -> Observation:
    """2.12 / 3.2 / 2.19 — ``productSubscriberStatus`` absent → 200 / ``"free"``.

    Requirement 2.19 makes the log record loud after the fix; the response is
    preserved either way, and that is what this golden pins. The ERROR record
    itself is Property 13's assertion, in the fix-checking suite.
    """
    with harness(
        step1=single_record_step1(MISSING_STATUS_CUSTOMER_ID, MISSING_STATUS_EMAIL),
        step2={MISSING_STATUS_CUSTOMER_ID: load_fixture("missing_product_subscriber_status")},
        bypass_emails="",
        known_passwords={MISSING_STATUS_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(MISSING_STATUS_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def case_login_wrong_password_with_active_subscription() -> Observation:
    """3.4 — wrong password, ACTIVE subscription → 401, regardless of subscription."""
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, ACTIVE_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(ACTIVE_EMAIL, WRONG_PASSWORD), requested_urls=h.router.urls)


def _rate_limit_attempts(count: int) -> Observation:
    """3.5 — ``count`` failed attempts from one IP; the last one is recorded.

    The attempts must fail: a successful login calls ``rate_limiter.reset()``
    (step 8), so a run of successes would never reach the limit. Wrong passwords
    keep every attempt on the counter, which is how the sixth attempt reaches 429.
    """
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, ACTIVE_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result: Dict[str, Any] = {}
        for _ in range(count):
            result = h.login(ACTIVE_EMAIL, WRONG_PASSWORD, DEFAULT_CLIENT_IP)
        return observe(result, requested_urls=h.router.urls)


def case_login_rate_limit_fifth_attempt() -> Observation:
    """3.5 — the fifth attempt is still inside the limit → 401, not 429."""
    return _rate_limit_attempts(5)


def case_login_rate_limit_sixth_attempt() -> Observation:
    """3.5 — the sixth attempt from one IP → 429."""
    return _rate_limit_attempts(6)


def case_login_missing_appstle_config() -> Observation:
    """3.6 — blank ``APPSTLE_API_URL`` / ``APPSTLE_API_KEY`` → 503, no Appstle call."""
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, ACTIVE_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
        missing_config=True,
    ) as h:
        return observe(h.login(ACTIVE_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def _appstle_failure_login(failure) -> Observation:
    """3.7 — Appstle fails at step 1; login falls through to free tier."""
    with harness(
        step1=failure,
        step2={},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(ACTIVE_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def case_login_appstle_timeout() -> Observation:
    """3.7 — Appstle timeout at login → 200 / ``"free"``, never a block."""
    return _appstle_failure_login(appstle_timeout())


def case_login_appstle_http_500() -> Observation:
    """3.7 — Appstle HTTP 500 at login → 200 / ``"free"``."""
    return _appstle_failure_login(appstle_http_error(500))


def case_login_appstle_malformed_json() -> Observation:
    """3.7 — unparseable Appstle body at login → 200 / ``"free"``."""
    return _appstle_failure_login(appstle_malformed_json())


def _refresh_with_appstle_down(claim_status: str) -> Observation:
    """3.8 — Appstle unavailable at refresh; the JWT's status must survive."""
    with harness(
        step1=appstle_timeout(),
        step2={},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        token = h.token_for(ACTIVE_EMAIL, claim_status)
        return observe(h.refresh(token), requested_urls=h.router.urls)


def case_refresh_appstle_down_preserves_active_claim() -> Observation:
    """3.8 — claims say ``"active"``, Appstle is down → the new token still says so."""
    return _refresh_with_appstle_down("active")


def case_refresh_appstle_down_preserves_free_claim() -> Observation:
    """3.8 — claims say ``"free"``, Appstle is down → the new token still says so."""
    return _refresh_with_appstle_down("free")


def case_login_new_user_weak_password() -> Observation:
    """3.9 — unknown email with a weak password → 400 plus ``failed_rules``."""
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, NEW_USER_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={},
    ) as h:
        return observe(h.login(NEW_USER_EMAIL, WEAK_PASSWORD), requested_urls=h.router.urls)


def case_login_bypass_email() -> Observation:
    """3.10 — a ``BYPASS_EMAILS`` address gets ``"active"`` with no Appstle call.

    The router is armed with an all-expired payload precisely so that any call
    would change the answer; ``requested_urls`` is recorded and asserted empty.
    """
    with harness(
        step1=single_record_step1(LAPSED_CUSTOMER_ID, BYPASS_EMAIL),
        step2={LAPSED_CUSTOMER_ID: load_fixture("lapsed_paused_subscriber")},
        bypass_emails=BYPASS_EMAIL,
        known_passwords={BYPASS_EMAIL: KNOWN_PASSWORD},
    ) as h:
        return observe(h.login(BYPASS_EMAIL, KNOWN_PASSWORD), requested_urls=h.router.urls)


def _refresh_with_age(age: timedelta) -> Observation:
    """3.11 — a token backdated by ``age`` presented to ``refresh()``."""
    with harness(
        step1=single_record_step1(ACTIVE_CUSTOMER_ID, ACTIVE_EMAIL),
        step2={ACTIVE_CUSTOMER_ID: load_fixture("renewed_subscriber")},
        bypass_emails="",
        known_passwords={ACTIVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        token = h.token_for(ACTIVE_EMAIL, "active", age=age)
        return observe(h.refresh(token), requested_urls=h.router.urls)


def case_refresh_two_minutes_expired_within_grace() -> Observation:
    """3.11 — 2 minutes past expiry is inside the 5-minute window → 200."""
    return _refresh_with_age(timedelta(minutes=62))


def case_refresh_ten_minutes_expired_beyond_grace() -> Observation:
    """3.11 — 10 minutes past expiry is beyond the window → 401."""
    return _refresh_with_age(timedelta(minutes=70))


def case_refresh_active_subscriber() -> Observation:
    """3.12 / 3.13 — a plain successful refresh: claim shape and null expiry fields."""
    return _refresh_with_age(timedelta(0))


def case_refresh_all_contracts_expired() -> Observation:
    """3.3 / 3.8 — refresh for the lapsed purchaser → 403 with the expired copy.

    ``refresh()`` carries its own copy of the ladder (clause 1.9), so its denial
    body is recorded separately from ``login()``'s.
    """
    with harness(
        step1=single_record_step1(LAPSED_CUSTOMER_ID, LAPSED_EMAIL),
        step2={LAPSED_CUSTOMER_ID: load_fixture("lapsed_paused_subscriber")},
        bypass_emails="",
        known_passwords={LAPSED_EMAIL: KNOWN_PASSWORD},
    ) as h:
        token = h.token_for(LAPSED_EMAIL, "active")
        return observe(h.refresh(token), requested_urls=h.router.urls)


NAMED_CASES: Dict[str, Callable[[], Observation]] = {
    "login/active_subscriber": case_login_active_subscriber,
    "login/active_contract_past_billing_dunning": case_login_active_contract_past_billing_dunning,
    "login/no_appstle_record": case_login_no_appstle_record,
    "login/all_contracts_expired": case_login_all_contracts_expired,
    "login/all_contracts_expired_multi_contract": case_login_all_contracts_expired_multi_contract,
    "login/empty_nodes_status_active": case_login_empty_nodes_status_active,
    "login/empty_nodes_status_paused": case_login_empty_nodes_status_paused,
    "login/empty_nodes_status_cancelled": case_login_empty_nodes_status_cancelled,
    "login/empty_nodes_status_missing": case_login_empty_nodes_status_missing,
    "login/wrong_password_with_active_subscription": case_login_wrong_password_with_active_subscription,
    "login/rate_limit_fifth_attempt": case_login_rate_limit_fifth_attempt,
    "login/rate_limit_sixth_attempt": case_login_rate_limit_sixth_attempt,
    "login/missing_appstle_config": case_login_missing_appstle_config,
    "login/appstle_timeout": case_login_appstle_timeout,
    "login/appstle_http_500": case_login_appstle_http_500,
    "login/appstle_malformed_json": case_login_appstle_malformed_json,
    "login/new_user_weak_password": case_login_new_user_weak_password,
    "login/bypass_email": case_login_bypass_email,
    "refresh/appstle_down_preserves_active_claim": case_refresh_appstle_down_preserves_active_claim,
    "refresh/appstle_down_preserves_free_claim": case_refresh_appstle_down_preserves_free_claim,
    "refresh/two_minutes_expired_within_grace": case_refresh_two_minutes_expired_within_grace,
    "refresh/ten_minutes_expired_beyond_grace": case_refresh_ten_minutes_expired_beyond_grace,
    "refresh/active_subscriber": case_refresh_active_subscriber,
    "refresh/all_contracts_expired": case_refresh_all_contracts_expired,
}


# ===========================================================================
# Generated corpus of non-bug inputs
# ===========================================================================
#
# A seeded random.Random rather than Hypothesis. Golden comparison needs the
# SAME inputs before and after the fix, and Hypothesis's example stream is not a
# stable key — it moves with the version, the database, and the shrinker. A
# seeded Random over the same axes as the harness's strategies gives the same
# combinatorial reach with a reproducible case list, and each case carries a
# fingerprint so drift is caught rather than silently tolerated.

CORPUS_SEED = 20260809          # FIXTURE_NOW's date, for no reason beyond legibility
CORPUS_SIZE = 100
CORPUS_MAX_DRAWS = 40_000       # rejection sampling budget; non-bug inputs are a minority
CORPUS_EMAIL_TEMPLATE = "corpus{index:03d}@example.com"
CORPUS_CUSTOMER_ID_BASE = 7_000_500_000
CORPUS_CONTRACT_ID_BASE = 9_200_000_000

FALLBACK_STATUSES = ("ACTIVE", "PAUSED", "CANCELLED", "EXPIRED", "NOT_A_STATUS", None)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _draw_date(rng: random.Random) -> Optional[str]:
    """``{past, future, null}`` — the three cases that decide paid time."""
    kind = rng.choice(("past", "past", "future", "null"))
    if kind == "null":
        return None
    days = rng.randint(1, 900)
    return _iso(at_offset(days=-days if kind == "past" else days))


def _draw_contract(
    rng: random.Random,
    contract_id: int,
    *,
    status: Optional[str] = None,
    next_billing_date: Optional[str] = None,
    force_next_billing: bool = False,
) -> dict:
    """One contract node over the full generated domain, with optional pinning."""
    return build_contract_node(
        contract_id=contract_id,
        status=rng.choice(CONTRACT_STATUSES) if status is None else status,
        created_at=_draw_date(rng),
        next_billing_date=next_billing_date if force_next_billing else _draw_date(rng),
        interval=rng.choice(INTERVAL_UNITS),
        interval_count=rng.randint(1, 12),
    )


# Strata. Pure rejection sampling from the full domain works but lands ~three
# quarters of its accepted cases on empty ``nodes[]``, because a randomly drawn
# contract set usually *does* change behavior under the fix and gets rejected.
# These shapes aim draws at the four preserved outcomes so the corpus actually
# exercises contract-bearing payloads. They only bias generation — every drawn
# plan still has to pass :func:`is_preservation_input`, which stays authoritative.
CORPUS_SHAPES = (
    "random",
    "random",
    "granting",
    "granting",
    "denied_paused",
    "denied_paused",
    "denied_cancelled",
    "free",
)

_PAUSED_LABELS = ("PAUSED", "paused")
_CANCELLED_LABELS = ("CANCELLED", "cancelled")
_UNRECOGNIZED_FALLBACKS = ("EXPIRED", "NOT_A_STATUS", "", None)


def _draw_shaped_nodes(rng: random.Random, shape: str, index: int) -> Tuple[List[dict], Optional[str]]:
    """Contract nodes plus the customer-level status that goes with ``shape``."""

    def cid(position: int) -> int:
        return CORPUS_CONTRACT_ID_BASE + index * 10 + position

    if shape == "free":
        return [], rng.choice(_UNRECOGNIZED_FALLBACKS)

    if shape == "granting":
        # nodes[0] grants, so the legacy ladder (ACTIVE customer-level status) and
        # the fixed rule (any contract grants) both land on 200 / "active".
        first_grants_via = rng.choice(("active_status", "paid_time"))
        if first_grants_via == "active_status":
            first = _draw_contract(rng, cid(0), status="ACTIVE")
        else:
            first = _draw_contract(
                rng,
                cid(0),
                status=rng.choice(_PAUSED_LABELS + _CANCELLED_LABELS),
                next_billing_date=_iso(at_offset(days=rng.randint(1, 400))),
                force_next_billing=True,
            )
        rest = [_draw_contract(rng, cid(position + 1)) for position in range(rng.randint(0, 3))]
        return [first, *rest], "ACTIVE"

    if shape in ("denied_paused", "denied_cancelled"):
        labels = _PAUSED_LABELS if shape == "denied_paused" else _CANCELLED_LABELS
        fallback = "PAUSED" if shape == "denied_paused" else "CANCELLED"
        nodes = [
            _draw_contract(
                rng,
                cid(position),
                status=rng.choice(labels),
                next_billing_date=_iso(at_offset(days=-rng.randint(1, 400))),
                force_next_billing=True,
            )
            for position in range(rng.randint(1, 4))
        ]
        return nodes, fallback

    return (
        [_draw_contract(rng, cid(position)) for position in range(rng.randint(0, 5))],
        rng.choice(FALLBACK_STATUSES),
    )


def _draw_plan(rng: random.Random, index: int) -> PayloadPlan:
    """Distribute a drawn contract set across 1-3 customer records and 1-2 pages."""
    shape = rng.choice(CORPUS_SHAPES)
    nodes, shaped_fallback = _draw_shaped_nodes(rng, shape, index)
    n_customers = rng.randint(1, 3)
    n_pages = rng.randint(1, 2)

    customer_ids = [CORPUS_CUSTOMER_ID_BASE + index * 10 + offset for offset in range(n_customers)]

    owned: Dict[int, List[dict]] = {cid: [] for cid in customer_ids}
    for position, node in enumerate(nodes):
        owned[customer_ids[position % n_customers]].append(node)

    pages_by_customer: Dict[int, List[List[dict]]] = {}
    for cid, contracts in owned.items():
        pages: List[List[dict]] = [[] for _ in range(n_pages)]
        for position, node in enumerate(contracts):
            pages[position % n_pages].append(node)
        trimmed = [page for page in pages if page]
        pages_by_customer[cid] = trimmed or [[]]

    if shape == "random":
        # Each record draws its own customer-level status, which is what makes the
        # order-independent aggregation in design change 11 observable.
        fallbacks = {cid: rng.choice(FALLBACK_STATUSES) for cid in customer_ids}
    else:
        # A shaped case keeps one status across records, so the legacy ladder's
        # first-record read and the fixed rule's priority aggregation agree.
        fallbacks = {cid: shaped_fallback for cid in customer_ids}

    return PayloadPlan(
        email=CORPUS_EMAIL_TEMPLATE.format(index=index),
        customer_ids=customer_ids,
        pages_by_customer=pages_by_customer,
        fallback_status_by_customer=fallbacks,
    )


def plan_fingerprint(plan: PayloadPlan) -> str:
    """SHA-256 over the plan's canonical form — the golden's drift guard.

    Contract ``id``s are excluded from the digest and the ``customer_id``s are
    normalized to their position, so the fingerprint tracks the *decision-relevant*
    payload rather than the numbering scheme. A change to the axes or the seed
    still moves it, which is the point.
    """
    canonical = {
        "customer_records": [
            {
                "position": position,
                "fallback_status": plan.fallback_status_by_customer[cid],
                "pages": [
                    [
                        {
                            "status": node.get("status"),
                            "createdAt": node.get("createdAt"),
                            "nextBillingDate": node.get("nextBillingDate"),
                            "billingPolicy": node.get("billingPolicy"),
                        }
                        for node in page
                    ]
                    for page in plan.pages_by_customer[cid]
                ],
            }
            for position, cid in enumerate(plan.customer_ids)
        ]
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


_CORPUS_CACHE: Optional[List[PayloadPlan]] = None


def corpus_plans() -> List[PayloadPlan]:
    """The deterministic corpus of non-bug inputs, built once per process.

    Rejection sampling: draw over the full domain, keep the plans
    :func:`is_preservation_input` accepts. Most draws are rejected — a random
    contract set usually *does* change behavior under the fix — so the budget is
    generous. The seed and the budget together make the accepted list a fixed
    function of this module's source, which is what the goldens key on.
    """
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE

    rng = random.Random(CORPUS_SEED)
    accepted: List[PayloadPlan] = []
    for index in range(CORPUS_MAX_DRAWS):
        if len(accepted) >= CORPUS_SIZE:
            break
        plan = _draw_plan(rng, index)
        if is_preservation_input(plan):
            accepted.append(plan)

    if len(accepted) < CORPUS_SIZE:
        raise RuntimeError(
            f"Corpus generation collected only {len(accepted)} of {CORPUS_SIZE} "
            f"non-bug inputs within {CORPUS_MAX_DRAWS} draws. Raise "
            f"CORPUS_MAX_DRAWS or loosen the draw distribution — do NOT loosen "
            f"is_preservation_input(), which is what keeps deliberately-changed "
            f"behavior out of the goldens."
        )

    _CORPUS_CACHE = accepted
    return _CORPUS_CACHE


def corpus_case_id(index: int) -> str:
    return f"corpus/{index:03d}"


def run_corpus_case(plan: PayloadPlan) -> Dict[str, Any]:
    """Drive ``login()`` and then ``refresh()`` for one corpus plan.

    Both callers carry their own copy of the decision ladder today (clause 1.9),
    so both are recorded: a fix that consolidates them onto ``decide_access()``
    must leave each caller's own body shape alone.
    """
    with harness(
        **plan.router_kwargs(),
        bypass_emails="",
        known_passwords={plan.email: KNOWN_PASSWORD},
    ) as h:
        login_result = h.login(plan.email, KNOWN_PASSWORD, DEFAULT_CLIENT_IP)
        login_urls = list(h.router.urls)

        h.router.reset()
        refresh_result = h.refresh(h.token_for(plan.email, "active"))
        refresh_urls = list(h.router.urls)

    return {
        "login": observe(login_result, requested_urls=login_urls).record,
        "refresh": observe(refresh_result, requested_urls=refresh_urls).record,
    }


def corpus_outcome_shape(record: Dict[str, Any]) -> Tuple[int, Optional[str]]:
    body = record.get("body") or {}
    return (record["status_code"], body.get("subscription_status") if isinstance(body, dict) else None)


# ===========================================================================
# Recorder — the only thing that writes the goldens
# ===========================================================================

def _git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:  # pragma: no cover - git absent or not a repo
        return None


FIXED_LAYER_MARKERS = ("decide_access", "_contract_grants", "_paid_through", "ContractView")


def fixed_decision_layer_present() -> bool:
    """Has the Task 8 / 9 decision layer landed in ``backend/subscription_auth.py``?"""
    from backend import subscription_auth

    return any(hasattr(subscription_auth, marker) for marker in FIXED_LAYER_MARKERS)


def record_goldens(path: Path = GOLDEN_PATH, *, force: bool = False) -> Dict[str, Any]:
    """Run every case and write the baseline. Refuses to run on fixed code.

    Task 10.3 re-asserts these goldens; re-recording them after the fix would
    make the preservation property compare the fixed code against itself. The
    guard is why that cannot happen by accident.
    """
    if fixed_decision_layer_present() and not force:
        raise SystemExit(
            "Refusing to record: backend/subscription_auth.py already exposes the "
            f"fixed decision layer ({', '.join(FIXED_LAYER_MARKERS)}). The "
            "preservation goldens MUST come from the unfixed code — Task 10.3 "
            "re-asserts them, it does not re-record them. Check out the pre-fix "
            "revision (see _meta.git_commit in the existing golden file) and run "
            "this again, or pass force=True if you genuinely mean to rebaseline."
        )

    named: Dict[str, Any] = {}
    for case_id in sorted(NAMED_CASES):
        named[case_id] = NAMED_CASES[case_id]().record

    corpus: List[Dict[str, Any]] = []
    for index, plan in enumerate(corpus_plans()):
        entry = {"case_id": corpus_case_id(index), "fingerprint": plan_fingerprint(plan)}
        entry.update(run_corpus_case(plan))
        corpus.append(entry)

    document = {
        "_meta": {
            "what": (
                "Preservation baseline for the subscription-multi-contract-access "
                "bugfix (Property 2). Each entry is the literal (status_code, "
                "normalized_body) that login()/refresh() returned, plus the token's "
                "decoded claims with iat/exp reduced to exp_minus_iat_seconds."
            ),
            "recorded_from": "UNFIXED backend/subscription_auth.py",
            "fixed_decision_layer_present": fixed_decision_layer_present(),
            "git_commit": _git_commit(),
            "recorded_by": RECORD_COMMAND,
            "regenerate": (
                "Check out the pre-fix revision of backend/subscription_auth.py, then run "
                f"{RECORD_COMMAND}. Do NOT re-record after the fix: Task 10.3 re-asserts "
                "these same goldens."
            ),
            "fixture_now": _iso(FIXTURE_NOW),
            "clock_seam": "backend.subscription_auth._utcnow monkeypatched to fixture_now()",
            "appstle_base_url": APPSTLE_API_URL,
            "token_normalization": (
                "body.token -> {'claim_keys': [...]}; claims recorded separately with "
                "exp_minus_iat_seconds instead of the moving iat/exp pair"
            ),
            "corpus_seed": CORPUS_SEED,
            "corpus_size": len(corpus),
            "corpus_draw_budget": CORPUS_MAX_DRAWS,
            "named_case_count": len(named),
            "excluded": (
                "The three Preservation Exceptions (2.3/1.7, 2.6/1.6, 2.16/1.14) are "
                "deliberately absent — they are asserted separately with their intended "
                "NEW values. Inputs where the legacy and fixed decisions disagree for any "
                "other reason are excluded too; see the module docstring."
            ),
        },
        "named": named,
        "corpus": corpus,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=False)
        handle.write("\n")
    return document


# ===========================================================================
# Golden loading
# ===========================================================================

def load_goldens(path: Path = GOLDEN_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise AssertionError(
            f"Preservation goldens are missing at {path}. They are recorded from the "
            f"UNFIXED code with:\n    {RECORD_COMMAND}"
        )
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def goldens() -> Dict[str, Any]:
    return load_goldens()


def _diff(label: str, observed: Any, golden: Any) -> str:
    return (
        f"{label} drifted from the recorded pre-fix baseline.\n"
        f"  observed: {json.dumps(observed, sort_keys=True)}\n"
        f"  golden:   {json.dumps(golden, sort_keys=True)}\n"
        f"The golden is the behavior of the UNFIXED code, recorded mechanically. "
        f"Do not re-record it to make this pass."
    )


# ===========================================================================
# Property 2 — Preservation
# ===========================================================================

@pytest.mark.parametrize("case_id", sorted(NAMED_CASES))
def test_property_2_named_case_matches_golden(goldens, case_id):
    """Every named preserved clause returns exactly what the unfixed code returned.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10,
    3.11, 3.12, 3.13**
    """
    golden = goldens["named"].get(case_id)
    assert golden is not None, (
        f"No golden recorded for {case_id!r}. Recorded cases: "
        f"{sorted(goldens['named'])}. Re-record with: {RECORD_COMMAND}"
    )

    observed = NAMED_CASES[case_id]().record
    assert observed == golden, _diff(f"Named case {case_id!r}", observed, golden)


@pytest.mark.parametrize("index", range(CORPUS_SIZE))
def test_property_2_generated_corpus_matches_golden(goldens, index):
    """For every generated non-bug input, ``login()`` and ``refresh()`` match the golden.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.12, 3.13**

    The fingerprint check comes first: if the corpus generator or the exclusion
    filter has drifted, the golden at this index describes a *different* input, and
    comparing responses against it would be meaningless.
    """
    plan = corpus_plans()[index]
    entries = goldens["corpus"]
    assert index < len(entries), (
        f"Golden corpus holds {len(entries)} cases but the generator produced at "
        f"least {index + 1}. Re-record with: {RECORD_COMMAND}"
    )
    entry = entries[index]

    fingerprint = plan_fingerprint(plan)
    assert entry["fingerprint"] == fingerprint, (
        f"Corpus case {corpus_case_id(index)} no longer generates the input its "
        f"golden was recorded from (fingerprint {fingerprint} vs recorded "
        f"{entry['fingerprint']}). The generator, the seed, or the exclusion filter "
        f"changed — fix that rather than re-recording, or the baseline stops "
        f"describing the behavior it claims to."
    )

    observed = run_corpus_case(plan)
    assert observed["login"] == entry["login"], _diff(
        f"{corpus_case_id(index)} login {_plan_summary(plan)}", observed["login"], entry["login"]
    )
    assert observed["refresh"] == entry["refresh"], _diff(
        f"{corpus_case_id(index)} refresh {_plan_summary(plan)}",
        observed["refresh"],
        entry["refresh"],
    )


def _plan_summary(plan: PayloadPlan) -> str:
    def describe(node: dict) -> str:
        return (
            f"{node.get('status')!r} created={node.get('createdAt')} "
            f"next={node.get('nextBillingDate')} grants={oracle_contract_grants(node)}"
        )

    return (
        f"(records={len(plan.customer_ids)}, fallbacks="
        f"{[plan.fallback_status_by_customer[cid] for cid in plan.customer_ids]}, "
        f"contracts=[{'; '.join(describe(n) for n in plan.all_contracts)}])"
    )


# ===========================================================================
# Corpus invariants — these keep Property 2 from going vacuous
# ===========================================================================

def test_corpus_contains_only_non_bug_inputs():
    """Every corpus case really is outside the bug condition.

    A generator bug that let a bug-condition input in would freeze behavior the
    fix is meant to change, and Task 10.3 would fail for the wrong reason.
    """
    offenders = [
        corpus_case_id(index)
        for index, plan in enumerate(corpus_plans())
        if not is_preservation_input(plan)
    ]
    assert not offenders, f"bug-condition inputs leaked into the corpus: {offenders}"


def test_corpus_covers_the_preserved_outcome_shapes():
    """The corpus reaches grant, free tier, and both denial flavours.

    Without this, a filter that accidentally accepted only (say) free-tier inputs
    would still pass every golden comparison while testing almost nothing.
    """
    goldens_doc = load_goldens()
    shapes = {corpus_outcome_shape(entry["login"]) for entry in goldens_doc["corpus"]}
    expected = {
        (200, "active"),
        (200, "free"),
        (403, "paused"),
        (403, "cancelled"),
    }
    missing = expected - shapes
    assert not missing, (
        f"corpus does not cover {sorted(missing)}; observed shapes {sorted(shapes)}. "
        f"Widen the draw distribution — the preserved surface includes grants, free "
        f"tier, and both denial flavours."
    )


def test_corpus_size_and_fingerprints_match_the_goldens():
    """The recorded corpus is exactly the corpus this module generates today."""
    goldens_doc = load_goldens()
    plans = corpus_plans()
    assert len(goldens_doc["corpus"]) == len(plans) == CORPUS_SIZE
    observed = [plan_fingerprint(plan) for plan in plans]
    recorded = [entry["fingerprint"] for entry in goldens_doc["corpus"]]
    assert observed == recorded, (
        "corpus fingerprints drifted from the goldens; see the failure in "
        "test_property_2_generated_corpus_matches_golden for the affected index"
    )


def test_goldens_were_recorded_from_unfixed_code():
    """Provenance check: the baseline must not have been re-recorded post-fix."""
    meta = load_goldens()["_meta"]
    assert meta["fixed_decision_layer_present"] is False, (
        "the goldens were recorded from code that already had the fixed decision "
        "layer, so Property 2 would be comparing the fix against itself"
    )
    assert meta["recorded_from"] == "UNFIXED backend/subscription_auth.py"
    assert meta["fixture_now"] == _iso(FIXTURE_NOW)
    assert meta["corpus_seed"] == CORPUS_SEED


# ===========================================================================
# Clause-level assertions the golden alone cannot express
# ===========================================================================
#
# The golden comparison above already pins every byte of these responses. What it
# cannot express is WHY a value matters — that the denial copy is byte-identical,
# that the bypass path issues no HTTP call at all, that exp - iat is one hour.
# These read the same live observations and state those requirements directly, so
# a future edit to a golden cannot quietly relax a named clause.


def test_active_subscriber_gets_full_access():
    """3.1 — ACTIVE subscriber → 200 / ``"active"``."""
    obs = case_login_active_subscriber()
    assert obs.status_code == 200
    assert obs.body["subscription_status"] == "active"
    assert obs.body["success"] is True


def test_no_appstle_record_gets_free_tier():
    """3.2 — no Appstle record → 200 / ``"free"``, not a denial."""
    obs = case_login_no_appstle_record()
    assert obs.status_code == 200
    assert obs.body["subscription_status"] == "free"


def test_expired_denial_copy_is_byte_identical_with_a_redirect():
    """3.3 / 2.21 — the expired denial copy and its redirect URL, byte for byte.

    This is the case most at risk from change 14 (adopting ``DENIAL_MESSAGES`` as
    the live source of denial copy, whose current values omit the
    ``"Resubscribe to continue."`` sentence). Both the single-contract and the
    two-contract shape are checked, plus ``refresh()``'s own copy of the message.
    """
    for label, obs in (
        ("login/all_contracts_expired", case_login_all_contracts_expired()),
        ("login/all_contracts_expired_multi_contract", case_login_all_contracts_expired_multi_contract()),
    ):
        assert obs.status_code == 403, label
        assert obs.body["error"] == EXPIRED_DENIAL, (
            f"{label}: denial copy must stay byte-identical. "
            f"got {obs.body['error']!r}, expected {EXPIRED_DENIAL!r}"
        )
        assert obs.body["subscription_status"] == "paused", label
        assert obs.body["redirect_url"], f"{label}: redirect_url must be non-null (3.3)"

    refreshed = case_refresh_all_contracts_expired()
    assert refreshed.status_code == 403
    assert refreshed.body["error"] == EXPIRED_DENIAL
    assert refreshed.body["redirect_url"]


def test_empty_nodes_are_decided_by_product_subscriber_status():
    """2.12 / 3.2 — with no contracts, the customer-level status decides."""
    active = case_login_empty_nodes_status_active()
    assert (active.status_code, active.body["subscription_status"]) == (200, "active")

    paused = case_login_empty_nodes_status_paused()
    assert paused.status_code == 403
    assert paused.body["error"] == EXPIRED_DENIAL

    cancelled = case_login_empty_nodes_status_cancelled()
    assert cancelled.status_code == 403
    assert cancelled.body["error"] == CANCELLED_DENIAL

    missing = case_login_empty_nodes_status_missing()
    assert (missing.status_code, missing.body["subscription_status"]) == (200, "free"), (
        "a missing productSubscriberStatus keeps free-tier access (2.19 makes the "
        "log record loud, it does not change the response)"
    )


def test_wrong_password_returns_401_regardless_of_subscription():
    """3.4 — an active subscription does not excuse a wrong password."""
    obs = case_login_wrong_password_with_active_subscription()
    assert obs.status_code == 401
    assert obs.body["error"] == INVALID_CREDENTIALS
    assert "token" not in obs.body


def test_rate_limit_trips_on_the_sixth_attempt():
    """3.5 — five attempts are allowed, the sixth is 429 with the same copy."""
    fifth = case_login_rate_limit_fifth_attempt()
    assert fifth.status_code == 401, "the fifth attempt is still inside the limit"

    sixth = case_login_rate_limit_sixth_attempt()
    assert sixth.status_code == 429
    assert sixth.body["error"] == RATE_LIMITED


def test_missing_appstle_config_returns_503_without_calling_appstle():
    """3.6 — configuration is checked before anything else happens."""
    obs = case_login_missing_appstle_config()
    assert obs.status_code == 503
    assert obs.body["error"] == SERVICE_UNAVAILABLE
    assert obs.requested_urls == [], (
        f"the 503 path must not reach Appstle; observed {obs.requested_urls}"
    )


def test_appstle_failures_fall_through_to_free_tier():
    """3.7 — timeout, HTTP 500, and malformed JSON all end in free tier, never a block."""
    for label, obs in (
        ("timeout", case_login_appstle_timeout()),
        ("http_500", case_login_appstle_http_500()),
        ("malformed_json", case_login_appstle_malformed_json()),
    ):
        assert obs.status_code == 200, f"{label} must not block login"
        assert obs.body["subscription_status"] == "free", label
        assert obs.token_claims["subscription_status"] == "free", label


def test_refresh_preserves_subscription_status_from_jwt_claims():
    """3.8 — Appstle down at refresh: the new token carries the old claim forward."""
    active = case_refresh_appstle_down_preserves_active_claim()
    assert active.status_code == 200
    assert active.body["success"] is True
    assert active.token_claims["subscription_status"] == "active", (
        "the status in the incoming claims must survive an Appstle outage"
    )

    free = case_refresh_appstle_down_preserves_free_claim()
    assert free.status_code == 200
    assert free.token_claims["subscription_status"] == "free"


def test_new_user_weak_password_returns_400_with_failed_rules():
    """3.9 — the failed-rule list is part of the contract, not just the status code."""
    obs = case_login_new_user_weak_password()
    assert obs.status_code == 400
    assert obs.body["success"] is False
    assert obs.body["failed_rules"], "the 400 body must list which rules failed"
    assert isinstance(obs.body["failed_rules"], list)
    assert "token" not in obs.body


def test_bypass_email_skips_the_appstle_call_entirely():
    """3.10 — ``BYPASS_EMAILS`` grants ``"active"`` without consulting Appstle.

    The router was armed with an all-expired payload, so a single call would have
    flipped the answer to 403. Zero recorded requests is the assertion.
    """
    obs = case_login_bypass_email()
    assert obs.status_code == 200
    assert obs.body["subscription_status"] == "active"
    assert obs.requested_urls == [], (
        f"bypass must skip the subscription check; observed {obs.requested_urls}"
    )


def test_refresh_grace_window_boundaries():
    """3.11 — 2 minutes expired is accepted, 10 minutes expired is 401."""
    within = case_refresh_two_minutes_expired_within_grace()
    assert within.status_code == 200, "2 minutes past expiry is inside the 5-minute window"
    assert within.body["success"] is True

    beyond = case_refresh_ten_minutes_expired_beyond_grace()
    assert beyond.status_code == 401
    assert beyond.body["success"] is False
    assert beyond.body["token"] is None


def test_jwt_claim_shape_and_one_hour_expiry():
    """3.12 — the same five claims and the same 1-hour expiry on every issued token."""
    for label, obs in (
        ("login/active_subscriber", case_login_active_subscriber()),
        ("login/no_appstle_record", case_login_no_appstle_record()),
        ("login/bypass_email", case_login_bypass_email()),
        ("refresh/active_subscriber", case_refresh_active_subscriber()),
        ("refresh/appstle_down", case_refresh_appstle_down_preserves_active_claim()),
    ):
        claims = obs.token_claims
        assert claims is not None, f"{label} should have issued a token"
        assert claims["claim_keys"] == TOKEN_CLAIM_KEYS, (
            f"{label}: claim key set changed. got {claims['claim_keys']}, "
            f"expected {TOKEN_CLAIM_KEYS}"
        )
        assert claims["exp_minus_iat_seconds"] == TOKEN_EXPIRY_SECONDS, (
            f"{label}: token expiry must stay 1 hour, got "
            f"{claims['exp_minus_iat_seconds']}s"
        )


def test_expiry_fields_are_null_on_every_success_path():
    """3.13 — ``expires_at`` and ``subscription_expires_at`` stay null (deferred scope)."""
    login_cases = {
        case_id: case
        for case_id, case in NAMED_CASES.items()
        if case_id.startswith("login/")
    }
    checked = 0
    for case_id, case in login_cases.items():
        obs = case()
        if obs.status_code != 200:
            continue
        checked += 1
        assert obs.body.get("expires_at") is None, (
            f"{case_id}: expires_at must stay null — expiration_date is never "
            f"populated (3.13, out of scope)"
        )
        assert obs.token_claims["subscription_expires_at"] is None, case_id
    assert checked >= 5, f"expected several success paths to check, got {checked}"


# ===========================================================================
# The three Preservation Exceptions — asserted with their intended NEW values
# ===========================================================================
#
# These are excluded from Property 2 by is_preservation_input(), and no golden
# exists for them: recording one would freeze behavior the fix deliberately
# changes, and Task 10.3 would then fail for exactly the wrong reason.
#
# Each asserts the value the FIXED code must produce, so each failed on unfixed
# code and carried xfail(strict=True) to keep the suite green while still
# documenting the change. Task 9.5 rewrote login()'s step 4 onto decide_access()
# and all three XPASSed, so the markers are gone: these are now ordinary
# assertions, and a regression on any of them is a hard failure.

EXCEPTION_CASE_IDS = (
    "exception/2.3_single_cancelled_with_paid_time",
    "exception/2.6_paused_null_next_billing_derivable",
    "exception/2.16_denial_message_from_newest_contract",
)


def test_exception_2_3_cancelled_with_paid_time_grants_access():
    """2.3 / 1.7 — CANCELLED with 21 days of paid time left → 200 / ``"active"``.

    **Validates: Requirements 2.3**

    Denied 403 "cancelled" before the fix. Cancelling means "stop billing me",
    not "revoke what I already paid for", so paid time still grants.
    """
    step2 = load_fixture("cancelled_with_paid_time")
    node = step2["subscriptionContracts"]["nodes"][0]
    assert node["status"] == "CANCELLED"
    assert oracle_contract_grants(node), "fixture drift: this contract must have paid time left"

    with harness(
        step1=single_record_step1(CANCELLED_PAID_CUSTOMER_ID, CANCELLED_PAID_EMAIL),
        step2={CANCELLED_PAID_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={CANCELLED_PAID_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(CANCELLED_PAID_EMAIL, KNOWN_PASSWORD)

    assert result["status_code"] == 200, (
        f"expected 200, got {result['status_code']} "
        f"error={result['body'].get('error')!r} — CANCELLED contract with "
        f"nextBillingDate {node['nextBillingDate']} (FIXTURE_NOW + 21 days)"
    )
    assert result["body"]["subscription_status"] == "active"


def test_exception_2_6_paused_null_next_billing_derivable_grants_access():
    """2.6 / 1.6 — PAUSED, null ``nextBillingDate``, ``createdAt`` + 1 month ahead.

    **Validates: Requirements 2.6**

    Denied 403 "expired" before the fix, which attempted no derivation at all.
    """
    step2 = load_fixture("paused_null_nextbilling_derivable")
    node = step2["subscriptionContracts"]["nodes"][0]
    assert node["status"] == "PAUSED"
    assert node["nextBillingDate"] is None
    assert oracle_contract_grants(node), (
        "fixture drift: createdAt + one interval must land in the future"
    )

    with harness(
        step1=single_record_step1(DERIVABLE_CUSTOMER_ID, DERIVABLE_EMAIL),
        step2={DERIVABLE_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={DERIVABLE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(DERIVABLE_EMAIL, KNOWN_PASSWORD)

    assert result["status_code"] == 200, (
        f"expected 200, got {result['status_code']} "
        f"error={result['body'].get('error')!r} — PAUSED, nextBillingDate null, "
        f"createdAt {node['createdAt']} + {node['billingPolicy']} is in the future"
    )
    assert result["body"]["subscription_status"] == "active"


def test_exception_2_16_denial_message_comes_from_the_newest_contract():
    """2.16 / 1.14 — newest contract CANCELLED, older PAUSED-expired → cancelled copy.

    **Validates: Requirements 2.16, 2.17**

    Before the fix the copy came from ``nodes[0]`` (PAUSED → expired); it now
    comes from the newest contract (CANCELLED → cancelled).

    Same status code either way (403); only the message and
    ``body.subscription_status`` move, which is why this needs its own assertion
    rather than being visible in a status-code comparison.

    **The fixture's customer-level ``productSubscriberStatus`` is overridden to
    PAUSED here**, and that override is load-bearing. The fixture ships with
    ``productSubscriberStatus`` CANCELLED, and the unfixed ladder keys on that
    customer-level field rather than on ``nodes[0]``, so with the fixture as
    built the unfixed code *already* emits the cancelled copy and the exception
    is invisible — the test XPASSes without proving anything. Clause 1.14
    describes a customer told "expired" when their newest contract was
    cancelled, and reaching that requires the customer-level label to say PAUSED
    while the newest contract says CANCELLED. That is exactly the point of the
    fix: the label is the wrong signal, and here it disagrees with the contract
    data.
    """
    step2 = load_fixture("denial_newest_cancelled_older_paused")
    step2["productSubscriberStatus"] = "PAUSED"
    nodes = step2["subscriptionContracts"]["nodes"]
    assert not any(oracle_contract_grants(node) for node in nodes), "fixture drift: none may grant"
    newest = oracle_newest(nodes)
    assert newest["status"] == "CANCELLED"
    assert nodes[0]["status"] == "PAUSED"

    with harness(
        step1=single_record_step1(DENIAL_NEWEST_CUSTOMER_ID, DENIAL_NEWEST_EMAIL),
        step2={DENIAL_NEWEST_CUSTOMER_ID: step2},
        bypass_emails="",
        known_passwords={DENIAL_NEWEST_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(DENIAL_NEWEST_EMAIL, KNOWN_PASSWORD)

    assert result["status_code"] == 403
    assert result["body"]["redirect_url"], "a denial still needs its resubscribe URL"
    assert result["body"]["error"] == CANCELLED_DENIAL, (
        f"expected the newest contract's copy {CANCELLED_DENIAL!r}, got "
        f"{result['body']['error']!r} — nodes[0] is PAUSED (created "
        f"{nodes[0]['createdAt']}), the newest is CANCELLED (created "
        f"{newest['createdAt']})"
    )
    assert result["body"]["subscription_status"] == "cancelled"


def test_goldens_never_encode_the_preservation_exceptions():
    """No golden may exist for a deliberately-changed behavior."""
    recorded = set(load_goldens()["named"])
    leaked = [case_id for case_id in EXCEPTION_CASE_IDS if case_id in recorded]
    assert not leaked, (
        f"the goldens encode Preservation Exceptions {leaked}, which the fix is "
        f"meant to change — remove them or Task 10.3 fails for the wrong reason"
    )


# ===========================================================================
# Recorder CLI
# ===========================================================================

def _main(argv: List[str]) -> int:
    if "--record" not in argv:
        print(f"usage: {RECORD_COMMAND}", file=sys.stderr)
        return 2

    force = "--force" in argv
    document = record_goldens(force=force)
    meta = document["_meta"]
    print(f"Wrote {GOLDEN_PATH}")
    print(f"  named cases : {meta['named_case_count']}")
    print(f"  corpus cases: {meta['corpus_size']} (seed {meta['corpus_seed']})")
    print(f"  git commit  : {meta['git_commit']}")
    print(f"  fixed layer present: {meta['fixed_decision_layer_present']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - recorder entry point
    raise SystemExit(_main(sys.argv[1:]))
