"""
Background scheduler for automatic statistics snapshot capture
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from persistence.database_async import AsyncSessionLocal
from core.stats.snapshot_service_async import SnapshotServiceAsync
from persistence.models.stats import SnapshotGranularity


logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


async def capture_hourly_snapshots():
    """Capture hourly snapshots for platform and all tenants"""
    logger.info("Starting hourly snapshot capture...")
    
    async with AsyncSessionLocal() as db:
        try:
            snapshot_service = SnapshotServiceAsync(db)
            
            # Capture platform snapshot
            platform_snapshot = await snapshot_service.capture_platform_snapshot(
                SnapshotGranularity.HOURLY
            )
            logger.info(f"Captured platform hourly snapshot: {platform_snapshot.id}")
            
            # Capture tenant snapshots
            tenant_snapshots = await snapshot_service.capture_tenant_snapshots(
                SnapshotGranularity.HOURLY
            )
            logger.info(f"Captured {len(tenant_snapshots)} tenant hourly snapshots")
            
        except Exception as e:
            logger.error(f"Error capturing hourly snapshots: {e}", exc_info=True)


async def capture_daily_snapshots():
    """Capture daily snapshots for platform and all tenants"""
    logger.info("Starting daily snapshot capture...")
    
    async with AsyncSessionLocal() as db:
        try:
            snapshot_service = SnapshotServiceAsync(db)
            
            # Capture platform snapshot
            platform_snapshot = await snapshot_service.capture_platform_snapshot(
                SnapshotGranularity.DAILY
            )
            logger.info(f"Captured platform daily snapshot: {platform_snapshot.id}")
            
            # Capture tenant snapshots
            tenant_snapshots = await snapshot_service.capture_tenant_snapshots(
                SnapshotGranularity.DAILY
            )
            logger.info(f"Captured {len(tenant_snapshots)} tenant daily snapshots")
            
        except Exception as e:
            logger.error(f"Error capturing daily snapshots: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    logger.info("Starting statistics snapshot scheduler...")
    
    scheduler = AsyncIOScheduler()
    
    # Schedule hourly snapshots (every hour at :00)
    scheduler.add_job(
        capture_hourly_snapshots,
        trigger=CronTrigger(minute=0),
        id='hourly_snapshots',
        name='Capture hourly statistics snapshots',
        replace_existing=True
    )
    
    # Schedule daily snapshots (midnight UTC)
    scheduler.add_job(
        capture_daily_snapshots,
        trigger=CronTrigger(hour=0, minute=0),
        id='daily_snapshots',
        name='Capture daily statistics snapshots',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully")
    
    # Log next run times
    for job in scheduler.get_jobs():
        logger.info(f"Job '{job.name}' - Next run: {job.next_run_time}")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is None:
        logger.warning("Scheduler not running")
        return
    
    logger.info("Stopping statistics snapshot scheduler...")
    scheduler.shutdown(wait=True)
    scheduler = None
    logger.info("Scheduler stopped")


def get_scheduler_status():
    """Get scheduler status and job information"""
    if scheduler is None:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }
