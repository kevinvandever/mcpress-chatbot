"""
Appstle Subscription Authentication Service

Verifies customer subscriptions via the Appstle API and manages
JWT-based session tokens for authenticated users.

This module handles CUSTOMER authentication only.
Admin authentication (backend/auth.py) remains completely separate.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import aiohttp
import jwt
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta

from pydantic import BaseModel, EmailStr

# Import RateLimiter from existing auth module
try:
    from backend.auth import RateLimiter
except ImportError:
    from auth import RateLimiter

# Import PasswordService for password authentication
try:
    from backend.password_service import PasswordService
except ImportError:
    from password_service import PasswordService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clock seam
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC instant for ACCESS-DECISION reads only.

    Single monkeypatch point for the offline property suite, which pins the
    clock to ``FIXTURE_NOW`` (see ``tests/fixtures/appstle/fixture_clock.py``)
    because the sanitized Appstle fixtures keep the captured dates verbatim and
    those dates are absolute.

    Behavior is identical to the inline ``datetime.now(timezone.utc)`` calls it
    replaces.  Token creation and the refresh grace-window check are not
    access-decision reads and deliberately still read the clock inline.
    """
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def _as_utc(value: datetime) -> datetime:
    """Return ``value`` as a UTC-aware datetime.

    A naive datetime is assumed to already be UTC and is simply tagged, which
    matches the ``if tzinfo is None: replace(tzinfo=timezone.utc)`` patch-up the
    existing decision ladders perform inline.  An aware datetime carrying some
    other offset is converted, so every datetime downstream of this function is
    directly comparable.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_iso8601(value: Any) -> Optional[datetime]:
    """Parse an Appstle ISO 8601 timestamp into a UTC-aware datetime.

    Centralizes the ``.replace("Z", "+00:00")`` dance and the
    ``if tzinfo is None`` coercion that the current code repeats in four places
    (design change 2).

    Behavior:

    * ``None`` in → ``None`` out, silently.  An absent date is normal Appstle
      data (``nextBillingDate`` can legitimately be null), not a failure.
    * ``Z``/``z`` suffix is translated to an explicit ``+00:00`` offset before
      parsing, so it works on Python versions where ``fromisoformat`` does not
      accept ``Z``.
    * An explicit offset is honoured and normalized to UTC.
    * A naive timestamp is treated as UTC.
    * A ``datetime`` passed straight through is normalized rather than rejected.
    * Anything unparseable → ``None`` plus a warning; never an exception, so a
      malformed date can never break a login.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return _as_utc(value)

    if not isinstance(value, str):
        logger.warning(
            "Failed to parse ISO 8601 datetime: expected str, got %s (%r)",
            type(value).__name__, value,
        )
        return None

    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse ISO 8601 datetime %r: %s", value, exc)
        return None

    return _as_utc(parsed)


# ---------------------------------------------------------------------------
# Calendar interval arithmetic
# ---------------------------------------------------------------------------

# Appstle's ``billingPolicy.interval`` values mapped to ``relativedelta`` keyword
# arguments.  Matching is EXACT and case-sensitive: per design Finding 2 Appstle
# sends upper-case units (`DAY`, `MONTH` observed; `WEEK`, `YEAR` supported but
# unobserved), and a lower-case or otherwise odd unit is a payload we do not
# understand.  Treating `"month"` as MONTH would be guessing at the meaning of an
# unrecognized value, and clause 2.8 requires unrecognized units to make
# ``paid_through`` underivable instead — which errs toward denial rather than
# handing out access on a guess.
_INTERVAL_TO_RELATIVEDELTA_KEY = {
    "DAY": "days",
    "WEEK": "weeks",
    "MONTH": "months",
    "YEAR": "years",
}


def _add_calendar_interval(
    anchor: Optional[datetime],
    interval: Optional[str],
    count: int = 1,
) -> Optional[datetime]:
    """Advance ``anchor`` by ``count`` billing intervals, calendar-aware (change 3).

    Requirement 2.7: MONTH and YEAR are real calendar units and must NOT be
    approximated as 30 or 365 days.  ``relativedelta`` handles the two cases that
    make the approximation wrong — month-end clamping (Jan 31 + 1 month is
    Feb 28/29, not Mar 2/3) and leap years (Feb 29 + 1 year is Feb 28) — where a
    fixed-day approximation drifts a little every month and a full day every leap
    year.  On an annual plan that drift decides access.

    ``count`` is honoured because it has to be: per design Finding 2 real Appstle
    data carries ``intervalCount`` 30 with ``interval`` DAY for the 30-day access
    product, so assuming 1 would understate paid time by a month on a live
    product.

    Returns ``None`` — never raises, never guesses — when:

    * ``anchor`` is ``None``.  Clause 2.8: interval arithmetic on a null anchor is
      meaningless, so it is not attempted.
    * ``interval`` is not exactly one of ``DAY``/``WEEK``/``MONTH``/``YEAR``
      (absent, empty, lower-case, or a unit we have never seen such as
      ``FORTNIGHT``).
    * ``count`` is not a positive integer.
    * The arithmetic would leave the representable datetime range.

    The ERROR-level log that clause 2.8 requires for an underivable
    ``paid_through`` belongs to ``_paid_through()`` (Task 8.4), which knows the
    contract the failure applies to; duplicating it here would emit two records
    per contract and name neither.

    The returned datetime is UTC-aware, since ``anchor`` is coerced through
    ``_as_utc()`` before the addition.
    """
    if anchor is None:
        return None

    key = _INTERVAL_TO_RELATIVEDELTA_KEY.get(interval) if isinstance(interval, str) else None
    if key is None:
        return None

    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        return None

    try:
        return _as_utc(anchor) + relativedelta(**{key: count})
    except (OverflowError, ValueError) as exc:
        # A date far enough out to overflow cannot be a real paid-through date;
        # fall back to "underivable" rather than letting a login raise.
        logger.warning(
            "Calendar interval overflow: anchor=%s interval=%s count=%s (%s)",
            anchor, interval, count, exc,
        )
        return None


# ---------------------------------------------------------------------------
# ContractView — the unit the access decision operates on
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContractView:
    """One normalized Appstle subscription contract (design change 1).

    Produced per node by the parser and consumed by the decision function, so
    the decision rule never touches raw payload dicts.

    Every datetime field is UTC-aware at construction: naive values are treated
    as UTC and other offsets are converted, which is what makes the
    ``paid_through`` comparisons in later changes safe without repeating
    ``tzinfo`` checks.

    ``renewal_anchor_field`` records WHERE the anchor came from, so the fallback
    log line can name the field and Property 12's ERROR path is testable.  Per
    design Finding 1, Appstle exposes no ``lastBillingDate``-style field, so in
    practice this is either ``"createdAt"`` or unset.
    """

    customer_id: int
    contract_id: Optional[str] = None
    status: Optional[str] = None
    next_billing_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    renewal_anchor: Optional[datetime] = None
    renewal_anchor_field: Optional[str] = None
    interval: Optional[str] = None
    interval_count: int = 1

    _DATETIME_FIELDS = ("next_billing_date", "created_at", "renewal_anchor")

    def __post_init__(self) -> None:
        for name in self._DATETIME_FIELDS:
            value = getattr(self, name)
            if isinstance(value, datetime):
                object.__setattr__(self, name, _as_utc(value))


# ---------------------------------------------------------------------------
# paid_through derivation and the per-contract grant rule
# ---------------------------------------------------------------------------

# Statuses that grant access only while paid time remains (clause 2.3).  ACTIVE
# is deliberately NOT in here: it short-circuits to a grant without consulting
# ``paid_through`` at all (clause 2.2).
_PAID_TIME_STATUSES = frozenset({"PAUSED", "CANCELLED"})

# The only renewal anchor Appstle actually exposes, per design Finding 1.  Named
# as a constant because ``_paid_through()`` has to recognize it to know that the
# anchor it is using is the weak one and must be logged at ERROR.
_WEAK_ANCHOR_FIELD = "createdAt"


def _paid_through(c: ContractView) -> Optional[datetime]:
    """Return the instant a contract's paid time runs out (design change 4).

    Implements the design's ``paidThrough``:

    1. ``next_billing_date`` when present.  This is the strong signal and, per
       design Finding 3, the only one that fired on any captured contract — every
       real payload carried a non-null ``nextBillingDate``, so everything below
       is exercised by synthetic fixtures today.
    2. Otherwise the renewal anchor plus ONE billing interval.

    **There is no anchor priority order to implement.** The provisional design
    had a ``lastBillingDate``-then-``createdAt`` ladder; design Finding 1 read the
    captured payloads and found that a contract node carries exactly two dates,
    ``createdAt`` and ``nextBillingDate``.  No ``lastBillingDate``,
    ``lastOrderDate``, ``lastPaymentDate``, ``billingAttempt``, or ``startDate``
    exists to prefer, so the ladder collapses to ``createdAt`` alone.  This
    function still reads ``ContractView.renewal_anchor`` rather than
    ``created_at`` directly, so the day Appstle grows a stronger anchor only the
    parser changes; when ``renewal_anchor`` is unset it falls back to
    ``created_at`` and labels it accordingly.

    **The ``createdAt`` path always logs at ERROR, and is always kept anyway.**
    ``createdAt`` + one interval is the end of the FIRST billing period, which is
    exact only for a contract that has never renewed.  Verified against real
    data: the renewed monthly subscriber has ``createdAt`` 2026-06-16 and MONTH ×
    1, so this path derives 2026-07-16 where the true paid-through was
    2026-08-16 — a full interval short.  The error direction is what makes it
    safe to keep: understating paid time can only DENY someone who should have
    been granted, never grant someone who should have been denied, and a denial
    is recoverable by resubscribing where a false grant is revenue given away.
    The ERROR record exists so those denials are visible rather than silent.

    Returns ``None`` — the "underivable" verdict, which clause 2.8 requires to
    make the contract not grant — plus an ERROR record when:

    * the anchor is null (no ``renewal_anchor`` and no ``created_at``).  Interval
      arithmetic on a null anchor is never attempted;
    * ``billingPolicy`` was absent, so ``ContractView.interval`` is ``None``;
    * the interval unit is not one Appstle is known to send (``FORTNIGHT``, a
      lower-case ``month``, an empty string);
    * ``interval_count`` is not a positive integer.

    The last four are exactly the cases ``_add_calendar_interval()`` reports as
    ``None``, so the classification lives in one place; this function's job is to
    attach the contract's identity to the failure and log it.
    """
    if c.next_billing_date is not None:
        return c.next_billing_date

    anchor = c.renewal_anchor
    anchor_field = c.renewal_anchor_field
    if anchor is None:
        # The parser normally fills ``renewal_anchor`` from ``createdAt``; this
        # keeps a hand-built or partially-populated view working the same way.
        anchor = c.created_at
        if anchor is not None:
            anchor_field = _WEAK_ANCHOR_FIELD

    if anchor is not None and anchor_field in (None, _WEAK_ANCHOR_FIELD):
        logger.error(
            "paid_through derived from %s for contract %s (customer %s) — "
            "understates paid time by one or more intervals for a renewed "
            "contract, so a paying customer may be denied",
            anchor_field or _WEAK_ANCHOR_FIELD, c.contract_id, c.customer_id,
        )

    paid_through = _add_calendar_interval(anchor, c.interval, c.interval_count)
    if paid_through is None:
        logger.error(
            "paid_through underivable for contract %s (customer %s): "
            "anchor=%s field=%r interval=%r intervalCount=%r — "
            "null anchor, or absent or unrecognized billing policy; "
            "contract does not grant",
            c.contract_id, c.customer_id, anchor, anchor_field,
            c.interval, c.interval_count,
        )
        return None

    return paid_through


