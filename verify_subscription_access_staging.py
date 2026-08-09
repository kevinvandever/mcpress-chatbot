#!/usr/bin/env python3
"""
Task 11 verification for spec `subscription-multi-contract-access`.

API-based only (`requests`), run LOCALLY against the deployed staging backend.
Never uses `railway shell` / `railway run` and never imports from `backend.*`.

What it verifies
----------------
1. ``GET /health`` is green — proves `backend/main.py` still boots with the
   `subscription_test_router` registration block removed (task 9.8).
2. ``POST /api/test/subscription-decision`` returns 404 — proves the fourth copy
   of the decision logic is gone (requirement 2.15).
3. ``POST /api/auth/login`` for the three captured Appstle customers, printing
   ``status_code``, ``subscription_status``, ``error`` and ``redirect_url`` for
   each (requirements 2.11, 2.19, 2.20 evidence; 3.1 / 3.3 preservation).

Real emails are NEVER hardcoded here. They come from the environment (or CLI
flags) at runtime, so this file is safe to commit:

    export VERIFY_MULTI_CONTRACT_EMAIL=...      # customerId 2788838535 (Dave)
    export VERIFY_RENEWED_EMAIL=...             # customerId 2788845447 (ACTIVE monthly)
    export VERIFY_LAPSED_EMAIL=...              # customerId 3289420039 (PAUSED, lapsed)

Passwords are optional:

    export VERIFY_MULTI_CONTRACT_PASSWORD=...   # etc.

Why passwords are optional — and what a run without them still proves
---------------------------------------------------------------------
`login()` decides the subscription BEFORE it touches the password (step 4 runs
ahead of steps 5/6a/6b). So a login with a deliberately rule-violating probe
password is still a complete read of the subscription decision:

  * 403 + subscription error  -> subscription check DENIED (message, status and
                                 redirect_url are all fully observable)
  * 401 "Invalid email or password"
                              -> subscription check GRANTED, then the password
                                 mismatched (existing customer)
  * 400 + failed_rules        -> subscription check GRANTED, then the new-user
                                 password rules rejected the probe

The probe password is chosen to fail every complexity rule, so the new-user
branch can never reach step 7 and can never create or overwrite a password
record for a real customer. Nothing is mutated.

A probe run therefore proves GRANTED vs DENIED but cannot read the granted
`subscription_status` ("active" vs "free") out of the body. Supply the real
password for a customer to get the literal 200 / "active" body.

Usage
-----
    python3 verify_subscription_access_staging.py
    python3 verify_subscription_access_staging.py --api-url https://... 
    python3 verify_subscription_access_staging.py --require-active multi_contract

Note on rate limiting: the backend allows 5 login attempts per IP per 15
minutes and only resets that counter on a fully successful (200) login. A full
run spends 3 attempts, so two probe runs back to back from the same IP will hit
429 on the sixth. Wait out the window rather than reading a 429 as a failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_API_URL = "https://mcpress-chatbot-staging.up.railway.app"

# Fails min-length? no (10 chars) — but fails uppercase, digit and special, so
# validate_password() rejects it and the new-user branch returns 400 before any
# password record is created.
PROBE_PASSWORD = "kiroprobe"

TIMEOUT = 60

# label -> (human description, email env var, password env var, captured customerId)
CUSTOMERS: List[Tuple[str, str, str, str, str]] = [
    (
        "multi_contract",
        "two PAUSED contracts, nodes[0] expired / nodes[1] paid through",
        "VERIFY_MULTI_CONTRACT_EMAIL",
        "VERIFY_MULTI_CONTRACT_PASSWORD",
        "2788838535",
    ),
    (
        "renewed_monthly",
        "single ACTIVE monthly contract (preserved 200 / active, 3.1)",
        "VERIFY_RENEWED_EMAIL",
        "VERIFY_RENEWED_PASSWORD",
        "2788845447",
    ),
    (
        "lapsed_paused",
        "single PAUSED contract, nextBillingDate in the past (preserved 403, 3.3)",
        "VERIFY_LAPSED_EMAIL",
        "VERIFY_LAPSED_PASSWORD",
        "3289420039",
    ),
]


class Results:
    """Collects PASS / FAIL / SKIP outcomes so the exit code is meaningful."""

    def __init__(self) -> None:
        self.rows: List[Tuple[str, str, str]] = []

    def record(self, outcome: str, name: str, detail: str = "") -> None:
        self.rows.append((outcome, name, detail))
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️ ", "INFO": "ℹ️ "}.get(outcome, "  ")
        print(f"{icon} {outcome:4}  {name}" + (f" — {detail}" if detail else ""))

    @property
    def failed(self) -> int:
        return sum(1 for outcome, _, _ in self.rows if outcome == "FAIL")

    def summary(self) -> None:
        print("\n" + "=" * 78)
        print("SUMMARY")
        print("=" * 78)
        for outcome, name, detail in self.rows:
            print(f"  {outcome:4}  {name}" + (f" — {detail}" if detail else ""))
        counts: Dict[str, int] = {}
        for outcome, _, _ in self.rows:
            counts[outcome] = counts.get(outcome, 0) + 1
        print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def _mask(email: str) -> str:
    """Mask an email for console output so a shared terminal log leaks nothing."""
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    head = local[:1] if local else ""
    return f"{head}{'*' * max(len(local) - 1, 1)}@{domain}"


# ---------------------------------------------------------------------------
# 1. GET /health
# ---------------------------------------------------------------------------

def check_health(api_url: str, results: Results) -> None:
    name = "GET /health is green (main.py boots without subscription_test_router)"
    try:
        resp = requests.get(f"{api_url}/health", timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        results.record("FAIL", name, f"request failed: {exc}")
        return

    body = _safe_json(resp)
    if resp.status_code == 200:
        results.record("PASS", name, f"200 {json.dumps(body)[:160]}")
    else:
        results.record("FAIL", name, f"status={resp.status_code} body={resp.text[:200]}")


# ---------------------------------------------------------------------------
# 2. POST /api/test/subscription-decision must be gone
# ---------------------------------------------------------------------------

def check_test_endpoint_removed(api_url: str, results: Results) -> None:
    name = "POST /api/test/subscription-decision returns 404 (2.15)"
    try:
        resp = requests.post(
            f"{api_url}/api/test/subscription-decision",
            json={"email": "probe@example.com"},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        results.record("FAIL", name, f"request failed: {exc}")
        return

    if resp.status_code == 404:
        results.record("PASS", name, "404 — endpoint deleted")
    else:
        results.record(
            "FAIL",
            name,
            f"status={resp.status_code} (endpoint still registered — is the deploy finished?) "
            f"body={resp.text[:200]}",
        )


# ---------------------------------------------------------------------------
# 3. POST /api/auth/login for each captured customer
# ---------------------------------------------------------------------------

def probe_login(
    api_url: str,
    label: str,
    description: str,
    email: str,
    password: Optional[str],
    customer_id: str,
    require_active: bool,
    results: Results,
) -> None:
    using_probe = password is None
    name = f"POST /api/auth/login [{label}] customerId={customer_id}"

    print("\n" + "-" * 78)
    print(f"{label}  ({description})")
    print(f"  email      : {_mask(email)}")
    print(f"  password   : {'PROBE (rule-violating, nothing mutated)' if using_probe else 'supplied via env'}")

    try:
        resp = requests.post(
            f"{api_url}/api/auth/login",
            json={"email": email, "password": password or PROBE_PASSWORD},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        results.record("FAIL", name, f"request failed: {exc}")
        return

    body = _safe_json(resp)

    # The four fields the task asks to be printed for every customer.
    print(f"  status_code        : {resp.status_code}")
    print(f"  subscription_status: {body.get('subscription_status')!r}")
    print(f"  error              : {body.get('error')!r}")
    print(f"  redirect_url       : {body.get('redirect_url')!r}")
    if body.get("failed_rules"):
        print(f"  failed_rules       : {body['failed_rules']}")

    code = resp.status_code

    if code == 429:
        results.record(
            "SKIP", name,
            "429 rate limited (5 attempts / 15 min / IP) — wait out the window and re-run",
        )
        return

    if code == 503:
        results.record("FAIL", name, "503 — Appstle config missing on this environment")
        return

    if code == 200:
        status = body.get("subscription_status")
        results.record(
            "PASS" if not require_active or status == "active" else "FAIL",
            name,
            f"200 subscription_status={status!r}",
        )
        return

    if code == 403:
        # Subscription check denied. Fully observable regardless of password.
        detail = f"403 DENIED status={body.get('subscription_status')!r} error={body.get('error')!r}"
        if not body.get("redirect_url"):
            results.record("FAIL", name, detail + " — redirect_url is empty (3.3 requires one)")
        elif require_active:
            results.record("FAIL", name, detail + " — expected a grant")
        else:
            results.record("PASS", name, detail)
        return

    if code in (400, 401):
        # Subscription check GRANTED; the request then died at the password step.
        why = "existing password record, probe password mismatched" if code == 401 \
            else "no password record, probe password rejected by the rules (nothing created)"
        detail = f"{code} — subscription check GRANTED ({why})"
        if require_active:
            results.record(
                "FAIL", name,
                detail + " — --require-active needs the real password to read the 200 body",
            )
        else:
            results.record("PASS", name, detail)
        return

    results.record("FAIL", name, f"unexpected status={code} body={resp.text[:200]}")


def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        parsed = resp.json()
        return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    except ValueError:
        return {}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Task 11 staging verification for subscription-multi-contract-access",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", DEFAULT_API_URL),
        help=f"backend base URL (default {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--require-active",
        action="append",
        default=[],
        metavar="LABEL",
        help="assert this customer returns 200 / 'active' (needs the real password); "
             "repeatable; labels: " + ", ".join(label for label, *_ in CUSTOMERS),
    )
    parser.add_argument(
        "--skip-logins",
        action="store_true",
        help="only run the /health and 404 checks",
    )
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    results = Results()

    print("=" * 78)
    print("Task 11 — staging verification, subscription-multi-contract-access")
    print("=" * 78)
    print(f"API_URL: {api_url}\n")

    check_health(api_url, results)
    check_test_endpoint_removed(api_url, results)

    if args.skip_logins:
        results.summary()
        return 1 if results.failed else 0

    for label, description, email_env, password_env, customer_id in CUSTOMERS:
        email = os.getenv(email_env, "").strip()
        if not email:
            results.record(
                "SKIP",
                f"POST /api/auth/login [{label}] customerId={customer_id}",
                f"{email_env} not set",
            )
            continue
        probe_login(
            api_url=api_url,
            label=label,
            description=description,
            email=email,
            password=(os.getenv(password_env) or None),
            customer_id=customer_id,
            require_active=label in args.require_active,
            results=results,
        )

    print("\n" + "-" * 78)
    print("Reminders that this script CANNOT check for you:")
    print("  * BYPASS_EMAILS on the STAGING Railway environment must no longer")
    print("    contain the multi-contract customer, or his 200 / 'active' proves")
    print("    only that the bypass works — not that the lockout is fixed.")
    print("  * `railway logs` must show the untruncated contract-count and")
    print("    per-contract lines, plus the ERROR records for a missing")
    print("    productSubscriberStatus, a createdAt-derived paid_through, an")
    print("    underivable paid_through, and an unfollowable next page.")

    results.summary()
    return 1 if results.failed else 0


if __name__ == "__main__":
    sys.exit(main())
