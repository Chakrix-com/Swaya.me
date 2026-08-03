"""
Coding Challenge API — authenticated host endpoints (invite, examiner review) and
the public candidate flow at /coding-challenge/{token}/...
"""
import hashlib
import html
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from shared.utils.redis_client import get_redis, RedisClient
from shared.utils.rate_limiter import limiter, get_user_id_key
from core.auth.dependencies import get_current_user, CurrentUser
from core.config.settings import settings
from persistence.models.quiz import (
    Quiz, QuizType, Question, QuestionType, CodeWorkspace, CodeWorkspaceStatus,
    CodeSubmission, CodeSubmissionStatus, CodingChallengeInvite, CodingResultVisibility,
)
from persistence.models.core import Tenant
from features.coding_challenge import coding_challenge_service_async as svc
from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["coding-challenge"])

_IDE_TEMPLATE_MAP_SETTING = {
    "code_server": "code_server_template_name",
}

# Kept in sync with the expires_delta passed to create_invite_token below —
# also used to derive "Expired" status for the pending-invites list, since
# the JWT itself carries no server-side record we could check instead.
INVITE_VALIDITY = timedelta(days=7)


class StartRequest(BaseModel):
    ide_type: str
    otp: str


class InviteRequest(BaseModel):
    candidate_emails: list[EmailStr] = Field(..., min_length=1, max_length=50)


class InviteResult(BaseModel):
    email: str
    invite_url: Optional[str] = None
    sent: bool = False
    error: Optional[str] = None


class InviteListItem(BaseModel):
    candidate_email: str
    invited_at: datetime
    email_sent: bool
    status: str  # "pending" | "expired" | "started"


class OtpRequestBody(BaseModel):
    """Empty body — the email being verified comes from the invite JWT itself,
    not a free-text field, unlike the exam OTP flow."""
    pass


