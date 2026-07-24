"""
Coding Challenge API — authenticated host endpoints (invite, examiner review) and
the public candidate flow at /coding-challenge/{token}/...
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from shared.utils.redis_client import get_redis, RedisClient
from shared.utils.rate_limiter import limiter
from core.auth.dependencies import get_current_user, CurrentUser
from core.config.settings import settings
from persistence.models.quiz import Quiz, QuizType, Question, QuestionType
from features.coding_challenge import coding_challenge_service_async as svc

router = APIRouter(tags=["coding-challenge"])


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
