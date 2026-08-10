"""Unit tests for the pure module-level helpers in ``backend/subscription_auth.py``.

Task 8.2 covers ``_parse_iso8601()`` and the ``ContractView`` dataclass; Task 8.3
adds ``_add_calendar_interval()``.  Task 8.4 appends ``_paid_through()`` and
``_contract_grants()`` to this same module.  Task 9.1 adds
``_parse_contract_nodes()``, Task 9.2 ``_extract_customer_ids()``, and Task 9.3
the contract pagination helpers.  Task 9.6 appends ``_is_bypass_email()``, the
allowlist parse ``login()`` and ``refresh()`` now share.

Almost everything here is pure Python: no HTTP, no database, no Appstle
credentials, no service instance.  The one exception is the pagination section at
the end — ``_fetch_contract_pages()`` is a method, because following a page means
issuing a request through the ``_appstle_get()`` seam — so those cases build an
offline service via ``tests/subscription_harness.py`` and patch that seam.  Still
no network and no database.

Nothing in this module drives ``login()`` / ``refresh()`` — those assertions live
in the property suites.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make the repository root importable so ``backend.*`` resolves regardless of
# where pytest is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend import subscription_auth  # noqa: E402
from backend.subscription_auth import (  # noqa: E402
    ContractView,
    _add_calendar_interval,
    _contract_grants,
    _extract_customer_ids,
    _is_bypass_email,
    _paid_through,
    _parse_iso8601,
)


# ---------------------------------------------------------------------------
# _parse_iso8601
# ---------------------------------------------------------------------------

def test_parse_iso8601_z_suffix():
    """The ``Z`` suffix Appstle actually sends parses to a UTC-aware datetime."""
    parsed = _parse_iso8601("2026-08-27T19:00:00Z")

    assert parsed == datetime(2026, 8, 27, 19, 0, 0, tzinfo=timezone.utc)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_parse_iso8601_explicit_offset_normalized_to_utc():
    """An explicit non-UTC offset is honoured and converted to UTC."""
    parsed = _parse_iso8601("2026-08-27T19:00:00+05:00")

    assert parsed == datetime(2026, 8, 27, 14, 0, 0, tzinfo=timezone.utc)
    assert parsed.utcoffset() == timedelta(0)


def test_parse_iso8601_naive_input_coerced_to_utc():
    """A naive timestamp is treated as UTC rather than left naive."""
    parsed = _parse_iso8601("2026-08-27T19:00:00")

    assert parsed == datetime(2026, 8, 27, 19, 0, 0, tzinfo=timezone.utc)
    assert parsed.tzinfo is not None


def test_parse_iso8601_garbage_returns_none_and_logs(caplog):
    """Unparseable input yields ``None`` plus a log record, never an exception."""
    with caplog.at_level("WARNING", logger="backend.subscription_auth"):
        parsed = _parse_iso8601("not-a-date")

    assert parsed is None
    assert any(
        "Failed to parse ISO 8601 datetime" in record.getMessage()
        for record in caplog.records
    )


def test_parse_iso8601_none_returns_none_without_logging(caplog):
    """A null date is normal Appstle data, so it must not be logged as a failure."""
    with caplog.at_level("WARNING", logger="backend.subscription_auth"):
        parsed = _parse_iso8601(None)

    assert parsed is None
    assert caplog.records == []


@pytest.mark.parametrize("value", ["", "   ", 12345, [], {}])
def test_parse_iso8601_other_bad_inputs_return_none(value):
    """Empty strings and non-string types fall through to ``None``, not a raise."""
    assert _parse_iso8601(value) is None


def test_parse_iso8601_passes_through_datetime():
    """A datetime given directly is normalized rather than rejected."""
    naive = datetime(2026, 8, 27, 19, 0, 0)

    assert _parse_iso8601(naive) == datetime(2026, 8, 27, 19, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# ContractView
# ---------------------------------------------------------------------------

def test_contract_view_datetimes_are_utc_aware_at_construction():
    """Naive datetimes handed to the constructor come back UTC-aware."""
    view = ContractView(
        customer_id=2788838535,
        contract_id="gid://shopify/SubscriptionContract/1",
        status="PAUSED",
        next_billing_date=datetime(2026, 8, 27, 19, 0, 0),
        created_at=datetime(2026, 6, 16, 12, 0, 0),
        renewal_anchor=datetime(2026, 6, 16, 12, 0, 0),
        renewal_anchor_field="createdAt",
        interval="MONTH",
        interval_count=1,
    )

    for value in (view.next_billing_date, view.created_at, view.renewal_anchor):
        assert value.tzinfo is not None
        assert value.utcoffset() == timedelta(0)


def test_contract_view_converts_non_utc_offsets():
    """An aware datetime with another offset is converted, not merely accepted."""
    view = ContractView(
        customer_id=1,
        next_billing_date=datetime(2026, 8, 27, 19, 0, 0, tzinfo=timezone(timedelta(hours=5))),
    )

    assert view.next_billing_date == datetime(2026, 8, 27, 14, 0, 0, tzinfo=timezone.utc)


def test_contract_view_defaults_and_null_dates():
    """Only ``customer_id`` is required; ``interval_count`` defaults to 1."""
    view = ContractView(customer_id=42)

    assert view.customer_id == 42
    assert view.contract_id is None
    assert view.status is None
    assert view.next_billing_date is None
    assert view.created_at is None
    assert view.renewal_anchor is None
    assert view.renewal_anchor_field is None
    assert view.interval is None
    assert view.interval_count == 1


def test_contract_view_is_frozen():
    """Frozen, so a parsed contract cannot be mutated behind the decision's back."""
    view = ContractView(customer_id=1, status="ACTIVE")

    with pytest.raises(Exception):
        view.status = "CANCELLED"  # type: ignore[misc]

# ---------------------------------------------------------------------------
# _add_calendar_interval (Task 8.3, design change 3, requirement 2.7)
# ---------------------------------------------------------------------------
#
# The unit whose failure mode is invisible: a 30-day approximation is right often
# enough to look correct in a spot check and wrong by a day or three every month.
# On a monthly plan that is a rounding error; on an annual plan renewed for years
# it is what decides whether a paying customer can log in.

ANCHOR = datetime(2026, 6, 16, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "interval,count,expected",
    [
        # Each of the four supported units at count 1.
        ("DAY", 1, datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)),
        ("WEEK", 1, datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)),
        ("MONTH", 1, datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)),
        ("YEAR", 1, datetime(2027, 6, 16, 12, 0, tzinfo=timezone.utc)),
    ],
)
def test_add_calendar_interval_each_supported_unit(interval, count, expected):
    """DAY, WEEK, MONTH, and YEAR all advance the anchor by one calendar unit.

    Only DAY and MONTH were observed in the capture (design Finding 2); WEEK and
    YEAR are supported anyway, so they are tested anyway.
    """
    assert _add_calendar_interval(ANCHOR, interval, count) == expected


@pytest.mark.parametrize(
    "interval,count,expected",
    [
        # intervalCount 30 with unit DAY is the live "30-Day Access" product, not
        # a hypothetical: assuming count == 1 would understate paid time by 29
        # days on a real Appstle contract.
        ("DAY", 30, datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)),
        ("WEEK", 2, datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)),
        ("MONTH", 3, datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)),
        ("MONTH", 12, datetime(2027, 6, 16, 12, 0, tzinfo=timezone.utc)),
        ("YEAR", 2, datetime(2028, 6, 16, 12, 0, tzinfo=timezone.utc)),
    ],
)
def test_add_calendar_interval_honours_interval_count(interval, count, expected):
    """``intervalCount`` multiplies the unit (design Finding 2: 30 is common)."""
    assert _add_calendar_interval(ANCHOR, interval, count) == expected


def test_add_calendar_interval_month_end_rollover_clamps():
    """Jan 31 + 1 month is Feb 28, not Mar 2 or Mar 3.

    A 30-day approximation lands on Mar 2 in 2027 — a full three days of paid
    time invented out of nothing, in the direction that grants access.
    """
    anchor = datetime(2027, 1, 31, 9, 30, tzinfo=timezone.utc)

    result = _add_calendar_interval(anchor, "MONTH", 1)

    assert result == datetime(2027, 2, 28, 9, 30, tzinfo=timezone.utc)
    assert result != anchor + timedelta(days=30)


def test_add_calendar_interval_month_end_rollover_clamps_in_leap_year():
    """Jan 31 + 1 month clamps to Feb 29 when February has 29 days."""
    anchor = datetime(2028, 1, 31, 9, 30, tzinfo=timezone.utc)

    assert _add_calendar_interval(anchor, "MONTH", 1) == datetime(
        2028, 2, 29, 9, 30, tzinfo=timezone.utc
    )


def test_add_calendar_interval_leap_day_plus_one_year():
    """Feb 29 + 1 year is Feb 28 of a non-leap year, and never a crash.

    ``anchor.replace(year=anchor.year + 1)`` raises ``ValueError`` on this input,
    which is the other way naive interval arithmetic fails: not a wrong date, a
    500 on a login.
    """
    anchor = datetime(2028, 2, 29, 0, 0, tzinfo=timezone.utc)

    result = _add_calendar_interval(anchor, "YEAR", 1)

    assert result == datetime(2029, 2, 28, 0, 0, tzinfo=timezone.utc)
    # No 365-day divergence assertion here: from a Feb 29 anchor the leap day is
    # already behind, so +365 days happens to land on the same 2029-02-28. The
    # units diverge when the leap day is AHEAD of the anchor, which is the case
    # asserted in the next test.


def test_add_calendar_interval_year_differs_from_365_day_approximation():
    """Across a leap day, +1 YEAR and +365 days are different instants."""
    anchor = datetime(2027, 6, 16, 12, 0, tzinfo=timezone.utc)  # 2028 is a leap year

    assert _add_calendar_interval(anchor, "YEAR", 1) == datetime(
        2028, 6, 16, 12, 0, tzinfo=timezone.utc
    )
    assert _add_calendar_interval(anchor, "YEAR", 1) != anchor + timedelta(days=365)


@pytest.mark.parametrize(
    "interval",
    [
        "FORTNIGHT",   # a unit Appstle has never sent
        "BIWEEKLY",
        "month",       # lower case — deliberately NOT recognized, see below
        "Month",
        "DAYS",        # plural
        "",
        None,          # billingPolicy absent entirely
        123,           # non-string
    ],
)
def test_add_calendar_interval_unrecognized_unit_returns_none(interval):
    """An unrecognized unit yields ``None`` rather than a guess.

    Case sensitivity is intentional. Appstle sends upper-case units, so
    ``"month"`` is a payload shape we do not understand, and clause 2.8 requires
    an unrecognized unit to make ``paid_through`` underivable — which denies
    access — rather than to be interpreted charitably into a grant. The harness's
    ``UNRECOGNIZED_INTERVALS`` and the fix-checking oracle both classify
    ``"month"`` the same way.
    """
    assert _add_calendar_interval(ANCHOR, interval, 1) is None


def test_add_calendar_interval_null_anchor_returns_none():
    """Clause 2.8: interval arithmetic is never attempted on a null anchor."""
    assert _add_calendar_interval(None, "MONTH", 1) is None


@pytest.mark.parametrize("count", [0, -1, None, 1.5, "3", True])
def test_add_calendar_interval_invalid_count_returns_none(count):
    """A non-positive, non-integer, or missing ``intervalCount`` is underivable.

    ``True`` is rejected explicitly: it is an ``int`` subclass that would
    otherwise silently behave as ``1``, and a boolean in this field means the
    payload is not what we think it is.
    """
    assert _add_calendar_interval(ANCHOR, "MONTH", count) is None


def test_add_calendar_interval_defaults_count_to_one():
    """``count`` defaults to 1, matching ``ContractView.interval_count``."""
    assert _add_calendar_interval(ANCHOR, "MONTH") == datetime(
        2026, 7, 16, 12, 0, tzinfo=timezone.utc
    )


def test_add_calendar_interval_result_is_utc_aware():
    """A naive anchor comes back UTC-aware, so ``paid_through`` stays comparable."""
    result = _add_calendar_interval(datetime(2026, 6, 16, 12, 0), "MONTH", 1)

    assert result == datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)


def test_add_calendar_interval_converts_non_utc_anchor():
    """An anchor on another offset is normalized before the addition."""
    anchor = datetime(2026, 6, 16, 1, 0, tzinfo=timezone(timedelta(hours=5)))

    # 2026-06-16T01:00+05:00 is 2026-06-15T20:00Z, so +1 month is 2026-07-15T20:00Z.
    assert _add_calendar_interval(anchor, "MONTH", 1) == datetime(
        2026, 7, 15, 20, 0, tzinfo=timezone.utc
    )


def test_add_calendar_interval_overflow_returns_none_without_raising():
    """An anchor near ``datetime.max`` yields ``None``, never an exception.

    Nothing in a login path may raise out of date arithmetic.
    """
    anchor = datetime(9999, 12, 31, 23, 0, tzinfo=timezone.utc)

    assert _add_calendar_interval(anchor, "YEAR", 5) is None

