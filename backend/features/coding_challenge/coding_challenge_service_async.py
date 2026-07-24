"""
Coding-challenge orchestration service — JWT invite mint/verify, email-OTP
verification (mirrors the existing exam OTP pattern), and startup reconciliation
for scheduled jobs that don't survive a backend restart on their own.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.security.jwt import create_access_token, decode_access_token
from persistence.models.quiz import (
    CodeWorkspace, CodeWorkspaceStatus, CodeSubmission, CodeSubmissionStatus,
)
from shared.exceptions.auth import InvalidTokenError, ExpiredTokenError
from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

_INTERRUPTED_MESSAGE = "interrupted by a backend restart, needs manual re-grade"


# ── JWT invite ───────────────────────────────────────────────────────────────

def create_invite_token(quiz_id: int, question_id: int, candidate_email: str,
                         expires_delta: Optional[timedelta] = None) -> str:
    """Signed invite link payload: quiz_id, question_id, candidate_email, exp."""
    return create_access_token(
        {"quiz_id": quiz_id, "question_id": question_id, "candidate_email": candidate_email.lower()},
        expires_delta=expires_delta or timedelta(days=7),
    )


def decode_invite_token(token: str) -> dict:
    """Decodes and validates a coding-challenge invite token's required claims."""
    try:
        payload = decode_access_token(token)
    except (InvalidTokenError, ExpiredTokenError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    for field in ("quiz_id", "question_id", "candidate_email", "jti"):
        if field not in payload:
            raise HTTPException(status_code=400, detail="Invalid invite link")
    return payload


# ── Email OTP verification (mirrors request_exam_otp / start_exam) ─────────

async def request_coding_challenge_otp(token_jti: str, candidate_email: str, redis) -> dict:
    """Generate + email a 6-digit OTP for the email already embedded in the invite JWT.
    Rate-limited to 3 requests per (invite, email) per 10 minutes."""
    from core.auth.email_service import send_email

    email_lower = candidate_email.lower()
    rate_key = f"coding_challenge_otp_rate:{token_jti}:{email_lower}"
    count = await redis.increment(rate_key)
    if count == 1:
        await redis.expire(rate_key, 600)
    if count > 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait 10 minutes.")

    otp = str(secrets.randbelow(900000) + 100000)
    otp_key = f"coding_challenge_otp:{token_jti}:{email_lower}"
    await redis.set_json(otp_key, {"otp": otp}, expire=600)

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto">
      <h2 style="color:#1677ff">Your Coding Challenge Verification Code</h2>
      <p>Use the code below to start your coding challenge:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:10px;text-align:center;
                  padding:20px;background:#f5f5f5;border-radius:8px;margin:20px 0">
        {otp}
      </div>
      <p style="color:#888;font-size:13px">This code expires in 10 minutes. Do not share it.</p>
    </div>
    """
    sent = await send_email(
        subject="Your coding challenge verification code",
        recipients=[candidate_email],
        html_body=html_body,
    )
    if not sent:
        # Transient SMTP failures happen — one immediate retry before failing the request.
        sent = await send_email(
            subject="Your coding challenge verification code",
            recipients=[candidate_email],
            html_body=html_body,
        )
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="Could not send the verification code right now. Please try again in a moment.",
        )
    return {"sent": True}


async def verify_coding_challenge_otp(token_jti: str, candidate_email: str, otp: str, redis) -> bool:
    """Compare + delete (single-use), mirrors start_exam's OTP verification."""
    email_lower = candidate_email.lower()
    otp_key = f"coding_challenge_otp:{token_jti}:{email_lower}"
    stored = await redis.get_json(otp_key)
    if not stored or stored.get("otp") != otp:
        return False
    await redis.delete(otp_key)
    return True


# ── Workspace lifetime cap (scheduled at /start time) ───────────────────────

def lifetime_cap_job_id(coder_workspace_name: str) -> str:
    """Deterministic job ID so a job can be found/cancelled/rescheduled without a
    separate stored column."""
    return f"coding-challenge-lifetime-cap:{coder_workspace_name}"


async def reap_abandoned_workspace(workspace_id: int) -> None:
    """Scheduled job callback: force-deletes a workspace that hasn't reached
    `submitted` by its hard lifetime cap, marking it `abandoned`."""
    from persistence.database_async import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        workspace = await db.get(CodeWorkspace, workspace_id)
        if not workspace:
            logger.warning("reap_abandoned_workspace: workspace %s not found", workspace_id)
            return
        if workspace.status != CodeWorkspaceStatus.ACTIVE:
            # already submitted/abandoned/destroyed by the time this fired — nothing to do
            return
        try:
            await coder_client.delete_workspace(workspace.coder_workspace_name)
        except Exception as e:
            logger.warning("reap_abandoned_workspace: delete_workspace(%s) failed: %s",
                            workspace.coder_workspace_name, e)
        workspace.status = CodeWorkspaceStatus.ABANDONED
        workspace.destroyed_at = datetime.utcnow()
        await db.commit()


def schedule_lifetime_cap_job(workspace_id: int, coder_workspace_name: str, fire_at: datetime) -> None:
    """Schedules (or reschedules) the hard-lifetime-cap DateTrigger job."""
    from apscheduler.triggers.date import DateTrigger
    from core.stats import scheduler as stats_scheduler

    if not stats_scheduler.scheduler:
        logger.warning("schedule_lifetime_cap_job: scheduler not running, skipping")
        return
    stats_scheduler.scheduler.add_job(
        reap_abandoned_workspace,
        trigger=DateTrigger(run_date=fire_at),
        args=[workspace_id],
        id=lifetime_cap_job_id(coder_workspace_name),
        replace_existing=True,
        misfire_grace_time=300,
    )


def cancel_lifetime_cap_job(coder_workspace_name: str) -> None:
    """Cancels the lifetime-cap job once grading has completed (no longer needed)."""
    from core.stats import scheduler as stats_scheduler

    if not stats_scheduler.scheduler:
        return
    job_id = lifetime_cap_job_id(coder_workspace_name)
    try:
        stats_scheduler.scheduler.remove_job(job_id)
    except Exception:
        pass  # already fired/removed — nothing to do


# ── Startup reconciliation (survives a backend restart between scheduling and firing) ──

async def reconcile_on_startup(db: AsyncSession) -> dict:
    """
    Run once during lifespan startup, after the scheduler itself has started:
    - Any code_workspace still `active` whose lifetime deadline has passed (or is
      close) gets its reap job re-scheduled (fired immediately if already overdue).
    - Any code_submission stuck at `queued`/`grading` is marked `failed` with a
      clear "interrupted by a backend restart" message — never silently re-run,
      since the underlying workspace may already be mid-teardown or partially
      executed against.
    Returns a small summary dict for startup logging.
    """
    now = datetime.utcnow()
    lifetime_seconds = settings.coder.workspace_max_lifetime_seconds

    result = await db.execute(
        select(CodeWorkspace).where(CodeWorkspace.status == CodeWorkspaceStatus.ACTIVE)
    )
    active_workspaces = result.scalars().all()
    rescheduled = 0
    for workspace in active_workspaces:
        deadline = workspace.created_at + timedelta(seconds=lifetime_seconds)
        fire_at = deadline if deadline > now else now
        schedule_lifetime_cap_job(workspace.id, workspace.coder_workspace_name, fire_at)
        rescheduled += 1

    result = await db.execute(
        select(CodeSubmission).where(
            CodeSubmission.status.in_([CodeSubmissionStatus.QUEUED, CodeSubmissionStatus.GRADING])
        )
    )
    stuck_submissions = result.scalars().all()
    for submission in stuck_submissions:
        submission.status = CodeSubmissionStatus.FAILED
        submission.error_message = _INTERRUPTED_MESSAGE
    if stuck_submissions:
        await db.commit()

    summary = {
        "lifetime_cap_jobs_rescheduled": rescheduled,
        "stuck_submissions_marked_failed": len(stuck_submissions),
    }
    logger.info("coding_challenge reconcile_on_startup: %s", summary)
    return summary
