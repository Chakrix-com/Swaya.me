"""
Quiz API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from persistence.database_async import get_async_db
from core.auth.dependencies import get_current_user, CurrentUser
from features.quiz.schemas import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    SessionStartRequest, SessionResponse, SessionJoinRequest, SessionJoinResponse,
    AnswerSubmitRequest, AnswerSubmitResponse,
    QuestionResultsResponse, SessionResultsResponse,
    WordCloudAnswerSubmitRequest, WordCloudResultsResponse,
    FeedbackSubmitRequest
)
from features.quiz.quiz_service_async import QuizBuilderServiceAsync
from features.quiz.question_service_async import QuestionServiceAsync
from features.quiz.session_service_async import SessionServiceAsync
from features.quiz.answer_service_async import AnswerServiceAsync
from features.quiz.feedback_service_async import FeedbackServiceAsync
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, SessionNotFoundError,
    ParticipantNotFoundError, QuizValidationError, InvalidQuizStatusError,
    InvalidSessionStatusError, DuplicateAnswerError, QuestionNotOpenError,
    TierLimitExceededError
)
from shared.utils.redis_client import get_redis, RedisClient
from core.config.tier_service import TierService

router = APIRouter(prefix="/quizzes", tags=["Quiz"])


# Dependency to get services
async def get_quiz_service(redis: RedisClient = Depends(get_redis)) -> QuizBuilderServiceAsync:
    tier_service = TierService(redis)
    return QuizBuilderServiceAsync(tier_service)


async def get_question_service(redis: RedisClient = Depends(get_redis)) -> QuestionServiceAsync:
    tier_service = TierService(redis)
    return QuestionServiceAsync(tier_service)


async def get_session_service(redis: RedisClient = Depends(get_redis)) -> SessionServiceAsync:
    tier_service = TierService(redis)
    return SessionServiceAsync(redis, tier_service)


async def get_answer_service(redis: RedisClient = Depends(get_redis)) -> AnswerServiceAsync:
    return AnswerServiceAsync(redis)


async def get_feedback_service() -> FeedbackServiceAsync:
    return FeedbackServiceAsync()


# Quiz CRUD Endpoints
@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    request: QuizCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Create new quiz"""
    try:
        return await service.create_quiz(db, request, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Get quiz by ID"""
    try:
        return await service.get_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[QuizListResponse])
async def list_quizzes(
    event_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """List quizzes for tenant"""
    return await service.list_quizzes(db, current_user, event_id)


@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    request: QuizUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Update quiz"""
    try:
        return await service.update_quiz(db, quiz_id, request, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Delete quiz"""
    try:
        await service.delete_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id}/publish", response_model=QuizResponse)
async def publish_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Publish quiz (validate and mark as READY)"""
    try:
        return await service.publish_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuizStatusError, QuizValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id}/unpublish", response_model=QuizResponse)
async def unpublish_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Unpublish quiz (revert to DRAFT status for editing)"""
    try:
        return await service.unpublish_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Question Management Endpoints
@router.post("/{quiz_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    quiz_id: int,
    request: QuestionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuestionServiceAsync = Depends(get_question_service)
):
    """Add question to quiz"""
    try:
        return await service.add_question(db, quiz_id, request, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuizStatusError, TierLimitExceededError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    request: QuestionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuestionServiceAsync = Depends(get_question_service)
):
    """Update question"""
    try:
        return await service.update_question(db, question_id, request, current_user)
    except QuestionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuestionServiceAsync = Depends(get_question_service)
):
    """Delete question"""
    try:
        await service.delete_question(db, question_id, current_user)
    except QuestionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Session Management Endpoints
@router.post("/sessions/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Start quiz session"""
    try:
        return await service.start_session(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuizStatusError, TierLimitExceededError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/join", response_model=SessionJoinResponse)
async def join_session(
    request: SessionJoinRequest,
    db: AsyncSession = Depends(get_async_db),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Join session as participant (anonymous)"""
    try:
        return await service.join_session(db, request)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TierLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/{session_id}/advance", response_model=SessionResponse)
async def advance_question(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Advance to next question"""
    try:
        return await service.advance_question(db, session_id, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidSessionStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/{session_id}/back", response_model=SessionResponse)
async def back_question(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Go back to previous question"""
    try:
        return await service.back_question(db, session_id, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidSessionStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """End session"""
    try:
        return await service.end_session(db, session_id, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Answer Submission Endpoints
@router.post("/sessions/submit-answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    request: AnswerSubmitRequest,
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Submit MCQ answer (participant)"""
    try:
        return await service.submit_answer(db, session_token, request)
    except ParticipantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except (QuestionNotOpenError, DuplicateAnswerError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/submit-word-cloud", response_model=AnswerSubmitResponse)
async def submit_word_cloud_answer(
    request: WordCloudAnswerSubmitRequest,
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Submit word cloud answer (participant - unlimited submissions)"""
    try:
        return await service.submit_word_cloud_answer(db, session_token, request)
    except ParticipantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except QuestionNotOpenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions/feedback")
async def submit_participant_feedback(
    request: FeedbackSubmitRequest,
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: FeedbackServiceAsync = Depends(get_feedback_service)
):
    """Submit feedback as a participant"""
    try:
        return await service.submit_participant_feedback(db, session_token, request)
    except ParticipantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except (SessionNotFoundError, QuizNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/feedback")
async def submit_user_feedback(
    request: FeedbackSubmitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: FeedbackServiceAsync = Depends(get_feedback_service)
):
    """Submit feedback as an authenticated user"""
    try:
        return await service.submit_user_feedback(db, current_user, request)
    except (SessionNotFoundError, QuizNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/questions/{question_id}/word-cloud-results", response_model=WordCloudResultsResponse)
async def get_word_cloud_results(
    question_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Get word cloud results for a question"""
    try:
        return await service.get_word_cloud_results(db, session_id, question_id)
    except QuestionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/results", response_model=SessionResultsResponse)
async def get_session_results(
    session_id: int,
    session_token: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Get session results"""
    try:
        # Check if participant token is still active
        if session_token:
            from persistence.models.quiz import Participant
            from sqlalchemy import select
            result = await db.execute(
                select(Participant).filter(
                    Participant.session_token == session_token
                )
            )
            participant = result.scalar_one_or_none()
            
            if participant and not participant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session has been restarted. Please rejoin with the new code."
                )
        
        return await service.get_session_results(db, session_id, session_token)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
