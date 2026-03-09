"""
Debug endpoint to inspect raw Appstle API responses.
Temporary — remove after debugging.
"""
from fastapi import APIRouter, Query
import aiohttp
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/debug/appstle-check")
async def debug_appstle_check(email: str = Query(...)):
    """Return the raw Appstle API response for a given email."""
    appstle_api_url = os.getenv("APPSTLE_API_URL")
    appstle_api_key = os.getenv("APPSTLE_API_KEY")

    if not appstle_api_url or not appstle_api_key:
        return {"error": "Appstle env vars not configured",
                "APPSTLE_API_URL_set": bool(appstle_api_url),
                "APPSTLE_API_KEY_set": bool(appstle_api_key)}

    url = f"{appstle_api_url}/api/external/v2/subscription-contract-details/customers"
    headers = {"X-API-Key": appstle_api_key}
    params = {"email": email}

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, params=params) as resp:
                status_code = resp.status
                try:
                    body = await resp.json()
                except Exception:
                    body = await resp.text()

                return {
                    "appstle_url_called": url,
                    "params": params,
                    "response_status": status_code,
                    "response_body": body,
                }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