# ---------------------------------------------------------------------------
# _paid_through / _contract_grants (Task 8.4, design changes 4 and 5,
# requirements 2.2, 2.3, 2.4, 2.6, 2.7, 2.8)
# ---------------------------------------------------------------------------
#
# NOW is pinned rather than read from the real clock. ``_contract_grants()``
# compares ``paid_through`` against ``_utcnow()`` (design change 2b), and a test
# whose verdict depends on the wall clock is a test that inverts itself later.

NOW = datetime(2026, 8, 9, 1, 31, 12, tzinfo=timezone.utc)
LOGGER_NAME = "backend.subscription_auth"


@contextmanager
def pinned_clock(instant: datetime = NOW):
    """Pin ``_utcnow()`` for the duration of the block.

    Patched as a module attribute, which is the single seam design change 2b
    exists to provide. ``monkeypatch`` would do the same job, but a
    function-scoped fixture cannot be used from a Hypothesis ``@given`` test, and
    keeping one mechanism here means these tests and the property suite pin the
    clock the same way.
    """
    original = subscription_auth._utcnow
    subscription_auth._utcnow = lambda: instant
    try:
        yield instant
    finally:
        subscription_auth._utcnow = original


def contract(**overrides) -> ContractView:
    """A ``ContractView`` with the fields these tests care about, others defaulted.

    ``renewal_anchor`` defaults to whatever ``created_at`` is, which is what the
    parser does per design Finding 1 — ``createdAt`` is the only anchor Appstle
    exposes.
    """
    fields = {
        "customer_id": 2788838535,
        "contract_id": "gid://shopify/SubscriptionContract/1",
        "status": "PAUSED",
        "interval": "MONTH",
        "interval_count": 1,
    }
    fields.update(overrides)
    if "renewal_anchor" not in fields and fields.get("created_at") is not None:
        fields["renewal_anchor"] = fields["created_at"]
        fields.setdefault("renewal_anchor_field", "createdAt")
    return ContractView(**fields)


def errors_in(caplog) -> list[str]:
    import logging

    return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]


# --- _paid_through: nextBillingDate is the strong signal --------------------

