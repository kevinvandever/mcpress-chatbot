"""
Freemium Usage Export API endpoint.

Provides admin-authenticated CSV/JSON export of free-tier usage data
from the free_usage_tracking table, including funnel summary statistics.
"""

import os
import csv
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

try:
    from auth_routes import get_current_user
except ImportError:
    from backend.auth_routes import get_current_user


router = APIRouter(prefix="/api/admin", tags=["admin"])

# Module-level database URL and pool (lazy initialization)
_database_url: Optional[str] = None
_pool: Optional[asyncpg.Pool] = None


def set_database_url(url: str) -> None:
    """Set the database URL for lazy pool creation. Called from main.py at startup."""
    global _database_url
    _database_url = url


async def _get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
    global _pool
    if _pool is None:
        if not _database_url:
            raise HTTPException(
                status_code=503,
                detail="Database not configured for freemium export",
            )
        _pool = await asyncpg.create_pool(
            _database_url,
            statement_cache_size=0,  # Fix for pgbouncer compatibility
        )
    return _pool


def _read_limit() -> int:
    """
    Read FREE_QUESTION_LIMIT from env. Default 8 on missing or invalid value.
    Same pattern as UsageGate._read_limit().
    """
    raw = os.getenv("FREE_QUESTION_LIMIT")
    if raw is None:
        return 8
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 8


def _parse_date(value: str, param_name: str) -> date:
    """
    Parse and validate an ISO 8601 date string (YYYY-MM-DD).
    Raises HTTP 400 on invalid format.
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format. Expected YYYY-MM-DD.",
        )


def _format_timestamp(dt: Optional[datetime]) -> str:
    """Format a datetime as ISO 8601 string."""
    if dt is None:
        return ""
    return dt.isoformat()


# --- Pure functions for testability (used by property tests) ---


def sort_users(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort user records by questions_used DESC, then last_question_at DESC.
    Pure function extracted for property-based testing.
    """
    return sorted(
        users,
        key=lambda u: (-(u.get("questions_used", 0)), _sort_key_timestamp(u.get("last_question_at"))),
    )


def _sort_key_timestamp(ts) -> float:
    """Convert a timestamp to a negative float for descending sort."""
    if ts is None:
        return float("inf")  # None sorts last
    if isinstance(ts, datetime):
        return -ts.timestamp()
    # If it's already a numeric value, negate it
    return -float(ts)


def compute_summary(users: List[Dict[str, Any]], questions_limit: int) -> Dict[str, Any]:
    """
    Compute funnel summary statistics from a list of user records.
    Pure function extracted for property-based testing.

    Each user dict must have a 'questions_used' key (int).
    """
    total = len(users)
    if total == 0:
        return {
            "total_free_users": 0,
            "reached_soft_warning": 0,
            "reached_strong_warning": 0,
            "reached_limit": 0,
            "average_questions_used": 0,
            "questions_limit": questions_limit,
        }

    soft_threshold = questions_limit - 2
    strong_threshold = questions_limit - 1
    limit_threshold = questions_limit

    reached_soft = sum(1 for u in users if u["questions_used"] >= soft_threshold)
    reached_strong = sum(1 for u in users if u["questions_used"] >= strong_threshold)
    reached_limit = sum(1 for u in users if u["questions_used"] >= limit_threshold)
    avg = round(sum(u["questions_used"] for u in users) / total, 1)

    return {
        "total_free_users": total,
        "reached_soft_warning": reached_soft,
        "reached_strong_warning": reached_strong,
        "reached_limit": reached_limit,
        "average_questions_used": avg,
        "questions_limit": questions_limit,
    }


def filter_users_by_date(
    users: List[Dict[str, Any]],
    start_date: Optional[date],
    end_date: Optional[date],
) -> List[Dict[str, Any]]:
    """
    Filter user records by created_at date range.
    Pure function extracted for property-based testing.

    Each user dict must have a 'created_at' key (datetime).
    start_date is inclusive, end_date is inclusive (through end of day).
    """
    if start_date is None and end_date is None:
        return users

    filtered = []
    for u in users:
        created = u.get("created_at")
        if created is None:
            continue

        # Normalize to date for comparison
        if isinstance(created, datetime):
            created_date = created.date()
        elif isinstance(created, date):
            created_date = created
        else:
            continue

        if start_date is not None and created_date < start_date:
            continue
        if end_date is not None and created_date > end_date:
            continue

        filtered.append(u)

    return filtered


# --- Endpoint ---


@router.get("/freemium-export")
async def export_freemium_usage(
    format: str = Query("csv", description="Output format: csv or json"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """
    Export free-tier usage data with funnel summary statistics.
    Requires admin authentication.
    """
    # Validate format
    if format not in ("csv", "json"):
        raise HTTPException(
            status_code=400,
            detail="Format must be 'csv' or 'json'",
        )

    # Parse and validate dates
    parsed_start: Optional[date] = None
    parsed_end: Optional[date] = None

    if start_date is not None:
        parsed_start = _parse_date(start_date, "start_date")
    if end_date is not None:
        parsed_end = _parse_date(end_date, "end_date")

    # Validate date range
    if parsed_start is not None and parsed_end is not None:
        if parsed_start > parsed_end:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before or equal to end_date.",
            )

    # Read current limit
    questions_limit = _read_limit()

    # Query database
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            # Build query with optional date filters
            query = """
                SELECT user_email, questions_used, created_at, last_question_at
                FROM free_usage_tracking
                WHERE ($1::date IS NULL OR created_at >= $1::date)
                  AND ($2::date IS NULL OR created_at <= ($2::date + INTERVAL '1 day' - INTERVAL '1 second'))
                ORDER BY questions_used DESC, last_question_at DESC
            """
            rows = await conn.fetch(query, parsed_start, parsed_end)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}",
        )

    # Convert rows to dicts
    users = [
        {
            "email": row["user_email"],
            "questions_used": row["questions_used"],
            "first_seen": _format_timestamp(row["created_at"]),
            "last_active": _format_timestamp(row["last_question_at"]),
        }
        for row in rows
    ]

    # Compute summary from raw data
    summary_input = [
        {"questions_used": row["questions_used"]}
        for row in rows
    ]
    summary = compute_summary(summary_input, questions_limit)

    # Return response in requested format
    if format == "json":
        return JSONResponse(
            content={"users": users, "summary": summary},
            media_type="application/json",
        )

    # CSV format
    today_str = date.today().strftime("%Y-%m-%d")
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["email", "questions_used", "first_seen", "last_active"])

    # User rows
    for user in users:
        writer.writerow([
            user["email"],
            user["questions_used"],
            user["first_seen"],
            user["last_active"],
        ])

    # Blank row separator
    writer.writerow([])

    # Summary rows with # prefix
    writer.writerow(["# Summary"])
    writer.writerow([f"# total_free_users", summary["total_free_users"]])
    writer.writerow([f"# reached_soft_warning", summary["reached_soft_warning"]])
    writer.writerow([f"# reached_strong_warning", summary["reached_strong_warning"]])
    writer.writerow([f"# reached_limit", summary["reached_limit"]])
    writer.writerow([f"# average_questions_used", summary["average_questions_used"]])
    writer.writerow([f"# questions_limit", summary["questions_limit"]])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=freemium-usage-export-{today_str}.csv",
        },
    )
