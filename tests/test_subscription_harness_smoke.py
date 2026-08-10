"""Self-check for the offline subscription test harness (Task 4).

The harness has no behavior of its own to assert, so these are smoke tests for
the harness itself: that it builds a real ``SubscriptionAuthService`` offline,
that the URL-keyed router serves step-1 and step-2 fixtures and records what was
requested, that the clock is pinned to ``FIXTURE_NOW``, that the password stub
and rate limiter steer the non-subscription response paths, that
``normalize_body`` reduces the token, and that the Hypothesis strategies produce
well-formed payload plans.

Deliberately NOT asserted here: the access decision. These tests must pass both
before and after the fix, so nothing below encodes an expectation about whether
a given contract set grants — that is Tasks 5, 6, and 7's job.

Run offline: ``python3 -m pytest tests/test_subscription_harness_smoke.py``
"""

from datetime import timedelta

import pytest
from hypothesis import HealthCheck, given, settings

from backend import subscription_auth
from tests.subscription_harness import (
    DEFAULT_CLIENT_IP,
    FIXTURE_NOW,
    KNOWN_PASSWORD,
    STEP1_PATH,
    WEAK_PASSWORD,
    WRONG_PASSWORD,
    PayloadRouter,
    RouterMiss,
    appstle_timeout,
    build_contract_node,
    harness,
    load_fixture,
    normalize_body,
    paginate,
    payload_plans,
    step1_payload,
)

DAVE_EMAIL = "multi.contract@example.com"
DAVE_CUSTOMER_ID = 2788838535


# ---------------------------------------------------------------------------
# The core proof: a step-1 + step-2 fixture pair routed through login()
# ---------------------------------------------------------------------------

def test_login_routes_step1_and_step2_fixtures_through_the_router():
    """Dave's captured payloads reach ``login()`` and the router records both URLs."""
    with harness(
        step1=load_fixture("step1_single_customer"),
        step2={DAVE_CUSTOMER_ID: load_fixture("dave_two_paused_contracts")},
        known_passwords={DAVE_EMAIL: KNOWN_PASSWORD},
    ) as h:
        result = h.login(DAVE_EMAIL, KNOWN_PASSWORD)

        # Both Appstle steps were actually issued, in order.
        assert len(h.router.requests) == 2
        step1, step2 = h.router.requests
        assert step1.is_step1
        assert step1.url.endswith(STEP1_PATH)
        assert step1.email == DAVE_EMAIL
        assert step2.customer_id == DAVE_CUSTOMER_ID
        assert h.router.fetched_customer(DAVE_CUSTOMER_ID)

        # A real decision came back on the documented response shape. Which
        # decision is Task 5/6's assertion, not this test's.
        assert result["status_code"] in (200, 403)
        assert isinstance(result["body"], dict)
        assert "success" in result["body"]


def test_router_records_urls_even_when_no_second_customer_is_fetched():
    """Property 7's negative half is observable: an unfetched ``customerId``.

    The two-record fixture is served, but whether the second record is requested
    is up to the code under test. The router is what makes the difference
    visible, which is the whole point of recording URLs.
    """
    step1 = load_fixture("step1_two_customers")
    c1, c2 = [record["customerId"] for record in step1]

    with harness(
        step1=step1,
        step2={
            c1: load_fixture("lapsed_paused_subscriber"),
            c2: load_fixture("cancelled_with_paid_time"),
        },
        known_passwords={"two.records@example.com": KNOWN_PASSWORD},
    ) as h:
        h.login("two.records@example.com", KNOWN_PASSWORD)

        assert h.router.fetched_customer(c1), "the first record must always be fetched"
        # No assertion on c2: unfixed code skips it, fixed code fetches it.
        # What matters is that the harness can tell the two apart.
        assert isinstance(h.router.fetched_customer(c2), bool)
        assert h.router.requested_customer_ids[0] == c1


# ---------------------------------------------------------------------------
# Router behavior in isolation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", [
    "dave_two_paused_contracts",
    "renewed_subscriber",
    "lapsed_paused_subscriber",
    "empty_nodes",
    "cancelled_with_paid_time",
    "active_past_billing_dunning",
    "paused_null_nextbilling_derivable",
    "paused_unrecognized_interval",
    "paused_absent_billing_policy",
    "denial_newest_cancelled_older_paused",
    "missing_product_subscriber_status",
    "contracts_page1",
    "contracts_page2",
    "step1_single_customer",
    "step1_two_customers",
    "no_subscription",
])
def test_every_committed_fixture_loads(fixture_name):
    """Every Task 2 fixture is loadable and mutation-isolated between loads."""
    first = load_fixture(fixture_name)
    assert first is not None
    if isinstance(first, dict):
        first["__harness_scribble__"] = True
    else:
        first.append({"__harness_scribble__": True})
    assert "__harness_scribble__" not in load_fixture(fixture_name)


