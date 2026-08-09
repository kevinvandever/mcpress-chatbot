"""Pinned reference instant for the Appstle fixtures.

The real-data fixtures in this directory keep the dates Appstle actually
returned, verbatim. Those dates are absolute, so any date-dependent assertion
made against them is only meaningful relative to the instant the payloads were
captured. ``FIXTURE_NOW`` is that instant.

Without a pinned clock, Dave's granting contract (``nextBillingDate``
2026-08-27) stops being in the future once wall-clock time passes that date, and
every date-dependent test silently inverts its verdict — Property 3 would begin
asserting the opposite of what it means to assert. So tests monkeypatch
``backend.subscription_auth._utcnow`` to return ``FIXTURE_NOW`` rather than
letting the decision layer read the real clock.

See ``README.md`` in this directory, and item 2b under
"Changes Required / backend/subscription_auth.py" in the spec's ``design.md``.
"""

from datetime import datetime, timedelta, timezone

# The instant inspect_appstle_contracts.py --save captured the three raw
# payloads. Every date-dependent assertion over these fixtures is relative
# to this, never to the real clock.
FIXTURE_NOW = datetime(2026, 8, 9, 1, 31, 12, tzinfo=timezone.utc)

# ISO-8601 form, matching how Appstle renders dates in the payloads
# (UTC with a trailing "Z").
FIXTURE_NOW_ISO = "2026-08-09T01:31:12Z"


def fixture_now() -> datetime:
    """Drop-in replacement for ``backend.subscription_auth._utcnow``."""
    return FIXTURE_NOW


def at_offset(**kwargs) -> datetime:
    """A ``datetime`` expressed as an offset from ``FIXTURE_NOW``.

    ``at_offset(days=-5)`` is five days before the capture instant.
    """
    return FIXTURE_NOW + timedelta(**kwargs)


# Offsets from FIXTURE_NOW baked into the synthetic fixtures at build time.
# Recorded here so the harness can reason about the fixtures' intent without
# re-parsing their dates. Keys are fixture filenames without the .json suffix.
SYNTHETIC_OFFSETS = {
    "contracts_page1": {
        "9000000181": {"createdAt": {"days": -70}, "nextBillingDate": {"days": -40}},
    },
    "contracts_page2": {
        "9000000182": {"createdAt": {"days": -16}, "nextBillingDate": {"days": 14}},
    },
    "cancelled_with_paid_time": {
        "9000000211": {"createdAt": {"days": -9}, "nextBillingDate": {"days": 21}},
    },
    "active_past_billing_dunning": {
        "9000000111": {"createdAt": {"days": -35}, "nextBillingDate": {"days": -5}},
    },
    "paused_null_nextbilling_derivable": {
        "9000000121": {"createdAt": {"days": -8}, "nextBillingDate": None},
    },
    "paused_unrecognized_interval": {
        "9000000131": {"createdAt": {"days": -8}, "nextBillingDate": None},
    },
    "paused_absent_billing_policy": {
        "9000000141": {"createdAt": {"days": -8}, "nextBillingDate": None},
    },
    "denial_newest_cancelled_older_paused": {
        "9000000151": {"createdAt": {"days": -120}, "nextBillingDate": {"days": -90}},
        "9000000152": {"createdAt": {"days": -40}, "nextBillingDate": {"days": -10}},
    },
}
