"""Direct unit tests for ``decide_access()`` (Task 8.6, design change 6).

**Validates: Requirements 2.1, 2.5, 2.9, 2.12, 2.13, 2.16, 2.17, 2.19**

``decide_access()`` is the single access decision path (2.13). It is pure and
module-level, so everything here calls it directly: no HTTP, no Appstle payloads,
no ``SubscriptionAuthService`` instance, no environment configuration. That seam
is the point — the current code's decision logic can only be reached through
``login()`` over a stubbed transport, which is how three copies of it drifted
apart unnoticed.

Assertions on ``login()``'s and ``refresh()``'s actual ``status_code`` and
``body`` live in the property suites (``test_subscription_fix_checking.py``,
``test_subscription_preservation_properties.py``) and stay there. This module
tests the decision function itself.

The clock is pinned for every case that depends on it. ``decide_access()`` reads
the clock only indirectly, through ``_contract_grants()`` → ``_paid_through()`` →
``_utcnow()`` (design change 2b), and a test whose verdict depends on the wall
clock is a test that inverts itself later.
"""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from itertools import permutations
from pathlib import Path

import pytest

# Make the repository root importable so ``backend.*`` resolves regardless of
# where pytest is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend import subscription_auth  # noqa: E402
from backend.subscription_auth import (  # noqa: E402
    MISSING_STATUS,
    AccessDecision,
    ContractView,
    decide_access,
)

LOGGER_NAME = "backend.subscription_auth"

# The capture instant the sanitized Appstle fixtures are written against; reused
# here so the dates in this module read the same as everywhere else in the suite.
NOW = datetime(2026, 8, 9, 1, 31, 12, tzinfo=timezone.utc)

EXPIRED_DENIAL = "Your subscription has expired. Resubscribe to continue."
CANCELLED_DENIAL = "Your subscription has been cancelled. Resubscribe to continue."
DEFAULT_DENIAL = "No subscription found"

EMAIL = "dave@example.com"


@contextmanager
def pinned_clock(instant: datetime = NOW):
    """Pin ``_utcnow()`` for the duration of the block.

    Patched as a module attribute, the single seam design change 2b exists to
    provide. Same mechanism as ``tests/test_subscription_helpers.py``, so the two
    modules cannot drift on how they pin time.
    """
    original = subscription_auth._utcnow
    subscription_auth._utcnow = lambda: instant
    try:
        yield instant
    finally:
        subscription_auth._utcnow = original


def contract(**overrides) -> ContractView:
    """A ``ContractView`` with the decision-relevant fields, others defaulted.

    ``renewal_anchor`` mirrors ``created_at`` the way the parser fills it (design
    Finding 1: ``createdAt`` is the only anchor Appstle exposes).
    """
    fields = {
        "customer_id": 2788838535,
        "contract_id": "gid://shopify/SubscriptionContract/1000000001",
        "status": "PAUSED",
        "interval": "MONTH",
        "interval_count": 1,
    }
    fields.update(overrides)
    if "renewal_anchor" not in fields and fields.get("created_at") is not None:
        fields["renewal_anchor"] = fields["created_at"]
        fields.setdefault("renewal_anchor_field", "createdAt")
    return ContractView(**fields)


def granting(**overrides) -> ContractView:
    """A contract that grants under the pinned clock: PAUSED, paid time left."""
    fields = {"status": "PAUSED", "next_billing_date": NOW + timedelta(days=18)}
    fields.update(overrides)
    return contract(**fields)


def expired(**overrides) -> ContractView:
    """A contract that does not grant: PAUSED, paid time exhausted."""
    fields = {"status": "PAUSED", "next_billing_date": NOW - timedelta(days=18)}
    fields.update(overrides)
    return contract(**fields)


def errors_in(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]


# ---------------------------------------------------------------------------
# AccessDecision — the shape callers branch on
# ---------------------------------------------------------------------------

def test_access_decision_is_frozen():
    """Frozen, so a decision cannot be edited between being made and being used."""
    decision = AccessDecision(granted=True, subscription_status="active")

    with pytest.raises(Exception):
        decision.granted = False  # type: ignore[misc]