def test_router_serves_pages_by_cursor_and_counts_them():
    """Per-page step-2 routing works, and page follows are recorded.

    Production does not follow pages yet (design Finding 4 — the cursor
    parameter name is unknown), so this exercises the router directly. Without
    it, Task 5's pagination case could not tell "page 2 was never requested"
    from "the harness cannot serve page 2".
    """
    customer_id = 7000000018
    page1, page2 = paginate(
        customer_id=customer_id,
        pages=[
            [build_contract_node(
                contract_id=9000000181, status="PAUSED",
                created_at="2026-05-31T01:31:12Z", next_billing_date="2026-06-30T01:31:12Z",
                interval="DAY", interval_count=30,
            )],
            [build_contract_node(
                contract_id=9000000182, status="PAUSED",
                created_at="2026-07-24T01:31:12Z", next_billing_date="2026-08-23T01:31:12Z",
                interval="DAY", interval_count=30,
            )],
        ],
    )
    assert page1["subscriptionContracts"]["pageInfo"]["hasNextPage"] is True
    assert page2["subscriptionContracts"]["pageInfo"]["hasNextPage"] is False

    router = PayloadRouter(step1=step1_payload([customer_id]), step2={customer_id: [page1, page2]})
    url = f"https://appstle.test/api/external/v2/subscription-customers/{customer_id}"

    served_page1 = _await(router(None, url))
    assert served_page1["subscriptionContracts"]["nodes"][0]["id"].endswith("9000000181")

    cursor = served_page1["subscriptionContracts"]["pageInfo"]["endCursor"]
    served_page2 = _await(router(None, url, {"cursor": cursor}))
    assert served_page2["subscriptionContracts"]["nodes"][0]["id"].endswith("9000000182")

    assert router.page_count(customer_id) == 2
    assert router.followed_next_page(customer_id) is True
    assert router.cursors_requested(customer_id) == [None, cursor]


def test_router_raises_on_an_unconfigured_customer():
    """A miss is loud, so a test cannot pass while the code fetched something
    the test never meant to serve."""
    router = PayloadRouter(step1=step1_payload([1]), step2={})
    with pytest.raises(RouterMiss):
        _await(router(None, "https://appstle.test/api/external/v2/subscription-customers/999"))


def test_router_can_inject_an_appstle_failure():
    """Routed exceptions reach the caller, which is how clause 3.7 is reachable."""
    with harness(
        step1=appstle_timeout(),
        known_passwords={"timeout@example.com": KNOWN_PASSWORD},
    ) as h:
        result = h.login("timeout@example.com", KNOWN_PASSWORD)

        # login() swallows Appstle failures and falls through rather than
        # blocking, so the observable proof is that the call was attempted.
        assert len(h.router.step1_requests) == 1
        assert result["status_code"] == 200


# ---------------------------------------------------------------------------
# Clock seam
# ---------------------------------------------------------------------------

def test_clock_seam_is_pinned_inside_the_harness_and_restored_after():
    """``_utcnow`` reads ``FIXTURE_NOW`` inside the harness, real time outside."""
    original = subscription_auth._utcnow
    with harness(step1=load_fixture("no_subscription")):
        assert subscription_auth._utcnow() == FIXTURE_NOW
    assert subscription_auth._utcnow is original
    assert subscription_auth._utcnow() != FIXTURE_NOW


# ---------------------------------------------------------------------------
# Non-subscription paths the harness has to be able to steer
# ---------------------------------------------------------------------------

def test_password_stub_drives_the_401_and_400_paths():
    """Wrong password → 401; new user with a weak password → 400 + failed_rules."""
    with harness(
        step1=load_fixture("no_subscription"),
        known_passwords={"existing@example.com": KNOWN_PASSWORD},
    ) as h:
        denied = h.login("existing@example.com", WRONG_PASSWORD)
        assert denied["status_code"] == 401
        assert denied["body"]["error"] == "Invalid email or password"

        h.reset()
        weak = h.login("brand.new@example.com", WEAK_PASSWORD)
        assert weak["status_code"] == 400
        assert weak["body"]["failed_rules"], "real complexity rules must be in force"

        h.reset()
        created = h.login("brand.new@example.com", KNOWN_PASSWORD)
        assert created["status_code"] == 200
        assert "brand.new@example.com" in h.passwords.created_emails


def test_rate_limiter_is_reachable_and_resettable():
    """5 attempts allowed, the 6th is 429, and ``reset()`` clears the count."""
    with harness(
        step1=load_fixture("no_subscription"),
        known_passwords={"limited@example.com": KNOWN_PASSWORD},
    ) as h:
        for _ in range(5):
            assert h.login("limited@example.com", WRONG_PASSWORD)["status_code"] == 401
        limited = h.login("limited@example.com", WRONG_PASSWORD)
        assert limited["status_code"] == 429
        assert limited["body"]["error"] == "Too many login attempts. Please try again later."

        h.reset_rate_limiter()
        assert h.login("limited@example.com", WRONG_PASSWORD)["status_code"] == 401


def test_missing_config_yields_503():
    """``missing_config=True`` reaches the config-check branch (clause 3.6)."""
    with harness(missing_config=True) as h:
        result = h.login("anyone@example.com", KNOWN_PASSWORD)
        assert result["status_code"] == 503
        assert result["body"]["error"] == "Subscription service temporarily unavailable"
        assert h.router.requests == [], "no Appstle call should be attempted"


