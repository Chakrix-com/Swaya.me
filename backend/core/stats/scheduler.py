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


_ADMIN_EMAIL = "meetnishant@gmail.com"


async def send_nightly_exam_emails():
    """Midnight batch: email detailed results to participants of all exams that
    have ended but haven't had participant emails sent yet.
    Sends a failure report to the admin if anything goes wrong."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from persistence.models.quiz import Quiz
    from features.quiz.exam_service_async import send_participant_results_emails
    from core.auth.email_service import send_email

    logger.info("Starting nightly exam participant email batch...")

    # quiz_id -> {"title": ..., "error": ..., "participant_failures": [...]}
    failures: dict = {}
    batch_error: str | None = None

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Quiz).filter(
                    Quiz.exam_end_at <= now,
                    Quiz.exam_participant_emails_sent == False,
                    Quiz.exam_session_id.isnot(None),
                )
            )
            quizzes = result.scalars().all()

            if not quizzes:
                logger.info("Nightly exam emails: no pending exams found")
                return

            logger.info(f"Nightly exam emails: processing {len(quizzes)} exam(s)")
            for quiz in quizzes:
                try:
                    participant_failures = await send_participant_results_emails(quiz.id)
                    quiz.exam_participant_emails_sent = True
                    if participant_failures:
                        failures[quiz.id] = {
                            "title": quiz.title,
                            "error": None,
                            "participant_failures": participant_failures,
                        }
                    logger.info(f"Participant emails done for quiz {quiz.id} "
                                f"({len(participant_failures)} failure(s))")
                except Exception as e:
                    err_str = str(e)
                    logger.error(f"Failed participant emails for quiz {quiz.id}: {err_str}", exc_info=True)
                    failures[quiz.id] = {
                        "title": getattr(quiz, "title", f"Quiz {quiz.id}"),
                        "error": err_str,
                        "participant_failures": [],
                    }

            await db.commit()
            logger.info("Nightly exam email batch complete")
    except Exception as e:
        batch_error = str(e)
        logger.error(f"Nightly exam email batch failed: {batch_error}", exc_info=True)

    # ── Send failure report if anything went wrong ────────────────────────────
    if not failures and not batch_error:
        return

    try:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        rows = ""
        for qid, info in failures.items():
            quiz_label = f"{info['title']} (id {qid})"
            if info["error"]:
                rows += f"""
<tr>
  <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;font-weight:600;color:#cf1322;">
    {quiz_label}
  </td>
  <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;color:#cf1322;">
    Quiz-level failure: {info['error']}
  </td>
</tr>"""
            for pf in info["participant_failures"]:
                rows += f"""
<tr>
  <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;color:#595959;">
    {quiz_label}
  </td>
  <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;color:#595959;">
    Participant {pf['email']}: {pf['error']}
  </td>
</tr>"""

        batch_row = ""
        if batch_error:
            batch_row = f"""
<tr>
  <td colspan="2" style="padding:10px 12px;background:#fff2f0;color:#cf1322;font-weight:600;">
    ⚠️ Batch-level failure (no quizzes processed): {batch_error}
  </td>
</tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <tr><td style="background:#cf1322;padding:20px 28px;">
    <div style="color:#fff;font-size:18px;font-weight:700;">Swaya.me — Nightly Email Batch: Failures</div>
    <div style="color:rgba(255,255,255,0.8);font-size:13px;margin-top:4px;">Run at {now_str}</div>
  </td></tr>
  <tr><td style="padding:24px 28px;">
    <p style="color:#1a1a1a;margin:0 0 16px;">The nightly exam results email batch completed with errors. Please investigate.</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #f0f0f0;border-radius:6px;overflow:hidden;">
      <tr style="background:#fafafa;">
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#8c8c8c;text-transform:uppercase;">Exam</th>
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#8c8c8c;text-transform:uppercase;">Error</th>
      </tr>
      {batch_row}{rows}
    </table>
  </td></tr>
</table>
</body></html>"""

        await send_email(
            subject=f"[Swaya.me] Nightly email batch failures — {now_str}",
            recipients=[_ADMIN_EMAIL],
            html_body=html,
        )
        logger.info(f"Failure report sent to {_ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"Could not send failure report email: {e}", exc_info=True)


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
    
    # Nightly exam participant results emails (midnight UTC)
    scheduler.add_job(
        send_nightly_exam_emails,
        trigger=CronTrigger(hour=0, minute=0),
        id='nightly_exam_emails',
        name='Send exam participant results emails (nightly batch)',
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