def test_access_decision_field_defaults():
    """A grant needs only two fields; the denial fields default to "not a denial"."""
    decision = AccessDecision(granted=True, subscription_status="active")

    assert decision.denial_message is None
    assert decision.redirect_url_needed is False
    assert decision.deciding_contract is None


# ---------------------------------------------------------------------------
# Clause 2.1 — ANY contract grants
# ---------------------------------------------------------------------------

def test_any_granting_contract_grants_access():
    """One granting contract carries the whole set (2.1)."""
    with pinned_clock():
        decision = decide_access([granting()], "PAUSED", EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"
    assert decision.denial_message is None
    assert decision.redirect_url_needed is False


def test_grant_wins_when_the_granting_contract_is_not_first():
    """Dave's shape: ``nodes[0]`` expired, ``nodes[1]`` still paid → granted.

    This is the bug as filed. The unfixed ladder reads only the first contract and
    denies; the rule here is an existence check over every contract.
    """
    nodes = [
        expired(
            contract_id="gid://shopify/SubscriptionContract/1000000001",
            created_at=datetime(2026, 6, 2, 22, 27, 41, tzinfo=timezone.utc),
            next_billing_date=datetime(2026, 7, 2, 22, 27, 41, tzinfo=timezone.utc),
        ),
        granting(
            contract_id="gid://shopify/SubscriptionContract/1000000002",
            created_at=datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc),
            next_billing_date=datetime(2026, 8, 27, 19, 0, tzinfo=timezone.utc),
        ),
    ]

    with pinned_clock():
        decision = decide_access(nodes, "PAUSED", EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"
    assert decision.deciding_contract is nodes[1]


def test_grant_ignores_a_denying_customer_level_status():
    """``productSubscriberStatus`` CANCELLED cannot veto a granting contract.

    Clause 2.12 demotes the customer-level field to a fallback consulted only when
    there are no contracts at all. Dave's customer-level status is PAUSED while his
    newest contract still has paid time, so a field that could override would
    reintroduce the lockout.
    """
    with pinned_clock():
        for fallback in ("CANCELLED", "PAUSED", None, MISSING_STATUS, "junk"):
            decision = decide_access([granting()], fallback, EMAIL)
            assert decision.granted is True, f"fallback={fallback!r} must not veto"
            assert decision.subscription_status == "active"


def test_active_contract_grants_even_with_paid_time_exhausted():
    """Clause 2.2's dunning window, reached through the decision function."""
    view = contract(status="ACTIVE", next_billing_date=NOW - timedelta(days=5))

    with pinned_clock():
        decision = decide_access([view], "CANCELLED", EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"


def test_cancelled_contract_with_paid_time_remaining_grants():
    """Preservation Exception 2.3 / 1.7: cancelled means "stop billing me"."""
    view = contract(status="CANCELLED", next_billing_date=NOW + timedelta(days=9))

    with pinned_clock():
        decision = decide_access([view], "CANCELLED", EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"


def test_deciding_contract_on_a_grant_is_the_newest_granting_contract():
    """The grant names WHICH contract carried it, deterministically.

    Reported for the log line, so a grant can be traced to a contract. It has to
    be picked by the same total order as the denial selection, otherwise the field
    would depend on Appstle's ordering even though the verdict did not.
    """
    older = granting(
        contract_id="gid://shopify/SubscriptionContract/1000000001",
        created_at=NOW - timedelta(days=60),
    )
    newer = granting(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        created_at=NOW - timedelta(days=5),
    )

    with pinned_clock():
        assert decide_access([older, newer], "PAUSED", EMAIL).deciding_contract is newer
        assert decide_access([newer, older], "PAUSED", EMAIL).deciding_contract is newer


def test_all_granting_statuses_together_still_grant_once():
    """A mixed set of granting and non-granting contracts yields one grant."""
    nodes = [
        expired(contract_id="gid://shopify/SubscriptionContract/1000000001"),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000002",
            status="EXPIRED",
            next_billing_date=NOW + timedelta(days=30),
        ),
        granting(contract_id="gid://shopify/SubscriptionContract/1000000003"),
    ]

    with pinned_clock():
        decision = decide_access(nodes, None, EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"


# ---------------------------------------------------------------------------
# Clauses 2.5 / 2.16 / 2.17 — denial, and which contract supplies the message
# ---------------------------------------------------------------------------

def test_no_granting_contract_denies_with_a_redirect():
    """Clause 2.5: nothing grants → denied, and a denial needs its resubscribe URL."""
    with pinned_clock():
        decision = decide_access([expired()], "PAUSED", EMAIL)

    assert decision.granted is False
    assert decision.redirect_url_needed is True
    assert decision.denial_message == EXPIRED_DENIAL
    assert decision.subscription_status == "paused"


def test_denial_message_comes_from_the_newest_contract():
    """Clause 2.16 / 1.14: newest CANCELLED, older PAUSED-expired → cancelled copy.

    The customer whose most recent subscription was cancelled is told "cancelled",
    not the less actionable "expired" the first contract would have produced.
    """
    older_paused = expired(
        contract_id="gid://shopify/SubscriptionContract/1000000001",
        status="PAUSED",
        created_at=datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc),
    )
    newest_cancelled = contract(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        status="CANCELLED",
        created_at=datetime(2026, 6, 30, 0, 0, tzinfo=timezone.utc),
        next_billing_date=NOW - timedelta(days=1),
    )

    with pinned_clock():
        decision = decide_access([older_paused, newest_cancelled], "PAUSED", EMAIL)

    assert decision.granted is False
    assert decision.denial_message == CANCELLED_DENIAL
    assert decision.subscription_status == "cancelled"
    assert decision.deciding_contract is newest_cancelled


def test_denial_message_ignores_the_customer_level_status():
    """The message comes from the newest CONTRACT, not the customer-level label.

    Clause 1.14's real case: the label says PAUSED while the newest contract says
    CANCELLED. Reading the label is what produced the wrong copy.
    """
    nodes = [
        expired(
            contract_id="gid://shopify/SubscriptionContract/1000000001",
            created_at=NOW - timedelta(days=120),
        ),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000002",
            status="CANCELLED",
            created_at=NOW - timedelta(days=40),
            next_billing_date=NOW - timedelta(days=10),
        ),
    ]

    with pinned_clock():
        decision = decide_access(nodes, "PAUSED", EMAIL)

    assert decision.denial_message == CANCELLED_DENIAL
    assert decision.subscription_status == "cancelled"


def test_newest_selection_tiebreaks_on_contract_id_for_identical_timestamps():
    """Clause 2.16's deterministic tiebreak: equal ``createdAt``, higher id wins.

    Without a tiebreak ``max()`` returns whichever equal-keyed contract happened to
    come first, so the denial copy would depend on Appstle's ordering — the order
    dependence clause 2.9 forbids. Which of the two wins matters less than that the
    same one wins every time, so both input orders are asserted.
    """
    same_instant = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    lower_id = expired(
        contract_id="gid://shopify/SubscriptionContract/1000000001",
        status="PAUSED",
        created_at=same_instant,
    )
    higher_id = contract(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        status="CANCELLED",
        created_at=same_instant,
        next_billing_date=NOW - timedelta(days=2),
    )

    with pinned_clock():
        forward = decide_access([lower_id, higher_id], "PAUSED", EMAIL)
        reversed_ = decide_access([higher_id, lower_id], "PAUSED", EMAIL)

    assert forward.deciding_contract is higher_id
    assert reversed_.deciding_contract is higher_id
    assert forward.denial_message == reversed_.denial_message == CANCELLED_DENIAL
    assert forward.subscription_status == reversed_.subscription_status == "cancelled"


def test_null_created_at_loses_to_a_contract_with_a_known_date():
    """A null ``createdAt`` sorts last in preference, so it is not called "newest".

    An unknown creation time is not evidence of being the most recent contract. The
    CANCELLED contract here has no date at all, so the dated PAUSED one supplies
    the copy — matching ``oracle_newest()`` in the property suites, which the
    fixture-driven assertions are written against.
    """
    dated_paused = expired(
        contract_id="gid://shopify/SubscriptionContract/1000000001",
        status="PAUSED",
        created_at=datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc),
    )
    undated_cancelled = contract(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        status="CANCELLED",
        created_at=None,
        renewal_anchor=None,
        next_billing_date=NOW - timedelta(days=3),
    )

    with pinned_clock():
        forward = decide_access([dated_paused, undated_cancelled], "PAUSED", EMAIL)
        reversed_ = decide_access([undated_cancelled, dated_paused], "PAUSED", EMAIL)

    for decision in (forward, reversed_):
        assert decision.deciding_contract is dated_paused
        assert decision.denial_message == EXPIRED_DENIAL
        assert decision.subscription_status == "paused"