def test_bypass_emails_skips_the_appstle_call():
    """``bypass_emails`` is wired through the environment (clause 3.10)."""
    with harness(
        step1=load_fixture("no_subscription"),
        bypass_emails="bypass@example.com",
        known_passwords={"bypass@example.com": KNOWN_PASSWORD},
    ) as h:
        result = h.login("bypass@example.com", KNOWN_PASSWORD)
        assert result["status_code"] == 200
        assert result["body"]["subscription_status"] == "active"
        assert h.router.requests == []


# ---------------------------------------------------------------------------
# Token helpers and normalize_body
# ---------------------------------------------------------------------------

def test_normalize_body_reduces_the_token_to_its_claim_keys():
    """Bodies compare across calls once the token collapses to its claim keys.

    Tokens issued in different seconds carry different ``iat``/``exp`` and so
    different signatures. That difference is not a behavior change, which is
    exactly why the golden comparison needs it normalized away.
    """
    with harness(
        step1=load_fixture("no_subscription"),
        known_passwords={"claims@example.com": KNOWN_PASSWORD},
    ) as h:
        first = h.login("claims@example.com", KNOWN_PASSWORD)
        h.reset()
        second = h.login("claims@example.com", KNOWN_PASSWORD)

        assert h.normalized_result(first) == h.normalized_result(second)
        assert normalize_body(first["body"])["token"] == {
            "claim_keys": ["exp", "iat", "sub", "subscription_expires_at", "subscription_status"]
        }

        # Two genuinely different token strings still normalize to one value.
        early = h.token_for("claims@example.com")
        later = h.token_for("claims@example.com", age=timedelta(seconds=90))
        assert early != later
        assert normalize_body({"token": early}) == normalize_body({"token": later})


def test_normalize_body_passes_through_bodies_without_a_token():
    denied = {"success": False, "error": "nope", "redirect_url": "https://x.test"}
    assert normalize_body(denied) == denied


def test_token_for_can_backdate_into_and_past_the_grace_window():
    """Refresh's 5-minute grace window (clause 3.11) is reachable from the harness."""
    with harness(step1=load_fixture("no_subscription")) as h:
        fresh_claims = h.claims(h.token_for("grace@example.com"))
        assert fresh_claims["exp"] - fresh_claims["iat"] == 3600

        inside = h.refresh(h.token_for("grace@example.com", age=timedelta(minutes=62)))
        assert inside["status_code"] != 401

        h.reset()
        outside = h.refresh(h.token_for("grace@example.com", age=timedelta(minutes=70)))
        assert outside["status_code"] == 401
        assert outside["body"]["error"] == "Token expired beyond grace window"


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@settings(max_examples=50, deadline=None)
@given(payload_plans())
def test_payload_plans_are_well_formed(plan):
    """Generated plans distribute every contract across 1-3 records and 1-3 pages."""
    assert 1 <= len(plan.customer_ids) <= 3
    assert len(set(plan.customer_ids)) == len(plan.customer_ids)
    assert all(1 <= count <= 3 for count in plan.page_counts.values())

    contract_ids = [node["id"] for node in plan.all_contracts]
    assert len(contract_ids) == len(set(contract_ids)), "contract ids must be unique"
    assert len(contract_ids) >= 1

    step1 = plan.step1
    assert [record["customerId"] for record in step1] == plan.customer_ids

    step2 = plan.step2
    assert set(step2) == set(plan.customer_ids)
    for cid, pages in step2.items():
        for index, page in enumerate(pages):
            page_info = page["subscriptionContracts"]["pageInfo"]
            assert page_info["hasNextPage"] is (index < len(pages) - 1)
        served = [
            node
            for page in pages
            for node in page["subscriptionContracts"]["nodes"]
        ]
        assert len(served) == sum(len(p) for p in plan.pages_by_customer[cid])

    # visible_contracts is what the unfixed code can reach; it is always a
    # prefix-slice of all_contracts, never more.
    assert len(plan.visible_contracts) <= len(plan.all_contracts)
    if plan.first_contract is not None:
        assert plan.first_contract is plan.visible_contracts[0]


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(payload_plans())
def test_generated_plans_drive_login_end_to_end(plan):
    """Any generated plan produces a documented response through ``login()``.

    No assertion on which decision: the point is that every shape the strategies
    can produce is servable by the router and survives the whole flow, so a
    property test failing later is failing on the decision rule and not on the
    harness.
    """
    with harness(**plan.router_kwargs(), known_passwords={plan.email: KNOWN_PASSWORD}) as h:
        result = h.login(plan.email, KNOWN_PASSWORD, DEFAULT_CLIENT_IP)

        assert result["status_code"] in (200, 403)
        assert h.router.step1_requests, "step 1 must always be issued"
        assert h.router.fetched_customer(plan.customer_ids[0])
        body = result["body"]
        if result["status_code"] == 200:
            assert body["subscription_status"] in ("active", "free")
        else:
            assert body["redirect_url"] == h.signup_url


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _await(coro):
    import asyncio

    return asyncio.run(coro)
