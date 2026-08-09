#!/usr/bin/env python3
"""
Inspect raw Appstle subscription contract data for one or more emails.

Dumps the FULL step-2 payload with no truncation, then summarizes every
contract so we can see which date fields Appstle actually returns —
specifically whether a lastBillingDate-style field exists and whether
nextBillingDate survives on CANCELLED contracts.

Usage:
    export APPSTLE_API_URL="https://..."
    export APPSTLE_API_KEY="..."

    python3 inspect_appstle_contracts.py dave@shireyllc.com
    python3 inspect_appstle_contracts.py email1@x.com email2@y.com
    python3 inspect_appstle_contracts.py dave@shireyllc.com --save

Flags:
    --save    Write each full payload to appstle-payload-{email}.json

Note: output contains customer PII (emails, dates). Don't paste publicly.
The API key is never printed.
"""

import argparse
import json
import os
import sys

import requests

TIMEOUT = 30


def _die(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def step1_customer_ids(api_url, api_key, email):
    """Look up ALL customerIds for an email (not just the first)."""
    url = f"{api_url}/api/external/v2/subscription-contract-details/customers"
    try:
        resp = requests.get(
            url,
            headers={"X-API-Key": api_key},
            params={"email": email},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        _die(f"step 1 request failed for {email}: {exc}")

    if resp.status_code != 200:
        _die(f"step 1 returned {resp.status_code} for {email}: {resp.text[:300]}")

    try:
        data = resp.json()
    except ValueError as exc:
        _die(f"step 1 returned non-JSON for {email}: {exc}")

    # Normalize to a list of customer records
    if isinstance(data, list):
        customers = data
    elif isinstance(data, dict):
        customers = data.get("content", [])
        if not customers and data.get("customerId"):
            customers = [data]
    else:
        customers = []

    ids = []
    for c in customers:
        if isinstance(c, dict) and c.get("customerId") is not None:
            ids.append(c["customerId"])

    return ids, data


def step2_customer_detail(api_url, api_key, customer_id):
    """Fetch the full customer detail payload for a customerId."""
    url = f"{api_url}/api/external/v2/subscription-customers/{customer_id}"
    try:
        resp = requests.get(
            url, headers={"X-API-Key": api_key}, timeout=TIMEOUT
        )
    except requests.exceptions.RequestException as exc:
        _die(f"step 2 request failed for customerId={customer_id}: {exc}")

    if resp.status_code != 200:
        _die(
            f"step 2 returned {resp.status_code} for customerId={customer_id}: "
            f"{resp.text[:300]}"
        )

    try:
        return resp.json()
    except ValueError as exc:
        _die(f"step 2 returned non-JSON for customerId={customer_id}: {exc}")


# Date-ish keys we care about when hunting for a paid-through signal
DATE_KEYS_OF_INTEREST = [
    "nextBillingDate",
    "createdAt",
    "updatedAt",
    "lastBillingDate",
    "lastOrderDate",
    "lastPaymentDate",
    "startDate",
    "endDate",
    "cancelledAt",
    "pausedAt",
    "nextOrderDate",
]


def summarize_contract(idx, node):
    """Print the fields that matter for the paid-through decision."""
    print(f"    Contract [{idx}]")
    print(f"      status          : {node.get('status')}")

    for key in DATE_KEYS_OF_INTEREST:
        if key in node:
            print(f"      {key:<16}: {node.get(key)}")

    billing = node.get("billingPolicy")
    if billing:
        print(f"      billingPolicy   : {json.dumps(billing)}")
    else:
        print("      billingPolicy   : (absent)")

    # Surface any other keys so we don't miss a field we didn't think to look for
    known = set(DATE_KEYS_OF_INTEREST) | {"status", "billingPolicy"}
    others = sorted(k for k in node.keys() if k not in known)
    if others:
        print(f"      other keys      : {', '.join(others)}")


def summarize(email, customer_id, payload):
    print(f"  customerId: {customer_id}")
    print(f"    productSubscriberStatus: {payload.get('productSubscriberStatus')}")

    contracts = payload.get("subscriptionContracts") or {}
    nodes = contracts.get("nodes") or []
    page_info = contracts.get("pageInfo")

    print(f"    contract count : {len(nodes)}")
    print(f"    pageInfo       : {json.dumps(page_info) if page_info else '(absent)'}")

    if page_info and page_info.get("hasNextPage"):
        print("    *** hasNextPage is TRUE — contracts are paginated, "
              "more exist beyond this page ***")

    if not nodes:
        print("    (no contract nodes — customer-level status is the only signal)")
        return

    for i, node in enumerate(nodes):
        if isinstance(node, dict):
            summarize_contract(i, node)
        else:
            print(f"    Contract [{i}]: unexpected type {type(node)}")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect raw Appstle subscription contract data"
    )
    parser.add_argument("emails", nargs="+", help="Customer email(s) to inspect")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save each full payload to appstle-payload-{email}.json",
    )
    args = parser.parse_args()

    api_url = os.environ.get("APPSTLE_API_URL")
    api_key = os.environ.get("APPSTLE_API_KEY")

    if not api_url or not api_key:
        _die(
            "APPSTLE_API_URL and APPSTLE_API_KEY must be set.\n"
            "  export APPSTLE_API_URL=\"https://...\"\n"
            "  export APPSTLE_API_KEY=\"...\""
        )

    api_url = api_url.rstrip("/")

    for email in args.emails:
        print("=" * 72)
        print(f"EMAIL: {email}")
        print("=" * 72)

        customer_ids, step1_raw = step1_customer_ids(api_url, api_key, email)

        print(f"  step 1 returned {len(customer_ids)} customer record(s): {customer_ids}")
        if len(customer_ids) > 1:
            print("  *** MULTIPLE customerIds — current code only checks the first ***")
        if not customer_ids:
            print("  no customerId found — treated as no subscription")
            print()
            continue

        for cid in customer_ids:
            payload = step2_customer_detail(api_url, api_key, cid)
            summarize(email, cid, payload)

            if args.save:
                safe = email.replace("@", "_at_").replace("/", "_")
                fname = f"appstle-payload-{safe}-{cid}.json"
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, default=str)
                print(f"    saved full payload → {fname}")

            print()
            print("    --- FULL PAYLOAD ---")
            print(json.dumps(payload, indent=2, default=str))
            print()


if __name__ == "__main__":
    main()
