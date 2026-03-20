"""
API routes for auto content ingestion.

Provides endpoints to trigger, monitor, and review ingestion runs.
All endpoints require admin authentication.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

# Service reference — set during startup via set_ingestion_service()
_ingestion_service = None


def set_ingestion_service(service) -> None:
    global _ingestion_service
    _ingestion_service = service


def _get_service():
    if _ingestion_service is None:
        raise HTTPException(status_code=503, detail="Ingestion service not available")
    return _ingestion_service


# Re-use the existing admin auth dependency
try:
    from auth_routes import get_current_user
except ImportError:
    from backend.auth_routes import get_current_user


@router.post("/trigger")
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Start an ingestion run as a background task. Returns 409 if one is already running."""
    service = _get_service()

    if service._running:
        raise HTTPException(status_code=409, detail="An ingestion run is already in progress")

    background_tasks.add_task(service.run_ingestion)
    return {"message": "Ingestion run started", "status": "running"}


@router.get("/status")
async def get_ingestion_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the current or most recent ingestion run status."""
    service = _get_service()
    run = await service.get_current_run()
    if not run:
        return {"status": "no_runs", "message": "No ingestion runs found"}
    # Convert datetime objects for JSON serialization
    for key in ("started_at", "completed_at"):
        if run.get(key):
            run[key] = run[key].isoformat()
    return run


@router.get("/history")
async def get_ingestion_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get paginated ingestion run history."""
    service = _get_service()
    runs = await service.get_run_history(limit=limit, offset=offset)
    # Convert datetime objects for JSON serialization
    for run in runs:
        for key in ("started_at", "completed_at"):
            if run.get(key):
                run[key] = run[key].isoformat()
    return {"runs": runs, "limit": limit, "offset": offset}