def test_all_null_created_at_falls_back_to_the_contract_id_tiebreak():
    """When no contract has a date, the id alone still gives one stable answer."""
    first = expired(
        contract_id="gid://shopify/SubscriptionContract/1000000001",
        status="PAUSED",
        created_at=None,
        renewal_anchor=None,
    )
    second = contract(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        status="CANCELLED",
        created_at=None,
        renewal_anchor=None,
        next_billing_date=NOW - timedelta(days=3),
    )

    with pinned_clock():
        forward = decide_access([first, second], None, EMAIL)
        reversed_ = decide_access([second, first], None, EMAIL)

    assert forward.deciding_contract is second
    assert reversed_.deciding_contract is second
    assert forward.denial_message == reversed_.denial_message == CANCELLED_DENIAL


def test_null_contract_id_does_not_raise_and_stays_deterministic():
    """A null ``contract_id`` compares as ``""`` rather than exploding the tiebreak."""
    same_instant = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    without_id = expired(contract_id=None, status="PAUSED", created_at=same_instant)
    with_id = contract(
        contract_id="gid://shopify/SubscriptionContract/1000000002",
        status="CANCELLED",
        created_at=same_instant,
        next_billing_date=NOW - timedelta(days=2),
    )

    with pinned_clock():
        forward = decide_access([without_id, with_id], None, EMAIL)
        reversed_ = decide_access([with_id, without_id], None, EMAIL)

    assert forward.deciding_contract is with_id
    assert reversed_.deciding_contract is with_id