def _contract_grants(c: ContractView) -> bool:
    """Does this ONE contract grant access on its own? (design change 5)

    Implements the design's ``contractGrants``.  Under requirement 2.1 a customer
    is granted access if ANY of their contracts returns ``True`` here, so this
    function never looks at other contracts and never at the customer-level
    ``productSubscriberStatus``.

    * ``ACTIVE`` → ``True``, short-circuited WITHOUT touching ``paid_through``
      (clause 2.2).  This is deliberate, not an oversight: when a renewal payment
      fails, Appstle can hold a contract ACTIVE with ``nextBillingDate`` already
      in the past while it retries, and access is meant to continue through that
      dunning window.  It is the one branch where a non-paying account keeps
      access.
    * ``PAUSED`` / ``CANCELLED`` → granted if and only if ``paid_through`` is in
      the future (clause 2.3).  Cancelling means "stop billing me", not "revoke
      the period I already paid for".  Note that PAUSED does not mean "suspended"
      on this system: per design Finding 3 it is what Appstle reports for a
      one-time or 30-day purchase that is simply not set to auto-renew, which is
      precisely why the derived date rather than the label decides.
    * Anything else, including an unrecognized status and a null one → ``False``
      (clause 2.4).  A label we do not understand is not evidence of paid time.

    Status matching is case-INSENSITIVE, mirroring the design's ``UPPER(k.status)``.

    That is the opposite of ``_add_calendar_interval()``'s deliberately
    case-SENSITIVE interval matching, and the asymmetry is intentional.  A status
    is a label being classified into a known bucket, and the classification is
    conservative in both directions: an unrecognized status does not grant, and
    recognizing ``"active"`` as ACTIVE cannot be wrong because Appstle has no
    other meaning for that word.  An interval unit is an input to arithmetic that
    produces a *date access is granted through*, so charitably reading ``"month"``
    as MONTH would be inventing paid time from a payload shape we do not
    understand — which clause 2.8 requires be treated as underivable instead.
    Case tolerance is safe where it only picks a bucket, and unsafe where it feeds
    a computation that hands out access.

    The clock is read through ``_utcnow()`` (design change 2b) rather than
    inline, so the offline suite can pin it to ``FIXTURE_NOW`` and keep the
    verbatim fixture dates meaningful.
    """
    status = c.status.upper() if isinstance(c.status, str) else ""

    if status == "ACTIVE":
        return True

    if status in _PAID_TIME_STATUSES:
        paid_through = _paid_through(c)
        return paid_through is not None and paid_through > _utcnow()

    return False


# ---------------------------------------------------------------------------
# Contract node parsing (design change 8)
# ---------------------------------------------------------------------------

def _parse_contract_nodes(
    payload: Any,
    customer_id: Any,
    email: Optional[str] = None,
) -> list[ContractView]:
    """Build one :class:`ContractView` per node in ``subscriptionContracts.nodes``.

    This is the fix for root cause 1.  The code it replaces read
    ``nodes[0].get("nextBillingDate")`` and discarded every other node, so a
    customer whose granting contract was not first was denied.  Here EVERY node
    is parsed, in payload order, and the per-contract ``status`` field is read for
    the first time anywhere in this codebase (clause 1.5) — until now only the
    customer-level ``productSubscriberStatus`` was consulted.

    Pure and module-level: no ``self``, no HTTP, no clock, no configuration, so it
    is directly unit-testable on a raw payload dict.

    Defensive at every level, because a malformed payload must never raise out of
    a login (clause 3.7 keeps Appstle failures falling through to free tier rather
    than blocking):

    * a non-dict ``payload``, a non-dict ``subscriptionContracts``, or a
      non-list ``nodes`` all yield ``[]``;
    * a non-dict node is skipped with a warning — one bad entry does not
      discard its siblings, which is the whole point of this rewrite;
    * unparseable dates become ``None`` via :func:`_parse_iso8601`, which makes
      the contract's ``paid_through`` underivable rather than inventing a date.

    ``created_at`` doubles as ``renewal_anchor`` with ``renewal_anchor_field``
    set to ``"createdAt"``.  Per design Finding 1 there is no stronger anchor to
    prefer: a contract node carries exactly two dates, ``createdAt`` and
    ``nextBillingDate``.  Recording the field name anyway is what lets
    ``_paid_through()`` name its ERROR record and keeps the anchor swappable if
    Appstle ever grows a ``lastBillingDate``.

    A ``billingPolicy`` whose ``intervalCount`` is not a positive integer is
    treated as unusable in full — ``interval`` is dropped too — so
    ``_paid_through()`` reports the contract as underivable (clause 2.8) instead
    of quietly assuming a count of 1 and handing out paid time the payload never
    claimed.
    """
    if not isinstance(payload, dict):
        return []

    block = payload.get("subscriptionContracts")
    if not isinstance(block, dict):
        return []

    nodes = block.get("nodes")
    if not isinstance(nodes, list):
        return []

    try:
        resolved_customer_id: Any = int(customer_id)
    except (TypeError, ValueError):
        # The view is only ever used for logging and the decision rule, neither
        # of which does arithmetic on the id, so an unparseable one is carried
        # through rather than dropping the customer's contracts.
        resolved_customer_id = customer_id

    views: list[ContractView] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            logger.warning(
                "Skipping non-dict subscription contract node at index %s for "
                "email=%s customerId=%s: type=%s",
                index, email, customer_id, type(node).__name__,
            )
            continue

        created_at = _parse_iso8601(node.get("createdAt"))
        interval, interval_count = _read_billing_policy(
            node.get("billingPolicy"), node.get("id"), email,
        )

        views.append(
            ContractView(
                customer_id=resolved_customer_id,
                contract_id=node.get("id"),
                status=node.get("status"),
                next_billing_date=_parse_iso8601(node.get("nextBillingDate")),
                created_at=created_at,
                renewal_anchor=created_at,
                renewal_anchor_field=_WEAK_ANCHOR_FIELD if created_at is not None else None,
                interval=interval,
                interval_count=interval_count,
            )
        )

    return views


def _read_billing_policy(
    policy: Any,
    contract_id: Any,
    email: Optional[str],
) -> tuple[Optional[str], int]:
    """Extract ``(interval, intervalCount)`` from a contract's ``billingPolicy``.

    Per design Finding 2 the keys are ``interval`` (a string such as ``DAY`` or
    ``MONTH``) and ``intervalCount`` (an integer, routinely 30 on this store's
    30-day access product, so it is never safe to assume 1).

    Returns ``(None, 1)`` when the policy is absent or unusable.  ``interval``
    ``None`` is the signal ``_paid_through()`` reads as "underivable", so an
    unusable count deliberately takes the whole policy down with it rather than
    substituting a count the payload never stated.
    """
    if policy is None:
        return None, 1

    if not isinstance(policy, dict):
        logger.warning(
            "Unexpected billingPolicy type %s on contract %s (email=%s) — "
            "treating the policy as absent",
            type(policy).__name__, contract_id, email,
        )
        return None, 1

    raw_interval = policy.get("interval")
    interval = raw_interval if isinstance(raw_interval, str) else None

    raw_count = policy.get("intervalCount")
    if raw_count is None:
        return interval, 1

    if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
        logger.warning(
            "Unusable billingPolicy.intervalCount %r on contract %s (email=%s) — "
            "treating the billing policy as absent so paid_through stays "
            "underivable rather than assuming a count",
            raw_count, contract_id, email,
        )
        return None, 1

    return interval, raw_count