def test_paid_through_prefers_next_billing_date_over_the_anchor(caplog):
    """``nextBillingDate`` wins outright; the anchor is not consulted at all.

    Per design Finding 3 this is the only path real data ever takes — every
    captured contract carried a non-null ``nextBillingDate``. The anchor here is
    deliberately set to a date whose ``+ 1 MONTH`` is a *different* instant, so a
    result equal to ``nextBillingDate`` cannot be a coincidence.
    """
    view = contract(
        next_billing_date=datetime(2026, 8, 27, 19, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 2, 22, 27, 41, tzinfo=timezone.utc),
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result == datetime(2026, 8, 27, 19, 0, tzinfo=timezone.utc)
    assert result != _add_calendar_interval(view.created_at, "MONTH", 1)
    assert errors_in(caplog) == [], (
        "the strong path must be silent; an ERROR here would fire on every "
        f"real contract. records={errors_in(caplog)}"
    )


def test_paid_through_prefers_next_billing_date_even_when_it_is_in_the_past():
    """A past ``nextBillingDate`` is still the answer, not a reason to derive one.

    The contract is simply not paid through any more. Falling back to the anchor
    here would invent paid time for a lapsed customer.
    """
    view = contract(
        next_billing_date=datetime(2026, 5, 23, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert _paid_through(view) == datetime(2026, 5, 23, 0, 0, tzinfo=timezone.utc)


# --- _paid_through: the anchor fallback ------------------------------------

def test_paid_through_derives_from_created_at_anchor_and_logs_error(caplog):
    """No ``nextBillingDate`` → ``createdAt`` + one interval, with an ERROR record.

    The ERROR is required (clause 2.6) because this path is exact only for a
    contract that has never renewed. Verified against the captured renewed
    subscriber: ``createdAt`` 2026-06-16 with MONTH × 1 derives 2026-07-16 where
    the real paid-through was 2026-08-16 — one full interval short.
    """
    view = contract(
        next_billing_date=None,
        created_at=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
        interval="MONTH",
        interval_count=1,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result == datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    messages = errors_in(caplog)
    assert any("createdAt" in message for message in messages), (
        f"clause 2.6 requires an ERROR naming the weak anchor. records={messages}"
    )


def test_paid_through_honours_interval_count_in_the_fallback():
    """``intervalCount`` 30 with DAY is the live 30-day product, not a hypothetical."""
    view = contract(
        next_billing_date=None,
        created_at=datetime(2026, 4, 23, 0, 0, tzinfo=timezone.utc),
        interval="DAY",
        interval_count=30,
    )

    assert _paid_through(view) == datetime(2026, 5, 23, 0, 0, tzinfo=timezone.utc)


def test_paid_through_uses_renewal_anchor_when_it_is_set_to_a_stronger_field(caplog):
    """An explicitly-named non-``createdAt`` anchor is used and NOT logged as weak.

    This documents the collapse recorded in design Finding 1 rather than a live
    branch: Appstle exposes no ``lastBillingDate``-style field today, so
    ``renewal_anchor_field`` is always ``"createdAt"`` or unset in practice. The
    function still reads ``renewal_anchor`` so that the day a stronger anchor
    appears, only the parser changes — and the ERROR log correctly stays quiet for
    it, because the "understates paid time" warning would then be false.
    """
    view = contract(
        next_billing_date=None,
        created_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        renewal_anchor=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
        renewal_anchor_field="lastBillingDate",
        interval="MONTH",
        interval_count=1,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result == datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc), (
        "the named anchor must win over created_at"
    )
    assert errors_in(caplog) == []


def test_paid_through_falls_back_to_created_at_when_renewal_anchor_is_unset(caplog):
    """A view with ``renewal_anchor`` unset still derives from ``created_at``.

    The parser fills both, but a partially-populated view must not silently lose
    its only anchor and turn into a denial.
    """
    view = ContractView(
        customer_id=1,
        contract_id="gid://shopify/SubscriptionContract/2",
        status="PAUSED",
        next_billing_date=None,
        created_at=datetime(2026, 8, 1, 1, 31, 12, tzinfo=timezone.utc),
        interval="MONTH",
        interval_count=1,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result == datetime(2026, 9, 1, 1, 31, 12, tzinfo=timezone.utc)
    assert any("createdAt" in message for message in errors_in(caplog))


# --- _paid_through: the underivable cases (clause 2.8) ---------------------

def test_paid_through_absent_billing_policy_returns_none_and_logs_error(caplog):
    """``billingPolicy`` absent → ``interval is None`` → underivable + ERROR."""
    view = contract(
        next_billing_date=None,
        created_at=datetime(2026, 8, 1, 1, 31, 12, tzinfo=timezone.utc),
        interval=None,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result is None
    assert any("underivable" in message for message in errors_in(caplog)), (
        f"clause 2.8 requires an ERROR record. records={errors_in(caplog)}"
    )


@pytest.mark.parametrize("interval", ["FORTNIGHT", "BIWEEKLY", "month", "", "DAYS"])
def test_paid_through_unrecognized_interval_returns_none_and_logs_error(interval, caplog):
    """An unrecognized unit is underivable, never charitably interpreted.

    ``"month"`` is in this list on purpose: reading it as MONTH would hand out a
    month of access on the strength of a payload shape we do not understand.
    Clause 2.8 requires underivable instead, which denies.
    """
    view = contract(
        next_billing_date=None,
        created_at=datetime(2026, 8, 1, 1, 31, 12, tzinfo=timezone.utc),
        interval=interval,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    assert result is None
    assert any("underivable" in message for message in errors_in(caplog))


def test_paid_through_null_anchor_returns_none_and_logs_error(caplog):
    """A null anchor is underivable, and no weak-anchor ERROR is emitted for it.

    Clause 2.8: interval arithmetic on a null anchor is meaningless and must not
    be attempted. The log must say "underivable" and must NOT claim the value was
    derived from ``createdAt``, since there was no ``createdAt`` to derive from.
    """
    view = ContractView(
        customer_id=1,
        contract_id="gid://shopify/SubscriptionContract/3",
        status="PAUSED",
        next_billing_date=None,
        created_at=None,
        renewal_anchor=None,
        interval="MONTH",
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        result = _paid_through(view)

    messages = errors_in(caplog)
    assert result is None
    assert any("underivable" in message for message in messages)
    assert not any("derived from" in message for message in messages), (
        f"nothing was derived, so nothing may be reported as derived. records={messages}"
    )


def test_paid_through_error_log_names_the_contract(caplog):
    """The ERROR record identifies which contract failed, not just that one did.

    An alert that cannot be traced to a customer is an alert nobody can action.
    """
    view = contract(
        customer_id=2788838535,
        contract_id="gid://shopify/SubscriptionContract/84206911553",
        next_billing_date=None,
        created_at=datetime(2026, 8, 1, 1, 31, 12, tzinfo=timezone.utc),
        interval="FORTNIGHT",
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME):
        _paid_through(view)

    log_text = "\n".join(errors_in(caplog))
    assert "84206911553" in log_text
    assert "2788838535" in log_text


# --- _contract_grants: ACTIVE short-circuits (clause 2.2) ------------------

def test_contract_grants_active_with_paid_through_in_the_past():
    """ACTIVE grants even though its paid-through has passed — the dunning grace.

    Appstle can hold a contract ACTIVE with ``nextBillingDate`` behind us while a
    renewal payment retries. Clause 2.2 grants through that window deliberately;
    it is the one branch where a non-paying account keeps access.
    """
    view = contract(
        status="ACTIVE",
        next_billing_date=NOW - timedelta(days=5),
        created_at=NOW - timedelta(days=35),
    )

    with pinned_clock():
        assert _contract_grants(view) is True


def test_contract_grants_active_with_null_paid_through_and_no_error_log(caplog):
    """ACTIVE grants with nothing to derive from, and derives nothing.

    The short-circuit is asserted through its side effects as well as its verdict:
    with a null anchor and no billing policy, ``_paid_through()`` would log two
    ERROR records. Silence proves ``paid_through`` was never consulted, which is
    what "short-circuits without touching paid_through" means.
    """
    view = ContractView(
        customer_id=1,
        contract_id="gid://shopify/SubscriptionContract/4",
        status="ACTIVE",
        next_billing_date=None,
        created_at=None,
        interval=None,
    )

    with caplog.at_level("ERROR", logger=LOGGER_NAME), pinned_clock():
        assert _contract_grants(view) is True

    assert errors_in(caplog) == [], (
        f"paid_through must not be consulted for ACTIVE. records={errors_in(caplog)}"
    )


# --- _contract_grants: PAUSED / CANCELLED gate on paid_through (2.3) -------

@pytest.mark.parametrize("status", ["PAUSED", "CANCELLED"])
def test_contract_grants_paused_and_cancelled_with_paid_time_remaining(status):
    """Paid time remaining grants, cancelled included.

    Cancelling means "stop billing me", not "revoke the period I already paid
    for". This is Preservation Exception 2.3 / 1.7 for the CANCELLED half.
    """
    view = contract(status=status, next_billing_date=NOW + timedelta(days=21))

    with pinned_clock():
        assert _contract_grants(view) is True


@pytest.mark.parametrize("status", ["PAUSED", "CANCELLED"])
def test_contract_grants_paused_and_cancelled_with_paid_time_exhausted(status):
    """A past paid-through does not grant."""
    view = contract(status=status, next_billing_date=NOW - timedelta(days=1))

    with pinned_clock():
        assert _contract_grants(view) is False


@pytest.mark.parametrize("status", ["PAUSED", "CANCELLED"])
def test_contract_grants_paused_and_cancelled_at_exactly_now(status):
    """``paid_through == now`` does not grant: the comparison is strictly greater.

    A boundary worth pinning rather than leaving to whichever inequality got
    typed — the design says ``pt > NOW()``, and paid time that ends at this
    instant has ended.
    """
    view = contract(status=status, next_billing_date=NOW)

    with pinned_clock():
        assert _contract_grants(view) is False


@pytest.mark.parametrize("status", ["PAUSED", "CANCELLED"])
def test_contract_grants_paused_and_cancelled_with_underivable_paid_through(status):
    """An underivable ``paid_through`` does not grant (clause 2.8, Property 12)."""
    view = contract(
        status=status,
        next_billing_date=None,
        created_at=NOW - timedelta(days=8),
        interval="FORTNIGHT",
    )

    with pinned_clock():
        assert _contract_grants(view) is False


def test_contract_grants_paused_derives_paid_through_from_the_anchor():
    """A PAUSED contract with a null ``nextBillingDate`` can still grant.

    Preservation Exception 2.6 / 1.6: anchor eight days ago on a monthly plan is
    roughly 22 days of paid time remaining. The unfixed code returns 403 here
    because it never attempts the derivation.
    """
    view = contract(
        status="PAUSED",
        next_billing_date=None,
        created_at=NOW - timedelta(days=8),
        interval="MONTH",
        interval_count=1,
    )

    with pinned_clock():
        assert _contract_grants(view) is True


# --- _contract_grants: everything else does not grant (clause 2.4) --------

@pytest.mark.parametrize(
    "status",
    ["EXPIRED", "SUSPENDED", "FAILED", "junk", "0", "", "ACTIVE_TRIAL", "PAUSE"],
)
def test_contract_grants_unknown_status_does_not_grant(status):
    """An unrecognized label is not evidence of paid time, whatever the dates say.

    ``nextBillingDate`` is deliberately in the future for all of these: the point
    is that a future date cannot rescue a status we do not understand.
    ``"ACTIVE_TRIAL"`` and ``"PAUSE"`` guard the matching from being a substring
    or prefix test.
    """
    view = contract(status=status, next_billing_date=NOW + timedelta(days=30))

    with pinned_clock():
        assert _contract_grants(view) is False


@pytest.mark.parametrize("status", [None, 0, [], {}])
def test_contract_grants_null_or_non_string_status_does_not_grant(status):
    """A null status does not grant, and a non-string one does not raise."""
    view = contract(status=status, next_billing_date=NOW + timedelta(days=30))

    with pinned_clock():
        assert _contract_grants(view) is False


# --- _contract_grants: case-insensitive status matching -------------------

@pytest.mark.parametrize("status", ["active", "Active", "aCtIvE", "ACTIVE"])
def test_contract_grants_active_is_case_insensitive(status):
    """``UPPER(k.status) = "ACTIVE"`` — the label is classified, not parsed."""
    view = contract(status=status, next_billing_date=NOW - timedelta(days=5))

    with pinned_clock():
        assert _contract_grants(view) is True


@pytest.mark.parametrize("status", ["paused", "Paused", "cancelled", "CanCelled"])
def test_contract_grants_paid_time_statuses_are_case_insensitive(status):
    """Lower-case PAUSED / CANCELLED still reach the paid-time gate, both ways."""
    granting = contract(status=status, next_billing_date=NOW + timedelta(days=3))
    denying = contract(status=status, next_billing_date=NOW - timedelta(days=3))

    with pinned_clock():
        assert _contract_grants(granting) is True
        assert _contract_grants(denying) is False


def test_status_case_insensitivity_is_asymmetric_with_interval_case_sensitivity():
    """The two case rules disagree on purpose; this pins the asymmetry.

    Same contract, same lower-casing applied to two different fields. The status
    ``"paused"`` is recognized, because classifying a label into a known bucket is
    safe and an unrecognized label denies either way. The interval ``"month"`` is
    NOT recognized, because it feeds arithmetic that produces the date access is
    granted through, and interpreting an unfamiliar unit charitably would invent
    paid time (clause 2.8). Tolerant where it picks a bucket, strict where it
    hands out access.
    """
    lower_status_recognized = contract(
        status="paused",
        next_billing_date=NOW + timedelta(days=3),
    )
    lower_interval_not_recognized = contract(
        status="paused",
        next_billing_date=None,
        created_at=NOW - timedelta(days=1),
        interval="month",
    )

    with pinned_clock():
        assert _contract_grants(lower_status_recognized) is True
        assert _paid_through(lower_interval_not_recognized) is None
        assert _contract_grants(lower_interval_not_recognized) is False


# --- _contract_grants reads the clock through the _utcnow() seam ----------

def test_contract_grants_reads_the_clock_through_the_utcnow_seam():
    """The same contract flips verdict when only ``_utcnow()`` moves.

    Design change 2b: the clock must be a single monkeypatchable seam, not an
    inline ``datetime.now()``. If this test fails, the pinned-clock fixture suite
    silently stops pinning anything.
    """
    view = contract(status="PAUSED", next_billing_date=NOW + timedelta(days=10))

    with pinned_clock(NOW):
        assert _contract_grants(view) is True

    with pinned_clock(NOW + timedelta(days=11)):
        assert _contract_grants(view) is False

# ---------------------------------------------------------------------------
# DENIAL_MESSAGES / _get_denial_message / _normalize_status
# (Task 8.5, design change 14, requirements 1.13, 2.17, 2.21, 3.3)
# ---------------------------------------------------------------------------
#
# The dict is dead code today: login() and refresh() carry the denial copy inline
# and never consult it. Task 8.6 makes it live through decide_access(), which is
# why its values have to be aligned FIRST. The pre-fix values read "Your
# subscription has expired" and "Your subscription is paused" — no "Resubscribe
# to continue." sentence, and PAUSED described as paused rather than expired.
# Wiring the dict in before aligning it would have rewritten the denial copy on
# the one path clause 3.3 promises to preserve byte for byte.
#
# The expected strings below are NOT transcribed. They are read from the
# preservation golden recorded from the unfixed code in Task 7, so this suite
# cannot agree with a hand-typed string that itself drifted.

_GOLDEN_PATH = _REPO_ROOT / "tests" / "fixtures" / "appstle" / "goldens" / "preservation_baseline.json"

# The two golden cases that carry live denial copy: an all-PAUSED-contracts
# customer (3.3, the preserved expired denial) and an empty-nodes customer whose
# customer-level status is CANCELLED (2.12).
_GOLDEN_EXPIRED_CASE = "login/all_contracts_expired"
_GOLDEN_CANCELLED_CASE = "login/empty_nodes_status_cancelled"


def _golden_denial_copy(case_id: str) -> str:
    """Read one denial string out of the Task 7 golden file.

    Deliberately not a transcription: the whole point of clause 2.21 is that the
    aligned dict must match what the UNFIXED code actually emitted, and the golden
    is the only mechanical record of that.
    """
    import json

    if not _GOLDEN_PATH.exists():
        pytest.fail(
            f"Preservation goldens are missing at {_GOLDEN_PATH}. They are recorded "
            f"from the unfixed code in Task 7 and are the source of truth for the "
            f"denial copy clause 2.21 pins."
        )

    with _GOLDEN_PATH.open(encoding="utf-8") as handle:
        goldens = json.load(handle)

    case = goldens["named"][case_id]
    assert case["status_code"] == 403, (
        f"Golden {case_id} is not a denial ({case['status_code']}); it cannot "
        f"witness denial copy."
    )
    return case["body"]["error"]


def test_denial_messages_expired_copy_is_byte_identical_to_the_golden():
    """3.3 — the preserved expired denial, compared against the recorded baseline.

    This is the assertion Task 8.5 exists for. If ``DENIAL_MESSAGES["PAUSED"]``
    still said "Your subscription is paused", Task 8.6 would ship a silent copy
    change to every expired subscriber.
    """
    expected = _golden_denial_copy(_GOLDEN_EXPIRED_CASE)

    assert subscription_auth.DENIAL_MESSAGES["PAUSED"] == expected
    assert subscription_auth.DENIAL_MESSAGES["EXPIRED"] == expected
    assert subscription_auth._get_denial_message("PAUSED") == expected
    assert subscription_auth._get_denial_message("EXPIRED") == expected


def test_denial_messages_cancelled_copy_is_byte_identical_to_the_golden():
    """The cancelled copy, likewise read from the golden rather than retyped."""
    expected = _golden_denial_copy(_GOLDEN_CANCELLED_CASE)

    assert subscription_auth.DENIAL_MESSAGES["CANCELLED"] == expected
    assert subscription_auth._get_denial_message("CANCELLED") == expected


def test_denial_messages_exact_strings():
    """The full aligned dict, spelled out, so a partial edit cannot pass.

    The golden comparisons above prove the two live strings are right; this pins
    the whole mapping including the ACTIVE key, which has no golden because the
    unfixed code has no path that denies a customer whose status reads ACTIVE.
    """
    expired = "Your subscription has expired. Resubscribe to continue."
    cancelled = "Your subscription has been cancelled. Resubscribe to continue."

    assert subscription_auth.DENIAL_MESSAGES == {
        "ACTIVE": expired,
        "EXPIRED": expired,
        "PAUSED": expired,
        "CANCELLED": cancelled,
    }
    assert subscription_auth.DEFAULT_DENIAL_MESSAGE == "No subscription found"


def test_denial_messages_active_key_maps_to_the_expired_copy():
    """The pathological case: label says ACTIVE, yet the contract did not grant.

    ``_contract_grants()`` short-circuits ACTIVE to a grant, so decide_access()
    can only land here if the label and the decision disagree. Falling through to
    "No subscription found" would be worse — the customer has a subscription; it
    just is not granting.
    """
    assert (
        subscription_auth.DENIAL_MESSAGES["ACTIVE"]
        == subscription_auth.DENIAL_MESSAGES["EXPIRED"]
    )
    assert subscription_auth._get_denial_message("ACTIVE") == _golden_denial_copy(
        _GOLDEN_EXPIRED_CASE
    )


@pytest.mark.parametrize(
    "status", ["paused", "Paused", "pAuSeD", "cancelled", "CanCelled", "active"]
)
def test_get_denial_message_is_case_insensitive(status):
    """``DENIAL_MESSAGES.get(status.upper(), ...)`` — Appstle's casing is not trusted."""
    assert (
        subscription_auth._get_denial_message(status)
        == subscription_auth.DENIAL_MESSAGES[status.upper()]
    )


@pytest.mark.parametrize(
    "status",
    ["SUSPENDED", "FAILED", "NOT_FOUND", "junk", "0", "ACTIVE_TRIAL", "PAUSE"],
)
def test_get_denial_message_unknown_status_reaches_the_default(status):
    """Clause 8.5's "leave ``DEFAULT_DENIAL_MESSAGE`` reachable", half one.

    ``"ACTIVE_TRIAL"`` and ``"PAUSE"`` guard against the lookup degrading into a
    prefix or substring match, which would tell an ACTIVE_TRIAL customer their
    subscription had expired.
    """
    assert subscription_auth._get_denial_message(status) == "No subscription found"


@pytest.mark.parametrize("status", [None, "", "   "])
def test_get_denial_message_empty_status_reaches_the_default(status):
    """Half two: absent or blank status also falls back, and never raises.

    Note ``"   "`` is truthy, so it takes the dict-lookup path rather than the
    ``if not status`` guard, and still has to land on the default.
    """
    assert subscription_auth._get_denial_message(status) == "No subscription found"


def test_get_denial_message_never_returns_an_unaligned_string():
    """No reachable status yields copy missing the "Resubscribe" sentence.

    The pre-fix values ("Your subscription has expired", "Your subscription is
    paused") are exact prefixes of the aligned ones, so an equality check against
    one key could pass while another key kept the truncated copy. This sweeps
    every value instead.
    """
    for status, message in subscription_auth.DENIAL_MESSAGES.items():
        assert message.endswith("Resubscribe to continue."), (
            f"DENIAL_MESSAGES[{status!r}] is not aligned with the inline copy: {message!r}"
        )


# --- _normalize_status: unchanged by this fix, pinned because it goes live ---

@pytest.mark.parametrize(
    "status,expected",
    [
        ("ACTIVE", "active"),
        ("CANCELLED", "cancelled"),
        ("EXPIRED", "expired"),
        ("PAUSED", "paused"),
        ("paused", "paused"),
        ("CanCelled", "cancelled"),
        ("SUSPENDED", "not_found"),
        ("junk", "not_found"),
        (None, "not_found"),
        ("", "not_found"),
    ],
)
def test_normalize_status(status, expected):
    """The ``subscription_status`` a denial body reports, keyed off the same label.

    Behavior is unchanged by Task 8.5 — pinned here because Task 8.6 makes this
    helper live, and the golden expects ``"paused"`` in the 3.3 denial body.
    """
    assert subscription_auth._normalize_status(status) == expected


def test_normalize_status_matches_the_golden_denial_body():
    """The 3.3 golden reports ``subscription_status="paused"``; so must the helper.

    Message and status are read from the same label by decide_access(), so pinning
    only the copy would leave half the denial body unverified.
    """
    import json

    with _GOLDEN_PATH.open(encoding="utf-8") as handle:
        golden = json.load(handle)["named"][_GOLDEN_EXPIRED_CASE]

    assert subscription_auth._normalize_status("PAUSED") == golden["body"][
        "subscription_status"
    ]


# ---------------------------------------------------------------------------
# _parse_contract_nodes (Task 9.1, design change 8, requirements 1.5, 2.1, 2.20)
# ---------------------------------------------------------------------------
#
# The unit that carries the fix for root cause 1.  What it replaces read
# ``nodes[0].get("nextBillingDate")`` and discarded every other node, so the whole
# point of these tests is that NOTHING is dropped: every node becomes a
# ContractView, the per-contract ``status`` field is read for the first time
# anywhere in this codebase (clause 1.5), and a malformed entry costs only itself.
#
# Pure Python throughout: ``_parse_contract_nodes`` takes a raw payload dict and
# needs no service instance, no env config, and no clock.

_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "appstle"

DAVE_CUSTOMER_ID = 2788838535


def _load_appstle_fixture(name: str) -> dict:
    import json

    with (_FIXTURE_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _payload(*nodes: dict) -> dict:
    """Wrap contract nodes in the ``subscriptionContracts`` envelope Appstle sends."""
    return {
        "__typename": "Customer",
        "productSubscriberStatus": "PAUSED",
        "subscriptionContracts": {
            "__typename": "SubscriptionContractConnection",
            "nodes": list(nodes),
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False},
        },
    }


def _node(**overrides) -> dict:
    node = {
        "id": "gid://shopify/SubscriptionContract/1",
        "status": "PAUSED",
        "createdAt": "2026-06-02T22:27:41Z",
        "nextBillingDate": "2026-07-02T22:00:00Z",
        "billingPolicy": {"interval": "DAY", "intervalCount": 30},
    }
    node.update(overrides)
    return node


def test_parse_contract_nodes_returns_every_node_from_daves_real_payload():
    """Both of Dave's contracts are parsed — the truncation is gone.

    Dave's captured payload is the canonical counterexample: ``nodes[0]`` expired
    on 2026-07-02 and ``nodes[1]`` is paid through 2026-08-27.  The old parser saw
    only the first, which is why he was locked out.
    """
    payload = _load_appstle_fixture("dave_two_paused_contracts")
    raw_nodes = payload["subscriptionContracts"]["nodes"]
    assert len(raw_nodes) == 2, "fixture drift: Dave must have two contracts"

    contracts = subscription_auth._parse_contract_nodes(
        payload, DAVE_CUSTOMER_ID, "multi.contract@example.com"
    )

    assert len(contracts) == 2
    # Payload order is preserved, so a caller can still reason about nodes[0].
    assert [c.contract_id for c in contracts] == [n["id"] for n in raw_nodes]
    assert [c.customer_id for c in contracts] == [DAVE_CUSTOMER_ID, DAVE_CUSTOMER_ID]
    assert contracts[0].next_billing_date == datetime(2026, 7, 2, 22, 0, tzinfo=timezone.utc)
    assert contracts[1].next_billing_date == datetime(2026, 8, 27, 19, 0, tzinfo=timezone.utc)
    assert contracts[0].created_at == datetime(2026, 6, 2, 22, 27, 41, tzinfo=timezone.utc)
    assert [c.interval for c in contracts] == ["DAY", "DAY"]
    assert [c.interval_count for c in contracts] == [30, 30]


def test_parse_contract_nodes_reads_the_per_contract_status_of_every_node():
    """Clause 1.5 — the per-contract ``status`` field, read for the first time.

    Verbatim, not upper-cased: ``_contract_grants()`` does its own
    case-insensitive comparison, and normalizing here would throw away what
    Appstle actually sent before anyone could log it.
    """
    payload = _payload(
        _node(id="c-1", status="PAUSED"),
        _node(id="c-2", status="ACTIVE"),
        _node(id="c-3", status="CANCELLED"),
        _node(id="c-4", status="cancelled"),
        _node(id="c-5", status="FORTNIGHTLY_NONSENSE"),
        _node(id="c-6", status=None),
    )

    contracts = subscription_auth._parse_contract_nodes(payload, 1, "x@example.com")

    assert [c.status for c in contracts] == [
        "PAUSED",
        "ACTIVE",
        "CANCELLED",
        "cancelled",
        "FORTNIGHTLY_NONSENSE",
        None,
    ]


def test_parse_contract_nodes_coerces_naive_datetimes_to_utc():
    """A date with no offset is treated as UTC rather than left naive.

    A naive datetime raises on comparison with an aware one, so leaving one in a
    ContractView would turn a malformed date into a 500 inside the access
    decision.
    """
    payload = _payload(
        _node(createdAt="2026-06-02T22:27:41", nextBillingDate="2026-07-02T22:00:00")
    )

    contract = subscription_auth._parse_contract_nodes(payload, 1, "x@example.com")[0]

    assert contract.created_at == datetime(2026, 6, 2, 22, 27, 41, tzinfo=timezone.utc)
    assert contract.next_billing_date == datetime(2026, 7, 2, 22, 0, tzinfo=timezone.utc)
    for value in (contract.created_at, contract.next_billing_date, contract.renewal_anchor):
        assert value.utcoffset() == timedelta(0)


def test_parse_contract_nodes_survives_unparseable_dates():
    """Garbage dates become ``None``; the contract is still returned.

    ``None`` dates make ``paid_through`` underivable, so the contract does not
    grant (clause 2.8) — the conservative outcome.  Dropping the contract instead
    would hide it from the log and from the denial-message selection.
    """
    payload = _payload(
        _node(id="bad-dates", createdAt="not-a-date", nextBillingDate="2026-13-45T99:00:00Z"),
        _node(id="good-dates"),
    )

    contracts = subscription_auth._parse_contract_nodes(payload, 1, "x@example.com")

    assert [c.contract_id for c in contracts] == ["bad-dates", "good-dates"]
    assert contracts[0].created_at is None
    assert contracts[0].next_billing_date is None
    assert contracts[0].renewal_anchor is None
    assert contracts[0].renewal_anchor_field is None
    assert subscription_auth._paid_through(contracts[0]) is None
    assert subscription_auth._contract_grants(contracts[0]) is False
    # The sibling is untouched.
    assert contracts[1].next_billing_date == datetime(2026, 7, 2, 22, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("bad", [None, "a string", 42, [], ["nested"]])
def test_parse_contract_nodes_skips_non_dict_nodes_and_keeps_the_rest(bad, caplog):
    """One unusable entry costs only itself, and says so in the log.

    The old parser's ``except (IndexError, AttributeError, TypeError)`` swallowed
    the whole extraction; here the siblings survive, which is the difference
    between "one contract is unreadable" and "this customer has no contracts".
    """
    payload = _payload(_node(id="before"), bad, _node(id="after"))

    with caplog.at_level("WARNING", logger="backend.subscription_auth"):
        contracts = subscription_auth._parse_contract_nodes(payload, 1, "x@example.com")

    assert [c.contract_id for c in contracts] == ["before", "after"]
    assert any(
        "non-dict subscription contract node" in record.getMessage()
        for record in caplog.records
    ), f"expected a warning naming the skipped node; got {[r.getMessage() for r in caplog.records]}"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "a string",
        [],
        {},
        {"subscriptionContracts": None},
        {"subscriptionContracts": "nope"},
        {"subscriptionContracts": {}},
        {"subscriptionContracts": {"nodes": None}},
        {"subscriptionContracts": {"nodes": "nope"}},
        {"subscriptionContracts": {"nodes": []}},
    ],
)
def test_parse_contract_nodes_returns_empty_list_for_unusable_payloads(payload):
    """No contracts, no exception — an empty list routes to the 2.12 fallback.

    Clause 3.7 keeps a malformed Appstle response falling through rather than
    blocking a login, so nothing in this parser may raise.
    """
    assert subscription_auth._parse_contract_nodes(payload, 1, "x@example.com") == []


def test_parse_contract_nodes_sets_created_at_as_the_renewal_anchor():
    """``createdAt`` is the anchor, and the view records that it was the weak one.

    Per design Finding 1 Appstle exposes no ``lastBillingDate``-style field, so
    there is no priority order to implement — but ``renewal_anchor_field`` still
    names the source, which is what lets ``_paid_through()`` log the ERROR that
    Property 12 asserts on.
    """
    contract = subscription_auth._parse_contract_nodes(
        _payload(_node(createdAt="2026-06-16T12:00:00Z")), 1, "x@example.com"
    )[0]

    assert contract.renewal_anchor == contract.created_at
    assert contract.renewal_anchor_field == "createdAt"


def test_parse_contract_nodes_leaves_the_anchor_unset_when_created_at_is_absent():
    """No ``createdAt`` means no anchor to name, so the field stays ``None``."""
    contract = subscription_auth._parse_contract_nodes(
        _payload(_node(createdAt=None)), 1, "x@example.com"
    )[0]

    assert contract.renewal_anchor is None
    assert contract.renewal_anchor_field is None


@pytest.mark.parametrize(
    "policy,expected_interval,expected_count",
    [
        # Absent policy — the clause 2.8 case, distinct from an unknown unit.
        (None, None, 1),
        # Both observed real shapes (design Finding 2).
        ({"interval": "DAY", "intervalCount": 30}, "DAY", 30),
        ({"interval": "MONTH", "intervalCount": 1}, "MONTH", 1),
        # intervalCount omitted reads as "one interval".
        ({"interval": "MONTH"}, "MONTH", 1),
        ({"interval": "MONTH", "intervalCount": None}, "MONTH", 1),
        # An unrecognized unit is carried through verbatim; _add_calendar_interval
        # is what rejects it, so the log can name what Appstle actually sent.
        ({"interval": "FORTNIGHT", "intervalCount": 1}, "FORTNIGHT", 1),
    ],
)
def test_parse_contract_nodes_reads_the_billing_policy(policy, expected_interval, expected_count):
    """``billingPolicy.interval`` / ``intervalCount``, per design Finding 2."""
    contract = subscription_auth._parse_contract_nodes(
        _payload(_node(billingPolicy=policy)), 1, "x@example.com"
    )[0]

    assert contract.interval == expected_interval
    assert contract.interval_count == expected_count


@pytest.mark.parametrize("bad_count", ["30", 0, -1, 1.5, True, [30]])
def test_parse_contract_nodes_drops_a_policy_with_an_unusable_interval_count(bad_count, caplog):
    """An unusable count takes the whole policy down, so ``paid_through`` fails.

    Substituting 1 would invent paid time the payload never claimed.  Clause 2.8
    wants underivable instead, which errs toward denial — recoverable — rather
    than toward a false grant.
    """
    payload = _payload(_node(billingPolicy={"interval": "MONTH", "intervalCount": bad_count}))

    with caplog.at_level("WARNING", logger="backend.subscription_auth"):
        contract = subscription_auth._parse_contract_nodes(payload, 1, "x@example.com")[0]

    assert contract.interval is None
    assert contract.interval_count == 1
    assert any("intervalCount" in record.getMessage() for record in caplog.records)


def test_parse_contract_nodes_treats_a_non_dict_billing_policy_as_absent(caplog):
    """A ``billingPolicy`` that is not an object cannot be read; say so and move on."""
    with caplog.at_level("WARNING", logger="backend.subscription_auth"):
        contract = subscription_auth._parse_contract_nodes(
            _payload(_node(billingPolicy="MONTHLY")), 1, "x@example.com"
        )[0]

    assert contract.interval is None
    assert contract.interval_count == 1
    assert any("billingPolicy" in record.getMessage() for record in caplog.records)


def test_parse_contract_nodes_tolerates_an_unparseable_customer_id():
    """A non-numeric ``customerId`` must not cost the customer their contracts.

    Nothing does arithmetic on the id — it is a log field and a decision-trace
    field — so it is carried through rather than dropped.
    """
    contracts = subscription_auth._parse_contract_nodes(
        _payload(_node()), "not-an-int", "x@example.com"
    )

    assert len(contracts) == 1
    assert contracts[0].customer_id == "not-an-int"


# ---------------------------------------------------------------------------
# _describe_contracts (requirement 2.20)
# ---------------------------------------------------------------------------

def test_describe_contracts_names_every_contract_status_and_date():
    """The log line carries what the decision turns on, for EVERY contract.

    Requirement 2.20: the ``str(data)[:500]`` truncation this replaces cut off
    before the second contract of a multi-contract payload, which is exactly the
    contract that explained Dave's lockout.
    """
    payload = _load_appstle_fixture("dave_two_paused_contracts")
    contracts = subscription_auth._parse_contract_nodes(payload, DAVE_CUSTOMER_ID, "x@example.com")

    described = subscription_auth._describe_contracts(contracts)

    for node in payload["subscriptionContracts"]["nodes"]:
        assert node["id"] in described
        assert node["status"] in described
        assert node["createdAt"][:10] in described
        assert node["nextBillingDate"][:10] in described
    # No raw payload repr: that is the shape requirement 2.20 exists to remove.
    assert "__typename" not in described


def test_describe_contracts_handles_an_empty_list():
    """No contracts is a statement worth logging, not a blank."""
    assert "no contracts" in subscription_auth._describe_contracts([])


# ---------------------------------------------------------------------------
# AppstleSubscriptionResponse (design change 7)
# ---------------------------------------------------------------------------

def test_appstle_response_defaults_to_no_contracts_and_a_null_expiration():
    """``contracts`` defaults to empty and is per-instance; ``expiration_date`` stays null.

    Clause 3.13: ``expiration_date`` is never populated, which is what keeps
    ``expires_at`` and ``subscription_expires_at`` null in the responses and the
    JWT.  Out of scope here, and pinned so it stays that way.
    """
    first = subscription_auth.AppstleSubscriptionResponse(is_valid=False)
    second = subscription_auth.AppstleSubscriptionResponse(is_valid=False)

    assert first.contracts == []
    assert first.expiration_date is None
    first.contracts.append(ContractView(customer_id=1))
    assert second.contracts == [], "the default list is shared between instances"


def test_appstle_response_carries_contract_views_unchanged():
    """A ContractView survives model validation as the same object.

    The decision layer receives these views directly, so a pydantic round-trip
    that rebuilt or coerced them would silently re-run ``__post_init__`` on
    already-normalized datetimes.
    """
    view = ContractView(customer_id=7, status="PAUSED", next_billing_date=datetime(2026, 8, 27))

    response = subscription_auth.AppstleSubscriptionResponse(is_valid=True, contracts=[view])

    assert response.contracts[0] is view


# ---------------------------------------------------------------------------
# _extract_customer_ids (Task 9.2, design change 9, requirement 2.10)
# ---------------------------------------------------------------------------
#
# The unit that carries the fix for root cause 2 — the truncation one level above
# ``nodes[0]``.  What it replaces, ``_extract_customer_id()``, returned on the
# first record with a non-null ``customerId``, so an email mapping to two Appstle
# customer records had the second record's contracts discarded before step 2 was
# ever issued (clause 1.3).
#
# Two things are asserted here: that the payload normalization carried over
# unchanged (Appstle has been observed sending a bare list, a ``{"content": [...]}``
# envelope, and a single bare record), and that nothing is dropped now.  Pure
# Python — no service instance, no env config, no HTTP.


def test_extract_customer_ids_from_bare_list():
    """The shape the real step-1 capture returned: a bare list of records."""
    data = _load_appstle_fixture("step1_single_customer")
    assert isinstance(data, list), "fixture drift: step-1 payloads are bare lists"

    assert _extract_customer_ids(data) == [2788838535]


def test_extract_customer_ids_from_content_envelope():
    """The paginated envelope shape, unchanged from the single-value version."""
    data = {"content": [{"customerId": 12345, "email": "user@example.com"}]}

    assert _extract_customer_ids(data) == [12345]


def test_extract_customer_ids_from_content_envelope_with_several_records():
    """Every record inside the envelope counts, not just the first."""
    data = {
        "content": [
            {"customerId": 111, "email": "a@example.com"},
            {"customerId": 222, "email": "a@example.com"},
            {"customerId": 333, "email": "a@example.com"},
        ],
        "totalPages": 1,
    }

    assert _extract_customer_ids(data) == [111, 222, 333]


def test_extract_customer_ids_from_single_bare_record():
    """A lone record that is not wrapped in a list or a ``content`` envelope."""
    data = {"customerId": 99999, "email": "user@example.com"}

    assert _extract_customer_ids(data) == [99999]


def test_extract_customer_ids_prefers_content_over_a_sibling_customer_id():
    """When both shapes are present the envelope wins, as it did before.

    A payload carrying ``content`` AND a top-level ``customerId`` is the paginated
    shape; treating the envelope as authoritative keeps the record list from being
    replaced by the wrapper itself.
    """
    data = {"customerId": 999, "content": [{"customerId": 111}, {"customerId": 222}]}

    assert _extract_customer_ids(data) == [111, 222]


def test_extract_customer_ids_returns_all_records_in_payload_order():
    """Requirement 2.10 — the second customer record is no longer dropped.

    This is the assertion the old helper could not make.  Order is the payload's
    own, which keeps ``ids[0]`` equal to what ``_extract_customer_id()`` returned;
    the access decision itself must not depend on the order (2.9).
    """
    data = _load_appstle_fixture("step1_two_customers")
    assert len(data) == 2, "fixture drift: this payload must map to two records"

    ids = _extract_customer_ids(data)

    assert ids == [record["customerId"] for record in data]
    assert ids == [3289420039, 7000000021]
    assert ids[0] == 3289420039


def test_extract_customer_ids_deduplicates_on_first_sight():
    """Duplicates collapse, and the first occurrence fixes the position.

    A repeated ``customerId`` would otherwise mean step 2 is fetched twice for the
    same customer and every contract counted twice.
    """
    data = [
        {"customerId": 111, "email": "a@example.com"},
        {"customerId": 222, "email": "a@example.com"},
        {"customerId": 111, "email": "a@example.com"},
        {"customerId": 222, "email": "a@example.com"},
    ]

    assert _extract_customer_ids(data) == [111, 222]


def test_extract_customer_ids_skips_null_ids_and_keeps_the_rest():
    """A record with no usable id costs only itself.

    The old helper skipped past null ids to find its one value; the same skipping
    must not now stop the scan, or a null first record would hide every id
    behind it.
    """
    data = [
        {"email": "a@example.com", "name": "No ID"},
        {"customerId": None, "email": "b@example.com"},
        {"customerId": 222, "email": "c@example.com"},
        {"customerId": None, "email": "d@example.com"},
        {"customerId": 333, "email": "e@example.com"},
    ]

    assert _extract_customer_ids(data) == [222, 333]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param([], id="empty-list"),
        pytest.param({}, id="empty-dict"),
        pytest.param({"content": []}, id="empty-content"),
        pytest.param({"content": None}, id="null-content"),
        pytest.param([{"email": "a@example.com"}], id="records-without-ids"),
        pytest.param([{"customerId": None}], id="null-id-only"),
    ],
)
def test_extract_customer_ids_returns_empty_when_no_id_is_present(payload):
    """No usable id yields ``[]``, which routes to the existing no-subscription
    response rather than a step-2 call for nothing (3.2)."""
    assert _extract_customer_ids(payload) == []


def test_extract_customer_ids_empty_for_the_no_subscription_fixture():
    """The real "no Appstle record" payload still reads as no customers (3.2)."""
    assert _extract_customer_ids(_load_appstle_fixture("no_subscription")) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="none"),
        pytest.param("customerId=111", id="string"),
        pytest.param(12345, id="int"),
        pytest.param(True, id="bool"),
        pytest.param(["not-a-record", 7, None], id="list-of-non-records"),
        pytest.param({"content": ["not-a-record", None]}, id="content-of-non-records"),
        pytest.param({"content": {"customerId": 111}}, id="content-not-a-list"),
    ],
)
def test_extract_customer_ids_never_raises_on_malformed_input(payload):
    """Malformed input degrades to ``[]`` instead of raising.

    ``verify_subscription()`` treats a raise here as an Appstle failure and falls
    through to free tier (3.7); returning ``[]`` keeps that path reachable without
    depending on exception handling for a merely odd payload.
    """
    assert _extract_customer_ids(payload) == []


def test_extract_customer_ids_keeps_usable_records_beside_malformed_ones():
    """One junk entry in the list must not cost the customers around it."""
    data = ["junk", {"customerId": 111}, None, {"customerId": 222}, 42]

    assert _extract_customer_ids(data) == [111, 222]


def test_extract_customer_ids_carries_ids_verbatim_without_coercion():
    """Ids are passed through as given rather than coerced to ``int``.

    Nothing does arithmetic on a ``customerId`` — it is interpolated into the
    step-2 URL and logged — so coercing here would turn an odd-but-usable id into
    a lost customer, which is the failure mode this whole fix is about.
    """
    data = [{"customerId": "2788838535"}, {"customerId": 2788838535}]

    ids = _extract_customer_ids(data)

    assert ids == ["2788838535", 2788838535]
    assert isinstance(ids[0], str)


def test_extract_customer_ids_survives_an_unhashable_id():
    """An unhashable id must not raise the way a ``set``-based dedupe would."""
    data = [{"customerId": ["odd"]}, {"customerId": 222}]

    assert _extract_customer_ids(data) == [["odd"], 222]


# ---------------------------------------------------------------------------
# Contract pagination — Task 9.3, requirement 2.11
# ---------------------------------------------------------------------------
#
# Requirement 2.11 in one sentence: a contract stranded on an unread page is a
# FALSE DENIAL of a paying customer, because access is granted if ANY contract
# grants.  So an unfollowable page is an ERROR, not a debug line.
#
# **Cursor-following is deferred by design decision, not by omission.**  Design
# Finding 4 read the captured payloads: ``subscriptionContracts.pageInfo`` is
# cursor-based (``hasPreviousPage``, ``hasNextPage``, ``startCursor``,
# ``endCursor``, opaque base64 cursors), but ``hasNextPage`` was ``false`` for all
# three captured customers, so no pagination request was ever exercised and the
# cursor's request-parameter name was never observed.  The recorded decision is
# "implement detection now, defer cursor-following", so in production
# ``_CONTRACT_PAGE_CURSOR_PARAM`` is ``None`` and ``_fetch_contract_pages()``
# detects the advertised page and logs at ERROR.
#
# The page-following loop is written, bounded, and routed through
# ``_appstle_get()`` all the same, and the tests below exercise it with that one
# constant patched to the harness's placeholder parameter name.  That is what
# makes "add cursor-following later without restructuring" a claim with evidence
# behind it rather than an intention.

import asyncio  # noqa: E402

from tests.subscription_harness import (  # noqa: E402
    PAGINATION_PARAM,
    build_contract_node,
    build_step2_payload,
    harness,
    load_fixture,
)

from backend.subscription_auth import (  # noqa: E402
    _CONTRACT_PAGE_CAP,
    _CONTRACT_PAGE_CURSOR_PARAM,
    _advertises_next_page,
    _read_page_info,
)

# The synthetic customer the two pagination fixtures belong to.
PAGED_CUSTOMER_ID = 7000000018
PAGED_EMAIL = "paged.customer@example.com"

# Contract ids in contracts_page1.json / contracts_page2.json. Page 2 carries the
# granting contract (nextBillingDate 2026-08-23, after FIXTURE_NOW), which is the
# whole point of the pair.
PAGE1_CONTRACT_ID = "gid://shopify/SubscriptionContract/9000000181"
PAGE2_CONTRACT_ID = "gid://shopify/SubscriptionContract/9000000182"


def _fetch_pages(service, first_page, *, contracts=None, customer_id=PAGED_CUSTOMER_ID):
    """Drive ``_fetch_contract_pages()`` to completion and return its contracts.

    ``session`` is ``None`` on purpose: the harness replaces ``_appstle_get`` with
    a router that never touches it, so passing one would only imply the test needs
    a real ``aiohttp`` session.
    """
    return asyncio.run(
        service._fetch_contract_pages(
            None, customer_id, PAGED_EMAIL, first_page, contracts,
        )
    )


def _errors(caplog):
    return [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]


# -- the pure pageInfo readers ----------------------------------------------

@pytest.mark.parametrize(
    "page_info, expected",
    [
        pytest.param({"hasNextPage": True}, True, id="bool-true"),
        pytest.param({"hasNextPage": False}, False, id="bool-false"),
        pytest.param({}, False, id="key-absent"),
        pytest.param({"hasNextPage": None}, False, id="null"),
        pytest.param({"hasNextPage": "true"}, True, id="string-true"),
        pytest.param({"hasNextPage": "TRUE"}, True, id="string-true-upper"),
        pytest.param({"hasNextPage": "1"}, True, id="string-one"),
        pytest.param({"hasNextPage": "false"}, False, id="string-false"),
        pytest.param({"hasNextPage": ""}, False, id="string-empty"),
        pytest.param({"hasNextPage": 1}, False, id="int"),
        pytest.param({"hasNextPage": {"nested": True}}, False, id="dict"),
    ],
)
def test_advertises_next_page_reads_only_an_affirmative_claim(page_info, expected):
    """``True`` and its stringified forms mean "more contracts"; nothing else does.

    The string tolerance is one-directional on purpose: a false positive costs a
    single ERROR log line, while a false negative silently drops a page and can
    deny a paying customer (2.11).
    """
    assert _advertises_next_page(page_info) is expected


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="none"),
        pytest.param("not-a-payload", id="string"),
        pytest.param({}, id="empty-dict"),
        pytest.param({"subscriptionContracts": None}, id="null-block"),
        pytest.param({"subscriptionContracts": []}, id="block-not-a-dict"),
        pytest.param({"subscriptionContracts": {}}, id="no-page-info"),
        pytest.param({"subscriptionContracts": {"pageInfo": None}}, id="null-page-info"),
        pytest.param({"subscriptionContracts": {"pageInfo": "x"}}, id="page-info-not-a-dict"),
    ],
)
def test_read_page_info_returns_empty_for_absent_or_malformed_shapes(payload):
    """An unrecognized payload shape reads as ``{}`` — i.e. as no next page.

    Treating malformed ``pageInfo`` as "a page may be missing" would emit an ERROR
    on every such login and bury the records that mean something.
    """
    assert _read_page_info(payload) == {}
    assert _advertises_next_page(_read_page_info(payload)) is False