@pytest.mark.parametrize(
    "status,expected_message,expected_status",
    [
        ("PAUSED", EXPIRED_DENIAL, "paused"),
        ("CANCELLED", CANCELLED_DENIAL, "cancelled"),
        ("EXPIRED", EXPIRED_DENIAL, "expired"),
        ("SUSPENDED", DEFAULT_DENIAL, "not_found"),
        ("junk", DEFAULT_DENIAL, "not_found"),
        ("", DEFAULT_DENIAL, "not_found"),
        (None, DEFAULT_DENIAL, "not_found"),
    ],
)
def test_denial_copy_comes_from_the_helpers_for_every_status(
    status, expected_message, expected_status
):
    """Clause 2.17: the copy is ``_get_denial_message()``, never an inline string.

    Every status a denied contract can carry is routed through the dict, including
    the unrecognized ones that must reach ``DEFAULT_DENIAL_MESSAGE`` rather than
    being described as expired.
    """
    view = contract(status=status, next_billing_date=NOW - timedelta(days=1))

    with pinned_clock():
        decision = decide_access([view], None, EMAIL)

    assert decision.granted is False
    assert decision.denial_message == expected_message
    assert decision.subscription_status == expected_status
    assert decision.redirect_url_needed is True


def test_denial_copy_matches_the_live_helpers_rather_than_a_transcription():
    """The strings above are the dict's, not a hand-typed copy that could drift."""
    view = contract(status="PAUSED", next_billing_date=NOW - timedelta(days=1))

    with pinned_clock():
        decision = decide_access([view], None, EMAIL)

    assert decision.denial_message == subscription_auth._get_denial_message("PAUSED")
    assert decision.subscription_status == subscription_auth._normalize_status("PAUSED")


def test_underivable_paid_through_denies_and_names_the_newest_contract():
    """Clause 2.8 through the decision function: underivable does not grant."""
    view = contract(
        status="PAUSED",
        next_billing_date=None,
        created_at=NOW - timedelta(days=2),
        interval="FORTNIGHT",
    )

    with pinned_clock():
        decision = decide_access([view], "PAUSED", EMAIL)

    assert decision.granted is False
    assert decision.denial_message == EXPIRED_DENIAL
    assert decision.deciding_contract is view


