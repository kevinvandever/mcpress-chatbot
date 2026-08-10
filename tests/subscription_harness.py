"""Offline test harness for the subscription multi-contract access bugfix.

Everything the three property suites need in order to drive
``SubscriptionAuthService.login()`` / ``.refresh()`` in-process with **no
network, no database, no Railway, and no Appstle credentials**:

* :func:`harness` — a context manager that builds a real
  ``SubscriptionAuthService`` against sane fake ``APPSTLE_*`` /
  ``JWT_SECRET_KEY`` / ``SUBSCRIPTION_SIGNUP_URL`` env values, pins the clock to
  ``FIXTURE_NOW``, swaps in a deterministic password stub, and patches the
  ``_appstle_get`` seam with a URL-keyed :class:`PayloadRouter`.
* :class:`PayloadRouter` — routes step-1 lookups, per-``customerId`` step-2
  requests, and per-page step-2 requests to fixture payloads, and **records
  every requested URL** so a test can assert that a second ``customerId`` or a
  second page was actually fetched (or, on unfixed code, was not).
* :func:`normalize_body` — reduces ``token`` to its decoded claim key set so
  response bodies compare across calls.
* Hypothesis composite strategies for contract dicts and for distributing
  contracts across 1-3 customer records and 1-3 pages.

Design references: ``.kiro/specs/subscription-multi-contract-access/design.md``
"Testing Strategy" and change 2b (the ``_utcnow()`` clock seam); fixture
provenance in ``tests/fixtures/appstle/README.md``.

Assertions belong on ``login()``'s / ``refresh()``'s returned ``status_code``
and ``body`` — never on parser internals. The harness deliberately exposes no
parser shortcuts.
"""

from __future__ import annotations

import asyncio
import copy
import functools
import json
import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import aiohttp
import jwt
from hypothesis import strategies as st

# Make the repository root importable so ``backend.*`` resolves when pytest is
# invoked from anywhere inside the project.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend import subscription_auth  # noqa: E402
from backend.subscription_auth import SubscriptionAuthService  # noqa: E402

from tests.fixtures.appstle import fixture_clock  # noqa: E402
from tests.fixtures.appstle.fixture_clock import (  # noqa: E402
    FIXTURE_NOW,
    at_offset,
    fixture_now,
)

__all__ = [
    # env / URL constants
    "APPSTLE_API_URL",
    "APPSTLE_API_KEY",
    "JWT_SECRET_KEY",
    "SUBSCRIPTION_SIGNUP_URL",
    "STEP1_PATH",
    "STEP2_PATH_TEMPLATE",
    "PAGINATION_PARAM",
    "KNOWN_PASSWORD",
    "WRONG_PASSWORD",
    "WEAK_PASSWORD",
    # fixtures
    "FIXTURE_DIR",
    "load_fixture",
    "FIXTURE_NOW",
    "fixture_now",
    "at_offset",
    "fixture_clock",
    "DEFAULT_EMAIL",
    "DEFAULT_CLIENT_IP",
    # router
    "RecordedRequest",
    "RouterMiss",
    "PayloadRouter",
    "step1_payload",
    "build_contract_node",
    "build_step2_payload",
    "paginate",
    "appstle_timeout",
    "appstle_http_error",
    "appstle_malformed_json",
    # password stub
    "StubPasswordService",
    # harness
    "Harness",
    "harness",
    "normalize_body",
    "decode_token_claims",
    # strategies
    "CONTRACT_STATUSES",
    "INTERVAL_UNITS",
    "PayloadPlan",
    "contract_statuses",
    "interval_units",
    "interval_counts",
    "next_billing_choices",
    "created_at_choices",
    "contract_dicts",
    "contract_sets",
    "payload_plans",
]


# ---------------------------------------------------------------------------
# Environment / URL constants
# ---------------------------------------------------------------------------

APPSTLE_API_URL = "https://appstle.test"
APPSTLE_API_KEY = "test-appstle-api-key"
JWT_SECRET_KEY = "harness-jwt-secret-do-not-use-in-production"
SUBSCRIPTION_SIGNUP_URL = "https://mcpress.test/subscribe"

STEP1_PATH = "/api/external/v2/subscription-contract-details/customers"
STEP2_PATH_TEMPLATE = "/api/external/v2/subscription-customers/{customer_id}"

# Synthetic placeholder cursor parameter. Design Finding 4: Appstle documents no
# pagination parameter for the step-2 endpoint and ``hasNextPage`` was false for
# every captured customer, so the real name is unknown. The router uses this
# name only so the *harness* can serve a second page; production code does not
# request one (Task 9.3 is detection-plus-ERROR-log only).
PAGINATION_PARAM = "cursor"

