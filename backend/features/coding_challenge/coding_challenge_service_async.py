"""
Coding-challenge orchestration service — JWT invite mint/verify, email-OTP
verification (mirrors the existing exam OTP pattern), and startup reconciliation
for scheduled jobs that don't survive a backend restart on their own.
"""
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.security.jwt import create_access_token, decode_access_token
from persistence.models.quiz import (
    CodeWorkspace, CodeWorkspaceStatus, CodeSubmission, CodeSubmissionStatus, Question,
)
from shared.exceptions.auth import InvalidTokenError, ExpiredTokenError
from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

_INTERRUPTED_MESSAGE = "interrupted by a backend restart, needs manual re-grade"


# ── JWT invite ───────────────────────────────────────────────────────────────

def create_invite_token(quiz_id: int, question_id: int, candidate_email: str,
                         attempt_number: int = 1,
                         expires_delta: Optional[timedelta] = None) -> str:
    """Signed invite link payload: quiz_id, question_id, candidate_email, attempt_number, exp."""
    return create_access_token(
        {
            "quiz_id": quiz_id, "question_id": question_id, "candidate_email": candidate_email.lower(),
            "attempt_number": attempt_number,
        },
        expires_delta=expires_delta or timedelta(days=7),
    )


def decode_invite_token(token: str) -> dict:
    """Decodes and validates a coding-challenge invite token's required claims.
    attempt_number defaults to 1 for links minted before this claim existed —
    every invite already sent keeps working unchanged."""
    try:
        payload = decode_access_token(token)
    except (InvalidTokenError, ExpiredTokenError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    for field in ("quiz_id", "question_id", "candidate_email", "jti"):
        if field not in payload:
            raise HTTPException(status_code=400, detail="Invalid invite link")
    payload.setdefault("attempt_number", 1)
    return payload


_GITHUB_URL_RE = re.compile(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$")
_FALLBACK_PROBLEM_STATEMENT = (
    "Could not fetch the problem statement README from the starter repo. "
    "Please open the repo link directly for instructions."
)


async def fetch_readme(git_repo_url: str) -> str:
    """
    Fetches the starter repo's README for display as the problem statement — plain
    httpx GET against raw.githubusercontent.com, no auth (public repos only, per
    scope). Tries main then master. Graceful fallback text if unreachable.
    """
    match = _GITHUB_URL_RE.search(git_repo_url.strip())
    if not match:
        return _FALLBACK_PROBLEM_STATEMENT
    owner, repo = match.group(1), match.group(2)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for branch in ("main", "master"):
            for filename in ("README.md", "README"):
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return resp.text
                except httpx.HTTPError:
                    continue
    return _FALLBACK_PROBLEM_STATEMENT


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


# ── Async workspace provisioning (scheduled by /start, mirrors run_grading_job) ──

def provision_job_id(workspace_id: int) -> str:
    """Deterministic job ID, same convention as lifetime_cap_job_id/grading's job id."""
    return f"coding-challenge-provision:{workspace_id}"


# ── swaya-submit-timer VS Code extension: session.json ─────────────────────

_SESSION_FILE_PATH = "/home/coder/.swaya/session.json"
# Absolute, not `~/.swaya/...` — write_file_to_workspace()'s relative-path branch
# resolves against ~/project (see its own docstring), which the PostToolUse hook
# auto-commits; a relative path here would put the invite token straight into
# the candidate's git history. /home/coder is confirmed as the real home dir
# from docker_container.workspace's own volume mount (container_path =
# "/home/coder" in main.tf), not assumed.


async def _write_session_file(workspace: CodeWorkspace, question: Optional[Question]) -> None:
    """
    Writes the swaya-submit-timer extension's session.json into the just-created
    workspace and chmod 600's it. Best-effort: a failure here logs a warning and
    returns rather than raising — the candidate's actual workspace access (the
    original browser tab) doesn't depend on this file existing, only the
    in-editor extension's convenience does.

    The invite token minted here doesn't need to be byte-identical to the
    candidate's original browser-tab link — confirmed /submit only reads
    quiz_id/question_id/candidate_email/attempt_number from the decoded
    payload, never compares jti (that's only used earlier, for OTP-flow Redis
    keys) — so a freshly-minted token with the same claims works identically
    for the extension's own /submit call.
    """
    try:
        invite_token = create_invite_token(
            workspace.quiz_id, workspace.question_id, workspace.candidate_email,
            workspace.attempt_number,
        )
        # Matches the exact pattern grading_service_async.py / coding_challenge.py
        # already use for building candidate-facing URLs from FRONTEND_URL.
        frontend_url = os.getenv("FRONTEND_URL", "https://www.swaya.me")
        session_data = {
            "apiBase": f"{frontend_url}/api/v1",
            "inviteToken": invite_token,
            "timeBudgetSeconds": question.time_budget_seconds if question else None,
            "createdAt": workspace.created_at.replace(tzinfo=timezone.utc).isoformat(),
        }
        await coder_client.write_file_to_workspace(
            workspace.coder_workspace_name, _SESSION_FILE_PATH, json.dumps(session_data),
        )
        await coder_client.exec_in_workspace(
            workspace.coder_workspace_name, f"chmod 600 {_SESSION_FILE_PATH}",
        )
    except Exception as e:
        logger.warning(
            "_write_session_file: failed for workspace %s: %s — extension will have "
            "no countdown/submit data, candidate's original tab is unaffected",
            workspace.coder_workspace_name, e,
        )


async def provision_workspace_job(workspace_id: int) -> None:
    """
    Scheduled job callback (fired via DateTrigger(run_date=utcnow()) immediately
    after /start returns its fast ack): does the actual `coder create` +
    wait_for_app_ready + mint_session_url work that /start used to do inline,
    which is what let nginx's proxy_read_timeout race a slow-but-successful
    provision under concurrency. Runs in its own DB session since it executes
    well after the request that scheduled it has already returned.
    """
    from persistence.database_async import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        workspace = await db.get(CodeWorkspace, workspace_id)
        if not workspace or workspace.status != CodeWorkspaceStatus.PROVISIONING:
            # Already handled (e.g. reconcile_on_startup already marked this
            # provision_failed after a restart) or a stale duplicate fire — nothing to do.
            logger.warning(
                "provision_workspace_job: workspace %s missing or not PROVISIONING, skipping",
                workspace_id,
            )
            return

        # ide_type is already validated against the (currently code_server-only)
        # supported set by /start before this row is ever created — see
        # _IDE_TEMPLATE_MAP_SETTING in broker/api/coding_challenge.py.
        template_name = settings.coder.code_server_template_name
        question = await db.get(Question, workspace.question_id)

        try:
            await coder_client.create_workspace(
                workspace.coder_workspace_name, template_name,
                question.git_repo_url or "" if question else "",
            )
            # coder create only confirms the agent connected, not that code-server
            # itself has finished starting inside the container — without this
            # wait, candidates hit a real "connection refused" 502 on first open
            # (confirmed live, same reasoning as the old inline /start flow).
            ready = await coder_client.wait_for_app_ready(workspace.coder_workspace_name)
            if not ready:
                logger.warning(
                    "provision_workspace_job: workspace %s not confirmed ready before "
                    "timeout, proceeding anyway", workspace.coder_workspace_name,
                )
            workspace_url, token_name = await coder_client.mint_session_url(
                workspace.coder_workspace_name, workspace.ide_type,
                settings.coder.url, settings.coder.service_account_username,
            )
        except Exception as e:
            logger.error(
                "provision_workspace_job: provisioning failed for workspace %s (%s): %s",
                workspace_id, workspace.coder_workspace_name, e,
            )
            workspace.status = CodeWorkspaceStatus.PROVISION_FAILED
            await db.commit()
            return

        workspace.status = CodeWorkspaceStatus.ACTIVE
        workspace.workspace_url = workspace_url
        workspace.coder_token_name = token_name
        # The candidate's time budget must anchor to when the workspace actually
        # became usable, not to when this row was first inserted (at /start time,
        # before provisioning even began) — otherwise slow/contended provisioning
        # would silently eat into their coding time. Mirrors the existing
        # reuse-terminal-row convention in /start (coding_challenge.py) that
        # already resets created_at when reprovisioning an abandoned/destroyed row.
        workspace.created_at = datetime.utcnow()
        await db.commit()
        await db.refresh(workspace)

        # Written with the just-committed created_at so the extension's countdown
        # deadline (createdAt + timeBudgetSeconds) matches exactly what the
        # original tab's own useCountdown computes — best-effort, doesn't block
        # or fail provisioning if it errors (see _write_session_file's docstring).
        await _write_session_file(workspace, question)

        lifetime_deadline = workspace.created_at + timedelta(
            seconds=settings.coder.workspace_max_lifetime_seconds
        )
        schedule_lifetime_cap_job(workspace.id, workspace.coder_workspace_name, lifetime_deadline)


def schedule_provision_job(workspace_id: int) -> None:
    """Schedules the async-provisioning job to fire effectively immediately."""
    from apscheduler.triggers.date import DateTrigger
    from core.stats import scheduler as stats_scheduler

    if not stats_scheduler.scheduler:
        logger.warning("schedule_provision_job: scheduler not running, workspace %s stuck", workspace_id)
        return
    stats_scheduler.scheduler.add_job(
        provision_workspace_job,
        trigger=DateTrigger(run_date=datetime.utcnow()),
        args=[workspace_id],
        id=provision_job_id(workspace_id),
        replace_existing=True,
    )


# ── Startup reconciliation (survives a backend restart between scheduling and firing) ──

async def reconcile_on_startup(db: AsyncSession) -> dict:
    """
    Run once during lifespan startup, after the scheduler itself has started:
    - Any code_workspace still `active` whose lifetime deadline has passed (or is
      close) gets its reap job re-scheduled (fired immediately if already overdue).
    - Any code_workspace still `provisioning` had its background provision_workspace_job
      killed along with the old process (APScheduler jobs don't survive a restart any
      more than the grading ones do) — marked `provision_failed` so it's never
      permanently stuck with nothing to poll toward; a retried /start cleanly reuses
      the row via the existing terminal-row-reuse path.
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
        select(CodeWorkspace).where(CodeWorkspace.status == CodeWorkspaceStatus.PROVISIONING)
    )
    stuck_workspaces = result.scalars().all()
    for workspace in stuck_workspaces:
        workspace.status = CodeWorkspaceStatus.PROVISION_FAILED
    if stuck_workspaces:
        await db.commit()

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
        "stuck_provisions_marked_failed": len(stuck_workspaces),
        "stuck_submissions_marked_failed": len(stuck_submissions),
    }
    logger.info("coding_challenge reconcile_on_startup: %s", summary)
    return summary