def test_read_page_info_returns_the_real_fixtures_page_info():
    """The committed fixtures carry the cursor-based ``pageInfo`` verbatim."""
    page1 = _read_page_info(load_fixture("contracts_page1"))
    page2 = _read_page_info(load_fixture("contracts_page2"))

    assert page1["hasNextPage"] is True
    assert page1["endCursor"] == "SYNTHETIC_PLACEHOLDER_CURSOR_PAGE1_END"
    assert page2["hasNextPage"] is False
    assert page2["hasPreviousPage"] is True


# -- the page cap and the deferral, as constants ----------------------------

def test_page_cap_is_ten():
    """The bounded page cap the design specifies.

    Bounded because the walk is driven by a cursor the *server* supplies: a server
    that keeps advertising ``hasNextPage`` would otherwise spin inside a login.
    """
    assert _CONTRACT_PAGE_CAP == 10


def test_cursor_parameter_is_unknown_so_following_is_deferred():
    """``None`` records design Finding 4's answer: the parameter name is unknown.

    This is the deferral, pinned as an assertion so it cannot be quietly replaced
    with a guessed parameter name.  Guessing would mean sending an unrecognized
    parameter to the live API and reading whatever came back as page 2 — which
    could duplicate page 1's contracts or return an unrelated slice, both worse
    than a logged gap.  Enabling cursor-following is a deliberate edit to this
    constant plus an update to this test.
    """
    assert _CONTRACT_PAGE_CURSOR_PARAM is None


