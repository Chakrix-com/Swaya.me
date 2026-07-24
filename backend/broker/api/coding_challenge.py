"""
Coding Challenge API — authenticated host endpoints (invite, examiner review) and
the public candidate flow at /coding-challenge/{token}/...
"""
import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from shared.utils.redis_client import get_redis, RedisClient
from shared.utils.rate_limiter import limiter
from core.auth.dependencies import get_current_user, CurrentUser
from core.config.settings import settings
from persistence.models.quiz import (
    Quiz, QuizType, Question, QuestionType, CodeWorkspace, CodeWorkspaceStatus,
    CodeSubmission, CodeSubmissionStatus,
)
from features.coding_challenge import coding_challenge_service_async as svc
from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["coding-challenge"])

_IDE_TEMPLATE_MAP_SETTING = {
    "code_server": "code_server_template_name",
    "intellij": "intellij_template_name",
}


class StartRequest(BaseModel):
    ide_type: str
    otp: str


class InviteRequest(BaseModel):
    candidate_email: EmailStr


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


@router.post("/quizzes/{quiz_id}/coding-challenge/invite")
async def invite_candidate(
    quiz_id: int,
    body: InviteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — mint a signed invite link and email it to the candidate."""
    import os
    from core.auth.email_service import send_email

    quiz, question = await _get_coding_challenge_question(db, quiz_id)
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    token = svc.create_invite_token(quiz_id, question.id, body.candidate_email, expires_delta=timedelta(days=7))
    frontend_url = os.getenv("FRONTEND_URL", "https://www.swaya.me")
    invite_url = f"{frontend_url}/c/{token}"

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto">
      <h2 style="color:#1677ff">You've been invited to a Coding Challenge</h2>
      <p>Quiz: <strong>{quiz.title}</strong></p>
      <p><a href="{invite_url}" style="display:inline-block;padding:10px 20px;background:#1677ff;
         color:#fff;border-radius:6px;text-decoration:none">Start Coding Challenge</a></p>
      <p style="color:#888;font-size:13px">Or open this link: {invite_url}</p>
    </div>
    """
    sent = await send_email(
        subject=f"Coding Challenge invite — {quiz.title}",
        recipients=[body.candidate_email],
        html_body=html_body,
    )
    return {"invite_url": invite_url, "sent": sent}


@router.get("/coding-challenge/{token}")
async def get_coding_challenge_info(token: str, db: AsyncSession = Depends(get_async_db)):
    """Public — decode the invite, fetch the problem statement, return IDE choices."""
    payload = svc.decode_invite_token(token)
    question = await db.get(Question, payload["question_id"])
    quiz = await db.get(Quiz, payload["quiz_id"])
    if not question or not quiz:
        raise HTTPException(status_code=404, detail="Coding challenge not found")

    problem_statement = await svc.fetch_readme(question.git_repo_url) if question.git_repo_url else ""
    return {
        "quiz_title": quiz.title,
        "problem_statement": problem_statement,
        "candidate_email": payload["candidate_email"],
        "ide_choices": ["code_server", "intellij"],
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


def _derive_workspace_name(quiz_id: int, question_id: int, candidate_email: str) -> str:
    """Deterministic per-(quiz, question, candidate) workspace name — this is what
    makes the invite link effectively single-use without the JWT itself needing to
    be one-time (a repeat /start reconnects to the same workspace, see idempotency
    check below)."""
    email_hash = hashlib.sha256(candidate_email.lower().encode()).hexdigest()[:8]
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
    quiz_id, question_id, candidate_email = (
        payload["quiz_id"], payload["question_id"], payload["candidate_email"],
    )

    if body.ide_type not in _IDE_TEMPLATE_MAP_SETTING:
        raise HTTPException(status_code=400, detail="Invalid ide_type")

    otp_ok = await svc.verify_coding_challenge_otp(payload["jti"], candidate_email, body.otp, redis)
    if not otp_ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    # Idempotency check first: a returning candidate reconnects to their own
    # already-running workspace rather than provisioning a second one.
    result = await db.execute(
        select(CodeWorkspace).filter(
            CodeWorkspace.quiz_id == quiz_id,
            CodeWorkspace.question_id == question_id,
            CodeWorkspace.candidate_email == candidate_email,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.status in (CodeWorkspaceStatus.PROVISIONING, CodeWorkspaceStatus.ACTIVE):
        workspace_url, token_name = await coder_client.mint_session_url(
            existing.coder_workspace_name, body.ide_type, settings.coder.url,
            settings.coder.service_account_username,
        )
        existing.workspace_url = workspace_url
        existing.coder_token_name = token_name
        await db.commit()
        return {"workspace_url": workspace_url}

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

    workspace_name = _derive_workspace_name(quiz_id, question_id, candidate_email)
    template_name = getattr(settings.coder, _IDE_TEMPLATE_MAP_SETTING[body.ide_type])

    await coder_client.create_workspace(workspace_name, template_name, question.git_repo_url or "")
    workspace_url, token_name = await coder_client.mint_session_url(
        workspace_name, body.ide_type, settings.coder.url, settings.coder.service_account_username,
    )

    workspace = CodeWorkspace(
        tenant_id=quiz.tenant_id,
        quiz_id=quiz_id,
        question_id=question_id,
        candidate_email=candidate_email,
        ide_type=body.ide_type,
        coder_workspace_name=workspace_name,
        coder_token_name=token_name,
        status=CodeWorkspaceStatus.ACTIVE,
        workspace_url=workspace_url,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    lifetime_deadline = workspace.created_at + timedelta(seconds=settings.coder.workspace_max_lifetime_seconds)
    svc.schedule_lifetime_cap_job(workspace.id, workspace_name, lifetime_deadline)

    return {"workspace_url": workspace_url}


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
    quiz_id, question_id, candidate_email = (
        payload["quiz_id"], payload["question_id"], payload["candidate_email"],
    )

    result = await db.execute(
        select(CodeWorkspace).filter(
            CodeWorkspace.quiz_id == quiz_id,
            CodeWorkspace.question_id == question_id,
            CodeWorkspace.candidate_email == candidate_email,
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
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found — call /start first")

    result = await db.execute(
        select(CodeSubmission).filter(CodeSubmission.workspace_id == workspace.id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return {"status": "not_submitted"}

    response = {"status": submission.status.value}
    if submission.status == CodeSubmissionStatus.GRADED:
        response["ai_score"] = submission.ai_score
        response["ai_verdict"] = submission.ai_verdict
    elif submission.status in (CodeSubmissionStatus.FAILED, CodeSubmissionStatus.PARTIAL_FAILED):
        response["error_message"] = submission.error_message
    return response


@router.get("/quiz-builder/questions/{question_id}/coding-challenge-review")
async def get_coding_challenge_review(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — examiner review, one entry per candidate who has a
    workspace for this question (a question can have many candidates via repeated
    /invite calls). All candidate-originated text (transcript, timeline, test
    output) is returned as plain strings — the frontend must render it as inert
    text, never dangerouslySetInnerHTML."""
    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    quiz = await db.get(Quiz, question.quiz_id)
    if not quiz or quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    result = await db.execute(
        select(CodeWorkspace).filter(CodeWorkspace.question_id == question_id)
    )
    workspaces = result.scalars().all()

    entries = []
    for workspace in workspaces:
        result = await db.execute(
            select(CodeSubmission).filter(CodeSubmission.workspace_id == workspace.id)
        )
        submission = result.scalar_one_or_none()
        entry = {
            "candidate_email": workspace.candidate_email,
            "workspace_status": workspace.status.value,
            "submission": None,
        }
        if submission:
            entry["submission"] = {
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
        entries.append(entry)

    return {"question_id": question_id, "candidates": entries}
