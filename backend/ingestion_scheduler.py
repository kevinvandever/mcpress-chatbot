"""
Scheduler for automated monthly content ingestion.

Uses APScheduler to trigger an ingestion run on the 1st of each month at 3:00 AM UTC.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def setup_ingestion_scheduler(ingestion_service) -> AsyncIOScheduler:
    """Create scheduler with monthly cron job (1st of month, 3:00 AM UTC)."""
    scheduler = AsyncIOScheduler()

    async def _run_job():
        try:
            # Check if a run completed recently this month to avoid double-running
            current = await ingestion_service.get_current_run()
            if current and current.get("status") == "running":
                logger.info("Skipping scheduled run — one is already in progress")
                return
            logger.info("🗓️ Starting scheduled monthly ingestion run")
            await ingestion_service.run_ingestion()
        except Exception as e:
            logger.error(f"Scheduled ingestion run failed: {e}")

    scheduler.add_job(
        _run_job,
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="monthly_ingestion",
        name="Monthly Content Ingestion",
        replace_existing=True,
    )
    return scheduler


async def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Start the scheduler. Called from FastAPI startup event."""
    scheduler.start()
    logger.info("✅ Ingestion scheduler started (monthly on 1st at 03:00 UTC)")


async def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Graceful shutdown. Called from FastAPI shutdown event."""
    scheduler.shutdown(wait=False)
    logger.info("🛑 Ingestion scheduler stopped")