# -- _fetch_contract_pages: single page, no next page -----------------------

def test_fetch_contract_pages_single_page_returns_its_contracts_without_error(caplog):
    """``hasNextPage`` false → one page, every contract on it, no ERROR, no request.

    Dave's real payload is the case that matters most here: two contracts on one
    page with ``hasNextPage`` false.  Pagination must not add an ERROR record to
    the ordinary path, or the records that mean "a paying customer may be locked
    out" become noise.
    """
    payload = load_fixture("dave_two_paused_contracts")

    with harness(step2={2788838535: payload}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, payload, customer_id=2788838535)

        assert len(contracts) == 2
        assert _errors(caplog) == []
        # No page was advertised, so no request was issued at all.
        assert h.router.requests == []


def test_fetch_contract_pages_accepts_already_parsed_contracts_without_reparsing():
    """Page 1's contracts are reused when the caller passes them in.

    Task 9.4 needs page 1's payload anyway (for the customer-level
    ``productSubscriberStatus``) and parses it there, so re-parsing here would
    double every contract.
    """
    payload = load_fixture("dave_two_paused_contracts")

    with harness(step2={2788838535: payload}) as h:
        already = subscription_auth._parse_contract_nodes(
            payload, 2788838535, PAGED_EMAIL,
        )
        contracts = _fetch_pages(
            h.service, payload, contracts=already, customer_id=2788838535,
        )

        assert len(contracts) == 2
        assert [c.contract_id for c in contracts] == [c.contract_id for c in already]
        # A copy, not the caller's list — extending pages must not mutate it.
        assert contracts is not already


