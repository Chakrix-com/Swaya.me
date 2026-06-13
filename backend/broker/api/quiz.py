"""
Quiz API Endpoints
"""
import asyncio
import json
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from persistence.database_async import get_async_db
from core.auth.dependencies import get_current_user, CurrentUser
from features.quiz.schemas import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionReorderRequest,
    SessionStartRequest, SessionResponse, SessionJoinRequest, SessionJoinResponse,
    SessionLeaveResponse, SessionLookupResponse, HomeStatsResponse,
    WhiteboardStateUpdateRequest, WhiteboardStateResponse,
    AnswerSubmitRequest, AnswerSubmitResponse,
    QuestionResultsResponse, SessionResultsResponse,
    WordCloudAnswerSubmitRequest, WordCloudResultsResponse,
    FeedbackSubmitRequest, LeaderboardResponse,
    SessionListResponse, TemplateDesignationRequest, TemplateQuizListItemResponse,
    FolderCreateRequest, FolderUpdateRequest, FolderAssignRequest, FolderResponse,
    ResultsHubResponse
)
from features.quiz.quiz_service_async import QuizBuilderServiceAsync
from features.quiz.schemas import OfflinePollPublishResponse
from features.quiz.question_service_async import QuestionServiceAsync
from features.quiz.session_service_async import SessionServiceAsync
from features.quiz.answer_service_async import AnswerServiceAsync
from features.quiz.feedback_service_async import FeedbackServiceAsync
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, SessionNotFoundError,
    ParticipantNotFoundError, QuizValidationError, InvalidQuizStatusError,
    InvalidSessionStatusError, DuplicateAnswerError, QuestionNotOpenError,
    TierLimitExceededError, ContentFilterError
)
from shared.utils.redis_client import get_redis, RedisClient
from core.config.tier_service import TierService
from persistence.models.quiz import Participant, QuizSession, Quiz
from features.quiz.import_service import ExcelImportService

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


async def get_import_service() -> ExcelImportService:
    return ExcelImportService()