# ---------------------------------------------------------------------------
# Clause 2.12 — the customer-level fallback, used only when there are no contracts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("contracts", [[], (), None])
def test_empty_contracts_reaches_the_fallback(contracts):
    """No contracts at all — including ``None`` and an empty tuple — falls back."""
    with pinned_clock():
        decision = decide_access(contracts, "ACTIVE", EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "active"
    assert decision.deciding_contract is None


def test_fallback_active_grants_active():
    """2.12: customer-level ACTIVE with no contracts → 200 / ``"active"`` (3.1)."""
    with pinned_clock():
        decision = decide_access([], "ACTIVE", EMAIL)

    assert decision == AccessDecision(granted=True, subscription_status="active")


def test_fallback_paused_denies_with_the_expired_copy():
    """2.12: customer-level PAUSED with no contracts → denied, expired copy (3.3)."""
    with pinned_clock():
        decision = decide_access([], "PAUSED", EMAIL)

    assert decision.granted is False
    assert decision.subscription_status == "paused"
    assert decision.denial_message == EXPIRED_DENIAL
    assert decision.redirect_url_needed is True
    assert decision.deciding_contract is None


def test_fallback_cancelled_denies_with_the_cancelled_copy():
    """2.12: customer-level CANCELLED with no contracts → denied, cancelled copy."""
    with pinned_clock():
        decision = decide_access([], "CANCELLED", EMAIL)

    assert decision.granted is False
    assert decision.subscription_status == "cancelled"
    assert decision.denial_message == CANCELLED_DENIAL
    assert decision.redirect_url_needed is True


@pytest.mark.parametrize("status", [None, "", "junk", "SUSPENDED", "NOT_FOUND", 0, []])
def test_fallback_null_or_unknown_grants_free_tier(status):
    """A null or unrecognized customer-level status grants free tier (3.2).

    Free tier rather than a denial is deliberate and preserved: an unknown label is
    not evidence that a customer's access should be revoked, and the usage gate
    still limits what free tier can do. Non-string values are included because a
    payload that carries one must not raise inside a login.
    """
    with pinned_clock():
        decision = decide_access([], status, EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "free"
    assert decision.denial_message is None
    assert decision.redirect_url_needed is False


@pytest.mark.parametrize(
    "status,expected",
    [
        ("active", "active"),
        ("Active", "active"),
        ("paused", "paused"),
        ("Paused", "paused"),
        ("cancelled", "cancelled"),
        ("CanCelled", "cancelled"),
    ],
)
def test_fallback_status_matching_is_case_insensitive(status, expected):
    """Appstle's casing is not trusted for the fallback label either."""
    with pinned_clock():
        decision = decide_access([], status, EMAIL)

    assert decision.subscription_status == expected
    assert decision.granted is (expected == "active")


def test_fallback_never_reports_a_deciding_contract():
    """Nothing decided the outcome, so nothing may be named as having decided it."""
    with pinned_clock():
        for status in ("ACTIVE", "PAUSED", "CANCELLED", None, MISSING_STATUS):
            assert decide_access([], status, EMAIL).deciding_contract is None


# ---------------------------------------------------------------------------
# Clause 2.19 — a MISSING productSubscriberStatus is loud
# ---------------------------------------------------------------------------

def test_missing_status_grants_free_tier_and_logs_an_error(caplog):
    """Clause 2.19: the outcome stays free tier; the downgrade stops being silent.

    ``MISSING_STATUS`` means the key was ABSENT from the payload, which is a
    payload-shape change, not customer data. Free tier is still the right and
    preserved response (3.2) — what changes is that it is now visible at ERROR
    instead of buried in a ``logger.info`` line nobody reads.
    """
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME), pinned_clock():
        decision = decide_access([], MISSING_STATUS, EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "free"

    messages = errors_in(caplog)
    assert messages, (
        "clause 2.19 requires an ERROR record for an absent productSubscriberStatus; "
        f"highest level observed was "
        f"{max((r.levelname for r in caplog.records), default='<no records>')}"
    )
    log_text = "\n".join(messages)
    assert "productSubscriberStatus" in log_text
    assert EMAIL in log_text, "an alert nobody can trace to a customer is unactionable"


def test_present_but_null_status_does_not_log_an_error(caplog):
    """A field present and null is normal data for a customer with no subscription.

    This is the distinction the sentinel exists to draw. ``None`` alone cannot
    express both cases, because ``data.get("productSubscriberStatus")`` returns
    ``None`` whether the key was absent or explicitly null — and logging ERROR for
    every free-tier customer would bury the one case clause 2.19 cares about.
    """
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME), pinned_clock():
        decision = decide_access([], None, EMAIL)

    assert decision.granted is True
    assert decision.subscription_status == "free"
    assert errors_in(caplog) == [], (
        f"a present-but-null status must stay quiet. records={errors_in(caplog)}"
    )


def test_missing_status_and_null_status_reach_the_same_decision():
    """Only the log level differs; the response is identical (3.2 preserved)."""
    with pinned_clock():
        assert decide_access([], MISSING_STATUS, EMAIL) == decide_access([], None, EMAIL)


def test_missing_status_is_not_consulted_when_contracts_exist(caplog):
    """The ERROR is about a missing FALLBACK, so it must not fire when unused.

    With contracts present the customer-level field is never read (2.12), and an
    ERROR here would fire on every multi-contract customer whose payload happens to
    omit the field — noise that would train everyone to ignore the record.
    """
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME), pinned_clock():
        granted = decide_access([granting()], MISSING_STATUS, EMAIL)
        denied = decide_access([expired()], MISSING_STATUS, EMAIL)

    assert granted.granted is True
    assert denied.granted is False
    assert not any("ABSENT" in message for message in errors_in(caplog)), (
        f"records={errors_in(caplog)}"
    )