def test_fetch_contract_pages_empty_nodes_yields_no_contracts_and_no_error(caplog):
    """An empty ``nodes[]`` page is normal data (2.12), not a missing page."""
    payload = load_fixture("empty_nodes")

    with harness(step2={PAGED_CUSTOMER_ID: payload}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, payload)

        assert contracts == []
        assert _errors(caplog) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="none"),
        pytest.param("junk", id="string"),
        pytest.param({}, id="empty-dict"),
        pytest.param({"subscriptionContracts": {"nodes": []}}, id="no-page-info"),
        pytest.param(
            {"subscriptionContracts": {"nodes": [], "pageInfo": "junk"}},
            id="page-info-not-a-dict",
        ),
        pytest.param(
            {"subscriptionContracts": {"nodes": [], "pageInfo": {"hasNextPage": None}}},
            id="null-has-next-page",
        ),
    ],
)
def test_fetch_contract_pages_survives_malformed_payloads(payload, caplog):
    """Malformed or absent ``pageInfo`` reads as no next page, and never raises.

    A raise here would propagate out of ``verify_subscription()`` and be handled
    as an Appstle failure, dropping the customer to free tier (3.7) on nothing
    worse than an unfamiliar payload shape.
    """
    with harness(step2={PAGED_CUSTOMER_ID: {}}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, payload)

        assert contracts == []
        assert _errors(caplog) == []
        assert h.router.requests == []


# -- _fetch_contract_pages: next page advertised, cursor unknown -------------