async def _assert_host_session_access(
    db: AsyncSession,
    session_id: int,
    current_user: CurrentUser
) -> None:
    result = await db.execute(
        select(QuizSession.id)
        .join(Quiz, Quiz.id == QuizSession.quiz_id)
        .filter(
            QuizSession.id == session_id,
            QuizSession.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


async def _require_participant_for_session(
    db: AsyncSession,
    session_id: int,
    session_token: str,
    redis: "RedisClient | None" = None,
) -> Participant:
    # Fast path: Redis cache set at join time
    if redis is not None:
        cached = await redis.get_json(f"session_token:{session_token}")
        if cached is not None:
            if cached.get("session_id") != session_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session token does not match session")
            if not cached.get("is_active", True):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session has been restarted. Please rejoin with the new code.")
            # Return a lightweight stub — only .session_id and .is_active are used downstream
            class _CachedParticipant:
                def __init__(self, d):
                    self.id = d["participant_id"]
                    self.session_id = d["session_id"]
                    self.is_active = d.get("is_active", True)
                    self.session_token = session_token
            return _CachedParticipant(cached)

    # Cache miss — fall back to DB
    result = await db.execute(
        select(Participant).filter(Participant.session_token == session_token)
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    if participant.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session token does not match session")
    if not participant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session has been restarted. Please rejoin with the new code."
        )
    return participant


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


@router.get("/{quiz_id:int}", response_model=QuizResponse)
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
    search: Optional[str] = None,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """List quizzes for tenant"""
    quizzes = await service.list_quizzes(db, current_user, event_id, include_archived=include_archived)
    if search:
        term = search.strip().lower()
        quizzes = [
            q for q in quizzes
            if term in q.title.lower()
        ]
    return quizzes


@router.get("/folders", response_model=List[FolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    return await service.list_folders(db, current_user)


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    request: FolderCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    try:
        return await service.create_folder(db, request, current_user)
    except (QuizNotFoundError, QuizValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    request: FolderUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    try:
        return await service.update_folder(db, folder_id, request, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    try:
        await service.delete_folder(db, folder_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{quiz_id:int}/folder", response_model=QuizResponse)
async def assign_quiz_folder(
    quiz_id: int,
    request: FolderAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    try:
        return await service.assign_quiz_folder(db, quiz_id, request.folder_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/templates", response_model=List[TemplateQuizListItemResponse])
async def list_templates(
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """List template quizzes visible to current user"""
    return await service.list_available_templates(db, current_user)


@router.get("/public-templates", response_model=List[TemplateQuizListItemResponse])
async def list_public_templates(
    db: AsyncSession = Depends(get_async_db),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Public endpoint — lists globally-scoped templates without auth (explore page)."""
    return await service.list_public_templates(db)


@router.get("/template-library", response_model=List[TemplateQuizListItemResponse])
async def list_template_library(
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """List template quizzes visible to current user (stable path)"""
    return await service.list_available_templates(db, current_user)


@router.post("/templates/{template_quiz_id}/use", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def use_template_quiz(
    template_quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Create a new draft quiz from a visible template"""
    try:
        return await service.create_quiz_from_template(db, template_quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TierLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/template-library/{template_quiz_id}/use", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def use_template_from_library(
    template_quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Create a new draft quiz from a visible template (stable path)"""
    try:
        return await service.create_quiz_from_template(db, template_quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TierLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{quiz_id:int}", response_model=QuizResponse)
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


@router.post("/{quiz_id:int}/template", response_model=QuizResponse)
async def set_template_status(
    quiz_id: int,
    request: TemplateDesignationRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Mark or unmark a quiz as template"""
    try:
        return await service.set_template_status(db, quiz_id, request, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{quiz_id:int}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/{quiz_id:int}/publish", response_model=QuizResponse)
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


@router.post("/{quiz_id:int}/publish-offline", response_model=OfflinePollPublishResponse)
async def publish_offline_poll(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Publish an offline poll — creates permanent session and shareable slug."""
    try:
        return await service.publish_offline_poll(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuizStatusError, QuizValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id:int}/unpublish", response_model=QuizResponse)
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


@router.post("/{quiz_id:int}/archive", response_model=QuizListResponse)
async def archive_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Soft-archive a quiz"""
    try:
        return await service.archive_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id:int}/unarchive", response_model=QuizListResponse)
async def unarchive_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Restore an archived quiz"""
    try:
        return await service.unarchive_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id:int}/duplicate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuizBuilderServiceAsync = Depends(get_quiz_service)
):
    """Duplicate quiz as a new DRAFT quiz"""
    try:
        return await service.duplicate_quiz(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{quiz_id:int}/sessions", response_model=SessionListResponse)
async def list_quiz_sessions(
    quiz_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """List all sessions for a quiz with participant and response counts"""
    try:
        return await service.list_sessions(db, quiz_id, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Import/Export Endpoints
@router.get("/import/template")
async def get_import_template(
    service: ExcelImportService = Depends(get_import_service)
):
    """Download the blank Excel template for bulk upload"""
    return FileResponse(
        path=service.get_template_path(),
        filename="Swaya_me_Test_Template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.post("/import/export-draft")
async def export_draft_to_excel(
    request: Request,
    service: ExcelImportService = Depends(get_import_service)
):
    """Generate and download an Excel file from the current frontend draft JSON"""
    try:
        draft_data = await request.json()
        file_bytes = service.generate_excel_from_draft(draft_data)
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Swaya_me_Draft_Export.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to export draft: {str(e)}")


@router.post("/import/validate")
async def validate_import_file(
    file: UploadFile = File(...),
    service: ExcelImportService = Depends(get_import_service)
):
    """Parse and validate an uploaded Excel file, returning a preview of results"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel (.xlsx) file.")
    
    try:
        content = await file.read()
        raw_data = await service.parse_excel(content)
        validation_results = service.validate_import(raw_data)
        return validation_results
    except QuizValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error during validation: {str(e)}")


@router.post("/import/finalize", response_model=QuizResponse)
async def finalize_import(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: ExcelImportService = Depends(get_import_service)
):
    """Create a new quiz and its questions from validated import data"""
    try:
        data = await request.json()
        if not data.get("canImport"):
            raise HTTPException(status_code=400, detail="Import data is invalid or has errors.")

        quiz = await service.create_from_import(db, data, current_user)
        # Reload with questions eagerly to avoid lazy-load in async context
        result = await db.execute(
            select(Quiz)
            .filter(Quiz.id == quiz.id)
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one()
        builder_service = await get_quiz_service()
        return builder_service._to_quiz_response(quiz)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finalize import: {str(e)}")


# Question Management Endpoints
@router.post("/{quiz_id:int}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
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
    except ContentFilterError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
    except ContentFilterError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put("/{quiz_id:int}/questions/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_questions(
    quiz_id: int,
    request: QuestionReorderRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuestionServiceAsync = Depends(get_question_service)
):
    """Reorder questions within a draft quiz"""
    try:
        await service.reorder_questions(db, quiz_id, request.question_orders, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidQuizStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{quiz_id:int}/questions/{question_id:int}/duplicate", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_question(
    quiz_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: QuestionServiceAsync = Depends(get_question_service)
):
    """Duplicate a question within the same quiz"""
    try:
        return await service.duplicate_question(db, quiz_id, question_id, current_user)
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
@router.get("/sessions/all", response_model=ResultsHubResponse)
async def list_all_sessions(
    page: int = 1,
    page_size: int = 20,
    quiz_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """List all sessions across all quizzes for the current user's tenant."""
    page_size = min(page_size, 100)
    return await service.list_all_sessions(db, current_user, page, page_size, quiz_type, status)


@router.get("/sessions/home-stats", response_model=HomeStatsResponse)
async def get_home_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Return aggregate stats for the logged-in host's home page."""
    return await service.get_home_stats(db, current_user.tenant_id)


@router.get("/sessions/lookup", response_model=SessionLookupResponse)
async def lookup_session(
    join_code: str,
    db: AsyncSession = Depends(get_async_db),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Return activity info by join code — no side effects, no auth required."""
    try:
        return await service.lookup_session(db, join_code)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


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

@router.post("/sessions/leave", response_model=SessionLeaveResponse)
async def leave_session(
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Leave session as participant (anonymous)"""
    try:
        return await service.leave_session(db, session_token)
    except ParticipantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


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


@router.post("/sessions/{session_id}/toggle-leaderboard", response_model=SessionResponse)
async def toggle_leaderboard(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Toggle leaderboard visibility for participants"""
    try:
        return await service.toggle_leaderboard(db, session_id, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


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


@router.get("/sessions/{session_id}/participants-list")
async def list_session_participants(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return display names of active participants in a session (host only, lobby use)."""
    from sqlalchemy import select as sa_select
    await _assert_host_session_access(db, session_id, current_user)
    rows = (await db.execute(
        sa_select(Participant.display_name, Participant.created_at)
        .where(Participant.session_id == session_id, Participant.is_active == True)
        .order_by(Participant.created_at.asc())
    )).all()
    return {
        "session_id": session_id,
        "participants": [
            {"name": r.display_name or "Anonymous"}
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/sessions/{session_id}/whiteboard-state", response_model=WhiteboardStateResponse)
async def get_whiteboard_state(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Get whiteboard state for current presenter question (host-only)."""
    try:
        return await service.get_whiteboard_state(db, session_id, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/whiteboard-state/public", response_model=WhiteboardStateResponse)
async def get_public_whiteboard_state(
    session_id: int,
    join_code: str,
    db: AsyncSession = Depends(get_async_db),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Get whiteboard state using join code (present viewers)."""
    try:
        return await service.get_public_whiteboard_state(db, session_id, join_code)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/sessions/{session_id}/whiteboard-state", response_model=WhiteboardStateResponse)
async def update_whiteboard_state(
    session_id: int,
    request: WhiteboardStateUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """Persist presenter whiteboard state for current question (host-only)."""
    try:
        return await service.update_whiteboard_state(db, session_id, request, current_user)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidSessionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/sessions/{session_id}/whiteboard-events/public")
async def stream_public_whiteboard_events(
    session_id: int,
    join_code: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    service: SessionServiceAsync = Depends(get_session_service)
):
    """SSE stream for whiteboard state updates for present viewers."""

    async def event_stream():
        last_payload = None
        while True:
            if await request.is_disconnected():
                break
            try:
                state = await service.get_public_whiteboard_state(db, session_id, join_code)
                payload = state.model_dump_json()
                if payload != last_payload:
                    yield f"event: whiteboard\ndata: {payload}\n\n"
                    last_payload = payload
            except SessionNotFoundError:
                error_payload = json.dumps({"error": "session_not_found"})
                yield f"event: error\ndata: {error_payload}\n\n"
                break

            # Keepalive comment for proxies and client reconnect stability
            yield ": ping\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    """Submit text answer (word cloud unlimited; other text types single submission)"""
    try:
        return await service.submit_word_cloud_answer(db, session_token, request)
    except ParticipantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except (QuestionNotOpenError, DuplicateAnswerError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ContentFilterError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/sessions/{session_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Get host leaderboard for a session (host-only)"""
    try:
        await _assert_host_session_access(db, session_id, current_user)
        return await service.get_leaderboard(db, session_id, None)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


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
    except ContentFilterError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
    except ContentFilterError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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


@router.get("/sessions/{session_id}/export")
async def export_session_results(
    session_id: int,
    format: str = Query(..., pattern="^(pdf|docx|pptx|xlsx)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    answer_service: AnswerServiceAsync = Depends(get_answer_service),
):
    """Export session results as PDF, DOCX, PPTX, or XLSX"""
    from features.quiz.export_service import ExportService
    export_svc = ExportService()
    file_bytes, media_type, filename = await export_svc.generate(
        session_id, format, db, current_user.tenant_id, answer_service
    )
    return StreamingResponse(
        iter([file_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/sessions/{session_id}/results", response_model=SessionResultsResponse)
async def get_session_results(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
    service: AnswerServiceAsync = Depends(get_answer_service),
    session_service: SessionServiceAsync = Depends(get_session_service),
):
    """Get host session results (host-only)"""
    try:
        await _assert_host_session_access(db, session_id, current_user)
        await session_service.reconcile_timed_question_state(db, session_id)
        return await service.get_session_results(db, session_id, None)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/audience-results", response_model=SessionResultsResponse)
async def get_participant_session_results(
    session_id: int,
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service),
    session_service: SessionServiceAsync = Depends(get_session_service),
    redis: RedisClient = Depends(get_redis),
):
    """Get participant-safe session results for the participant's own session"""
    try:
        await _require_participant_for_session(db, session_id, session_token, redis=redis)
        await session_service.reconcile_timed_question_state(db, session_id)
        return await service.get_session_results(
            db,
            session_id,
            participant_token=session_token,
            include_question_results=False,
            include_text_responses=False,
        )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/audience-leaderboard", response_model=LeaderboardResponse)
async def get_participant_leaderboard(
    session_id: int,
    session_token: str,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Get leaderboard for a participant's own session"""
    try:
        await _require_participant_for_session(db, session_id, session_token)
        return await service.get_leaderboard(db, session_id, session_token)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