def _describe_contracts(contracts: list[ContractView]) -> str:
    """Render contracts for the log line requirement 2.20 asks for.

    Replaces ``str(data)[:500]``, which truncated before the second contract of a
    multi-contract payload and so hid exactly the data needed to diagnose this
    class of bug.  Each contract contributes its id, its per-contract ``status``,
    both dates, and the billing interval — the fields the decision actually turns
    on — with no cap on how many contracts are described.
    """
    if not contracts:
        return " (no contracts)"

    parts = []
    for index, c in enumerate(contracts):
        parts.append(
            f" [{index}] contract={c.contract_id} status={c.status} "
            f"createdAt={c.created_at} nextBillingDate={c.next_billing_date} "
            f"interval={c.interval}x{c.interval_count}"
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Contract pagination (design change 11, requirement 2.11)
# ---------------------------------------------------------------------------

# Hard ceiling on step-2 requests per customer record.  Bounded because the loop
# is driven by a cursor the *server* supplies: a server that keeps advertising
# ``hasNextPage``, or that hands back a cursor pointing at a page it already
# served, would otherwise spin inside a login request.  Ten pages of contracts
# for one customer is already far past anything this store produces (the largest
# captured customer has two contracts on a single page).
_CONTRACT_PAGE_CAP = 10

# The query parameter name ``/api/external/v2/subscription-customers/{id}``
# accepts for a contract cursor.
#
# ``None`` means "unknown", and unknown is the honest state per design Finding 4.
# ``subscriptionContracts.pageInfo`` is cursor-based — ``hasPreviousPage``,
# ``hasNextPage``, ``startCursor``, ``endCursor``, with opaque base64 cursors —
# but ``hasNextPage`` was ``false`` for all three captured customers, so no
# pagination request was ever exercised and the parameter name was never
# observed.  Guessing it would mean sending an unrecognized parameter to the live
# API and reading whatever came back as a second page of contracts, which is a
# worse failure than knowing the page is missing.
#
# So the design decision recorded in Finding 4 is **detection now, cursor-
# following deferred**: while this is ``None``,
# :meth:`SubscriptionAuthService._fetch_contract_pages` detects an advertised
# next page and logs at ERROR that contracts may be missing.  The loop that would
# follow the page is written, routed through ``_appstle_get()``, and tested — it
# is enabled by setting this one constant to the real parameter name once
# Appstle's docs confirm it or a multi-page customer appears.  Nothing else has
# to change.
_CONTRACT_PAGE_CURSOR_PARAM: Optional[str] = None


def _read_page_info(payload: Any) -> Dict[str, Any]:
    """Return a contract payload's ``subscriptionContracts.pageInfo`` dict.

    Absent, null, or wrongly-typed ``pageInfo`` reads as ``{}`` — which
    :func:`_advertises_next_page` then reports as "no next page" — because a
    payload shape we do not recognize is not evidence that a page is missing, and
    an ERROR record per login for every such payload would bury the real ones.
    """
    if not isinstance(payload, dict):
        return {}

    block = payload.get("subscriptionContracts")
    if not isinstance(block, dict):
        return {}

    page_info = block.get("pageInfo")
    if not isinstance(page_info, dict):
        return {}

    return page_info


def _advertises_next_page(page_info: Dict[str, Any]) -> bool:
    """Does this ``pageInfo`` claim there are more contracts to read?

    Accepts the boolean ``True`` Appstle actually sends, and also the strings
    ``"true"``/``"1"`` in case a serialization change ever stringifies it.  The
    lenient reading is deliberate and safe in this one direction: a false
    positive costs one ERROR log line, while a false negative silently drops the
    page and, under "grant if any contract grants", a granting contract stranded
    on an unread page is a false denial of a paying customer (2.11).

    Everything else — ``False``, ``None``, an absent key, a number, a dict — reads
    as no next page.
    """
    value = page_info.get("hasNextPage")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    return False


# ---------------------------------------------------------------------------
# _extract_customer_ids (design change 9, requirement 2.10)
# ---------------------------------------------------------------------------

def _extract_customer_ids(data: Any) -> list:
    """Collect EVERY ``customerId`` in the step-1 Appstle lookup response.

    Root cause 2 of the multi-contract lockout: ``_extract_customer_id()``, which
    this replaces, returned on the first record with a non-null ``customerId``, so
    an email mapping to two Appstle customer records had the second record's
    contracts silently discarded one level above the ``nodes[0]`` truncation
    (clause 1.3 → requirement 2.10).

    Payload normalization is carried over unchanged, because Appstle has been
    observed sending all three shapes:

      * a bare list of customer records — ``[{"customerId": 123, ...}]``
      * a paginated envelope — ``{"content": [{"customerId": 123, ...}]}``
      * a single bare record — ``{"customerId": 123, ...}``

    Ordering is the payload's own, and duplicates are dropped on first sight, so
    ``[111, 222, 111]`` reads as ``[111, 222]``.  Order preservation matters for
    one reason only: it keeps ``ids[0]`` equal to what ``_extract_customer_id()``
    returned, which is what makes this change inert until Task 9.4 loops over the
    whole list.  The access decision itself must not depend on the order (2.9).

    Values are carried verbatim rather than coerced to ``int`` — design change 9
    writes the return as ``list[int]`` from the observed payloads, but nothing
    does arithmetic on the id (it is interpolated into the step-2 URL and logged),
    and coercing here would turn an odd-but-usable id into a lost customer.

    Never raises: a malformed payload yields ``[]``, which routes to the same
    no-subscription response an absent ``customerId`` already produced.
    """
    records: Any = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("content")
        if not isinstance(records, list):
            records = []
        # A single bare record, not wrapped in a list or a "content" envelope.
        if not records and data.get("customerId") is not None:
            records = [data]

    customer_ids: list = []
    for record in records:
        if not isinstance(record, dict):
            continue
        cid = record.get("customerId")
        if cid is None:
            continue
        # ``in`` rather than a set: an unhashable id would raise, and losing a
        # customer to a TypeError is the failure mode this whole fix is about.
        if cid not in customer_ids:
            customer_ids.append(cid)

    return customer_ids


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CustomerLoginRequest(BaseModel):
    """Request body for customer login with email and password."""
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot-password endpoint."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset-password endpoint."""
    token: str
    new_password: str


class AppstleSubscriptionResponse(BaseModel):
    """Parsed response from the Appstle subscription API.

    ``contracts`` is the field the access decision reads (design change 7).  The
    five scalar fields below it are kept so no external consumer breaks —
    ``backend/test_tag_auth_unit.py`` constructs this model directly, and
    ``login()`` / ``refresh()`` still read ``product_subscriber_status`` and
    ``next_billing_date`` until Tasks 9.5 / 9.6 move them onto
    ``decide_access()``.

    ``expiration_date`` stays ``None`` on every path: populating it is out of
    scope (clause 3.13), so ``expires_at`` in the login body and
    ``subscription_expires_at`` in the JWT remain null.
    """
    is_valid: bool
    subscription_status: Optional[str] = None  # "ACTIVE", "CANCELLED", "EXPIRED", "PAUSED", or None
    expiration_date: Optional[datetime] = None
    customer_email: Optional[str] = None
    next_billing_date: Optional[datetime] = None  # Contract billing date from Appstle API
    # Raw status: ACTIVE, PAUSED, CANCELLED, None when the key was present and
    # null, or the MISSING_STATUS sentinel when the key was ABSENT from the
    # payload.  Typed ``Any`` rather than ``Optional[str]`` precisely to carry
    # that sentinel: ``data.get("productSubscriberStatus")`` cannot distinguish
    # "absent" from "present and null", and clause 2.19 requires an ERROR record
    # for the absent case only.  decide_access() tests it with ``is``.
    product_subscriber_status: Any = None
    contracts: list[ContractView] = []  # EVERY contract, in payload order (2.1)


class LoginSuccessResponse(BaseModel):
    """Returned on successful login with an active subscription."""
    success: bool = True
    token: str
    email: str
    subscription_status: str
    expires_at: Optional[str] = None  # ISO datetime


class LoginDeniedResponse(BaseModel):
    """Returned when login is denied due to subscription issues."""
    success: bool = False
    error: str
    subscription_status: Optional[str] = None
    redirect_url: Optional[str] = None


class RefreshResponse(BaseModel):
    """Returned from the token refresh endpoint."""
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None
    redirect_url: Optional[str] = None


# ---------------------------------------------------------------------------
# The tag-based fallback used to live here (TagConfig, load_tag_config(),
# _derive_status_from_tags(), and the two service methods
# _extract_customer_tags() / _parse_tags_response()).  It is DELETED, per
# requirement 2.18 and design change 15.
#
# Clause 2.18 allowed either wiring its verdict into the decision path or
# deleting it.  Deletion is the behavior-preserving choice: the tag verdict was
# already discarded (clause 1.12 — it populated is_valid and subscription_status
# but never product_subscriber_status, the only field the decision path reads),
# so those customers landed in free tier before this deletion and still do.
# Wiring it in would instead CHANGE live behavior on the strength of a signal
# this system has already documented as wrong twice: customer tags reported
# "active" for a paused subscription.
#
# Where the parser fell back to tags it now reports the customer-level status as
# MISSING_STATUS and lets decide_access()'s productSubscriberStatus fallback
# decide (free tier, plus the ERROR record clause 2.19 asks for).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Status-specific denial messages
# ---------------------------------------------------------------------------

# Values are the EXACT strings login() and refresh() emit inline today (clause
# 2.21). The pre-fix values omitted the "Resubscribe to continue." sentence, so
# adopting the dict as the live source without aligning it first would silently
# rewrite the denial copy on the preserved expired-subscriber path (3.3).
#
# ACTIVE is here for the pathological case only: the status label says ACTIVE but
# the contract did not grant. That combination cannot arise from _contract_grants()
# — ACTIVE short-circuits to a grant — so reaching this entry means the label and
# the decision disagreed, and the expired copy is the honest thing to show.
_EXPIRED_DENIAL = "Your subscription has expired. Resubscribe to continue."
_CANCELLED_DENIAL = "Your subscription has been cancelled. Resubscribe to continue."

DENIAL_MESSAGES: Dict[str, str] = {
    "ACTIVE": _EXPIRED_DENIAL,
    "EXPIRED": _EXPIRED_DENIAL,
    "PAUSED": _EXPIRED_DENIAL,
    "CANCELLED": _CANCELLED_DENIAL,
}

# Default message for not_found, unknown, empty, or any other status.
# Stays reachable: an unrecognized or absent status must not be described as
# expired or cancelled, because neither claim is known to be true.
DEFAULT_DENIAL_MESSAGE = "No subscription found"


def _get_denial_message(status: Optional[str]) -> str:
    """Return the user-facing denial message for a given subscription status."""
    if not status:
        return DEFAULT_DENIAL_MESSAGE
    return DENIAL_MESSAGES.get(status.upper(), DEFAULT_DENIAL_MESSAGE)


# Fixed priority for folding the customer-level fallback status of several
# Appstle customer records into one value (requirement 2.9, used by
# ``verify_subscription()`` via ``_merge_customer_records()``).  Anything not
# listed ranks after these three, and a null or blank value ranks last of all.
_FALLBACK_STATUS_PRIORITY = ("ACTIVE", "PAUSED", "CANCELLED")


def _aggregate_product_subscriber_status(values: Any) -> Optional[str]:
    """Reduce several records' ``productSubscriberStatus`` values to one.

    Priority is fixed — ``ACTIVE > PAUSED > CANCELLED > other > None`` — rather
    than "whichever record Appstle listed first".  First-seen would make the
    aggregate, and therefore the fallback verdict clause 2.12 draws from it, depend
    on payload order, which clause 2.9 forbids: the same set of customer records in
    a different order has to produce the same answer.

    The ordering is the generous one on purpose.  ACTIVE outranks PAUSED and
    CANCELLED so a customer holding an active record alongside a lapsed one is not
    denied by the lapsed one — the same "any grant wins" reasoning ``decide_access()``
    applies to contracts (2.1), applied one level up.

    Ties are broken deterministically, so two unrecognized values cannot make the
    result order-dependent either: same rank → smallest upper-cased string, then
    smallest raw string.  The winner is returned VERBATIM rather than upper-cased,
    because callers upper-case for comparison themselves and the raw value is what
    belongs in a log.

    ``None``, non-strings, and blank strings are ignored entirely; if nothing
    usable remains the result is ``None``, which is the "no status" input
    ``decide_access()`` already treats as free tier.
    """
    ranked: list = []
    for value in values or ():
        if not isinstance(value, str) or not value.strip():
            continue
        upper = value.upper()
        rank = (
            _FALLBACK_STATUS_PRIORITY.index(upper)
            if upper in _FALLBACK_STATUS_PRIORITY
            else len(_FALLBACK_STATUS_PRIORITY)
        )
        ranked.append((rank, upper, value))

    if not ranked:
        return None

    return min(ranked)[2]


def _normalize_status(status: Optional[str]) -> str:
    """Normalize a subscription status string for response payloads."""
    if not status:
        return "not_found"
    mapping = {
        "ACTIVE": "active",
        "CANCELLED": "cancelled",
        "EXPIRED": "expired",
        "PAUSED": "paused",
    }
    return mapping.get(status.upper(), "not_found")


# ---------------------------------------------------------------------------
# The single access decision path (design change 6)
# ---------------------------------------------------------------------------

class _MissingStatus:
    """Type of the ``MISSING_STATUS`` sentinel.  One instance, never compared by
    value — callers and ``decide_access()`` test it with ``is``.

    ``__bool__`` is ``False`` so the sentinel behaves like the ``None`` it stands
    in for anywhere it reaches an ``if not status:`` guard that predates it, and
    ``__repr__`` names itself so it reads clearly in a log line or a pytest diff.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - repr is for humans
        return "MISSING_STATUS"

    def __bool__(self) -> bool:
        return False


# Passed as ``product_subscriber_status`` when the ``productSubscriberStatus`` key
# was ABSENT from the Appstle payload, as opposed to present and null.
#
# Clause 2.19 requires an ERROR-level record for the absent case only: an absent
# field means the payload is not the shape we think it is, which is what silently
# dropped customers to free tier and is the thing worth waking someone up for.  A
# field that is present and null is normal data for a customer with no
# subscription and stays quiet.  ``None`` alone cannot express both, since
# ``data.get("productSubscriberStatus")`` returns ``None`` either way.
#
# A sentinel rather than a second ``status_present: bool`` parameter, for two
# reasons: the design fixes ``decide_access()``'s signature at
# ``(contracts, product_subscriber_status, email)``, and a parallel boolean is a
# second thing to keep in sync with the value it describes — exactly the drift
# this spec exists to remove.  Task 9.4 supplies it, using a presence check
# (``"productSubscriberStatus" in payload``) rather than a truthiness test.
MISSING_STATUS = _MissingStatus()

# Customer-level fallback statuses that deny (clause 2.12).  ACTIVE is handled
# separately because it grants, and everything else falls through to free tier.
_FALLBACK_DENYING_STATUSES = frozenset({"PAUSED", "CANCELLED"})


@dataclass(frozen=True)
class AccessDecision:
    """The outcome of ONE access decision, and the only thing callers branch on.

    ``login()`` and ``refresh()`` (Tasks 9.5 / 9.6) read ``granted``,
    ``subscription_status``, ``denial_message``, and ``redirect_url_needed``;
    ``deciding_contract`` is there for the log line, so a decision can be traced
    to the contract that produced it.

    ``redirect_url_needed`` rather than the URL itself: the signup URL lives on
    the service instance, and ``decide_access()`` is a pure module-level function
    that must not read configuration.
    """

    granted: bool
    subscription_status: str
    denial_message: Optional[str] = None
    redirect_url_needed: bool = False
    deciding_contract: Optional[ContractView] = None


def _newest_contract_key(c: ContractView) -> tuple:
    """Sort key implementing "most recent contract by ``createdAt``" (clause 2.16).

    Three components, so ``max()`` over any permutation of the same set returns
    the same contract (clause 2.9):

    1. ``0`` when ``created_at`` is null, ``1`` otherwise — a null ``createdAt``
       sorts LAST in preference, i.e. it loses to any contract whose age is
       actually known, and wins only when nothing else has a date either.  An
       unknown creation time is not evidence of being the most recent.
    2. ``created_at`` itself.  Every ``ContractView`` datetime is UTC-aware at
       construction, so the comparison needs no ``tzinfo`` patch-up.  The
       placeholder used for the null group is never compared against a real
       datetime, because component 1 already separates the groups.
    3. ``contract_id`` as a string — the deterministic tiebreak clause 2.16
       requires for identical timestamps.  Without it ``max()`` would return
       whichever equal-keyed contract came first in the list, which is precisely
       the order dependence clause 2.9 forbids.
    """
    created = c.created_at
    return (
        0 if created is None else 1,
        created if created is not None else datetime.min.replace(tzinfo=timezone.utc),
        str(c.contract_id or ""),
    )


def decide_access(
    contracts: Any,
    product_subscriber_status: Any,
    email: Optional[str] = None,
) -> AccessDecision:
    """Decide access for ONE customer.  The single decision path (2.13).

    Replaces the three drifted copies of the step-4 ladder in ``login()``,
    ``refresh()``, and the deleted test endpoint.  Pure and module-level: no
    HTTP, no database, no environment, no service instance, and no clock read of
    its own — the clock is reached only indirectly through ``_contract_grants()``
    → ``_paid_through()`` → ``_utcnow()``, which is what lets the offline suite
    pin it.  Logging is the only side effect.

    The rule, in order:

    1. **ANY contract grants → granted, ``"active"``** (clause 2.1).  Every
       contract is evaluated, not just ``nodes[0]``; that truncation is the bug.
    2. **Contracts exist but none grants → denied** (clause 2.5).  The message
       and the reported status come from the MOST RECENT contract (clause 2.16)
       via ``_get_denial_message()`` / ``_normalize_status()`` (clause 2.17), so a
       customer whose newest subscription was cancelled is told "cancelled"
       rather than "expired".
    3. **No contracts at all → fall back to the customer-level
       ``productSubscriberStatus``** (clause 2.12), which is a fallback and never
       the primary signal: ``ACTIVE`` grants ``"active"``, ``PAUSED`` /
       ``CANCELLED`` deny with the matching message, and anything else —
       unrecognized, null, or absent — grants free tier, with an ERROR record
       when the field was ABSENT (``MISSING_STATUS``, clause 2.19).

    Order independence (clause 2.9) holds for the verdict, the
    ``subscription_status``, and the denial message: the grant test is an
    existence check over the whole set, and both contract selections go through
    ``_newest_contract_key()``, which is a total order.  Every contract is
    evaluated rather than short-circuiting on the first grant, so the ERROR
    records ``_paid_through()`` emits are the same set whatever order Appstle
    returned.

    ``contracts`` is consumed defensively (``list(contracts or [])``) so a
    generator, a tuple, or ``None`` all work, and the caller's list is never
    mutated.
    """
    contract_list = list(contracts or [])

    # Not short-circuited on purpose: see the docstring's note on log stability.
    granting = [c for c in contract_list if _contract_grants(c)]
    if granting:
        deciding = max(granting, key=_newest_contract_key)
        logger.info(
            "Access granted for email=%s: %s of %s contract(s) grant, deciding "
            "contract=%s status=%s",
            email, len(granting), len(contract_list),
            deciding.contract_id, deciding.status,
        )
        return AccessDecision(
            granted=True,
            subscription_status="active",
            deciding_contract=deciding,
        )

    if contract_list:
        newest = max(contract_list, key=_newest_contract_key)
        logger.info(
            "Access denied for email=%s: none of %s contract(s) grant; newest "
            "contract=%s status=%s createdAt=%s",
            email, len(contract_list), newest.contract_id, newest.status,
            newest.created_at,
        )
        return AccessDecision(
            granted=False,
            subscription_status=_normalize_status(newest.status),
            denial_message=_get_denial_message(newest.status),
            redirect_url_needed=True,
            deciding_contract=newest,
        )

    # No contracts: the customer-level fallback (clause 2.12).
    status_absent = product_subscriber_status is MISSING_STATUS
    status_upper = (
        product_subscriber_status.upper()
        if isinstance(product_subscriber_status, str)
        else ""
    )

    if status_upper == "ACTIVE":
        logger.info(
            "Access granted for email=%s: no contracts, customer-level "
            "productSubscriberStatus=ACTIVE",
            email,
        )
        return AccessDecision(granted=True, subscription_status="active")

    if status_upper in _FALLBACK_DENYING_STATUSES:
        logger.info(
            "Access denied for email=%s: no contracts, customer-level "
            "productSubscriberStatus=%s",
            email, status_upper,
        )
        return AccessDecision(
            granted=False,
            subscription_status=_normalize_status(status_upper),
            denial_message=_get_denial_message(status_upper),
            redirect_url_needed=True,
        )

    if status_absent:
        # Clause 2.19: the outcome stays free tier — the safer of the two — but
        # the downgrade stops being invisible.  An absent field means the payload
        # shape changed, and every customer hitting it is silently losing access
        # they may have paid for.
        logger.error(
            "productSubscriberStatus ABSENT from Appstle response for email=%s "
            "with no contracts — granting free tier, but the payload is not the "
            "shape this code expects and paid customers may be downgraded",
            email,
        )
    else:
        logger.info(
            "Free-tier access for email=%s: no contracts, "
            "productSubscriberStatus=%r",
            email, product_subscriber_status,
        )

    return AccessDecision(granted=True, subscription_status="free")


# ---------------------------------------------------------------------------
# BYPASS_EMAILS allowlist (design change 13, requirement 2.14)
# ---------------------------------------------------------------------------

_BYPASS_EMAILS_ENV = "BYPASS_EMAILS"


def _is_bypass_email(email: Any) -> bool:
    """Is ``email`` on the ``BYPASS_EMAILS`` allowlist?

    One helper, called by BOTH ``login()`` and ``refresh()``, because the list
    computation living inline in ``login()`` only is clause 1.10: a bypass user was
    granted access at login and could be bounced an hour later when the token
    refreshed.  Two copies of a three-line parse is all it took for the two
    callers to drift, so there is now one (requirement 2.14).

    The environment variable is read on EVERY call rather than cached at import or
    at ``__init__``.  Railway sets it per environment and the value is edited
    without a redeploy — Task 11 removes Dave from it on staging mid-verification
    — and a cached copy would silently serve the value that happened to be present
    when the process booted.  A ``getenv`` per login is not a cost worth
    optimizing.

    Parsing is deliberately forgiving of the ways a hand-edited env var goes
    wrong, since every one of them silently denies a bypass user otherwise:

    * ``"a@x.com,b@x.com,"`` — a trailing comma yields an empty entry, dropped;
    * ``" a@x.com , b@x.com "`` — surrounding whitespace on either the entry or
      the incoming email is stripped;
    * ``"A@X.com"`` vs ``"a@x.com"`` — matching is case-insensitive;
    * ``""`` or unset — an empty allowlist, so nothing bypasses.

    A non-string or blank ``email`` is ``False`` rather than an exception: this
    runs on the login path, and an odd email must deny the bypass, not break the
    request.
    """
    if not isinstance(email, str):
        return False

    candidate = email.strip().lower()
    if not candidate:
        return False

    raw = os.getenv(_BYPASS_EMAILS_ENV, "") or ""
    return candidate in [
        entry.strip().lower() for entry in raw.split(",") if entry.strip()
    ]


# ---------------------------------------------------------------------------
# SubscriptionAuthService
# ---------------------------------------------------------------------------

class SubscriptionAuthService:
    """
    Verifies customer credentials against the Appstle subscription API,
    issues and validates JWT session tokens, and handles token refresh.
    """

    def __init__(self):
        self.appstle_api_url: Optional[str] = os.getenv("APPSTLE_API_URL")
        self.appstle_api_key: Optional[str] = os.getenv("APPSTLE_API_KEY")
        self.jwt_secret: str = os.getenv("JWT_SECRET_KEY", "")
        self.signup_url: str = os.getenv("SUBSCRIPTION_SIGNUP_URL", "")

        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=1)
        self.grace_window = timedelta(minutes=5)
        self.appstle_timeout = 10  # seconds

        # Rate limiter: 5 attempts per IP per 15 minutes
        self.rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)

        # Password service for local password authentication
        try:
            self.password_service = PasswordService()
        except Exception as exc:
            logger.warning("⚠️ PasswordService initialization failed: %s — password auth disabled", exc)
            self.password_service = None

        # Configuration health check
        self._config_valid = True
        if not self.appstle_api_url:
            logger.warning("⚠️ APPSTLE_API_URL is not set — subscription verification disabled")
            self._config_valid = False
        if not self.appstle_api_key:
            logger.warning("⚠️ APPSTLE_API_KEY is not set — subscription verification disabled")
            self._config_valid = False
        if not self.jwt_secret:
            logger.warning("⚠️ JWT_SECRET_KEY is not set — token signing will fail")
            self._config_valid = False
        if not self.signup_url:
            logger.warning("⚠️ SUBSCRIPTION_SIGNUP_URL is not set — redirect URLs will be empty")

        # The tag-based subscription config (self.tag_config = load_tag_config())
        # and the log line that echoed its patterns are gone with the rest of the
        # tag fallback (2.18, design change 15).

    # ------------------------------------------------------------------
    # _build_contract_response
    # ------------------------------------------------------------------
    def _build_contract_response(
        self,
        data: Any,
        customer_id: Any,
        email: str,
    ) -> AppstleSubscriptionResponse:
        """Assemble one customer record's step-2 payload into a response model.

        The thin assembler half of design change 8: :func:`_parse_contract_nodes`
        does the per-node work, this method attaches the customer-level fields and
        logs the payload the way requirement 2.20 asks for.

        Replaces ``_parse_contract_response()``, which extracted only
        ``nodes[0].nextBillingDate``.  ``contracts`` now carries EVERY contract
        (clause 2.1), which is what ``decide_access()`` reads once Tasks 9.4-9.6
        wire it in.

        **The tag fallback is gone** (2.18, design change 15, Task 9.7).  A
        non-dict payload, or one with no ``productSubscriberStatus`` key, used to
        route to ``_parse_tags_response()``, whose verdict never reached the
        decision path because it never set ``product_subscriber_status`` (clause
        1.12).  Both paths now report the customer-level status as
        ``MISSING_STATUS`` — the "key was ABSENT" sentinel — and hand the decision
        to ``decide_access()``'s ``productSubscriberStatus`` fallback (clause
        2.12), which grants free tier and logs at ERROR (clause 2.19).  Free tier
        is where those customers landed before the deletion too, since the tag
        verdict was discarded; what changes is that the downgrade is now loud
        instead of silent.

        Contracts parsed from the payload are still attached on the fallback
        paths, so a payload that carries contracts but no customer-level status
        keeps them and is decided on them.  ``productSubscriberStatus`` is a
        fallback and never the primary signal (clause 2.12), so discarding
        contracts here would invert that.  (For a non-dict payload
        ``_parse_contract_nodes()`` returns ``[]`` anyway.)

        Absence is detected with a KEY-PRESENCE test rather than a truthiness
        one: ``data.get(...)`` cannot tell an absent key from a present null, and
        clause 2.19 wants the ERROR for the absent case only — a present null is
        ordinary data for a customer with no subscription.

        **The scalar ``next_billing_date`` still comes from the FIRST contract**,
        which is byte-identical to the ``nodes[0].nextBillingDate`` the old parser
        produced.  Nothing decides on it any more — ``login()`` and ``refresh()``
        read ``contracts`` through ``decide_access()`` — it is kept for logging
        continuity and for external consumers of this model.

        ``expiration_date`` is never set, on any path (clause 3.13).
        """
        contracts = _parse_contract_nodes(data, customer_id, email)

        # Requirement 2.20: the contract count plus each contract's status and
        # dates, in place of the str(data)[:500] truncation that cut off before
        # the second contract of a multi-contract payload.
        logger.info(
            "Appstle step-2 payload for email=%s customerId=%s: %d contract(s)%s",
            email, customer_id, len(contracts), _describe_contracts(contracts),
        )

        if not isinstance(data, dict):
            # No customer-level status can be read out of a payload that is not
            # even a dict, so it is reported as absent and decide_access() decides
            # (free tier + ERROR, clause 2.19).
            logger.warning(
                "Contract response for email=%s customerId=%s is %s, not a dict — "
                "reporting productSubscriberStatus as absent",
                email, customer_id, type(data).__name__,
            )
            return AppstleSubscriptionResponse(
                is_valid=False,
                subscription_status=None,
                customer_email=email,
                product_subscriber_status=MISSING_STATUS,
                contracts=contracts,
            )

        if "productSubscriberStatus" not in data:
            # Absent, not merely null.  No log line here on purpose: clause 2.19's
            # ERROR belongs to decide_access(), which knows whether the customer
            # had contracts to decide on and is therefore actually falling back.
            return AppstleSubscriptionResponse(
                is_valid=False,
                subscription_status=None,
                customer_email=email,
                product_subscriber_status=MISSING_STATUS,
                contracts=contracts,
            )

        product_subscriber_status: Optional[str] = data.get("productSubscriberStatus")

        # Logging continuity only — see the docstring.
        next_billing_date = contracts[0].next_billing_date if contracts else None

        logger.info(
            "Contract data for email=%s: productSubscriberStatus=%s, nextBillingDate=%s",
            email, product_subscriber_status, next_billing_date,
        )

        # ``is_valid`` means "a customer record was read", so it is True whenever
        # the key was present — including present-and-null, which used to detour
        # through the tag fallback and come back False.  Nothing decides on this
        # field (``login()`` and ``refresh()`` read ``contracts`` and
        # ``product_subscriber_status``), so the verdict is unchanged either way.
        return AppstleSubscriptionResponse(
            is_valid=True,
            subscription_status=product_subscriber_status,
            customer_email=email,
            product_subscriber_status=product_subscriber_status,
            next_billing_date=next_billing_date,
            contracts=contracts,
        )

    # ``_with_contracts()`` lived here.  It existed only to attach parsed
    # contracts to a response built by the tag fallback, so it went with it
    # (Task 9.7); every path above now builds its own response with ``contracts``
    # already set.

    # ------------------------------------------------------------------
    # _appstle_get
    # ------------------------------------------------------------------
    async def _appstle_get(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Issue an authenticated GET to the Appstle API and return parsed JSON.

        Single choke point for every Appstle HTTP call.  It performs the status
        check, the JSON parse, and the error raising that steps 1 and 2 of
        ``verify_subscription()`` previously duplicated inline, with identical
        behavior:

          - non-200 → ``aiohttp.ClientResponseError`` carrying the upstream status
          - unparseable body → ``ValueError``
          - timeouts propagate untouched from ``session.get``

        Callers therefore keep falling through to free tier exactly as before.

        This is also the test seam: property tests patch this one method with a
        payload router keyed by URL, so the parser, the multi-customer
        traversal, and the pagination loop all stay inside the system under
        test.
        """
        headers = {"X-API-Key": self.appstle_api_key}

        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                logger.error(
                    "Appstle API returned status %d for url=%s params=%s",
                    resp.status, url, params,
                )
                raise aiohttp.ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message=f"Appstle API returned {resp.status}",
                )

            try:
                data = await resp.json()
            except Exception as exc:
                logger.error("Malformed JSON from Appstle API (url=%s): %s", url, exc)
                raise ValueError(f"Malformed Appstle response: {exc}") from exc

        # Requirement 2.20: no raw-payload repr.  The 500-character truncation
        # this replaces cut off before the interesting contracts in a
        # multi-contract payload, hiding the very data needed to diagnose this
        # bug class; the structured per-contract line is emitted by
        # _build_contract_response() instead, which knows what the fields mean.
        # It also kept customer PII (emails, cardholder names, masked card
        # numbers) in the application log, which nothing needed.
        logger.info(
            "Appstle API response for url=%s params=%s: %s payload",
            url, params, type(data).__name__,
        )
        return data

    # ------------------------------------------------------------------
    # _fetch_contract_pages
    # ------------------------------------------------------------------
    async def _fetch_contract_pages(
        self,
        session: aiohttp.ClientSession,
        customer_id: Any,
        email: Optional[str],
        first_page: Any,
        first_page_contracts: Optional[list] = None,
    ) -> list:
        """Return EVERY contract for one customer record, across all its pages.

        Requirement 2.11.  The caller (Task 9.4) has already fetched page 1 —
        it needs that payload's customer-level ``productSubscriberStatus``
        regardless — and passes it in here as ``first_page``, optionally with the
        ``ContractView``s it already parsed from it so the nodes are not parsed
        twice.  Everything returned is accumulated in payload order: page 1's
        contracts first, then page 2's, and so on.

        **Why this matters more than it used to.** Under the old "first contract
        decides" rule an unread page was merely incomplete data.  Under "grant if
        any contract grants" (2.1) a granting contract stranded on an unread page
        is a FALSE DENIAL of a paying customer, so incomplete data now biases
        toward lockout — which is why an unfollowable page is an ERROR and not a
        debug line.

        **Cursor-following is deferred, and this ships as detection plus an ERROR
        log.**  Design Finding 4: ``pageInfo`` is cursor-based, but ``hasNextPage``
        was ``false`` on all three captured customers, so the request parameter
        name that carries a cursor was never observed and is not in Appstle's
        documented surface.  While ``_CONTRACT_PAGE_CURSOR_PARAM`` is ``None``
        this method reads page 1, notices ``hasNextPage``, logs at ERROR that
        contracts may be missing (naming the ``customerId`` and the ``endCursor``
        so the page can be chased by hand), and returns what it has.  It does not
        guess a parameter name at the live API: sending an unrecognized parameter
        and reading the response as "page 2" could duplicate page 1's contracts or
        silently return an unrelated slice, which is worse than a logged gap.

        The loop below is nonetheless real, not a placeholder.  It requests
        subsequent pages through ``_appstle_get()`` — the same seam the property
        tests' router patches, which is how it is exercised against
        ``contracts_page1.json`` / ``contracts_page2.json`` — accumulates across
        pages, and is bounded by ``_CONTRACT_PAGE_CAP``.  Setting that one
        constant to the real parameter name turns cursor-following on with no
        restructuring here.

        Failures on a SECOND or later page are swallowed after an ERROR log, and
        the contracts gathered so far are returned.  Letting the exception
        propagate would discard page 1's contracts too and route the customer
        through the Appstle-unavailable path to free tier (3.7); returning a
        partial set at least lets a granting contract that was already read do its
        job.  A failure on page 1 is the caller's to handle and still falls
        through as before.
        """
        contracts: list = (
            list(first_page_contracts)
            if first_page_contracts is not None
            else _parse_contract_nodes(first_page, customer_id, email)
        )

        page_info = _read_page_info(first_page)
        step2_url = (
            f"{self.appstle_api_url}"
            f"/api/external/v2/subscription-customers/{customer_id}"
        )
        seen_cursors: list = []
        pages_read = 1

        while _advertises_next_page(page_info):
            cursor = page_info.get("endCursor")

            if _CONTRACT_PAGE_CURSOR_PARAM is None:
                # Design Finding 4: detection only, by decision.
                logger.error(
                    "Appstle advertises another page of contracts for customerId=%s "
                    "(email=%s) but it cannot be followed: the cursor request "
                    "parameter is unknown (design Finding 4). Contracts may be "
                    "missing, and under 'grant if any contract grants' a granting "
                    "contract on an unread page is a false denial of a paying "
                    "customer. %d contract(s) read from %d page(s); "
                    "endCursor=%r for manual follow-up",
                    customer_id, email, len(contracts), pages_read, cursor,
                )
                break

            if pages_read >= _CONTRACT_PAGE_CAP:
                logger.error(
                    "Stopped paginating Appstle contracts for customerId=%s "
                    "(email=%s) at the %d-page cap while hasNextPage is still "
                    "true. Contracts may be missing, which under 'grant if any "
                    "contract grants' can falsely deny a paying customer. "
                    "%d contract(s) read; endCursor=%r",
                    customer_id, email, _CONTRACT_PAGE_CAP, len(contracts), cursor,
                )
                break

            if cursor is None or cursor in seen_cursors:
                # A missing cursor, or one already used, cannot advance the walk;
                # following it would re-read a page already counted.
                logger.error(
                    "Appstle advertises another page of contracts for customerId=%s "
                    "(email=%s) but the cursor does not advance (endCursor=%r, "
                    "already used: %s). Contracts may be missing; %d contract(s) "
                    "read from %d page(s)",
                    customer_id, email, cursor, seen_cursors, len(contracts), pages_read,
                )
                break

            seen_cursors.append(cursor)
            try:
                page = await self._appstle_get(
                    session, step2_url, params={_CONTRACT_PAGE_CURSOR_PARAM: cursor},
                )
            except Exception as exc:
                logger.error(
                    "Failed to fetch contract page %d for customerId=%s (email=%s) "
                    "with cursor=%r: %s. Contracts may be missing; returning the "
                    "%d contract(s) already read rather than discarding them",
                    pages_read + 1, customer_id, email, cursor, exc, len(contracts),
                )
                break

            page_contracts = _parse_contract_nodes(page, customer_id, email)
            contracts.extend(page_contracts)
            pages_read += 1

            logger.info(
                "Appstle contract page %d for customerId=%s (email=%s): "
                "%d contract(s)%s",
                pages_read, customer_id, email, len(page_contracts),
                _describe_contracts(page_contracts),
            )

            page_info = _read_page_info(page)

        return contracts

    # ------------------------------------------------------------------
    # verify_subscription
    # ------------------------------------------------------------------
    async def verify_subscription(self, email: str) -> AppstleSubscriptionResponse:
        """Collect EVERY contract Appstle holds for ``email`` (design change 11).

        Step 1: ``GET .../subscription-contract-details/customers?email={email}``
                → ``_extract_customer_ids()``, which returns ALL customer records
                the email maps to (requirement 2.10).  An empty list is the
                no-subscription case and returns the same response it always did
                (clauses 3.2, 3.7).

        Step 2: for EACH ``customerId``,
                ``GET .../subscription-customers/{customerId}`` through
                ``_appstle_get()``, parsed by ``_parse_contract_nodes()`` via
                ``_build_contract_response()``, then extended across pages by
                ``_fetch_contract_pages()`` (requirement 2.11).  Contracts
                accumulate across every record and every page.

        Step 3: merge the per-record responses into one
                ``AppstleSubscriptionResponse`` carrying the full contract list.

        **What changed, and why it matters.**  The previous version fetched
        ``customer_ids[0]`` and dropped the rest, which is root cause 2 of the
        lockout: an email mapping to two Appstle customer records had the second
        record's contracts silently discarded one level above the ``nodes[0]``
        truncation.  Under "grant if any contract grants" (2.1) that is a false
        denial of a paying customer, so the loop is the fix, and it is also why
        the multi-record ERROR log this replaces is gone — the condition it warned
        about no longer exists.

        **The customer-level fallback is aggregated by fixed priority**, not
        first-seen: ``ACTIVE > PAUSED > CANCELLED > other > None`` (see
        ``_aggregate_product_subscriber_status``).  First-seen would make the
        verdict depend on the order Appstle happened to list the customer
        records, which clause 2.9 forbids.  It only matters when
        ``subscriptionContracts.nodes[]`` is empty for every record — clause 2.12
        keeps ``productSubscriberStatus`` a fallback and never the primary signal.

        **Error handling is unchanged, deliberately** (clause 3.7).  Timeouts,
        non-200 responses, and malformed JSON still propagate out of here, and
        ``login()`` / ``refresh()`` still fall through to free tier rather than
        blocking a login.  A failure on a SECOND or later record additionally logs
        at ERROR, because contracts already read are being discarded, but the
        exception type and the fall-through are exactly as before.  (A failure on
        a later *page* is handled differently — ``_fetch_contract_pages()``
        swallows it and keeps what it has — because there the customer's
        customer-level status is already in hand.)

        Returns an ``AppstleSubscriptionResponse`` whose ``contracts`` field is
        what the access decision reads.

        Raises:
            aiohttp.ClientError on network issues
            asyncio.TimeoutError on timeout
            ValueError on malformed response
        """
        timeout = aiohttp.ClientTimeout(total=self.appstle_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Step 1: Look up EVERY customerId for this email
            step1_url = f"{self.appstle_api_url}/api/external/v2/subscription-contract-details/customers"
            step1_data = await self._appstle_get(session, step1_url, params={"email": email})

            customer_ids = _extract_customer_ids(step1_data)

            # Requirement 2.20: the record count and the ids themselves, in place
            # of the str(data)[:500] repr the step-1 log used to emit — which
            # truncated multi-record payloads and carried customer PII besides.
            logger.info(
                "Appstle step-1 lookup for email=%s: %d customer record(s) %s",
                email, len(customer_ids), customer_ids,
            )

            if not customer_ids:
                logger.info("No customerId found for email=%s — no subscription", email)
                return AppstleSubscriptionResponse(
                    is_valid=False, subscription_status=None, customer_email=email,
                )

            record_responses: list[AppstleSubscriptionResponse] = []
            contracts: list[ContractView] = []

            # Step 2: every customer record, every page (2.10, 2.11)
            for index, customer_id in enumerate(customer_ids):
                step2_url = (
                    f"{self.appstle_api_url}"
                    f"/api/external/v2/subscription-customers/{customer_id}"
                )

                try:
                    step2_data = await self._appstle_get(session, step2_url)
                except Exception as exc:
                    if index > 0:
                        # Falls through to free tier as it always has (3.7), but
                        # the customer had contracts we already read and are now
                        # throwing away, which is worth a record.
                        logger.error(
                            "Appstle step 2 failed for customer record %d of %d "
                            "(customerId=%s, email=%s): %s — discarding the %d "
                            "contract(s) already collected and falling through to "
                            "free tier",
                            index + 1, len(customer_ids), customer_id, email,
                            exc, len(contracts),
                        )
                    raise

                record = self._build_contract_response(step2_data, customer_id, email)
                record_responses.append(record)
                contracts.extend(
                    await self._fetch_contract_pages(
                        session, customer_id, email, step2_data, record.contracts,
                    )
                )

            # Step 3: one response carrying every contract found
            return self._merge_customer_records(record_responses, contracts, email)

    # ------------------------------------------------------------------
    # _merge_customer_records
    # ------------------------------------------------------------------
    def _merge_customer_records(
        self,
        responses: list,
        contracts: list,
        email: str,
    ) -> AppstleSubscriptionResponse:
        """Fold one response per Appstle customer record into a single response.

        A single record — the only shape seen in real data, since each of the
        three captured emails mapped to exactly one ``customerId`` — returns that
        record's own response verbatim, with ``contracts`` replaced by the
        accumulated list so later pages are not lost.  Nothing else about it is
        recomputed, which is what keeps every preserved single-record path
        (including the tag fallback, deleted in Task 9.7) byte-identical.

        Two or more records are merged:

        * ``contracts`` — every contract from every record, in the order they
          were read.  This is the field the access decision reads, and the
          decision is order-independent (2.9), so the order is for the log only.
        * ``product_subscriber_status`` / ``subscription_status`` — aggregated by
          the fixed priority in ``_aggregate_product_subscriber_status()``.
        * ``is_valid`` — true if ANY record was valid, matching "grant if any
          contract grants" (2.1) rather than requiring unanimity.
        * ``next_billing_date`` — the first contract's, for logging continuity
          only, exactly as the single-record assembler sets it.  Nothing reads it
          for a decision.
        * ``expiration_date`` — left ``None`` on every path (clause 3.13).
        """
        if len(responses) == 1:
            return responses[0].model_copy(update={"contracts": contracts})

        product_subscriber_status = _aggregate_product_subscriber_status(
            r.product_subscriber_status for r in responses
        )
        # The aggregator only ranks strings, so the MISSING_STATUS sentinel drops
        # out of it.  If EVERY record was missing the key, the merged response has
        # to say so too, or clause 2.19's ERROR record would be lost for a
        # multi-record customer whose payload shape changed.
        if product_subscriber_status is None and all(
            r.product_subscriber_status is MISSING_STATUS for r in responses
        ):
            product_subscriber_status = MISSING_STATUS

        subscription_status = _aggregate_product_subscriber_status(
            r.subscription_status for r in responses
        )

        logger.info(
            "Merged %d Appstle customer record(s) for email=%s: %d contract(s) "
            "total, aggregated productSubscriberStatus=%r%s",
            len(responses), email, len(contracts), product_subscriber_status,
            _describe_contracts(contracts),
        )

        return AppstleSubscriptionResponse(
            is_valid=any(r.is_valid for r in responses),
            subscription_status=subscription_status,
            customer_email=email,
            product_subscriber_status=product_subscriber_status,
            next_billing_date=contracts[0].next_billing_date if contracts else None,
            contracts=contracts,
        )

    # ------------------------------------------------------------------
    # create_token
    # ------------------------------------------------------------------
    def create_token(
        self,
        email: str,
        subscription_status: str,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """
        Create a JWT with the following claims:
          - sub: user email
          - subscription_status: e.g. "active"
          - subscription_expires_at: unix timestamp (or None)
          - iat: issued-at unix timestamp
          - exp: iat + 1 hour
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": email,
            "subscription_status": subscription_status,
            "subscription_expires_at": (
                int(expires_at.timestamp()) if expires_at else None
            ),
            "iat": int(now.timestamp()),
            "exp": int((now + self.token_expiry).timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)

    # ------------------------------------------------------------------
    # verify_token
    # ------------------------------------------------------------------
    def verify_token(
        self, token: str, allow_grace: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Decode and verify a JWT.

        If allow_grace=True, tokens that expired within the last 5 minutes
        are still accepted (used for the refresh flow).

        Returns the decoded claims dict, or None if verification fails.
        """
        try:
            claims = jwt.decode(
                token, self.jwt_secret, algorithms=[self.algorithm]
            )
            return claims
        except jwt.ExpiredSignatureError:
            if not allow_grace:
                return None
            # Decode without verifying expiration to check grace window
            try:
                claims = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False},
                )
                exp = claims.get("exp", 0)
                now = datetime.now(timezone.utc).timestamp()
                if now - exp <= self.grace_window.total_seconds():
                    return claims
                return None
            except jwt.InvalidTokenError:
                return None
        except jwt.InvalidTokenError:
            return None


    # ------------------------------------------------------------------
    # login
    # ------------------------------------------------------------------
    async def login(
        self, email: str, password: str, client_ip: str
    ) -> Dict[str, Any]:
        """
        Full login flow — subscription check always comes first:
        1. Check configuration
        2. Check rate limit for client_ip
        3. Call Appstle API to verify subscription (always, for all users)
        4. Decide access via decide_access() — grant with subscription_status
           "active" or "free", or deny with 403 (2.13)
        5. Lookup customer_passwords record by email
        6a. If record exists: verify password → if mismatch, return 401
        6b. If no record (new user): validate password rules → if fail, return 400
        7. If new user: create customer_passwords record
        8. Return success with token (subscription_status="active" or "free")

        Returns a dict with keys:
          - status_code: int (200, 400, 401, 429, 500, 503)
          - body: LoginSuccessResponse | LoginDeniedResponse (as dict)
        """
        import asyncio

        # 1. Configuration check
        if not self._config_valid:
            logger.warning("Login attempt with missing Appstle configuration")
            return {
                "status_code": 503,
                "body": LoginDeniedResponse(
                    error="Subscription service temporarily unavailable",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }

        # 2. Rate limit check
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for IP %s", client_ip)
            return {
                "status_code": 429,
                "body": LoginDeniedResponse(
                    error="Too many login attempts. Please try again later.",
                    subscription_status=None,
                    redirect_url=None,
                ).model_dump(),
            }

        # 2b. Bypass subscription check for configured emails (cofounders, partners)
        #
        # The inline list parse that used to live here is now _is_bypass_email(),
        # shared with refresh() (design change 13).  refresh() had no bypass check
        # at all, so a bypass user granted access here was bounced an hour later
        # (clause 1.10); one helper is what keeps the two from drifting again.
        is_bypass_user = _is_bypass_email(email)
        if is_bypass_user:
            logger.info("Bypass user detected: %s — skipping subscription check", email)

        # 3. Call Appstle API to verify subscription FIRST (for all users)
        # If Appstle is unavailable, fall through to free-tier instead of blocking login
        appstle_resp = None
        if not is_bypass_user:
            try:
                appstle_resp = await self.verify_subscription(email)
            except asyncio.TimeoutError:
                logger.error("Appstle API timeout for email=%s — falling back to free-tier", email)
            except aiohttp.ClientResponseError as exc:
                logger.error("Appstle API error: status=%s for email=%s — falling back to free-tier", exc.status, email)
            except ValueError as exc:
                logger.error("Malformed Appstle response for email=%s: %s — falling back to free-tier", email, exc)
            except Exception as exc:
                logger.error("Unexpected error calling Appstle API for email=%s: %s — falling back to free-tier", email, exc)

        # 4. Decide access — ONE call into the single decision path (2.13)
        #
        # The five-scenario ladder that used to live here is gone (design change
        # 12).  It branched on the CUSTOMER-level product_subscriber_status plus
        # the single scalar next_billing_date the old parser lifted from
        # nodes[0], which is the lockout bug: every other contract was invisible
        # to it.  Its replacement is one call into decide_access() — the single
        # decision path (2.13), shared with refresh() — followed by a single
        # branch on decision.granted.
        #
        # Neither of the two branches ahead of that call changes:
        #   - a BYPASS_EMAILS user gets "active" without an Appstle lookup (3.10)
        #   - appstle_resp is None means the Appstle call above failed, and login
        #     still falls through to free tier rather than blocking (3.7)
        if is_bypass_user:
            subscription_status = "active"
            logger.info("Bypass user granted active status: email=%s", email)
        elif appstle_resp is None:
            subscription_status = "free"
            logger.info("Free-tier login (Appstle unavailable) for email=%s", email)
        else:
            # EVERY contract, from every customer record and every page, is
            # weighed (2.1-2.5).  Denials take their copy and their reported
            # status from the most recent contract via DENIAL_MESSAGES /
            # _get_denial_message() (2.16, 2.17) — no inline denial strings
            # remain here.  product_subscriber_status is passed through as the
            # empty-contracts fallback only (2.12).
            decision = decide_access(
                appstle_resp.contracts,
                appstle_resp.product_subscriber_status,
                email,
            )

            if not decision.granted:
                return {
                    "status_code": 403,
                    "body": LoginDeniedResponse(
                        error=decision.denial_message,
                        subscription_status=decision.subscription_status,
                        redirect_url=self.signup_url,
                    ).model_dump(),
                }

            # "active" for a granting contract or a customer-level ACTIVE
            # fallback, "free" when there is nothing to grant on but nothing to
            # deny on either (3.2).
            subscription_status = decision.subscription_status

        # 5. Check password (regardless of subscription status)
        existing_record = None
        is_new_user = True
        if self.password_service:
            try:
                existing_record = await self.password_service.get_customer(email)
                is_new_user = existing_record is None
            except Exception as exc:
                logger.error("Error looking up password record for email=%s: %s", email, exc)
                # Continue without password check if DB is unavailable

        # 6a. Existing user: verify password against stored hash
        if existing_record:
            try:
                password_valid = self.password_service.verify_password(
                    password, existing_record["password_hash"]
                )
            except Exception as exc:
                logger.error("Error verifying password for email=%s: %s", email, exc)
                return {
                    "status_code": 500,
                    "body": LoginDeniedResponse(
                        error="An unexpected error occurred",
                        subscription_status=None,
                        redirect_url=None,
                    ).model_dump(),
                }

            if not password_valid:
                logger.info("Password mismatch for email=%s", email)
                return {
                    "status_code": 401,
                    "body": LoginDeniedResponse(
                        error="Invalid email or password",
                        subscription_status=None,
                        redirect_url=None,
                    ).model_dump(),
                }

        # 6b. New user: validate password rules
        if is_new_user and self.password_service:
            failed_rules = self.password_service.validate_password(password)
            if failed_rules:
                logger.info("Password validation failed for new user email=%s: %s", email, failed_rules)
                return {
                    "status_code": 400,
                    "body": {
                        "success": False,
                        "error": "Password validation failed",
                        "failed_rules": failed_rules,
                    },
                }

        # 7. New user: create password record
        if is_new_user and self.password_service:
            try:
                await self.password_service.create_customer(email, password)
                logger.info("Created password record for new user email=%s", email)
            except Exception as exc:
                logger.error("Failed to create password record for email=%s: %s", email, exc)
                # Don't block login if record creation fails

        # 8. Success — reset rate limiter and issue token
        self.rate_limiter.reset(client_ip)

        token = self.create_token(
            email=email,
            subscription_status=subscription_status,
            expires_at=appstle_resp.expiration_date if appstle_resp else None,
        )

        expires_at_iso = (
            appstle_resp.expiration_date.isoformat()
            if appstle_resp and appstle_resp.expiration_date
            else None
        )

        logger.info("Successful login for email=%s subscription_status=%s", email, subscription_status)
        return {
            "status_code": 200,
            "body": LoginSuccessResponse(
                token=token,
                email=email,
                subscription_status=subscription_status,
                expires_at=expires_at_iso,
            ).model_dump(),
        }


    # ------------------------------------------------------------------
    # refresh
    # ------------------------------------------------------------------
    async def refresh(self, token: str) -> Dict[str, Any]:
        """
        Refresh flow:
        1. Verify existing token with grace window (allow 5 min expired)
        2. Check configuration
        2b. Skip the subscription check for BYPASS_EMAILS users (2.14)
        3. Re-verify subscription with Appstle API
        4. Decide access via decide_access() — the same single decision path
           login() uses (2.13) — or preserve the JWT's status when Appstle is
           unavailable (3.8)
        5. Issue new token with the current subscription_status ("active" or "free")

        Returns a dict with keys:
          - status_code: int (200, 401, 403, 503)
          - body: RefreshResponse (as dict)
        """
        import asyncio

        # 1. Verify token (with grace window)
        claims = self.verify_token(token, allow_grace=True)
        if claims is None:
            return {
                "status_code": 401,
                "body": RefreshResponse(
                    success=False,
                    error="Token expired beyond grace window",
                ).model_dump(),
            }

        email = claims.get("sub", "")

        # 2. Configuration check
        if not self._config_valid:
            return {
                "status_code": 503,
                "body": RefreshResponse(
                    success=False,
                    error="Subscription service temporarily unavailable",
                ).model_dump(),
            }

        # 2b. Bypass subscription check for configured emails (2.14, clause 1.10)
        #
        # This check is NEW here and is the whole of clause 1.10: login() had it,
        # refresh() did not, so a cofounder or partner on the allowlist logged in
        # successfully and was denied an hour later when the token refreshed.  It
        # sits ahead of the Appstle call for the same reason it does in login() —
        # a bypass user's subscription is not consulted at all — and mirrors that
        # method's ordering, after the configuration check.
        if _is_bypass_email(email):
            logger.info(
                "Bypass user detected: %s — skipping subscription check on refresh",
                email,
            )
            new_token = self.create_token(
                email=email,
                subscription_status="active",
                expires_at=None,
            )
            logger.info("Token refreshed for email=%s subscription_status=active (bypass)", email)
            return {
                "status_code": 200,
                "body": RefreshResponse(
                    success=True,
                    token=new_token,
                ).model_dump(),
            }

        # 3. Re-verify subscription
        # If Appstle is unavailable, preserve the current subscription status from the token
        appstle_resp = None
        try:
            appstle_resp = await self.verify_subscription(email)
        except asyncio.TimeoutError:
            logger.error("Appstle API timeout during refresh for email=%s — preserving current status", email)
        except Exception as exc:
            logger.error("Appstle API error during refresh for email=%s: %s — preserving current status", email, exc)

        # 4. Decide access — the SAME single call login() makes (2.13)
        #
        # The five-scenario ladder that used to live here was the second of three
        # copies of step 4 (clause 1.9), and it read the customer-level
        # product_subscriber_status plus the single scalar next_billing_date the
        # old parser lifted from nodes[0] — so it denied Dave for exactly the same
        # reason login() did.  Both callers now share decide_access(), which is
        # what makes Property 10 (login and refresh agree) hold by construction
        # rather than by vigilance.
        #
        # The Appstle-unavailable branch below is unchanged (3.8): the status
        # carried in the existing JWT claims is preserved rather than re-derived,
        # which is the one place login() and refresh() are *meant* to differ —
        # login() has no prior claims to preserve and falls through to free tier.
        # The 5-minute grace window (3.11) is decided by verify_token() in step 1
        # and is untouched here.
        if appstle_resp is None:
            subscription_status = claims.get("subscription_status", "free")
            logger.info("Refresh with preserved status=%s (Appstle unavailable) for email=%s", subscription_status, email)
            new_token = self.create_token(
                email=email,
                subscription_status=subscription_status,
                expires_at=None,
            )
            logger.info("Token refreshed for email=%s subscription_status=%s", email, subscription_status)
            return {
                "status_code": 200,
                "body": RefreshResponse(
                    success=True,
                    token=new_token,
                ).model_dump(),
            }

        # EVERY contract, from every customer record and every page, is weighed
        # (2.1-2.5).  Denials take their copy from the most recent contract via
        # DENIAL_MESSAGES / _get_denial_message() (2.16, 2.17), so no inline denial
        # strings remain here either — which is what keeps refresh()'s copy
        # byte-identical to login()'s instead of merely similar.
        # product_subscriber_status is passed through as the empty-contracts
        # fallback only (2.12).
        decision = decide_access(
            appstle_resp.contracts,
            appstle_resp.product_subscriber_status,
            email,
        )

        if not decision.granted:
            # RefreshResponse carries no subscription_status field, so the denial
            # body is (success, error, redirect_url) — the same shape it has always
            # had.  decision.subscription_status is reported in the log instead.
            logger.info(
                "Refresh denied for email=%s: subscription_status=%s",
                email, decision.subscription_status,
            )
            return {
                "status_code": 403,
                "body": RefreshResponse(
                    success=False,
                    error=decision.denial_message,
                    redirect_url=self.signup_url,
                ).model_dump(),
            }

        # "active" for a granting contract or a customer-level ACTIVE fallback,
        # "free" when there is nothing to grant on but nothing to deny on either.
        subscription_status = decision.subscription_status

        new_token = self.create_token(
            email=email,
            subscription_status=subscription_status,
            expires_at=appstle_resp.expiration_date if appstle_resp else None,
        )
        logger.info("Token refreshed for email=%s subscription_status=%s", email, subscription_status)
        return {
            "status_code": 200,
            "body": RefreshResponse(
                success=True,
                token=new_token,
            ).model_dump(),
        }
