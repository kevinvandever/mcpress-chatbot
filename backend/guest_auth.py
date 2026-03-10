"""
Guest user authentication for public-facing features

This module provides lightweight authentication for guest users accessing
code upload and chat features. Guest IDs are auto-generated UUIDs stored
in browser localStorage.

Private Beta Mode:
- Set GUEST_ACCESS_ENABLED=false to require admin login during testing
- Set GUEST_ACCESS_ENABLED=true (or omit) to allow public guest access

Future: This will be replaced with MCPress SSO token validation when
the app is integrated behind MCPressOnline authentication.
"""
import os
import uuid
import re
from fastapi import Header, HTTPException
from typing import Optional


def validate_guest_id(guest_id: str) -> bool:
    """
    Validate that guest_id is a valid UUID v4 format

    Args:
        guest_id: Guest user ID to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(guest_id))


async def get_guest_user_id(
    x_guest_user_id: Optional[str] = Header(None, description="Guest user ID (UUID)")
) -> str:
    """
    Extract and validate guest user ID from request header

    This is a lightweight auth mechanism for MVP testing. Guest IDs are
    auto-generated UUIDs stored in browser localStorage. No login required.

    Future: Replace with MCPress SSO token validation:
    - Validate MCPress JWT token instead of guest UUID
    - Extract user_id from MCPress token claims
    - Return MCPress user_id for quota tracking

    Args:
        x_guest_user_id: Guest user ID from X-Guest-User-Id header

    Returns:
        Validated guest user ID

    Raises:
        HTTPException: If guest ID is missing or invalid format
    """
    if not x_guest_user_id:
        raise HTTPException(
            status_code=401,
            detail="Guest user ID required. Please reload the application."
        )

    if not validate_guest_id(x_guest_user_id):
        raise HTTPException(
            status_code=401,
            detail="Invalid guest user ID format"
        )

    return x_guest_user_id


def is_guest_access_enabled() -> bool:
    """
    Check if guest access is enabled via environment variable

    Returns:
        True if GUEST_ACCESS_ENABLED is not set or is 'true' (case-insensitive)
        False if GUEST_ACCESS_ENABLED is 'false' (private beta mode)
    """
    env_value = os.getenv('GUEST_ACCESS_ENABLED', 'true').lower()
    return env_value in ('true', '1', 'yes', 'on')


def generate_guest_id() -> str:
    """
    Generate a new guest user ID

    Used by frontend on first visit to auto-create guest identity.

    Returns:
        New UUID v4 as string
    """
    return str(uuid.uuid4())