def test_missing_status_sentinel_is_a_singleton_distinct_from_none_and_falsey():
    """The sentinel is identity-checked, and is falsey so legacy guards still work."""
    assert MISSING_STATUS is subscription_auth.MISSING_STATUS
    assert MISSING_STATUS is not None
    assert not MISSING_STATUS
    assert repr(MISSING_STATUS) == "MISSING_STATUS"


# ---------------------------------------------------------------------------
# Clause 2.9 — order independence
# ---------------------------------------------------------------------------

def _comparable(decision: AccessDecision) -> tuple:
    """The three things clause 2.9 requires to be order-independent, plus the
    contract that produced them.

    ``deciding_contract`` is compared by ``contract_id`` rather than by identity so
    the tuple stays readable in a failure message.
    """
    return (
        decision.granted,
        decision.subscription_status,
        decision.denial_message,
        decision.redirect_url_needed,
        decision.deciding_contract.contract_id if decision.deciding_contract else None,
    )


def _mixed_contract_set() -> list[ContractView]:
    """A set spanning every branch of the per-contract rule, all denying.

    Deliberately all-denying so the denial-selection path — the one with a genuine
    ordering decision to make — is what gets permuted. Statuses differ, so picking
    the wrong contract changes both the copy and the reported status.
    """
    return [
        expired(
            contract_id="gid://shopify/SubscriptionContract/1000000001",
            status="PAUSED",
            created_at=datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc),
        ),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000002",
            status="CANCELLED",
            created_at=datetime(2026, 6, 30, 0, 0, tzinfo=timezone.utc),
            next_billing_date=NOW - timedelta(days=1),
        ),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000003",
            status="SUSPENDED",
            created_at=datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc),
            next_billing_date=NOW + timedelta(days=90),
        ),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000004",
            status="PAUSED",
            created_at=None,
            renewal_anchor=None,
            next_billing_date=None,
            interval="FORTNIGHT",
        ),
    ]


def test_denial_decision_is_identical_across_every_permutation():
    """Clause 2.9 on the denial path: verdict, status, and copy all order-free.

    Every one of the 24 orderings of a four-contract set, because the ordering bug
    is the one that shipped: Appstle returns contracts oldest-first and the unfixed
    code read whichever happened to be first.
    """
    nodes = _mixed_contract_set()

    with pinned_clock():
        baseline = _comparable(decide_access(nodes, "PAUSED", EMAIL))
        for ordering in permutations(nodes):
            assert _comparable(decide_access(list(ordering), "PAUSED", EMAIL)) == baseline, (
                "order changed the decision for ordering "
                f"{[c.contract_id for c in ordering]}"
            )

    assert baseline[0] is False
    assert baseline[2] == CANCELLED_DENIAL, "the newest contract is the CANCELLED one"


