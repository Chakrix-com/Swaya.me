"""
Exam API — public and authenticated endpoints for exam participation and results.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from shared.utils.redis_client import get_redis, RedisClient
from features.quiz.schemas import (
    ExamInfoResponse,
    ExamOtpRequest,
    ExamStartRequest,
    ExamStartResponse,
    ExamAnswerRequest,
    ExamSubmitRequest,
    ExamSubmitResponse,
    ExamResultsResponse,
    ExamPublishResponse,
    AnalyzeResultsRequest,
    ParticipantDetailResponse,
)
from features.quiz import exam_service_async as svc
from shared.exceptions.quiz import QuizNotFoundError, QuizValidationError, InvalidQuizStatusError, ProctoringViolationError
from core.auth.dependencies import get_current_user, CurrentUser, require_admin
from core.ai.gemini_service import analyze_exam_results, GeminiError

router = APIRouter(tags=["exam"])


@router.post("/e/{slug}/request-otp")
async def request_exam_otp(
    slug: str,
    body: ExamOtpRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
):
    """Public — send a 6-digit OTP to the participant's email before exam start."""
    try:
        return await svc.request_exam_otp(db, slug, body.display_name, body.email, redis)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/e/{slug}", response_model=ExamInfoResponse)
async def get_exam_info(slug: str, db: AsyncSession = Depends(get_async_db)):
    """Public — get info about an exam (status, dates, question count)."""
    try:
        return await svc.get_exam_info(db, slug)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/e/{slug}/start", response_model=ExamStartResponse)
async def start_exam(
    slug: str,
    body: ExamStartRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
):
    """Public — start exam; verifies OTP, returns all questions and session_token."""
    try:
        return await svc.start_exam(db, slug, body.display_name, body.email, body.otp, redis)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/e/{slug}/answer")
async def save_answer(slug: str, body: ExamAnswerRequest, db: AsyncSession = Depends(get_async_db)):
    """Public — upsert a single answer; updates last_activity_at."""
    try:
        return await svc.save_answer(
            db, slug, body.session_token, body.question_id, body.selected_option_index
        )
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/e/{slug}/submit", response_model=ExamSubmitResponse)
async def submit_exam(
    slug: str,
    body: ExamSubmitRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — submit exam; score and return full result."""
    try:
        return await svc.submit_exam(db, slug, body.session_token, redis=redis)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProctoringViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/e/{slug}/result", response_model=ExamSubmitResponse)
async def get_my_result(slug: str, body: ExamSubmitRequest, db: AsyncSession = Depends(get_async_db)):
    """Public — retrieve participant's own score/breakdown after submission."""
    try:
        return await svc.get_my_result(db, slug, body.session_token)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/quiz/{quiz_id}/exam-results", response_model=ExamResultsResponse)
async def get_exam_results(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — full results: leaderboard + per-question analytics."""
    try:
        return await svc.get_exam_results(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/quiz/{quiz_id}/exam-results/participant/{participant_id}", response_model=ParticipantDetailResponse)
async def get_participant_detail(
    quiz_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — per-question breakdown for a single participant."""
    try:
        return await svc.get_participant_detail(db, quiz_id, participant_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quiz/{quiz_id}/analyze-results")
async def analyze_exam_results_endpoint(
    quiz_id: int,
    body: AnalyzeResultsRequest = Body(default=AnalyzeResultsRequest()),
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Authenticated host — AI analysis of exam results via Gemini."""
    try:
        results = await svc.get_exam_results(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if results.total_completed == 0:
        raise HTTPException(status_code=400, detail="No completed participants yet — analysis requires at least one submission.")

    try:
        analysis = await analyze_exam_results(results.model_dump(), body.custom_prompt)
    except GeminiError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"analysis": analysis}


@router.post("/quizzes/{quiz_id}/publish-exam", response_model=ExamPublishResponse)
async def publish_exam(
    quiz_id: int,
    fresh_start: bool = Query(False),
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — publish exam: generate slug + create session."""
    try:
        return await svc.publish_exam(db, quiz_id, current_user, fresh_start=fresh_start)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (QuizValidationError, InvalidQuizStatusError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quizzes/{quiz_id}/unpublish-exam")
async def unpublish_exam(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Authenticated host — unpublish exam (reverts to DRAFT)."""
    try:
        return await svc.unpublish_exam(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (QuizValidationError, InvalidQuizStatusError) as e:
        raise HTTPException(status_code=400, detail=str(e))
