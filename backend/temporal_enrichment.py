"""
Temporal Enrichment Service: Bulk RPG Era Metadata Population
Feature: temporal-rag-anti-hallucination

API endpoint to enrich existing books with rpg_era values based on publication_year.
Mapping rules:
  - year <= 2000  -> 'fixed-format'
  - 2001-2013     -> 'rpg-iv'
  - 2014-2019     -> 'free-form'
  - 2020+         -> 'fully-free'
  - None          -> 'general'

Skips books where rpg_era is already set to a non-'general' value.
Wraps all updates in a single transaction for atomicity.
"""

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException

try:
    import asyncpg
except ImportError:
    pass

router = APIRouter()


def year_to_era(year: int | None) -> str:
    """
    Map a publication year to an RPG era string.

    Args:
        year: Publication year as an integer, or None.

    Returns:
        One of: 'fixed-format', 'rpg-iv', 'free-form', 'fully-free', 'general'.
    """
    if year is None:
        return "general"
    if year <= 2000:
        return "fixed-format"
    if year <= 2013:
        return "rpg-iv"
    if year <= 2019:
        return "free-form"
    return "fully-free"


async def _get_pool():
    """Create a temporary connection pool for enrichment execution."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return await asyncpg.create_pool(database_url, min_size=1, max_size=2)


@router.post("/api/temporal/enrich")
async def enrich_temporal_metadata():
    """
    Bulk-enrich books with rpg_era based on publication_year.

    Reads all books, applies year->era mapping for books where rpg_era
    is 'general' or NULL, skips books with manually-set eras.
    All updates run in a single transaction for atomicity.

    Returns a JSON summary with counts per era category and total updated.
    """
    pool = None
    try:
        pool = await _get_pool()

        async with pool.acquire() as conn:
            # Read all books
            rows = await conn.fetch(
                "SELECT id, publication_year, rpg_era FROM books"
            )

            if not rows:
                return {
                    "status": "success",
                    "message": "No books found in database",
                    "total_books": 0,
                    "total_updated": 0,
                    "updates_by_era": {},
                    "skipped": 0,
                    "timestamp": datetime.now().isoformat(),
                }

            # Determine which books need updating
            updates = []  # list of (id, new_era)
            skipped = 0
            for row in rows:
                current_era = row["rpg_era"]
                # Skip books where rpg_era is already set to a non-general value
                if current_era is not None and current_era != "general":
                    skipped += 1
                    continue
                new_era = year_to_era(row["publication_year"])
                updates.append((row["id"], new_era))

            # Apply all updates in a single transaction
            era_counts: dict[str, int] = {}
            if updates:
                async with conn.transaction():
                    for book_id, new_era in updates:
                        await conn.execute(
                            "UPDATE books SET rpg_era = $1 WHERE id = $2",
                            new_era,
                            book_id,
                        )
                        era_counts[new_era] = era_counts.get(new_era, 0) + 1

            return {
                "status": "success",
                "message": f"Enriched {len(updates)} books with temporal metadata",
                "total_books": len(rows),
                "total_updated": len(updates),
                "updates_by_era": era_counts,
                "skipped": skipped,
                "timestamp": datetime.now().isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Temporal enrichment failed: {str(e)}",
        )
    finally:
        if pool:
            await pool.close()
