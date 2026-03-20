#!/usr/bin/env python3
"""
Backfill author URLs from article Excel data.

Uploads export_subset_DMU_v2.xlsx to the backfill-author-urls endpoint
to populate author site_url values from article data.

Usage:
    python3 backfill_author_urls.py
    python3 backfill_author_urls.py --production
"""
import requests
import sys
import os

STAGING_URL = "https://mcpress-chatbot-staging.up.railway.app"
PRODUCTION_URL = "https://mcpress-chatbot-production.up.railway.app"
ARTICLE_EXCEL = "export_subset_DMU_v2.xlsx"


def main():
    # Default to staging, use --production flag for production
    api_url = PRODUCTION_URL if "--production" in sys.argv else STAGING_URL
    api_url = os.getenv("API_URL", api_url)

    print(f"Backfilling author URLs against: {api_url}")

    if not os.path.exists(ARTICLE_EXCEL):
        print(f"❌ File not found: {ARTICLE_EXCEL}")
        sys.exit(1)

    with open(ARTICLE_EXCEL, 'rb') as f:
        files = {'file': (ARTICLE_EXCEL, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(
            f"{api_url}/api/excel/backfill-author-urls",
            files=files,
            timeout=120
        )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Backfill complete:")
        print(f"   Mapping size: {data.get('mapping_size', 'N/A')}")
        print(f"   Authors checked: {data.get('authors_checked', 'N/A')}")
        print(f"   Authors updated: {data.get('authors_updated', 'N/A')}")
        print(f"   Authors not found: {data.get('authors_not_found', 'N/A')}")
    else:
        print(f"❌ Backfill failed: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
