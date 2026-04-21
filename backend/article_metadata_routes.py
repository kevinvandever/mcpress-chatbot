"""
API routes for article metadata quality management.

Provides endpoints to trigger metadata backfill, monitor backfill runs,
list articles with poor metadata, and view metadata quality diagnostics.
All endpoints require admin authentication.

Feature: article-metadata-quality
"""

import logging
import uuid
from dataclasses import asdict
from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["article-metadata"])

# Service reference — set during startup via set_backfill_service()
_backfill_service = None


def set_backfill_service(service) -> None:
    """Set the MetadataBackfillService instance (called during app startup)."""
    global _backfill_service
    _backfill_service = service


def _get_service():
    if _backfill_service is None:
        raise HTTPException(status_code=503, detail="Backfill service not available")
    return _backfill_service


# Re-use the existing admin auth dependency
try:
    from auth_routes import get_current_user
except ImportError:
    from backend.auth_routes import get_current_user


@router.post("/api/articles/backfill-metadata")
async def trigger_backfill(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Start a metadata backfill process as a background task.

    Returns a run_id and status 'started'.
    Returns 409 if a backfill is already running.
    """
    service = _get_service()

    if service.is_running:
        raise HTTPException(
            status_code=409,
            detail="A metadata backfill is already in progress",
        )

    # Pre-generate run_id so we can return it immediately.
    # Create the initial record before the background task starts,
    # then let the background task update it on completion.
    run_id = str(uuid.uuid4())

    async def _run_backfill():
        try:
            result = await service.run_backfill(run_id=run_id)
            logger.info(
                "Background backfill completed: run_id=%s, status=%s",
                result.run_id,
                result.status,
            )
        except Exception as e:
            logger.error("Background backfill failed: %s", e)

    background_tasks.add_task(_run_backfill)

    return {"run_id": run_id, "status": "started"}


@router.get("/api/articles/backfill-metadata/{run_id}")
async def get_backfill_result(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get backfill run result by run_id."""
    service = _get_service()

    result = await service.get_run_by_id(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Backfill run '{run_id}' not found")

    # Convert datetime objects for JSON serialization
    for key in ("started_at", "completed_at"):
        if result.get(key):
            result[key] = result[key].isoformat()

    return result


@router.get("/api/articles/poor-metadata")
async def get_poor_metadata_articles(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List articles with poor metadata (numeric titles or unknown authors)."""
    service = _get_service()

    articles = await service.identify_poor_metadata_articles()

    return {
        "count": len(articles),
        "articles": articles,
    }


@router.get("/api/diagnostics/article-metadata")
async def get_metadata_diagnostics(
    detailed: bool = Query(default=False),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Return metadata quality statistics.

    Use ?detailed=true to get the full list of articles with poor metadata
    instead of a sample of up to 20.
    """
    service = _get_service()

    diagnostics = await service.get_diagnostics(detailed=detailed)

    return asdict(diagnostics)


@router.post("/api/articles/fix-urls")
async def fix_article_urls(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Fix malformed article_url values in the books table.

    Corrects 'ww.mcpressonline.com' → 'www.mcpressonline.com' typos.
    Returns count of URLs fixed.
    """
    service = _get_service()
    await service._ensure_pool()

    async with service.pool.acquire() as conn:
        # Find and fix bad URLs
        result = await conn.execute("""
            UPDATE books
            SET article_url = REPLACE(article_url, '://ww.mcpressonline.com', '://www.mcpressonline.com')
            WHERE article_url LIKE '%://ww.mcpressonline.com%'
              AND article_url NOT LIKE '%://www.mcpressonline.com%'
        """)
        fixed_count = int(result.split()[-1]) if result else 0

    logger.info("Fixed %d article URLs (ww. → www.)", fixed_count)
    return {"fixed_count": fixed_count, "detail": "Corrected ww.mcpressonline.com → www.mcpressonline.com"}