async def _get_coding_challenge_question(db: AsyncSession, quiz_id: int) -> tuple[Quiz, Question]:
    """Looks up a quiz's single CODING_CHALLENGE question (one-problem-per-challenge,
    per the design's demo scope)."""
    result = await db.execute(select(Quiz).filter(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz or quiz.quiz_type != QuizType.CODING_CHALLENGE:
        raise HTTPException(status_code=404, detail="Coding-challenge quiz not found")

    result = await db.execute(
        select(Question).filter(
            Question.quiz_id == quiz_id, Question.question_type == QuestionType.CODING_CHALLENGE
        )
    )
    question = result.scalars().first()
    if not question:
        raise HTTPException(status_code=400, detail="Quiz has no coding-challenge question configured")
    return quiz, question


@router.post("/quizzes/{quiz_id}/coding-challenge/invite", response_model=list[InviteResult])
@limiter.limit("5/minute", key_func=get_user_id_key)
async def invite_candidate(
    request: Request,
    quiz_id: int,
    body: InviteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — mint a signed invite link per candidate and email it.
    Accepts a batch (1-50 emails); each is processed independently so one bad
    address can't fail the whole send. Also upserts a CodingChallengeInvite row
    per candidate — the invite JWT itself is stateless, so this is the only
    record of "who was invited" until (or unless) they actually start."""
    import os
    from core.auth.email_service import send_email

    quiz, question = await _get_coding_challenge_question(db, quiz_id)
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    tenant = await db.get(Tenant, quiz.tenant_id)
    tenant_name = tenant.name if tenant else "The hiring team"

    frontend_url = os.getenv("FRONTEND_URL", "https://www.swaya.me")

    # De-dupe case-insensitively, preserving first-seen casing for the email itself
    seen = set()
    emails = []
    for e in body.candidate_emails:
        key = e.lower()
        if key not in seen:
            seen.add(key)
            emails.append(e)

    safe_title = html.escape(quiz.title)
    safe_tenant = html.escape(tenant_name)
    minutes = question.time_budget_seconds // 60 if question.time_budget_seconds else None
    expiry_text = (datetime.utcnow() + INVITE_VALIDITY).strftime("%B %-d, %Y")

    results: list[InviteResult] = []
    for candidate_email in emails:
        candidate_email_lower = candidate_email.lower()

        # Re-invite gate: a host can grant another attempt once the current one is
        # over, but never while the candidate is still mid-attempt — force-closing a
        # live workspace under them would risk losing in-progress work. Blocked
        # per-candidate, not raised, so one blocked email in a batch never fails the
        # others (see the batch's own de-dupe/independent-processing note above).
        latest_result = await db.execute(
            select(CodeWorkspace)
            .filter(
                CodeWorkspace.quiz_id == quiz_id,
                CodeWorkspace.question_id == question.id,
                CodeWorkspace.candidate_email == candidate_email_lower,
            )
            .order_by(CodeWorkspace.attempt_number.desc())
            .limit(1)
        )
        latest_workspace = latest_result.scalar_one_or_none()
        if latest_workspace and latest_workspace.status in (CodeWorkspaceStatus.PROVISIONING, CodeWorkspaceStatus.ACTIVE):
            results.append(InviteResult(
                email=candidate_email,
                sent=False,
                error="Candidate has an attempt in progress — re-invite becomes available once they submit or it expires.",
            ))
            continue

        next_attempt_number = (latest_workspace.attempt_number + 1) if latest_workspace else 1
        token = svc.create_invite_token(
            quiz_id, question.id, candidate_email, attempt_number=next_attempt_number,
            expires_delta=INVITE_VALIDITY,
        )
        invite_url = f"{frontend_url}/c/{token}"

        time_chip = f"""
            <tr><td style="padding:10px 0;border-bottom:1px solid #f1f5f9;">
              <table cellpadding="0" cellspacing="0" border="0"><tr>
                <td style="width:28px;font-size:16px;vertical-align:middle;">&#9200;</td>
                <td style="font-size:13px;color:#334155;vertical-align:middle;">
                  <strong style="color:#0f172a;">{minutes} minutes</strong> to complete, starting once the workspace opens
                </td>
              </tr></table>
            </td></tr>""" if minutes else ""

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Coding challenge invite — {safe_title}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1e293b;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;padding:40px 16px 48px;">
<tr><td align="center">

<table width="560" cellpadding="0" cellspacing="0" border="0"
       style="max-width:560px;width:100%;border-radius:20px;overflow:hidden;
              box-shadow:0 4px 24px rgba(15,23,42,0.12);">

  <!-- ═══ HEADER ═══ -->
  <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#1d4ed8 100%);padding:28px 32px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td>
        <div style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;line-height:1;">
          swaya<span style="font-weight:300;color:rgba(255,255,255,0.7);">.me</span>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1.2px;margin-top:4px;">Coding Challenge Invite</div>
      </td>
    </tr></table>
  </td></tr>

  <!-- ═══ WHITE CARD BODY ═══ -->
  <tr><td style="background:#ffffff;padding:32px 32px 28px;">

    <p style="font-size:20px;margin:0 0 8px;color:#0f172a;font-weight:700;line-height:1.4;">
      You're invited to a coding challenge
    </p>
    <p style="font-size:14px;margin:0 0 24px;color:#475569;line-height:1.6;">
      <strong style="color:#0f172a;">{safe_tenant}</strong> has invited you to complete
      <strong style="color:#0f172a;">&ldquo;{safe_title}&rdquo;</strong> as part of their evaluation process.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">
      {time_chip}
      <tr><td style="padding:10px 0;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="width:28px;font-size:16px;vertical-align:middle;">&#128274;</td>
          <td style="font-size:13px;color:#334155;vertical-align:middle;">
            You'll verify your email with a one-time code before you start
          </td>
        </tr></table>
      </td></tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
      <tr><td align="center">
        <a href="{invite_url}"
           style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#ffffff;
                  text-decoration:none;padding:14px 40px;border-radius:999px;font-size:14px;
                  font-weight:700;letter-spacing:.3px;box-shadow:0 4px 14px rgba(29,78,216,0.35);">
          Start Coding Challenge &#8594;
        </a>
      </td></tr>
    </table>

    <p style="font-size:12px;color:#94a3b8;text-align:center;margin:0 0 4px;line-height:1.6;">
      This link expires on {expiry_text}.
    </p>
    <p style="font-size:11px;color:#cbd5e1;text-align:center;margin:0;line-height:1.6;word-break:break-all;">
      Trouble with the button? Paste this into your browser:<br/>{invite_url}
    </p>

  </td></tr>

  <!-- ═══ FOOTER ═══ -->
  <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td>
        <div style="font-size:18px;font-weight:900;color:#94a3b8;letter-spacing:-0.3px;">
          swaya<span style="font-weight:300;">.me</span>
        </div>
      </td>
      <td align="right">
        <p style="margin:0;font-size:11px;color:#94a3b8;line-height:1.7;text-align:right;">
          Questions? Reply to this email or contact {safe_tenant}.<br/>
          &copy; 2026 &nbsp;<a href="https://www.swaya.me" style="color:#64748b;text-decoration:none;">Swaya.me</a>
        </p>
      </td>
    </tr></table>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
        error = None
        try:
            sent = await send_email(
                subject=f"Coding Challenge invite — {quiz.title}",
                recipients=[candidate_email],
                html_body=html_body,
            )
        except Exception as e:
            logger.error("invite_candidate: send failed for %s: %s", candidate_email, e)
            sent = False
            error = "Email delivery failed"

        existing = await db.execute(
            select(CodingChallengeInvite).filter(
                CodingChallengeInvite.quiz_id == quiz_id,
                CodingChallengeInvite.question_id == question.id,
                CodingChallengeInvite.candidate_email == candidate_email_lower,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.email_sent = sent
            row.invited_by_user_id = current_user.user_id
            row.latest_invited_attempt_number = next_attempt_number
            row.updated_at = datetime.utcnow()  # force bump even if no other field changed
        else:
            db.add(CodingChallengeInvite(
                tenant_id=current_user.tenant_id,
                quiz_id=quiz_id,
                question_id=question.id,
                candidate_email=candidate_email_lower,
                invited_by_user_id=current_user.user_id,
                email_sent=sent,
                latest_invited_attempt_number=next_attempt_number,
            ))

        results.append(InviteResult(email=candidate_email, invite_url=invite_url, sent=sent, error=error))

    await db.commit()
    return results


@router.get("/quizzes/{quiz_id}/coding-challenge/invites", response_model=list[InviteListItem])
async def list_coding_challenge_invites(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Host-facing list of everyone ever invited to this challenge, with status
    derived at read time (never stored) so it can't drift out of sync:
    'started' if a CodeWorkspace exists for them, else 'expired' once past the
    invite's fixed validity window, else 'pending'."""
    quiz, question = await _get_coding_challenge_question(db, quiz_id)
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    invites_result = await db.execute(
        select(CodingChallengeInvite)
        .filter(
            CodingChallengeInvite.quiz_id == quiz_id,
            CodingChallengeInvite.question_id == question.id,
        )
        .order_by(CodingChallengeInvite.updated_at.desc())
    )
    invites = invites_result.scalars().all()

    started_result = await db.execute(
        select(CodeWorkspace.candidate_email).filter(
            CodeWorkspace.quiz_id == quiz_id,
            CodeWorkspace.question_id == question.id,
        )
    )
    started_emails = {e.lower() for e in started_result.scalars().all()}

    now = datetime.utcnow()
    items = []
    for inv in invites:
        if inv.candidate_email.lower() in started_emails:
            status = "started"
        elif now > inv.updated_at + INVITE_VALIDITY:
            status = "expired"
        else:
            status = "pending"
        items.append(InviteListItem(
            candidate_email=inv.candidate_email,
            invited_at=inv.updated_at,
            email_sent=inv.email_sent,
            status=status,
        ))
    return items


@router.get("/coding-challenge/{token}")
async def get_coding_challenge_info(token: str, db: AsyncSession = Depends(get_async_db)):
    """Public — decode the invite, fetch the problem statement, return IDE choices."""
    payload = svc.decode_invite_token(token)
    question = await db.get(Question, payload["question_id"])
    quiz = await db.get(Quiz, payload["quiz_id"])
    if not question or not quiz:
        raise HTTPException(status_code=404, detail="Coding challenge not found")

    problem_statement = await svc.fetch_readme(question.git_repo_url) if question.git_repo_url else ""
    tenant = await db.get(Tenant, quiz.tenant_id)
    return {
        "quiz_title": quiz.title,
        "tenant_name": tenant.name if tenant else None,
        "problem_statement": problem_statement,
        "candidate_email": payload["candidate_email"],
        "ide_choices": ["code_server"],
        "time_budget_seconds": question.time_budget_seconds,
        "git_repo_url": question.git_repo_url,
        "result_visibility": question.result_visibility.value if question.result_visibility else "hidden",
    }


@router.post("/coding-challenge/{token}/request-otp")
@limiter.limit("10/minute")
async def request_coding_challenge_otp(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
):
    """Public — send a 6-digit OTP to the email already embedded in the invite JWT."""
    payload = svc.decode_invite_token(token)
    return await svc.request_coding_challenge_otp(payload["jti"], payload["candidate_email"], redis)


def _utc_iso(dt: datetime) -> str:
    """created_at/updated_at columns are naive datetimes populated with
    datetime.utcnow() (see TimestampMixin) — plain .isoformat() on those omits
    any timezone marker, which browsers then parse as *local* time, not UTC.
    On a candidate whose timezone is ahead of UTC this makes a just-created
    workspace look hours old, instantly blowing past the countdown budget.
    Appending Z makes the UTC-ness explicit so Date parsing in JS is correct."""
    return dt.isoformat() + "Z"


def _effective_time_budget(question: Optional[Question]) -> int:
    """The host's configured time_budget_seconds can exceed the platform's hard
    workspace lifetime cap — the workspace gets force-destroyed at the cap
    regardless, so the candidate-facing countdown must never promise more time
    than that. Falls back to the cap alone if the host never set a budget."""
    cap = settings.coder.workspace_max_lifetime_seconds
    if question and question.time_budget_seconds:
        return min(question.time_budget_seconds, cap)
    return cap


def _derive_workspace_name(quiz_id: int, question_id: int, candidate_email: str, attempt_number: int = 1) -> str:
    """Deterministic per-(quiz, question, candidate, attempt) workspace name — this is
    what makes an invite link effectively single-use within its own attempt without the
    JWT itself needing to be one-time (a repeat /start reconnects to the same workspace,
    see idempotency check below). attempt_number is folded into the hash so a host-granted
    re-invite gets a genuinely distinct Coder resource name instead of colliding with the
    previous attempt's."""
    email_hash = hashlib.sha256(f"{candidate_email.lower()}:{attempt_number}".encode()).hexdigest()[:8]
    return f"cc-{quiz_id}-{question_id}-{email_hash}"


@router.post("/coding-challenge/{token}/start")
async def start_coding_challenge(
    token: str,
    body: StartRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
):
    """Public — verify OTP, check capacity, provision (or reconnect to) the
    candidate's own Coder workspace."""
    payload = svc.decode_invite_token(token)
    quiz_id, question_id, candidate_email, attempt_number = (
        payload["quiz_id"], payload["question_id"], payload["candidate_email"], payload["attempt_number"],
    )

    if body.ide_type not in _IDE_TEMPLATE_MAP_SETTING:
        raise HTTPException(status_code=400, detail="Invalid ide_type")

    otp_ok = await svc.verify_coding_challenge_otp(payload["jti"], candidate_email, body.otp, redis)
    if not otp_ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    # Idempotency check first: a returning candidate reconnects to their own
    # already-running workspace rather than provisioning a second one. Scoped to
    # this specific attempt — a link for attempt 2 must never resolve to attempt 1's
    # (already-terminal) workspace row.
    result = await db.execute(
        select(CodeWorkspace).filter(
            CodeWorkspace.quiz_id == quiz_id,
            CodeWorkspace.question_id == question_id,
            CodeWorkspace.candidate_email == candidate_email,
            CodeWorkspace.attempt_number == attempt_number,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.status == CodeWorkspaceStatus.SUBMITTED:
        # A candidate who already submitted and revisits their invite link (closed
        # tab, browser crash, etc.) must never fall through to create_workspace
        # below — the deterministic workspace name is still in use by the now-
        # destroyed-but-recorded workspace, so a second create collides and 500s.
        # There's nothing left for them to do here regardless.
        raise HTTPException(status_code=409, detail="You've already submitted this challenge.")
    if existing and existing.status == CodeWorkspaceStatus.ACTIVE:
        # mint_session_url derives a deterministic token name from the workspace name
        # (see Workspace isolation), so re-minting for a returning candidate without
        # revoking the still-live token from their first /start collides with
        # "a token with this name already exists" — found live via a real candidate
        # hitting this exact path (their second /start on an already-active
        # workspace), which burned their one-time OTP on the crash with no recovery.
        if existing.coder_token_name:
            try:
                await coder_client.revoke_token(existing.coder_token_name)
            except Exception as e:
                logger.warning("start: revoke_token(%s) failed before re-mint: %s", existing.coder_token_name, e)
        workspace_url, token_name = await coder_client.mint_session_url(
            existing.coder_workspace_name, body.ide_type, settings.coder.url,
            settings.coder.service_account_username,
        )
        existing.workspace_url = workspace_url
        existing.coder_token_name = token_name
        await db.commit()
        question = await db.get(Question, question_id)
        return {
            "status": "active",
            "workspace_url": workspace_url,
            "workspace_created_at": _utc_iso(existing.created_at),
            "effective_time_budget_seconds": _effective_time_budget(question),
        }

    if existing and existing.status == CodeWorkspaceStatus.PROVISIONING:
        # A provisioning job is already in flight for this attempt (or, if the
        # backend restarted mid-job, reconcile_on_startup will already have flipped
        # this to PROVISION_FAILED before we'd ever see PROVISIONING here again) —
        # nothing to (re)start, just tell the frontend to poll /status.
        question = await db.get(Question, question_id)
        return {
            "status": "provisioning",
            "workspace_created_at": _utc_iso(existing.created_at),
            "effective_time_budget_seconds": _effective_time_budget(question),
        }

    # Concurrency cap — checked before provisioning a genuinely new workspace.
    result = await db.execute(
        select(func.count()).select_from(CodeWorkspace).filter(
            CodeWorkspace.status.in_([CodeWorkspaceStatus.PROVISIONING, CodeWorkspaceStatus.ACTIVE])
        )
    )
    active_count = result.scalar_one()
    if active_count >= settings.coder.max_concurrent_workspaces:
        raise HTTPException(status_code=429, detail="Sandbox is at capacity, please try again shortly")

    question = await db.get(Question, question_id)
    quiz = await db.get(Quiz, quiz_id)
    if not question or not quiz:
        raise HTTPException(status_code=404, detail="Coding challenge not found")

    workspace_name = _derive_workspace_name(quiz_id, question_id, candidate_email, attempt_number)

    if existing and existing.coder_token_name:
        # Reprovisioning a terminal (abandoned/destroyed/provision_failed) attempt:
        # delete_workspace is just `coder delete`, which does not revoke the
        # workspace's API token — the token name is deterministic (derived from
        # workspace_name), so a fresh mint later (inside the background job) would
        # collide with the still-existing one from the prior attempt. Same
        # "revoke before re-mint" rule as the reconnect branch above.
        try:
            await coder_client.revoke_token(existing.coder_token_name)
        except Exception as e:
            logger.warning("start: revoke_token(%s) failed before reprovision re-mint: %s",
                            existing.coder_token_name, e)

    # Provisioning itself (coder create + wait_for_app_ready + mint_session_url) no
    # longer happens inline here — it's a fully-synchronous, 70-150s+ chain under
    # concurrency that used to race nginx's proxy_read_timeout, giving a candidate a
    # false failure for a workspace that actually succeeded moments later (confirmed
    # via coding_challenge_concurrency_check.py). Instead: persist a PROVISIONING
    # row and return immediately; provision_workspace_job does the real work in the
    # background, and the frontend polls /status for readiness.
    if existing:
        # `existing` here is a terminal-but-not-SUBMITTED row (abandoned/destroyed/
        # provision_failed) — both coder_workspace_name and (quiz_id, question_id,
        # candidate_email, attempt_number) are uniquely constrained, so a fresh
        # INSERT for the same attempt always collides. Reuse the row in place.
        workspace = existing
        workspace.ide_type = body.ide_type
        workspace.coder_token_name = None
        workspace.status = CodeWorkspaceStatus.PROVISIONING
        workspace.workspace_url = None
        workspace.created_at = datetime.utcnow()
        workspace.destroyed_at = None
    else:
        workspace = CodeWorkspace(
            tenant_id=quiz.tenant_id,
            quiz_id=quiz_id,
            question_id=question_id,
            candidate_email=candidate_email,
            attempt_number=attempt_number,
            ide_type=body.ide_type,
            coder_workspace_name=workspace_name,
            status=CodeWorkspaceStatus.PROVISIONING,
        )
        db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    svc.schedule_provision_job(workspace.id)

    return {
        "status": "provisioning",
        "workspace_created_at": _utc_iso(workspace.created_at),
        "effective_time_budget_seconds": _effective_time_budget(question),
    }


@router.post("/coding-challenge/{token}/submit")
async def submit_coding_challenge(
    token: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Public — fast, idempotent. Only revoke_token happens synchronously; everything
    else (test execution, transcript harvest, AI scoring) is a scheduled job."""
    from apscheduler.triggers.date import DateTrigger
    from core.stats import scheduler as stats_scheduler
    from features.coding_challenge.grading_service_async import run_grading_job

    payload = svc.decode_invite_token(token)
    quiz_id, question_id, candidate_email, attempt_number = (
        payload["quiz_id"], payload["question_id"], payload["candidate_email"], payload["attempt_number"],
    )

    result = await db.execute(
        select(CodeWorkspace).filter(
            CodeWorkspace.quiz_id == quiz_id,
            CodeWorkspace.question_id == question_id,
            CodeWorkspace.candidate_email == candidate_email,
            CodeWorkspace.attempt_number == attempt_number,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found — call /start first")

    # Idempotency check: a second /submit for an already-submitted workspace returns
    # the existing status instead of re-revoking and re-scheduling a second grading job.
    result = await db.execute(
        select(CodeSubmission).filter(CodeSubmission.workspace_id == workspace.id)
    )
    existing_submission = result.scalar_one_or_none()
    if existing_submission:
        return {"status": existing_submission.status.value}

    # The one synchronous, load-bearing call: this is the actual mechanism behind
    # "no further edits from this instant".
    if workspace.coder_token_name:
        try:
            await coder_client.revoke_token(workspace.coder_token_name)
        except Exception as e:
            logger.warning("submit: revoke_token(%s) failed: %s", workspace.coder_token_name, e)

    workspace.status = CodeWorkspaceStatus.SUBMITTED
    workspace.submitted_at = datetime.utcnow()

    submission = CodeSubmission(
        workspace_id=workspace.id,
        question_id=question_id,
        status=CodeSubmissionStatus.QUEUED,
        submitted_at=datetime.utcnow(),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    if stats_scheduler.scheduler:
        stats_scheduler.scheduler.add_job(
            run_grading_job,
            trigger=DateTrigger(run_date=datetime.utcnow()),
            args=[submission.id],
            id=f"coding-challenge-grading:{submission.id}",
            replace_existing=True,
        )

    return {"status": "queued"}


@router.get("/coding-challenge/{token}/status")
async def get_coding_challenge_status(token: str, db: AsyncSession = Depends(get_async_db)):
    """Public — candidate-facing polling endpoint. Frontend polls this every few
    seconds (capped at a max poll duration client-side) until it reaches a terminal
    status."""
    payload = svc.decode_invite_token(token)

    result = await db.execute(
        select(CodeWorkspace).filter(
            CodeWorkspace.quiz_id == payload["quiz_id"],
            CodeWorkspace.question_id == payload["question_id"],
            CodeWorkspace.candidate_email == payload["candidate_email"],
            CodeWorkspace.attempt_number == payload["attempt_number"],
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found — call /start first")

    if workspace.status == CodeWorkspaceStatus.PROVISION_FAILED:
        # Distinct from "not_submitted" so the frontend stops polling and shows a
        # real error + retry action, instead of waiting forever for a workspace_url
        # that will never arrive.
        return {
            "status": "provision_failed",
            "detail": "Workspace provisioning failed — please try starting again.",
        }

    result = await db.execute(
        select(CodeSubmission).filter(CodeSubmission.workspace_id == workspace.id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        question = await db.get(Question, payload["question_id"])
        response = {
            "status": "not_submitted",
            "workspace_created_at": _utc_iso(workspace.created_at),
            "effective_time_budget_seconds": _effective_time_budget(question),
        }
        # Only hand back a workspace_url the candidate can actually use — an
        # abandoned/destroyed workspace's URL is dead, so the frontend must fall
        # back to re-verifying (which reconnects/re-provisions) instead.
        if workspace.status in (CodeWorkspaceStatus.PROVISIONING, CodeWorkspaceStatus.ACTIVE):
            response["workspace_url"] = workspace.workspace_url
        return response

    response = {"status": submission.status.value}
    if submission.status == CodeSubmissionStatus.GRADED:
        # Candidate-facing detail is gated by the host's result_visibility choice —
        # this is the one place that promise is actually enforced, not just a
        # frontend rendering choice, so a candidate hitting this endpoint directly
        # can't see more than the host configured.
        question = await db.get(Question, submission.question_id)
        visibility = question.result_visibility if question else CodingResultVisibility.HIDDEN
        if visibility == CodingResultVisibility.FULL:
            response["ai_score"] = submission.ai_score
            response["ai_verdict"] = submission.ai_verdict
        elif visibility == CodingResultVisibility.STATUS_ONLY:
            response["result_signal"] = "positive" if (submission.ai_score or 0) >= 50 else "needs_improvement"
    # FAILED / PARTIAL_FAILED intentionally carry no error_message here — those are
    # system-side grading failures, never the candidate's fault, and raw exception
    # text (Coder CLI stderr, AI-provider errors) must never reach an unauthenticated
    # candidate. The host sees the real error via the review endpoint instead.
    return response


@router.post("/quiz-builder/questions/{question_id}/coding-challenge-review/submissions/{submission_id}/regrade")
async def regrade_coding_challenge_submission(
    question_id: int,
    submission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — re-run AI scoring for a PARTIAL_FAILED submission (harvest
    succeeded, only the AI-assessment call failed) using the already-persisted
    code_timeline/ai_transcript_raw. No candidate involvement, no workspace needed.
    A FAILED submission (harvest itself failed) has nothing to re-score and is
    rejected — the candidate must be re-invited instead."""
    from features.coding_challenge.grading_service_async import regrade_submission

    submission = await db.get(CodeSubmission, submission_id)
    if not submission or submission.question_id != question_id:
        raise HTTPException(status_code=404, detail="Submission not found")

    question = await db.get(Question, question_id)
    quiz = await db.get(Quiz, question.quiz_id) if question else None
    if not quiz or quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    if submission.status != CodeSubmissionStatus.PARTIAL_FAILED:
        raise HTTPException(
            status_code=400,
            detail="Only partially-failed submissions can be regraded — this one has no recoverable data.",
        )

    ok = await regrade_submission(submission_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Submission is no longer in a regradable state")
    await db.refresh(submission)
    return {"status": submission.status.value}


@router.get("/quiz-builder/questions/{question_id}/coding-challenge-review")
async def get_coding_challenge_review(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — the full candidate pipeline for this question, one
    row per unique candidate email spanning invited-but-not-started through
    graded. Merges CodingChallengeInvite (invited, possibly never started),
    CodeWorkspace (started), and CodeSubmission (submitted/graded) — these are
    three independent records for the same person, so this is where they get
    unified into a single pipeline `status` rather than three disconnected
    views the host has to piece together themselves.
    All candidate-originated text (transcript, timeline, test output) is
    returned as plain strings — the frontend must render it as inert text,
    never dangerouslySetInnerHTML."""
    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    quiz = await db.get(Quiz, question.quiz_id)
    if not quiz or quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    invites_result = await db.execute(
        select(CodingChallengeInvite).filter(CodingChallengeInvite.question_id == question_id)
    )
    invites_by_email = {inv.candidate_email.lower(): inv for inv in invites_result.scalars().all()}

    workspaces_result = await db.execute(
        select(CodeWorkspace)
        .filter(CodeWorkspace.question_id == question_id)
        .order_by(CodeWorkspace.attempt_number.asc())
    )
    workspaces_by_email: dict[str, list[CodeWorkspace]] = {}
    for ws in workspaces_result.scalars().all():
        workspaces_by_email.setdefault(ws.candidate_email.lower(), []).append(ws)

    def _submission_dict(submission: CodeSubmission) -> dict:
        return {
            "id": submission.id,
            "status": submission.status.value,
            "test_output": submission.test_output,
            "passed_count": submission.passed_count,
            "total_count": submission.total_count,
            "score_breakdown": submission.score_breakdown,
            "ai_score": submission.ai_score,
            "ai_verdict": submission.ai_verdict,
            "ai_rationale": submission.ai_rationale,
            "ai_token_usage": submission.ai_token_usage,
            "code_timeline": submission.code_timeline,
            "ai_transcript_raw": submission.ai_transcript_raw,
            "error_message": submission.error_message,
            "submitted_at": submission.submitted_at,
            "graded_at": submission.graded_at,
        }

    def _attempt_status(workspace: Optional[CodeWorkspace], submission: Optional[CodeSubmission],
                         invite: Optional[CodingChallengeInvite]) -> str:
        if submission:
            return submission.status.value  # queued | grading | graded | partial_failed | failed
        if workspace:
            return "abandoned" if workspace.status in (CodeWorkspaceStatus.ABANDONED, CodeWorkspaceStatus.DESTROYED) else "in_progress"
        if invite and now > invite.updated_at + INVITE_VALIDITY:
            return "expired"
        return "pending"

    now = datetime.utcnow()
    all_emails = set(invites_by_email) | set(workspaces_by_email)
    entries = []
    for email_lower in all_emails:
        invite = invites_by_email.get(email_lower)
        attempt_workspaces = workspaces_by_email.get(email_lower, [])

        attempts = []
        for workspace in attempt_workspaces:
            sub_result = await db.execute(
                select(CodeSubmission).filter(CodeSubmission.workspace_id == workspace.id)
            )
            submission = sub_result.scalar_one_or_none()
            attempts.append({
                "attempt_number": workspace.attempt_number,
                "status": _attempt_status(workspace, submission, invite),
                "started_at": workspace.created_at,
                "workspace_status": workspace.status.value,
                "submission": _submission_dict(submission) if submission else None,
            })

        # A re-invite mints a new attempt_number and an email immediately, but no
        # CodeWorkspace row exists until the candidate actually starts — without this,
        # the review screen would silently keep showing the *previous* attempt's
        # terminal status with no sign a re-invite was ever sent.
        highest_started = attempts[-1]["attempt_number"] if attempts else 0
        invited_attempt = invite.latest_invited_attempt_number if invite else None
        if invited_attempt and invited_attempt > highest_started:
            attempts.append({
                "attempt_number": invited_attempt,
                "status": "expired" if now > invite.updated_at + INVITE_VALIDITY else "pending",
                "started_at": None,
                "workspace_status": None,
                "submission": None,
            })

        # The latest attempt drives the candidate's summary row (status Tag, filter
        # bucket) — that's the one the host cares about "right now". No workspace at
        # all yet (invited-but-never-started) falls back to the invite-only status.
        latest = attempts[-1] if attempts else None
        latest_workspace = attempt_workspaces[-1] if attempt_workspaces else None
        summary_status = latest["status"] if latest else _attempt_status(None, None, invite)

        entries.append({
            "candidate_email": latest_workspace.candidate_email if latest_workspace else invite.candidate_email,
            "status": summary_status,
            "invited_at": invite.updated_at if invite else None,
            "started_at": latest_workspace.created_at if latest_workspace else None,
            "workspace_status": latest_workspace.status.value if latest_workspace else None,
            "submission": latest["submission"] if latest else None,
            "attempt_count": len(attempts),
            "attempts": attempts,
            # Same rule as the invite endpoint's gate — a host can grant another
            # attempt once the current one is terminal, never while it's still live.
            "can_reinvite": not (latest_workspace and latest_workspace.status in (
                CodeWorkspaceStatus.PROVISIONING, CodeWorkspaceStatus.ACTIVE,
            )),
        })

    return {
        "question_id": question_id,
        "quiz_id": quiz.id,
        "has_custom_weights": question.grading_weights is not None,
        "candidates": entries,
    }