def test_granting_decision_is_identical_across_every_permutation():
    """Clause 2.9 on the grant path, with one granting contract among several."""
    nodes = _mixed_contract_set()
    nodes.append(
        granting(
            contract_id="gid://shopify/SubscriptionContract/1000000005",
            created_at=datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc),
        )
    )

    with pinned_clock():
        baseline = _comparable(decide_access(nodes, "CANCELLED", EMAIL))
        for ordering in permutations(nodes):
            assert _comparable(decide_access(list(ordering), "CANCELLED", EMAIL)) == baseline, (
                "order changed the decision for ordering "
                f"{[c.contract_id for c in ordering]}"
            )

    assert baseline[0] is True
    assert baseline[1] == "active"


def test_multiple_granting_contracts_are_order_independent():
    """Two granting contracts of different ages still name the same decider."""
    nodes = [
        granting(
            contract_id="gid://shopify/SubscriptionContract/1000000001",
            created_at=NOW - timedelta(days=400),
        ),
        granting(
            contract_id="gid://shopify/SubscriptionContract/1000000002",
            created_at=NOW - timedelta(days=30),
        ),
        contract(
            contract_id="gid://shopify/SubscriptionContract/1000000003",
            status="ACTIVE",
            created_at=NOW - timedelta(days=200),
            next_billing_date=NOW - timedelta(days=1),
        ),
    ]

    with pinned_clock():
        results = {_comparable(decide_access(list(o), None, EMAIL)) for o in permutations(nodes)}

    assert len(results) == 1, f"order-dependent outcomes: {results}"


# ---------------------------------------------------------------------------
# Purity — no I/O, no mutation, and the clock only through the seam
# ---------------------------------------------------------------------------

def test_decide_access_does_not_mutate_or_reorder_the_input():
    """The caller's list survives the call unchanged.

    ``verify_subscription()`` accumulates contracts across customer records and
    logs them after deciding, so a function that sorted its argument in place would
    quietly rewrite what the log reports.
    """
    nodes = _mixed_contract_set()
    before = list(nodes)

    with pinned_clock():
        decide_access(nodes, "PAUSED", EMAIL)

    assert nodes == before
    assert [c.contract_id for c in nodes] == [c.contract_id for c in before]


def test_decide_access_accepts_a_generator():
    """A one-shot iterable is materialized once, not consumed twice and lost."""
    nodes = [expired(), granting()]

    with pinned_clock():
        decision = decide_access((c for c in nodes), "PAUSED", EMAIL)

    assert decision.granted is True


def test_decide_access_reads_the_clock_only_through_the_utcnow_seam():
    """The same inputs flip verdict when only ``_utcnow()`` moves.

    Design change 2b: if this fails, the pinned-clock suites have silently stopped
    pinning anything and every date-dependent assertion is at the mercy of the wall
    clock.
    """
    nodes = [granting(next_billing_date=NOW + timedelta(days=10))]

    with pinned_clock(NOW):
        assert decide_access(nodes, "PAUSED", EMAIL).granted is True

    with pinned_clock(NOW + timedelta(days=11)):
        later = decide_access(nodes, "PAUSED", EMAIL)

    assert later.granted is False
    assert later.denial_message == EXPIRED_DENIAL


def test_decide_access_works_without_an_email():
    """``email`` is for the log line only; the decision must not depend on it."""
    with pinned_clock():
        assert decide_access([granting()], "PAUSED", None) == decide_access(
            [granting()], "PAUSED", EMAIL
        )


def test_every_denial_requests_a_redirect_and_every_grant_does_not():
    """``redirect_url_needed`` tracks ``granted`` exactly, on every path.

    A denial without a resubscribe URL is a dead end for a customer who wants to
    pay; a grant carrying one would put a redirect in a success response.
    """
    cases = [
        ([granting()], "PAUSED"),
        ([expired()], "PAUSED"),
        ([], "ACTIVE"),
        ([], "PAUSED"),
        ([], "CANCELLED"),
        ([], None),
        ([], MISSING_STATUS),
    ]

    with pinned_clock():
        for contracts, fallback in cases:
            decision = decide_access(contracts, fallback, EMAIL)
            assert decision.redirect_url_needed is (not decision.granted), (
                f"contracts={len(contracts)} fallback={fallback!r} → {decision}"
            )
            assert (decision.denial_message is None) is decision.granted, (
                f"a denial needs copy and a grant must not carry any: {decision}"
            )
