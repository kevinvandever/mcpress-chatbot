"""
Code Upload Cleanup Scheduler
Story: STORY-006
Created: 2025-10-13

Background scheduler for automatic cleanup of expired files
"""

import asyncio
from datetime import datetime
from typing import Optional

try:
    from code_upload_service import CodeUploadService
except ImportError:
    from backend.code_upload_service import CodeUploadService


class CleanupScheduler:
    """
    Background scheduler for cleaning up expired files

    Runs cleanup tasks on a fixed interval:
    - Hourly: Cleanup expired files
    - Daily: Reset quotas, purge old deleted files
    """

    def __init__(self, service: CodeUploadService):
        """
        Initialize scheduler

        Args:
            service: CodeUploadService instance
        """
        self.service = service
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def cleanup_hourly(self):
        """Run hourly cleanup tasks"""
        print(f"⏰ [{datetime.now()}] Running hourly cleanup...")

        try:
            stats = await self.service.cleanup_expired_files()

            if stats['database_files_deleted'] > 0 or stats['storage_files_deleted'] > 0:
                print(f"✅ Cleanup complete:")
                print(f"   - Database: {stats['database_files_deleted']} files, {stats['database_bytes_freed']:,} bytes")
                print(f"   - Storage: {stats['storage_files_deleted']} files, {stats['storage_bytes_freed']:,} bytes")
                print(f"   - Sessions cleaned: {stats['sessions_cleaned']}")
            else:
                print("✅ Cleanup complete: No expired files found")

        except Exception as e:
            print(f"❌ Hourly cleanup failed: {e}")

    async def reset_quotas_daily(self):
        """Run daily quota reset (at midnight)"""
        print(f"🔄 [{datetime.now()}] Running daily quota reset...")

        try:
            async with self.service.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT reset_daily_quotas()
                """)

                print(f"✅ Daily quota reset complete: {result} users reset")

        except Exception as e:
            print(f"❌ Daily quota reset failed: {e}")

    async def purge_old_files_weekly(self):
        """Run weekly purge of old deleted files"""
        print(f"🗑️  [{datetime.now()}] Running weekly purge...")

        try:
            async with self.service.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT purge_old_deleted_files(7)
                """)

                print(f"✅ Weekly purge complete: {result} old files permanently deleted")

        except Exception as e:
            print(f"❌ Weekly purge failed: {e}")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        hour_counter = 0
        day_counter = 0

        while self.running:
            try:
                # Run hourly cleanup
                await self.cleanup_hourly()

                hour_counter += 1

                # Every 24 hours, run daily tasks
                if hour_counter % 24 == 0:
                    await self.reset_quotas_daily()
                    day_counter += 1

                # Every 7 days, run weekly tasks
                if day_counter % 7 == 0 and day_counter > 0:
                    await self.purge_old_files_weekly()

                # Wait 1 hour
                await asyncio.sleep(3600)  # 3600 seconds = 1 hour

            except asyncio.CancelledError:
                print("🛑 Scheduler cancelled")
                break
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                # Continue running even if one iteration fails
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def start(self):
        """Start the scheduler"""
        if self.running:
            print("⚠️  Scheduler already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        print("✅ Cleanup scheduler started (runs hourly)")

    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return

        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        print("🛑 Cleanup scheduler stopped")

    async def run_manual_cleanup(self):
        """Manually trigger cleanup (useful for testing)"""
        print("🔧 Manual cleanup triggered...")
        await self.cleanup_hourly()


# Global scheduler instance
_scheduler: Optional[CleanupScheduler] = None


def init_scheduler(service: CodeUploadService) -> CleanupScheduler:
    """
    Initialize global scheduler

    Args:
        service: CodeUploadService instance

    Returns:
        CleanupScheduler instance
    """
    global _scheduler
    _scheduler = CleanupScheduler(service)
    return _scheduler


def get_scheduler() -> CleanupScheduler:
    """Get global scheduler instance"""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler first.")
    return _scheduler


def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler"""
    if _scheduler:
        await _scheduler.stop()