# Passwords used by the stub password service. ``KNOWN_PASSWORD`` and
# ``WRONG_PASSWORD`` both satisfy the real complexity rules, so a 401 in a test
# is unambiguously a password *mismatch* and never a rule failure.
KNOWN_PASSWORD = "Harness#Pass1"
WRONG_PASSWORD = "Harness#Nope2"
WEAK_PASSWORD = "short"

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "appstle"


@functools.lru_cache(maxsize=None)
def _load_fixture_cached(name: str) -> Any:
    path = FIXTURE_DIR / (name if name.endswith(".json") else f"{name}.json")
    if not path.exists():
        available = sorted(p.stem for p in FIXTURE_DIR.glob("*.json"))
        raise FileNotFoundError(
            f"No Appstle fixture named {name!r} in {FIXTURE_DIR}. Available: {available}"
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_fixture(name: str) -> Any:
    """Load a sanitized fixture from ``tests/fixtures/appstle`` by stem name.

    Returns a deep copy, so a test may mutate the payload it gets back (for
    example overwriting ``productSubscriberStatus`` to reach the PAUSED and
    CANCELLED fallback branches) without leaking into other cases.
    """
    return copy.deepcopy(_load_fixture_cached(name))


# ---------------------------------------------------------------------------
# Payload construction helpers
# ---------------------------------------------------------------------------

def step1_payload(customer_ids: Sequence[int], email: str = "harness@example.com") -> List[dict]:
    """Build a step-1 customer-lookup payload (bare list of customer records)."""
    return [{"customerId": int(cid), "email": email} for cid in customer_ids]


def build_contract_node(
    *,
    contract_id: Union[int, str],
    status: Optional[str],
    created_at: Optional[str],
    next_billing_date: Optional[str],
    interval: Optional[str] = "MONTH",
    interval_count: int = 1,
    customer_id: Optional[int] = None,
    selling_plan_name: str = "Harness Plan",
) -> dict:
    """Build one ``subscriptionContracts.nodes[]`` entry shaped like the fixtures.

    ``interval=None`` omits ``billingPolicy`` entirely (the "absent policy" case
    from clause 2.8), which is distinct from an unrecognized interval unit.
    """
    node: Dict[str, Any] = {
        "__typename": "SubscriptionContract",
        "id": f"gid://shopify/SubscriptionContract/{contract_id}",
        "createdAt": created_at,
        "nextBillingDate": next_billing_date,
        "status": status,
        "lastPaymentStatus": None,
        "lines": {
            "__typename": "SubscriptionLineConnection",
            "nodes": [
                {
                    "__typename": "SubscriptionLine",
                    "id": f"gid://shopify/SubscriptionLine/{contract_id}",
                    "sellingPlanName": selling_plan_name,
                    "sku": "ChatMaster",
                    "title": "MC ChatMaster",
                    "quantity": 1,
                }
            ],
            "pageInfo": {
                "__typename": "PageInfo",
                "hasPreviousPage": False,
                "hasNextPage": False,
                "startCursor": f"HARNESS_CURSOR_LINE_{contract_id}",
                "endCursor": f"HARNESS_CURSOR_LINE_{contract_id}",
            },
        },
    }
    if interval is not None:
        node["billingPolicy"] = {
            "__typename": "SubscriptionBillingPolicy",
            "interval": interval,
            "intervalCount": interval_count,
        }
    if customer_id is not None:
        node["customer"] = {
            "__typename": "Customer",
            "id": f"gid://shopify/Customer/{customer_id}",
        }
    return node


def build_step2_payload(
    *,
    customer_id: int,
    nodes: Sequence[dict],
    product_subscriber_status: Optional[str] = "PAUSED",
    has_next_page: bool = False,
    has_previous_page: bool = False,
    start_cursor: Optional[str] = None,
    end_cursor: Optional[str] = None,
    include_product_subscriber_status: bool = True,
) -> dict:
    """Build a step-2 customer payload shaped like the sanitized fixtures."""
    payload: Dict[str, Any] = {
        "__typename": "Customer",
        "id": f"gid://shopify/Customer/{customer_id}",
        "tags": [],
        "subscriptionContracts": {
            "__typename": "SubscriptionContractConnection",
            "nodes": list(nodes),
            "pageInfo": {
                "__typename": "PageInfo",
                "hasPreviousPage": has_previous_page,
                "hasNextPage": has_next_page,
                "startCursor": start_cursor or f"HARNESS_CURSOR_{customer_id}_START",
                "endCursor": end_cursor or f"HARNESS_CURSOR_{customer_id}_END",
            },
        },
    }
    if include_product_subscriber_status:
        payload["productSubscriberStatus"] = product_subscriber_status
    return payload


def paginate(
    *,
    customer_id: int,
    pages: Sequence[Sequence[dict]],
    product_subscriber_status: Optional[str] = "PAUSED",
) -> List[dict]:
    """Split contract nodes into a list of step-2 page payloads.

    Page *n* advertises ``hasNextPage=True`` and an ``endCursor`` that the router
    accepts as the ``?cursor=`` value for page *n+1*, so a caller that follows
    ``pageInfo`` reaches the later pages and a caller that does not is visibly
    missing them in :attr:`PayloadRouter.requests`.
    """
    payloads: List[dict] = []
    total = len(pages)
    for index, page_nodes in enumerate(pages):
        payloads.append(
            build_step2_payload(
                customer_id=customer_id,
                nodes=page_nodes,
                product_subscriber_status=product_subscriber_status,
                has_next_page=index < total - 1,
                has_previous_page=index > 0,
                start_cursor=f"HARNESS_CURSOR_{customer_id}_PAGE{index + 1}_START",
                end_cursor=f"HARNESS_CURSOR_{customer_id}_PAGE{index + 1}_END",
            )
        )
    return payloads


# ---------------------------------------------------------------------------
# URL-keyed payload router
# ---------------------------------------------------------------------------

class RouterMiss(LookupError):
    """Raised when the router has no payload configured for a requested URL.

    Deliberately loud: a silent ``None`` here would let a test pass while the
    system under test asked for something the test never intended to serve.
    """


@dataclass(frozen=True)
class RecordedRequest:
    """One ``_appstle_get`` call the router observed."""

    url: str
    params: Optional[Dict[str, Any]]

    @property
    def is_step1(self) -> bool:
        return self.url.endswith(STEP1_PATH)

    @property
    def customer_id(self) -> Optional[int]:
        """The ``customerId`` a step-2 URL addressed, or ``None`` for step 1."""
        if self.is_step1:
            return None
        tail = self.url.rstrip("/").rsplit("/", 1)[-1]
        try:
            return int(tail)
        except ValueError:
            return None

    @property
    def cursor(self) -> Optional[str]:
        if not self.params:
            return None
        value = self.params.get(PAGINATION_PARAM)
        return str(value) if value is not None else None

    @property
    def email(self) -> Optional[str]:
        if not self.params:
            return None
        value = self.params.get("email")
        return str(value) if value is not None else None


# A routed value may be a payload, an exception to raise, or a zero-argument
# callable producing either.
Routed = Union[Any, BaseException, Callable[[], Any]]


class PayloadRouter:
    """Stand-in for ``SubscriptionAuthService._appstle_get`` keyed by URL.

    Constructed with a step-1 payload and a ``customerId -> step-2 payload``
    mapping. A mapping value may be:

    * a payload dict — served for every request for that customer;
    * a list of payload dicts — successive pages, selected by the ``?cursor=``
      parameter (page 1 when no cursor is supplied);
    * an ``Exception`` instance or class — raised, which is how the preserved
      Appstle-failure paths (timeout, HTTP error, malformed JSON) are reached;
    * a callable returning any of the above.

    Every call is recorded in :attr:`requests` before the payload is resolved,
    so a test can assert what was fetched even when the call raises.
    """

    def __init__(
        self,
        *,
        step1: Routed = None,
        step2: Optional[Dict[int, Routed]] = None,
        default_step2: Routed = None,
        base_url: str = APPSTLE_API_URL,
    ) -> None:
        self.step1: Routed = step1 if step1 is not None else []
        self.step2: Dict[int, Routed] = {int(k): v for k, v in (step2 or {}).items()}
        self.default_step2 = default_step2
        self.base_url = base_url
        self.requests: List[RecordedRequest] = []

    # -- recording accessors -------------------------------------------------

    @property
    def urls(self) -> List[str]:
        """Every URL requested, in order."""
        return [r.url for r in self.requests]

    @property
    def step1_requests(self) -> List[RecordedRequest]:
        return [r for r in self.requests if r.is_step1]

    @property
    def step2_requests(self) -> List[RecordedRequest]:
        return [r for r in self.requests if not r.is_step1]

    @property
    def requested_customer_ids(self) -> List[int]:
        """``customerId``s a step-2 request was actually issued for, in order."""
        seen: List[int] = []
        for req in self.step2_requests:
            cid = req.customer_id
            if cid is not None and cid not in seen:
                seen.append(cid)
        return seen

    def fetched_customer(self, customer_id: int) -> bool:
        """Was a step-2 request issued for ``customer_id``?

        Property 7's negative half on unfixed code: the second ``customerId`` is
        never fetched, and this is how a test proves it.
        """
        return int(customer_id) in self.requested_customer_ids

    def cursors_requested(self, customer_id: Optional[int] = None) -> List[Optional[str]]:
        """Cursor values sent for a customer's step-2 requests, in order."""
        out: List[Optional[str]] = []
        for req in self.step2_requests:
            if customer_id is None or req.customer_id == int(customer_id):
                out.append(req.cursor)
        return out

    def page_count(self, customer_id: int) -> int:
        """How many step-2 requests were issued for ``customer_id``."""
        return sum(1 for r in self.step2_requests if r.customer_id == int(customer_id))

    def followed_next_page(self, customer_id: int) -> bool:
        """Did anything request a page beyond the first for ``customer_id``?"""
        return any(c is not None for c in self.cursors_requested(customer_id))

    def reset(self) -> None:
        self.requests.clear()

    # -- routing -------------------------------------------------------------

    async def __call__(
        self,
        session: Any,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Match ``SubscriptionAuthService._appstle_get``'s signature exactly.

        Bound onto the *instance*, so ``self`` is not passed through.
        """
        record = RecordedRequest(url=url, params=dict(params) if params else None)
        self.requests.append(record)

        if record.is_step1:
            return _resolve(self.step1, url)

        customer_id = record.customer_id
        if customer_id is None:
            raise RouterMiss(f"Could not parse a customerId out of step-2 url {url!r}")

        if customer_id in self.step2:
            routed = self.step2[customer_id]
        elif self.default_step2 is not None:
            routed = self.default_step2
        else:
            raise RouterMiss(
                f"No step-2 payload configured for customerId {customer_id} "
                f"(url={url!r}); configured: {sorted(self.step2)}"
            )

        resolved = _resolve(routed, url)

        # A list means paginated pages; pick the page the cursor asks for.
        if isinstance(resolved, list) and resolved and _looks_like_page_list(resolved):
            return _select_page(resolved, record.cursor, url)
        return copy.deepcopy(resolved)


def _resolve(routed: Routed, url: str) -> Any:
    """Unwrap a routed value: call callables, raise exceptions, copy payloads."""
    value = routed
    if callable(value) and not isinstance(value, type):
        value = value()
    if isinstance(value, type) and issubclass(value, BaseException):
        raise value(f"Harness router raised {value.__name__} for {url!r}")
    if isinstance(value, BaseException):
        raise value
    return copy.deepcopy(value)


def _looks_like_page_list(value: Sequence[Any]) -> bool:
    return all(isinstance(item, dict) and "subscriptionContracts" in item for item in value)


def _select_page(pages: Sequence[dict], cursor: Optional[str], url: str) -> dict:
    if cursor is None:
        return copy.deepcopy(pages[0])
    for index, page in enumerate(pages[:-1]):
        end_cursor = (page.get("subscriptionContracts", {}).get("pageInfo", {}) or {}).get("endCursor")
        if end_cursor == cursor:
            return copy.deepcopy(pages[index + 1])
    raise RouterMiss(
        f"Unknown {PAGINATION_PARAM}={cursor!r} for {url!r}; "
        f"expected one of "
        f"{[(p.get('subscriptionContracts', {}).get('pageInfo', {}) or {}).get('endCursor') for p in pages[:-1]]}"
    )


# ---------------------------------------------------------------------------
# Appstle failure injectors (routed values that raise)
# ---------------------------------------------------------------------------

def appstle_timeout() -> asyncio.TimeoutError:
    """Route value that reproduces an Appstle timeout (clause 3.7 / 3.8)."""
    return asyncio.TimeoutError()


def appstle_http_error(status: int = 500) -> aiohttp.ClientResponseError:
    """Route value that reproduces a non-200 Appstle response (clause 3.7).

    ``_appstle_get`` raises ``ClientResponseError`` with the upstream status, and
    ``login()`` branches on ``exc.status``, so the status has to be carried here
    rather than faked with a bare exception.
    """
    return aiohttp.ClientResponseError(
        request_info=None,  # type: ignore[arg-type]
        history=(),
        status=status,
        message=f"Appstle API returned {status}",
    )


def appstle_malformed_json() -> ValueError:
    """Route value that reproduces an unparseable Appstle body (clause 3.7)."""
    return ValueError("Malformed Appstle response: harness injected")


# ---------------------------------------------------------------------------
# Deterministic password service stub
# ---------------------------------------------------------------------------

class StubPasswordService:
    """In-memory stand-in for ``PasswordService``.

    Same public surface the login flow touches (``get_customer``,
    ``verify_password``, ``validate_password``, ``create_customer``), with:

    * no database — records live in a dict;
    * no bcrypt — hashes are ``"stubhash::<password>"``, so verification is
      exact, deterministic, and fast (real bcrypt at 12 rounds costs ~0.3s per
      call, which Hypothesis would multiply by a hundred);
    * the **real** complexity rules, borrowed from ``PasswordService`` rather
      than reimplemented, so the 400 ``failed_rules`` path (clause 3.9) is
      faithful;
    * ``raise_on_*`` switches for the error paths ``login()`` handles.
    """

    MIN_LENGTH = 8
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Borrow the production rules verbatim; it reads only the two class
    # constants above, so binding it here keeps the 400 path honest.
    validate_password = subscription_auth.PasswordService.validate_password

    def __init__(self, known: Optional[Dict[str, str]] = None) -> None:
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.created_emails: List[str] = []
        self.raise_on_get = False
        self.raise_on_verify = False
        self.raise_on_create = False
        for email, password in (known or {}).items():
            self.register(email, password)

    # -- helpers -------------------------------------------------------------

    def register(self, email: str, password: str = KNOWN_PASSWORD) -> Dict[str, Any]:
        """Pre-seed an existing customer so login takes the 6a verify path."""
        key = email.lower().strip()
        record = {
            "id": len(self.customers) + 1,
            "email": key,
            "password_hash": self.hash_password(password),
            "created_at": FIXTURE_NOW,
            "updated_at": FIXTURE_NOW,
        }
        self.customers[key] = record
        return record

    def hash_password(self, password: str) -> str:
        return f"stubhash::{password}"

    def verify_password(self, password: str, hashed: str) -> bool:
        if self.raise_on_verify:
            raise RuntimeError("stub password verification failure")
        return self.hash_password(password) == hashed

    # -- async surface -------------------------------------------------------

    async def get_customer(self, email: str) -> Optional[Dict[str, Any]]:
        if self.raise_on_get:
            raise RuntimeError("stub password lookup failure")
        return self.customers.get(email.lower().strip())

    async def create_customer(self, email: str, password: str) -> Dict[str, Any]:
        if self.raise_on_create:
            raise RuntimeError("stub password record creation failure")
        self.created_emails.append(email.lower().strip())
        return self.register(email, password)


# ---------------------------------------------------------------------------
# Token / body normalization
# ---------------------------------------------------------------------------

def decode_token_claims(token: str, *, secret: str = JWT_SECRET_KEY) -> Dict[str, Any]:
    """Decode a harness-issued JWT, verifying only the signature.

    Time-based claims are not checked: a normalizer that raised on an expired or
    backdated token would fail exactly on the tokens the grace-window cases
    (clause 3.11) are built to produce.
    """
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False, "verify_nbf": False},
    )


def normalize_body(body: Any, *, secret: str = JWT_SECRET_KEY) -> Any:
    """Return ``body`` with ``token`` reduced to its decoded claim key set.

    A fresh JWT differs on every call (``iat``/``exp`` move, and the signature
    with them), so string equality on ``token`` would make every comparison
    fail for a reason that has nothing to do with the access decision. What is
    actually load-bearing is the claim *shape* (clause 3.12), so the token
    collapses to ``{"claim_keys": [...]}`` and stays comparable across calls and
    across the fix.

    Non-dict bodies and bodies without a token pass through unchanged.
    """
    if not isinstance(body, dict):
        return copy.deepcopy(body)

    normalized = copy.deepcopy(body)
    if "token" in normalized:
        token = normalized["token"]
        if isinstance(token, str) and token:
            try:
                claims = decode_token_claims(token, secret=secret)
                normalized["token"] = {"claim_keys": sorted(claims.keys())}
            except jwt.InvalidTokenError as exc:  # pragma: no cover - defensive
                normalized["token"] = {"undecodable": str(exc)}
    return normalized


# ---------------------------------------------------------------------------
# The harness itself
# ---------------------------------------------------------------------------

DEFAULT_EMAIL = "harness@example.com"
DEFAULT_CLIENT_IP = "203.0.113.7"


@dataclass
class Harness:
    """A wired-up service plus the seams a test needs to steer and inspect it."""

    service: SubscriptionAuthService
    router: PayloadRouter
    passwords: StubPasswordService
    signup_url: str = SUBSCRIPTION_SIGNUP_URL
    jwt_secret: str = JWT_SECRET_KEY

    # -- driving the system under test ---------------------------------------

    def login(
        self,
        email: str = DEFAULT_EMAIL,
        password: str = KNOWN_PASSWORD,
        client_ip: str = DEFAULT_CLIENT_IP,
    ) -> Dict[str, Any]:
        """Run ``login()`` to completion and return its ``{status_code, body}``."""
        return _run(self.service.login(email, password, client_ip))

    def refresh(self, token: str) -> Dict[str, Any]:
        """Run ``refresh()`` to completion and return its ``{status_code, body}``."""
        return _run(self.service.refresh(token))

    # -- token helpers -------------------------------------------------------

    def token_for(
        self,
        email: str = DEFAULT_EMAIL,
        subscription_status: str = "active",
        *,
        age: Optional[Any] = None,
    ) -> str:
        """Issue a token for ``email``, optionally backdated by ``age``.

        ``age`` is a ``timedelta``; a token backdated past its 1-hour expiry is
        how the 5-minute grace window (clause 3.11) is exercised.
        """
        token = self.service.create_token(email, subscription_status)
        if age is None:
            return token
        claims = decode_token_claims(token, secret=self.jwt_secret)
        shift = int(age.total_seconds())
        claims["iat"] -= shift
        claims["exp"] -= shift
        return jwt.encode(claims, self.jwt_secret, algorithm="HS256")

    def claims(self, token: str) -> Dict[str, Any]:
        return decode_token_claims(token, secret=self.jwt_secret)

    def normalize(self, body: Any) -> Any:
        return normalize_body(body, secret=self.jwt_secret)

    def normalized_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """``{status_code, body}`` with the token reduced — the comparable form."""
        return {
            "status_code": result["status_code"],
            "body": self.normalize(result["body"]),
        }

    # -- state control -------------------------------------------------------

    def reset_rate_limiter(self) -> None:
        """Clear all recorded attempts.

        Called automatically between cases; exposed because a Hypothesis test
        runs many examples inside one harness and must not trip the 5-attempt
        limit partway through (which would turn every later example into a 429).
        """
        self.service.rate_limiter.attempts.clear()

    def reset(self) -> None:
        """Reset the rate limiter and the router's recorded requests."""
        self.reset_rate_limiter()
        self.router.reset()

    def set_bypass_emails(self, *emails: str) -> None:
        os.environ["BYPASS_EMAILS"] = ",".join(emails)

    # -- convenience configuration ------------------------------------------

    def route(self, *, step1: Routed = None, step2: Optional[Dict[int, Routed]] = None) -> None:
        """Replace the routed payloads without rebuilding the service."""
        if step1 is not None:
            self.router.step1 = step1
        if step2 is not None:
            self.router.step2 = {int(k): v for k, v in step2.items()}


def _run(coro) -> Any:
    """Drive a coroutine to completion on a private event loop.

    ``asyncio.run`` per call keeps each case independent and lets Hypothesis
    tests stay synchronous, so no ``pytest-asyncio`` event-loop fixture has to be
    threaded through the property suites.
    """
    return asyncio.run(coro)


@contextmanager
def harness(
    *,
    step1: Routed = None,
    step2: Optional[Dict[int, Routed]] = None,
    default_step2: Routed = None,
    known_passwords: Optional[Dict[str, str]] = None,
    bypass_emails: str = "",
    clock: Optional[Callable[[], Any]] = None,
    env: Optional[Dict[str, Optional[str]]] = None,
    missing_config: bool = False,
    signup_url: str = SUBSCRIPTION_SIGNUP_URL,
    log_level: Optional[int] = None,
):
    """Build a fully wired :class:`Harness` and restore all global state on exit.

    Uses no pytest fixtures on purpose. ``monkeypatch`` is function-scoped, and a
    Hypothesis ``@given`` test runs many examples inside a single function call,
    so a fixture-based harness would be built once and shared silently across
    examples. A context manager makes the lifetime explicit and works the same
    inside and outside Hypothesis.

    What is patched, and unwound afterwards:

    * ``APPSTLE_API_URL`` / ``APPSTLE_API_KEY`` / ``JWT_SECRET_KEY`` /
      ``SUBSCRIPTION_SIGNUP_URL`` / ``BYPASS_EMAILS`` env values;
    * ``backend.subscription_auth._utcnow`` → ``fixture_now`` (design change 2b),
      so the verbatim fixture dates are read against ``FIXTURE_NOW``;
    * ``service._appstle_get`` → a :class:`PayloadRouter`;
    * ``service.password_service`` → a :class:`StubPasswordService`.

    ``missing_config=True`` blanks the Appstle credentials so the 503 path
    (clause 3.6) is reachable. ``env`` overrides or, with a ``None`` value,
    deletes any additional variable.
    """
    overrides: Dict[str, Optional[str]] = {
        "APPSTLE_API_URL": "" if missing_config else APPSTLE_API_URL,
        "APPSTLE_API_KEY": "" if missing_config else APPSTLE_API_KEY,
        "JWT_SECRET_KEY": JWT_SECRET_KEY,
        "SUBSCRIPTION_SIGNUP_URL": signup_url,
        "BYPASS_EMAILS": bypass_emails,
        # PasswordService is replaced by the stub, but its constructor raises
        # without this, which would log a warning on every build.
        "DATABASE_URL": "postgresql://harness/offline",
    }
    if env:
        overrides.update(env)

    original_env = {key: os.environ.get(key) for key in overrides}
    original_utcnow = subscription_auth._utcnow

    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        subscription_auth._utcnow = clock or fixture_now

        service = SubscriptionAuthService()

        router = PayloadRouter(step1=step1, step2=step2, default_step2=default_step2)
        service._appstle_get = router  # type: ignore[method-assign]

        passwords = StubPasswordService(known_passwords)
        service.password_service = passwords  # type: ignore[assignment]

        built = Harness(
            service=service,
            router=router,
            passwords=passwords,
            signup_url=signup_url,
            jwt_secret=JWT_SECRET_KEY,
        )
        built.reset_rate_limiter()

        if log_level is not None:
            logging.getLogger("backend.subscription_auth").setLevel(log_level)

        yield built
    finally:
        subscription_auth._utcnow = original_utcnow
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# The status domain the decision rule has to survive. ACTIVE / PAUSED /
# CANCELLED are the three Appstle values observed or documented; EXPIRED is in
# DENIAL_MESSAGES but was never observed on a contract; the junk and None
# entries exist because clause 2.4 says every other value must not grant, and
# because status has misled twice on this system already.
JUNK_STATUSES = ("", "SUSPENDED", "NOT_A_STATUS", "paused", "active ", "0")
CONTRACT_STATUSES = ("ACTIVE", "PAUSED", "CANCELLED", "EXPIRED", *JUNK_STATUSES, None)

# DAY and MONTH are the only units the capture showed; WEEK and YEAR are
# supported but unobserved. "FORTNIGHT" stands in for an unrecognized unit and
# ``None`` means ``billingPolicy`` is absent entirely — clause 2.8 treats those
# two as distinct inputs, and both must yield an underivable paid_through.
UNRECOGNIZED_INTERVALS = ("FORTNIGHT", "BIWEEKLY", "", "month")
INTERVAL_UNITS = ("DAY", "WEEK", "MONTH", "YEAR", *UNRECOGNIZED_INTERVALS, None)

FALLBACK_STATUSES = ("ACTIVE", "PAUSED", "CANCELLED", "EXPIRED", None)


def _iso(dt) -> str:
    """Render a datetime the way Appstle does: UTC with a trailing ``Z``."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def contract_statuses() -> st.SearchStrategy[Optional[str]]:
    """Per-contract ``status``, including junk and ``None``."""
    return st.sampled_from(CONTRACT_STATUSES)


def interval_units() -> st.SearchStrategy[Optional[str]]:
    """``billingPolicy.interval``; ``None`` means the policy is absent."""
    return st.sampled_from(INTERVAL_UNITS)


def interval_counts() -> st.SearchStrategy[int]:
    """``billingPolicy.intervalCount``. Real data uses 30 routinely, so this is
    never safe to assume is 1."""
    return st.integers(min_value=1, max_value=12)


def past_dates() -> st.SearchStrategy[str]:
    """An ISO date strictly before ``FIXTURE_NOW``."""
    return st.integers(min_value=1, max_value=900).map(lambda d: _iso(at_offset(days=-d)))


def future_dates() -> st.SearchStrategy[str]:
    """An ISO date strictly after ``FIXTURE_NOW``."""
    return st.integers(min_value=1, max_value=900).map(lambda d: _iso(at_offset(days=d)))


def next_billing_choices() -> st.SearchStrategy[Optional[str]]:
    """``nextBillingDate`` over {past, future, null} — the three cases that
    decide whether a PAUSED or CANCELLED contract has paid time left."""
    return st.one_of(past_dates(), future_dates(), st.none())


def created_at_choices() -> st.SearchStrategy[Optional[str]]:
    """``createdAt`` anchors, past and future, plus null.

    Future anchors are included deliberately: they are nonsense from Appstle but
    they are what makes ``createdAt`` + interval land in the future, and a null
    anchor is the clause 2.8 case where interval arithmetic must not be
    attempted at all.
    """
    return st.one_of(past_dates(), future_dates(), st.none())


@st.composite
def contract_dicts(
    draw,
    *,
    contract_id: Optional[Union[int, str]] = None,
    customer_id: Optional[int] = None,
    status: Optional[st.SearchStrategy] = None,
    next_billing_date: Optional[st.SearchStrategy] = None,
    created_at: Optional[st.SearchStrategy] = None,
    interval: Optional[st.SearchStrategy] = None,
) -> dict:
    """One ``subscriptionContracts.nodes[]`` entry drawn across the full domain.

    Any axis can be narrowed by passing a strategy, which is how a scoped
    property pins (say) status to CANCELLED while still generating dates.
    """
    drawn_status = draw(status or contract_statuses())
    drawn_next_billing = draw(next_billing_date or next_billing_choices())
    drawn_created_at = draw(created_at or created_at_choices())
    drawn_interval = draw(interval or interval_units())
    drawn_count = draw(interval_counts())
    cid = contract_id if contract_id is not None else draw(
        st.integers(min_value=9_000_000_001, max_value=9_000_009_999)
    )

    return build_contract_node(
        contract_id=cid,
        status=drawn_status,
        created_at=drawn_created_at,
        next_billing_date=drawn_next_billing,
        interval=drawn_interval,
        interval_count=drawn_count,
        customer_id=customer_id,
    )


@st.composite
def contract_sets(
    draw,
    *,
    min_size: int = 1,
    max_size: int = 4,
    contracts: Optional[st.SearchStrategy] = None,
) -> List[dict]:
    """A list of contract dicts with unique, deterministic contract ids.

    Ids are rewritten after generation rather than drawn uniquely, because the
    denial-message tiebreak (clause 2.16) compares ``contract_id`` and a
    duplicate id would make the "deterministic tiebreak" assertion vacuous.
    """
    nodes = draw(st.lists(contracts or contract_dicts(), min_size=min_size, max_size=max_size))
    for index, node in enumerate(nodes):
        node["id"] = f"gid://shopify/SubscriptionContract/{9_000_010_000 + index}"
        node["lines"]["nodes"][0]["id"] = f"gid://shopify/SubscriptionLine/{9_000_010_000 + index}"
    return nodes


@dataclass
class PayloadPlan:
    """A generated distribution of contracts across customer records and pages.

    Feed it straight into the router::

        with harness(**plan.router_kwargs()) as h:
            result = h.login(plan.email)
    """

    email: str
    customer_ids: List[int]
    pages_by_customer: Dict[int, List[List[dict]]]
    fallback_status_by_customer: Dict[int, Optional[str]]

    @property
    def step1(self) -> List[dict]:
        return step1_payload(self.customer_ids, email=self.email)

    @property
    def step2(self) -> Dict[int, List[dict]]:
        return {
            cid: paginate(
                customer_id=cid,
                pages=self.pages_by_customer[cid],
                product_subscriber_status=self.fallback_status_by_customer[cid],
            )
            for cid in self.customer_ids
        }

    def router_kwargs(self) -> Dict[str, Any]:
        return {"step1": self.step1, "step2": self.step2}

    @property
    def all_contracts(self) -> List[dict]:
        """Every contract in the plan, across all records and all pages."""
        return [
            node
            for cid in self.customer_ids
            for page in self.pages_by_customer[cid]
            for node in page
        ]

    @property
    def visible_contracts(self) -> List[dict]:
        """Contracts the UNFIXED code can reach: first record, first page only.

        Useful for expressing bug-condition clause (a) — some contract grants but
        nothing visible here does.
        """
        if not self.customer_ids:
            return []
        pages = self.pages_by_customer[self.customer_ids[0]]
        return list(pages[0]) if pages else []

    @property
    def first_contract(self) -> Optional[dict]:
        """``nodes[0]`` of the first customer record's first page — exactly what
        the unfixed ``_parse_contract_response()`` reads."""
        visible = self.visible_contracts
        return visible[0] if visible else None

    @property
    def page_counts(self) -> Dict[int, int]:
        return {cid: len(self.pages_by_customer[cid]) for cid in self.customer_ids}

    @property
    def is_multi_customer(self) -> bool:
        return len(self.customer_ids) > 1

    @property
    def is_paginated(self) -> bool:
        return any(count > 1 for count in self.page_counts.values())


@st.composite
def payload_plans(
    draw,
    *,
    contracts: Optional[st.SearchStrategy] = None,
    min_customers: int = 1,
    max_customers: int = 3,
    min_pages: int = 1,
    max_pages: int = 3,
    email: str = DEFAULT_EMAIL,
) -> PayloadPlan:
    """Distribute a generated contract set across 1-3 customer records and 1-3 pages.

    Both truncations in the bug are shape-level rather than value-level — the
    unfixed code reads ``nodes[0]`` of the first record's first page — so the
    distribution *is* the interesting variable, and it has to be generated
    rather than fixed.

    Contracts are dealt round-robin across records and then round-robin across
    pages within each record. A record may legitimately end up with zero
    contracts when the record count exceeds the contract count; that lands on the
    empty-``nodes[]`` fallback (clause 2.12), which is a case worth generating.
    """
    nodes = draw(contract_sets(contracts=contracts, min_size=1, max_size=6))
    n_customers = draw(st.integers(min_value=min_customers, max_value=max_customers))
    n_pages = draw(st.integers(min_value=min_pages, max_value=max_pages))

    customer_ids = [7_000_100_000 + i for i in range(n_customers)]

    per_customer: Dict[int, List[dict]] = {cid: [] for cid in customer_ids}
    for index, node in enumerate(nodes):
        per_customer[customer_ids[index % n_customers]].append(node)

    pages_by_customer: Dict[int, List[List[dict]]] = {}
    for cid, owned in per_customer.items():
        pages: List[List[dict]] = [[] for _ in range(n_pages)]
        for index, node in enumerate(owned):
            pages[index % n_pages].append(node)
        # Trailing empty pages would advertise hasNextPage for nothing; keep the
        # first page plus every page that actually carries a contract.
        trimmed = [page for page in pages if page]
        pages_by_customer[cid] = trimmed or [[]]

    fallback_status_by_customer = {
        cid: draw(st.sampled_from(FALLBACK_STATUSES)) for cid in customer_ids
    }

    return PayloadPlan(
        email=email,
        customer_ids=customer_ids,
        pages_by_customer=pages_by_customer,
        fallback_status_by_customer=fallback_status_by_customer,
    )