def test_fetch_contract_pages_logs_error_when_next_page_cannot_be_followed(caplog):
    """``hasNextPage`` true with an unknown cursor parameter → ERROR, page 1 kept.

    The shipped behavior per design Finding 4.  Two things are asserted together
    because either alone would be a bug: the ERROR record exists (the gap is
    visible rather than silent), and page 1's contracts are still returned (a
    detected gap must not cost the contracts that WERE read).
    """
    page1 = load_fixture("contracts_page1")

    with harness(step2={PAGED_CUSTOMER_ID: [page1, load_fixture("contracts_page2")]}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert [c.contract_id for c in contracts] == [PAGE1_CONTRACT_ID]

        errors = _errors(caplog)
        assert len(errors) == 1
        message = errors[0]
        assert "cannot be followed" in message
        assert "Contracts may be missing" in message
        # The customerId and the endCursor are both in the record, so the missing
        # page can be chased by hand from the log alone.
        assert str(PAGED_CUSTOMER_ID) in message
        assert "SYNTHETIC_PLACEHOLDER_CURSOR_PAGE1_END" in message
        assert PAGED_EMAIL in message

        # Detection only: no page-2 request was issued, so no fabricated cursor
        # parameter reached the API.
        assert h.router.requests == []


def test_fetch_contract_pages_error_names_the_false_denial_risk(caplog):
    """The ERROR text says WHY it is an ERROR, in reviewable words.

    Requirement 2.11's reasoning — a granting contract on an unread page is a
    false denial of a paying customer — belongs in the record itself.  Whoever
    reads this line at 2am is deciding whether to chase it, and severity alone
    does not tell them that a customer may be locked out.
    """
    page1 = load_fixture("contracts_page1")

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            _fetch_pages(h.service, page1)

        message = _errors(caplog)[0]
        assert "false denial" in message
        assert "paying customer" in message


def test_fetch_contract_pages_logs_once_per_customer_not_once_per_contract(caplog):
    """One advertised page produces exactly one ERROR, regardless of contract count."""
    nodes = [
        build_contract_node(
            contract_id=n, status="PAUSED",
            created_at="2026-07-01T00:00:00Z", next_billing_date="2026-07-31T00:00:00Z",
        )
        for n in range(5)
    ]
    page1 = build_step2_payload(
        customer_id=PAGED_CUSTOMER_ID, nodes=nodes, has_next_page=True,
    )

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert len(contracts) == 5
        assert len(_errors(caplog)) == 1


# -- _fetch_contract_pages: the loop, with the cursor parameter supplied -----
#
# These cases patch ``_CONTRACT_PAGE_CURSOR_PARAM`` to the harness's placeholder
# name. They are not a claim about the live API — production keeps ``None`` and
# the test above pins that — they prove the accumulation, the page cap, and the
# ``_appstle_get()`` routing are real code that works, so enabling cursor-
# following later is one constant rather than a rewrite.

def test_fetch_contract_pages_accumulates_across_pages_when_following_is_enabled(
    monkeypatch, caplog,
):
    """Page 2's granting contract is reached, and both pages' contracts come back.

    ``contracts_page2.json`` holds a contract paid through 2026-08-23, after
    ``FIXTURE_NOW`` — the contract whose loss to an unread page would be the false
    denial requirement 2.11 is about.
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    page1 = load_fixture("contracts_page1")
    page2 = load_fixture("contracts_page2")

    with harness(step2={PAGED_CUSTOMER_ID: [page1, page2]}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        # Payload order, page by page.
        assert [c.contract_id for c in contracts] == [PAGE1_CONTRACT_ID, PAGE2_CONTRACT_ID]
        assert all(c.customer_id == PAGED_CUSTOMER_ID for c in contracts)
        # Page 2's contract is the granting one, which is why losing it matters.
        assert subscription_auth._contract_grants(contracts[1]) is True
        assert subscription_auth._contract_grants(contracts[0]) is False

        # Followed pages are not a gap, so nothing is logged at ERROR.
        assert _errors(caplog) == []


def test_fetch_contract_pages_requests_go_through_appstle_get(monkeypatch):
    """The page-2 request is issued via ``_appstle_get()``, carrying the cursor.

    That seam is what lets the property tests' router serve
    ``contracts_page1.json`` / ``contracts_page2.json`` offline; a request made any
    other way would be invisible to it (and would need a network).
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    page1 = load_fixture("contracts_page1")

    with harness(step2={PAGED_CUSTOMER_ID: [page1, load_fixture("contracts_page2")]}) as h:
        _fetch_pages(h.service, page1)

        assert len(h.router.requests) == 1
        request = h.router.requests[0]
        assert request.url.endswith(f"/subscription-customers/{PAGED_CUSTOMER_ID}")
        assert request.customer_id == PAGED_CUSTOMER_ID
        assert request.cursor == "SYNTHETIC_PLACEHOLDER_CURSOR_PAGE1_END"
        assert h.router.followed_next_page(PAGED_CUSTOMER_ID) is True


def _endless_page_source(*, start=1):
    """An ``_appstle_get`` stand-in that always advertises one more page.

    Each response carries a fresh advancing cursor, so only the page cap can stop
    the walk — which is exactly what the cap exists for.
    """
    calls = []

    async def fake_appstle_get(session, url, params=None):
        calls.append({"url": url, "params": dict(params) if params else None})
        index = start + len(calls)
        return build_step2_payload(
            customer_id=PAGED_CUSTOMER_ID,
            nodes=[
                build_contract_node(
                    contract_id=9000000000 + index,
                    status="PAUSED",
                    created_at="2026-07-01T00:00:00Z",
                    next_billing_date="2026-07-31T00:00:00Z",
                )
            ],
            has_next_page=True,
            has_previous_page=True,
            end_cursor=f"CURSOR_PAGE{index}_END",
        )

    return fake_appstle_get, calls


def test_fetch_contract_pages_stops_at_the_page_cap(monkeypatch, caplog):
    """A server that never stops advertising pages is cut off at the cap, loudly.

    ``_CONTRACT_PAGE_CAP`` counts pages READ, page 1 included, so the cap allows
    nine further requests.  Reaching it is a gap like any other, so it is an
    ERROR: contracts beyond page 10 are unread, and any one of them could have
    granted.
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    fake_get, calls = _endless_page_source()
    page1 = build_step2_payload(
        customer_id=PAGED_CUSTOMER_ID,
        nodes=[
            build_contract_node(
                contract_id=9000000001, status="PAUSED",
                created_at="2026-07-01T00:00:00Z", next_billing_date="2026-07-31T00:00:00Z",
            )
        ],
        has_next_page=True,
        end_cursor="CURSOR_PAGE1_END",
    )

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        h.service._appstle_get = fake_get
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert len(calls) == _CONTRACT_PAGE_CAP - 1
        assert len(contracts) == _CONTRACT_PAGE_CAP
        # Every request carried a distinct cursor, so the cap stopped the walk
        # rather than a repeated-cursor guard.
        cursors = [c["params"][PAGINATION_PARAM] for c in calls]
        assert len(set(cursors)) == len(cursors)

        errors = _errors(caplog)
        assert len(errors) == 1
        assert f"{_CONTRACT_PAGE_CAP}-page cap" in errors[0]
        assert "Contracts may be missing" in errors[0]


def test_fetch_contract_pages_stops_on_a_cursor_that_does_not_advance(
    monkeypatch, caplog,
):
    """A repeated ``endCursor`` ends the walk instead of re-reading a page.

    Cheaper than letting the cap absorb it: nine identical requests inside a login
    would cost latency for contracts already counted.
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    calls = []

    async def echoing_cursor(session, url, params=None):
        calls.append(dict(params) if params else None)
        return build_step2_payload(
            customer_id=PAGED_CUSTOMER_ID,
            nodes=[
                build_contract_node(
                    contract_id=9000000002, status="PAUSED",
                    created_at="2026-07-01T00:00:00Z",
                    next_billing_date="2026-07-31T00:00:00Z",
                )
            ],
            has_next_page=True,
            end_cursor="STUCK_CURSOR",
        )

    page1 = build_step2_payload(
        customer_id=PAGED_CUSTOMER_ID,
        nodes=[
            build_contract_node(
                contract_id=9000000001, status="PAUSED",
                created_at="2026-07-01T00:00:00Z", next_billing_date="2026-07-31T00:00:00Z",
            )
        ],
        has_next_page=True,
        end_cursor="STUCK_CURSOR",
    )

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        h.service._appstle_get = echoing_cursor
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert len(calls) == 1
        assert len(contracts) == 2

        errors = _errors(caplog)
        assert len(errors) == 1
        assert "does not advance" in errors[0]


def test_fetch_contract_pages_stops_when_a_next_page_has_no_cursor(monkeypatch, caplog):
    """``hasNextPage`` true with a null ``endCursor`` is a gap, not a crash."""
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    page1 = load_fixture("contracts_page1")
    page1["subscriptionContracts"]["pageInfo"]["endCursor"] = None

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert [c.contract_id for c in contracts] == [PAGE1_CONTRACT_ID]
        assert h.router.requests == []
        assert "does not advance" in _errors(caplog)[0]


def test_fetch_contract_pages_keeps_earlier_contracts_when_a_later_page_fails(
    monkeypatch, caplog,
):
    """A failed page-2 fetch logs ERROR and returns page 1's contracts anyway.

    Letting the exception escape would discard page 1 too and route the customer
    through the Appstle-unavailable path to free tier (3.7).  A partial set at
    least lets a granting contract that was already read do its job — the same
    "incomplete data must not bias toward lockout" reasoning as 2.11 itself.
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )
    page1 = load_fixture("contracts_page1")

    async def failing_get(session, url, params=None):
        raise asyncio.TimeoutError()

    with harness(step2={PAGED_CUSTOMER_ID: page1}) as h:
        h.service._appstle_get = failing_get
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            contracts = _fetch_pages(h.service, page1)

        assert [c.contract_id for c in contracts] == [PAGE1_CONTRACT_ID]

        errors = _errors(caplog)
        assert len(errors) == 1
        assert "Failed to fetch contract page 2" in errors[0]
        assert "Contracts may be missing" in errors[0]

# ---------------------------------------------------------------------------
# _aggregate_product_subscriber_status (Task 9.4, requirement 2.9)
# ---------------------------------------------------------------------------
#
# Only reached when an email maps to more than one Appstle customer record, and
# only load-bearing when EVERY record has an empty ``nodes[]`` — clause 2.12 keeps
# ``productSubscriberStatus`` a fallback.  Tested on its own anyway because the
# thing it has to guarantee is a negative: no ordering of the same set of records
# may produce a different answer (2.9).

from itertools import permutations  # noqa: E402

from backend.subscription_auth import (  # noqa: E402
    _aggregate_product_subscriber_status as _aggregate,
)


@pytest.mark.parametrize(
    "values, expected",
    [
        pytest.param(["ACTIVE", "CANCELLED"], "ACTIVE", id="active-beats-cancelled"),
        pytest.param(["PAUSED", "ACTIVE"], "ACTIVE", id="active-beats-paused"),
        pytest.param(["CANCELLED", "PAUSED"], "PAUSED", id="paused-beats-cancelled"),
        pytest.param(["EXPIRED", "CANCELLED"], "CANCELLED", id="cancelled-beats-other"),
        pytest.param(["EXPIRED", None], "EXPIRED", id="other-beats-none"),
        pytest.param([None, None], None, id="all-none"),
        pytest.param([], None, id="empty"),
        pytest.param(["ACTIVE"], "ACTIVE", id="single"),
    ],
)
def test_aggregate_status_follows_the_fixed_priority(values, expected):
    """``ACTIVE > PAUSED > CANCELLED > other > None``, as clause 2.9 requires.

    The generous end of the ladder is the point: a customer holding an ACTIVE
    record alongside a lapsed one must not be denied by the lapsed one, which is
    the same "any grant wins" rule (2.1) applied one level up from contracts.
    """
    assert _aggregate(values) == expected


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(["ACTIVE", "PAUSED", "CANCELLED"], id="all-three"),
        pytest.param(["CANCELLED", "EXPIRED", None], id="cancelled-other-none"),
        pytest.param(["EXPIRED", "SUSPENDED", None], id="two-unrecognized"),
        pytest.param([None, "PAUSED", "PAUSED"], id="duplicates"),
    ],
)
def test_aggregate_status_is_order_independent(values):
    """Every permutation of the same values gives the same answer (2.9).

    This is the property the replaced "first customerId wins" behavior did not
    have, and the reason the aggregation is a priority ladder rather than a
    first-seen read.
    """
    results = {_aggregate(list(order)) for order in permutations(values)}
    assert len(results) == 1


@pytest.mark.parametrize(
    "values, expected",
    [
        pytest.param(["", "   ", "ACTIVE"], "ACTIVE", id="blank-ignored"),
        pytest.param(["", None], None, id="blank-only"),
        pytest.param([123, {"status": "ACTIVE"}, "PAUSED"], "PAUSED", id="non-strings-ignored"),
        pytest.param([123, None], None, id="non-strings-only"),
        pytest.param(None, None, id="none-iterable"),
    ],
)
def test_aggregate_status_ignores_unusable_values(values, expected):
    """Blanks and non-strings drop out rather than winning or raising.

    A blank status is what the assembler already treats as absent, and a raise
    here would be read by ``login()`` as an Appstle failure and drop the customer
    to free tier (3.7) over a merely odd payload.
    """
    assert _aggregate(values) == expected


def test_aggregate_status_returns_the_raw_value_not_the_upper_cased_one():
    """The winner is returned verbatim; callers upper-case for comparison.

    ``login()`` reads ``(product_subscriber_status or "").upper()``, so casing does
    not change a verdict — but the raw value is what belongs in a log line, and
    normalizing here would quietly rewrite what Appstle actually said.
    """
    assert _aggregate(["active"]) == "active"


def test_aggregate_status_breaks_ties_deterministically():
    """Two same-rank values cannot make the result order-dependent.

    ``ACTIVE`` and ``active`` rank identically, as do any two unrecognized
    strings.  Without the tiebreak ``min()`` would return whichever came first,
    which is exactly the order dependence 2.9 forbids.
    """
    assert _aggregate(["active", "ACTIVE"]) == _aggregate(["ACTIVE", "active"])
    assert _aggregate(["ZED", "ALPHA"]) == _aggregate(["ALPHA", "ZED"]) == "ALPHA"


# ---------------------------------------------------------------------------
# verify_subscription (Task 9.4, design change 11, requirements 2.9-2.12, 2.20)
# ---------------------------------------------------------------------------
#
# The collection layer, tested at the seam it collects through.  ``login()`` still
# runs the old five-scenario ladder until Tasks 9.5 / 9.6, so what is asserted
# here is the ``AppstleSubscriptionResponse`` — specifically ``contracts``, the
# field ``decide_access()`` will read — plus the router's record of WHICH requests
# were actually issued.  A response that looks right because a second customer
# record was never fetched is the failure mode this whole spec exists to remove,
# so "was it fetched" is asserted directly rather than inferred.
#
# Response-level assertions in this module are the exception the module docstring
# names for the pagination section, and for the same reason: the behavior under
# test is a fetch loop, not a verdict.  The verdict is asserted through
# ``login()`` in the property suites.

CUSTOMER_A = 5000000001
CUSTOMER_B = 5000000002
MULTI_EMAIL = "multi.record@example.com"

DAVE_CUSTOMER_ID = 2788838535
DAVE_EMAIL = "multi.contract@example.com"


def _verify(service, email=MULTI_EMAIL):
    """Drive ``verify_subscription()`` to completion.

    ``aiohttp.ClientSession`` is really constructed — it is cheap, opens no
    connection, and is closed by the ``async with`` — but every request inside it
    goes to the harness router, so nothing leaves the machine.
    """
    return asyncio.run(service.verify_subscription(email))


def _contract_node(contract_id, *, status="PAUSED", next_billing_days=30, created_days=-30):
    """One contract node, dated relative to ``FIXTURE_NOW``."""
    return build_contract_node(
        contract_id=contract_id,
        status=status,
        created_at=_fixture_iso(created_days),
        next_billing_date=(
            None if next_billing_days is None else _fixture_iso(next_billing_days)
        ),
    )


def _fixture_iso(days):
    return at_offset(days=days).strftime("%Y-%m-%dT%H:%M:%SZ")


def _infos(caplog):
    return [r.getMessage() for r in caplog.records if r.levelname == "INFO"]


import aiohttp  # noqa: E402

from tests.subscription_harness import (  # noqa: E402
    appstle_http_error,
    appstle_malformed_json,
    appstle_timeout,
    at_offset,
    paginate,
    step1_payload,
)


# -- no customer records: the preserved no-subscription response -------------

def test_verify_subscription_with_no_customer_ids_returns_the_no_subscription_response():
    """An empty id list returns the same response it always did (3.2, 3.7).

    This is the path a customer with no Appstle record takes to 200 / ``"free"``,
    and it must not acquire a step-2 request or a contract list on the way.
    """
    with harness(step1=load_fixture("no_subscription")) as h:
        response = _verify(h.service)

    assert response.is_valid is False
    assert response.subscription_status is None
    assert response.product_subscriber_status is None
    assert response.next_billing_date is None
    assert response.expiration_date is None
    assert response.customer_email == MULTI_EMAIL
    assert response.contracts == []
    assert h.router.step2_requests == []


# -- one customer record: unchanged, plus every contract ---------------------

def test_verify_subscription_single_record_keeps_every_contract_and_one_request():
    """Dave's real payload: one step-2 request, BOTH of his contracts returned.

    The old parser read ``nodes[0].nextBillingDate`` and dropped node 1 — the
    granting one.  Both are here now, in payload order, while the scalar fields
    stay exactly as the single-record assembler set them.
    """
    payload = load_fixture("dave_two_paused_contracts")

    with harness(
        step1=step1_payload([DAVE_CUSTOMER_ID], email=DAVE_EMAIL),
        step2={DAVE_CUSTOMER_ID: payload},
    ) as h:
        response = _verify(h.service, DAVE_EMAIL)

    assert h.router.requested_customer_ids == [DAVE_CUSTOMER_ID]
    assert len(response.contracts) == 2
    assert [c.status for c in response.contracts] == ["PAUSED", "PAUSED"]
    assert {c.customer_id for c in response.contracts} == {DAVE_CUSTOMER_ID}

    assert response.is_valid is True
    assert response.product_subscriber_status == "PAUSED"
    assert response.subscription_status == "PAUSED"
    # Logging continuity only: still the FIRST contract's date, as before.
    assert response.next_billing_date == response.contracts[0].next_billing_date
    assert response.expiration_date is None


def test_verify_subscription_single_record_with_empty_nodes_keeps_its_fallback_status():
    """Empty ``nodes[]`` still reports ``productSubscriberStatus`` (clause 2.12)."""
    payload = load_fixture("empty_nodes")
    customer_id = payload["id"].rsplit("/", 1)[-1]

    with harness(
        step1=step1_payload([int(customer_id)]),
        step2={int(customer_id): payload},
    ) as h:
        response = _verify(h.service)

    assert response.contracts == []
    assert response.product_subscriber_status == payload["productSubscriberStatus"]


# -- multiple customer records: root cause 2 (clause 1.3 → requirement 2.10) --

def test_verify_subscription_fetches_every_customer_record():
    """Both ``customerId``s are requested, and both records' contracts come back.

    The replaced code called ``_extract_customer_ids(...)[0]`` and never issued the
    second request, so a granting contract under the second record was a false
    denial of a paying customer.  Asserting on the router is the point: the
    contract list alone could not tell the difference between "fetched and merged"
    and "never fetched".
    """
    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_B], email=MULTI_EMAIL),
        step2={
            CUSTOMER_A: build_step2_payload(
                customer_id=CUSTOMER_A,
                nodes=[_contract_node(901, next_billing_days=-40)],
                product_subscriber_status="PAUSED",
            ),
            CUSTOMER_B: build_step2_payload(
                customer_id=CUSTOMER_B,
                nodes=[_contract_node(902, next_billing_days=21)],
                product_subscriber_status="PAUSED",
            ),
        },
    ) as h:
        response = _verify(h.service)

    assert h.router.requested_customer_ids == [CUSTOMER_A, CUSTOMER_B]
    assert h.router.fetched_customer(CUSTOMER_B) is True
    assert len(response.contracts) == 2
    assert [c.customer_id for c in response.contracts] == [CUSTOMER_A, CUSTOMER_B]
    assert response.contracts[1].contract_id.endswith("/902")


def test_verify_subscription_collects_contracts_from_three_records():
    """The loop is a loop, not an unrolled pair."""
    ids = [CUSTOMER_A, CUSTOMER_B, 5000000003]

    with harness(
        step1=step1_payload(ids, email=MULTI_EMAIL),
        step2={
            cid: build_step2_payload(customer_id=cid, nodes=[_contract_node(910 + index)])
            for index, cid in enumerate(ids)
        },
    ) as h:
        response = _verify(h.service)

    assert h.router.requested_customer_ids == ids
    assert [c.customer_id for c in response.contracts] == ids


def test_verify_subscription_deduplicates_repeated_customer_ids():
    """A repeated ``customerId`` is fetched once, so its contracts appear once."""
    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_A], email=MULTI_EMAIL),
        step2={
            CUSTOMER_A: build_step2_payload(
                customer_id=CUSTOMER_A, nodes=[_contract_node(903)],
            ),
        },
    ) as h:
        response = _verify(h.service)

    assert h.router.requested_customer_ids == [CUSTOMER_A]
    assert len(response.contracts) == 1


# -- multiple records: the aggregated fallback status (2.9, 2.12) -------------

def _two_record_harness(status_a, status_b, ids=(CUSTOMER_A, CUSTOMER_B)):
    """Two records, both with empty ``nodes[]`` so only the fallback status is left."""
    first, second = ids
    return harness(
        step1=step1_payload([first, second], email=MULTI_EMAIL),
        step2={
            first: build_step2_payload(
                customer_id=first, nodes=[], product_subscriber_status=status_a,
            ),
            second: build_step2_payload(
                customer_id=second, nodes=[], product_subscriber_status=status_b,
            ),
        },
    )


@pytest.mark.parametrize(
    "status_a, status_b, expected",
    [
        pytest.param("CANCELLED", "ACTIVE", "ACTIVE", id="active-wins"),
        pytest.param("ACTIVE", "CANCELLED", "ACTIVE", id="active-wins-reversed"),
        pytest.param("CANCELLED", "PAUSED", "PAUSED", id="paused-beats-cancelled"),
        pytest.param("EXPIRED", "CANCELLED", "CANCELLED", id="cancelled-beats-other"),
    ],
)
def test_verify_subscription_aggregates_the_fallback_status_by_priority(
    status_a, status_b, expected,
):
    """The merged ``productSubscriberStatus`` follows the fixed priority (2.9).

    Reached only when every record has an empty ``nodes[]`` — with contracts
    present the decision reads those instead (2.12).
    """
    with _two_record_harness(status_a, status_b) as h:
        response = _verify(h.service)

    assert response.contracts == []
    assert response.product_subscriber_status == expected


def test_verify_subscription_fallback_status_is_independent_of_record_order():
    """Swapping the two records changes nothing about the merged status.

    First-seen aggregation would return ``CANCELLED`` for one ordering and
    ``ACTIVE`` for the other, and a customer's access would depend on the order
    Appstle happened to list their records.
    """
    with _two_record_harness("CANCELLED", "ACTIVE") as h:
        forward = _verify(h.service)
    with _two_record_harness("ACTIVE", "CANCELLED") as h:
        reversed_ = _verify(h.service)

    assert forward.product_subscriber_status == reversed_.product_subscriber_status
    assert forward.is_valid == reversed_.is_valid


def test_verify_subscription_contract_set_is_independent_of_record_order():
    """The same contracts are collected whichever record comes first (2.9)."""
    payloads = {
        CUSTOMER_A: build_step2_payload(
            customer_id=CUSTOMER_A, nodes=[_contract_node(921, next_billing_days=-40)],
        ),
        CUSTOMER_B: build_step2_payload(
            customer_id=CUSTOMER_B, nodes=[_contract_node(922, next_billing_days=21)],
        ),
    }

    with harness(step1=step1_payload([CUSTOMER_A, CUSTOMER_B]), step2=payloads) as h:
        forward = _verify(h.service)
    with harness(step1=step1_payload([CUSTOMER_B, CUSTOMER_A]), step2=payloads) as h:
        reversed_ = _verify(h.service)

    assert {c.contract_id for c in forward.contracts} == {
        c.contract_id for c in reversed_.contracts
    }
    assert forward.is_valid == reversed_.is_valid


# -- multiple records, multiple pages (2.11) ---------------------------------

def test_verify_subscription_accumulates_pages_within_each_record(monkeypatch):
    """Every page of every record lands in one contract list.

    ``_CONTRACT_PAGE_CURSOR_PARAM`` is patched to the harness placeholder because
    design Finding 4 leaves the real parameter name unknown, so production ships
    detection-plus-ERROR-log.  Patching it exercises the loop
    ``verify_subscription()`` drives, which is what turns "cursor-following can be
    switched on by one constant" into a claim with a test behind it.
    """
    monkeypatch.setattr(
        subscription_auth, "_CONTRACT_PAGE_CURSOR_PARAM", PAGINATION_PARAM,
    )

    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_B]),
        step2={
            CUSTOMER_A: paginate(
                customer_id=CUSTOMER_A,
                pages=[[_contract_node(931, next_billing_days=-40)], [_contract_node(932, next_billing_days=-35)]],
            ),
            CUSTOMER_B: paginate(
                customer_id=CUSTOMER_B,
                pages=[[_contract_node(933, next_billing_days=-30)], [_contract_node(934, next_billing_days=21)]],
            ),
        },
    ) as h:
        response = _verify(h.service)

    assert h.router.page_count(CUSTOMER_A) == 2
    assert h.router.page_count(CUSTOMER_B) == 2
    assert h.router.followed_next_page(CUSTOMER_B) is True
    assert [c.contract_id.rsplit("/", 1)[-1] for c in response.contracts] == [
        "931", "932", "933", "934",
    ]


def test_verify_subscription_logs_an_error_when_a_next_page_cannot_be_followed(caplog):
    """An unfollowable page is an ERROR on the real code path, not just in isolation.

    Under "grant if any contract grants" a granting contract stranded on an unread
    page is a false denial of a paying customer (2.11), so this record has to reach
    the log from ``verify_subscription()`` itself.
    """
    with harness(
        step1=step1_payload([CUSTOMER_A]),
        step2={CUSTOMER_A: load_fixture("contracts_page1")},
    ) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            response = _verify(h.service)

    assert h.router.page_count(CUSTOMER_A) == 1
    assert len(response.contracts) == 1
    assert any("Contracts may be missing" in message for message in _errors(caplog))


# -- Appstle failures still fall through to free tier (3.7) ------------------

@pytest.mark.parametrize(
    "failure, expected",
    [
        pytest.param(appstle_timeout, asyncio.TimeoutError, id="timeout"),
        pytest.param(appstle_malformed_json, ValueError, id="malformed-json"),
        pytest.param(lambda: appstle_http_error(500), aiohttp.ClientResponseError, id="http-500"),
    ],
)
def test_verify_subscription_propagates_a_first_record_failure_unchanged(failure, expected):
    """Timeout, malformed JSON, and a non-200 still raise the same types (3.7).

    ``login()`` catches exactly these and falls through to free tier rather than
    blocking the login, so the collection rewrite must not convert them into a
    response.
    """
    with harness(step1=step1_payload([CUSTOMER_A]), step2={CUSTOMER_A: failure()}) as h:
        with pytest.raises(expected):
            _verify(h.service)


def test_verify_subscription_step1_failure_propagates_unchanged():
    """A step-1 failure is unchanged too — the id list is never reached."""
    with harness(step1=appstle_timeout()) as h:
        with pytest.raises(asyncio.TimeoutError):
            _verify(h.service)

    assert h.router.step2_requests == []


def test_verify_subscription_later_record_failure_propagates_and_logs_error(caplog):
    """A second-record failure keeps the 3.7 fall-through, but says what was lost.

    The exception type and the fall-through are unchanged on purpose; the ERROR
    record exists because contracts that were already read are being discarded,
    which under "grant if any contract grants" can silently downgrade a paying
    customer to free tier.
    """
    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_B]),
        step2={
            CUSTOMER_A: build_step2_payload(customer_id=CUSTOMER_A, nodes=[_contract_node(941)]),
            CUSTOMER_B: appstle_timeout(),
        },
    ) as h:
        with caplog.at_level("ERROR", logger="backend.subscription_auth"):
            with pytest.raises(asyncio.TimeoutError):
                _verify(h.service)

    assert h.router.requested_customer_ids == [CUSTOMER_A, CUSTOMER_B]
    errors = _errors(caplog)
    assert any("customer record 2 of 2" in message for message in errors)
    assert any("falling through to free tier" in message for message in errors)


# -- observability (2.20) ----------------------------------------------------

def test_verify_subscription_step1_log_names_every_customer_record(caplog):
    """The step-1 log records the count and the ids, not a truncated payload repr.

    The ``str(data)[:500]`` line this replaces cut off before the interesting part
    of a multi-record payload — hiding exactly the data needed to diagnose this
    class of bug — and carried customer PII into the application log besides.
    """
    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_B]),
        step2={
            CUSTOMER_A: build_step2_payload(customer_id=CUSTOMER_A, nodes=[_contract_node(951)]),
            CUSTOMER_B: build_step2_payload(customer_id=CUSTOMER_B, nodes=[_contract_node(952)]),
        },
    ) as h:
        with caplog.at_level("INFO", logger="backend.subscription_auth"):
            _verify(h.service)

    step1_lines = [m for m in _infos(caplog) if "step-1 lookup" in m]
    assert len(step1_lines) == 1
    assert "2 customer record(s)" in step1_lines[0]
    assert str(CUSTOMER_A) in step1_lines[0]
    assert str(CUSTOMER_B) in step1_lines[0]


def test_verify_subscription_merge_log_describes_every_collected_contract(caplog):
    """The merge log names each contract's status and dates, with no cap (2.20)."""
    with harness(
        step1=step1_payload([CUSTOMER_A, CUSTOMER_B]),
        step2={
            CUSTOMER_A: build_step2_payload(
                customer_id=CUSTOMER_A, nodes=[_contract_node(961, status="CANCELLED")],
            ),
            CUSTOMER_B: build_step2_payload(
                customer_id=CUSTOMER_B, nodes=[_contract_node(962, status="ACTIVE")],
            ),
        },
    ) as h:
        with caplog.at_level("INFO", logger="backend.subscription_auth"):
            _verify(h.service)

    merge_lines = [m for m in _infos(caplog) if "Merged" in m]
    assert len(merge_lines) == 1
    assert "2 contract(s) total" in merge_lines[0]
    assert "status=CANCELLED" in merge_lines[0]
    assert "status=ACTIVE" in merge_lines[0]
    assert "/961" in merge_lines[0] and "/962" in merge_lines[0]


# ---------------------------------------------------------------------------
# _is_bypass_email (Task 9.6, requirement 2.14)
# ---------------------------------------------------------------------------
#
# The allowlist parse used to live inline in ``login()`` and nowhere else, which
# is clause 1.10: a bypass user was granted at login and bounced an hour later on
# refresh.  ``login()`` and ``refresh()`` now call this one function, so these
# cases cover the parse for both callers at once.
#
# Every case below is a way a hand-edited ``BYPASS_EMAILS`` value silently denies
# someone it was meant to let through.


def test_is_bypass_email_exact_match(monkeypatch):
    """The plain case: the email is listed verbatim."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com")

    assert _is_bypass_email("dave@example.com") is True


def test_is_bypass_email_unlisted_email_is_false(monkeypatch):
    """A non-member of a populated list does not bypass."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com,partner@example.com")

    assert _is_bypass_email("stranger@example.com") is False


