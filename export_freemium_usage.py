#!/usr/bin/env python3
"""
Export freemium usage data from MC ChatMaster.

Authenticates against the admin API and downloads free-tier usage data
as CSV or JSON. Follows the project's API-based script pattern.

Usage:
    python3 export_freemium_usage.py
    python3 export_freemium_usage.py --format json
    python3 export_freemium_usage.py --start-date 2025-01-01 --end-date 2025-06-30
    python3 export_freemium_usage.py --output /path/to/report.csv

Environment variables:
    ADMIN_EMAIL     - Admin login email (required)
    ADMIN_PASSWORD  - Admin login password (required)
    API_URL         - Backend URL (default: https://mcpress-chatbot-production.up.railway.app)
"""

import argparse
import json
import os
import sys
from datetime import date

import requests


DEFAULT_API_URL = "https://mcpress-chatbot-production.up.railway.app"


def authenticate(api_url, email, password):
    """Authenticate against the admin login endpoint and return access token."""
    try:
        response = requests.post(
            f"{api_url}/api/admin/login",
            json={"email": email, "password": password},
            timeout=30
        )
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: Could not reach {api_url} - {e}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Connection error: Request to {api_url} timed out")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        sys.exit(1)

    if response.status_code != 200:
        detail = ""
        try:
            detail = response.json().get("detail", response.text)
        except (ValueError, AttributeError):
            detail = response.text
        print(f"Authentication failed: {response.status_code} - {detail}")
        sys.exit(1)

    try:
        token = response.json().get("access_token")
    except (ValueError, AttributeError):
        print("Authentication failed: Could not parse response")
        sys.exit(1)

    if not token:
        print("Authentication failed: No access_token in response")
        sys.exit(1)

    return token


def export_data(api_url, token, fmt, start_date, end_date):
    """Call the freemium export endpoint and return the response."""
    params = {"format": fmt}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{api_url}/api/admin/freemium-export",
            params=params,
            headers=headers,
            timeout=60
        )
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: Could not reach {api_url} - {e}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Connection error: Export request timed out")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        sys.exit(1)

    if response.status_code == 401:
        print("Export failed: Authentication token expired or invalid")
        sys.exit(1)

    if response.status_code != 200:
        detail = ""
        try:
            detail = response.json().get("detail", response.text)
        except (ValueError, AttributeError):
            detail = response.text
        print(f"Export failed: {response.status_code} - {detail}")
        sys.exit(1)

    return response


def count_users(response_body, fmt):
    """Parse the response body and return the user count."""
    if fmt == "json":
        try:
            data = json.loads(response_body)
            return len(data.get("users", []))
        except (ValueError, TypeError):
            return 0
    else:
        # CSV: count non-empty, non-comment lines after the header
        lines = response_body.split("\n")
        count = 0
        header_seen = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if not header_seen:
                header_seen = True
                continue
            count += 1
        return count


def main():
    parser = argparse.ArgumentParser(
        description="Export freemium usage data from MC ChatMaster"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Export format (default: csv)"
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Filter start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Filter end date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: freemium-usage-export-{today}.{format})"
    )
    args = parser.parse_args()

    # Read environment variables
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    api_url = os.environ.get("API_URL", DEFAULT_API_URL)

    if not email or not password:
        print("Error: ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required")
        sys.exit(1)

    # Determine output file path
    fmt = args.format
    if args.output:
        output_path = args.output
    else:
        today = date.today().isoformat()
        output_path = f"freemium-usage-export-{today}.{fmt}"

    # Authenticate
    token = authenticate(api_url, email, password)

    # Export data
    response = export_data(api_url, token, fmt, args.start_date, args.end_date)

    # Save to file
    body = response.text
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(body)

    # Count users and print summary
    user_count = count_users(body, fmt)
    print(f"Exported {user_count} users to {output_path}")


if __name__ == "__main__":
    main()