def test_is_bypass_email_matches_any_entry_in_the_list(monkeypatch):
    """Every entry is checked, not just the first."""
    monkeypatch.setenv(
        "BYPASS_EMAILS", "first@example.com,second@example.com,third@example.com"
    )

    assert _is_bypass_email("first@example.com") is True
    assert _is_bypass_email("second@example.com") is True
    assert _is_bypass_email("third@example.com") is True


@pytest.mark.parametrize(
    "listed, candidate",
    [
        ("Dave@Example.COM", "dave@example.com"),
        ("dave@example.com", "DAVE@EXAMPLE.COM"),
        ("DaVe@ExAmPlE.cOm", "dAvE@eXaMpLe.CoM"),
    ],
)
def test_is_bypass_email_is_case_insensitive(monkeypatch, listed, candidate):
    """Case differs constantly between Shopify, the env var, and the login form."""
    monkeypatch.setenv("BYPASS_EMAILS", listed)

    assert _is_bypass_email(candidate) is True


@pytest.mark.parametrize(
    "raw",
    [
        " dave@example.com ",
        "\tdave@example.com",
        "partner@example.com,   dave@example.com",
        "partner@example.com, dave@example.com , other@example.com",
    ],
)
def test_is_bypass_email_strips_whitespace_around_entries(monkeypatch, raw):
    """Whitespace around an env-var entry is stripped, not matched literally."""
    monkeypatch.setenv("BYPASS_EMAILS", raw)

    assert _is_bypass_email("dave@example.com") is True


def test_is_bypass_email_strips_whitespace_around_the_candidate(monkeypatch):
    """A padded incoming email matches too — the padding is not the identity."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com")

    assert _is_bypass_email("  dave@example.com  ") is True


@pytest.mark.parametrize(
    "raw",
    [
        "dave@example.com,",
        "dave@example.com,,",
        ",dave@example.com",
        "dave@example.com, ,partner@example.com",
        ",,dave@example.com,,",
    ],
)
def test_is_bypass_email_tolerates_stray_commas(monkeypatch, raw):
    """A trailing or doubled comma yields empty entries, which are dropped.

    Without the filter the empty string would join the allowlist, so an email
    that normalized to ``""`` would bypass — and the real member listed alongside
    it would still match, hiding the hole.
    """
    monkeypatch.setenv("BYPASS_EMAILS", raw)

    assert _is_bypass_email("dave@example.com") is True


@pytest.mark.parametrize("raw", ["", "   ", ",", ",,", " , , "])
def test_is_bypass_email_empty_env_var_allows_nobody(monkeypatch, raw):
    """An empty or comma-only value is an empty allowlist, never a match-all."""
    monkeypatch.setenv("BYPASS_EMAILS", raw)

    assert _is_bypass_email("dave@example.com") is False
    assert _is_bypass_email("") is False


def test_is_bypass_email_unset_env_var_allows_nobody(monkeypatch):
    """An absent variable is the production default and must deny everyone."""
    monkeypatch.delenv("BYPASS_EMAILS", raising=False)

    assert _is_bypass_email("dave@example.com") is False


def test_is_bypass_email_empty_entries_do_not_match_an_empty_email(monkeypatch):
    """A blank email never bypasses, even against a comma-littered list."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com,,")

    assert _is_bypass_email("") is False
    assert _is_bypass_email("   ") is False


@pytest.mark.parametrize("candidate", [None, 0, [], {}, 12345, object()])
def test_is_bypass_email_non_string_candidate_is_false_without_raising(
    monkeypatch, candidate
):
    """This runs on the login path: an odd value must deny, not raise."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com")

    assert _is_bypass_email(candidate) is False


def test_is_bypass_email_does_not_match_a_substring(monkeypatch):
    """Membership is per-entry equality, not a substring search."""
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com")

    assert _is_bypass_email("dave@example.com.attacker.test") is False
    assert _is_bypass_email("ave@example.com") is False
    assert _is_bypass_email("xdave@example.com") is False


def test_is_bypass_email_reads_the_env_var_on_every_call(monkeypatch):
    """The value is re-read per call, never cached at import or on the service.

    Task 11 removes Dave from ``BYPASS_EMAILS`` on staging mid-verification, and
    Railway edits the variable without a redeploy, so a cached list would serve
    whatever was set when the process booted.
    """
    monkeypatch.setenv("BYPASS_EMAILS", "dave@example.com")
    assert _is_bypass_email("dave@example.com") is True

    monkeypatch.setenv("BYPASS_EMAILS", "someone.else@example.com")
    assert _is_bypass_email("dave@example.com") is False

    monkeypatch.delenv("BYPASS_EMAILS", raising=False)
    assert _is_bypass_email("dave@example.com") is False
