"""
Offline Poll API — public and authenticated endpoints for offline poll participation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from persistence.database_async import get_async_db
from features.quiz.schemas import (
    OfflinePollInfoResponse,
    OfflinePollJoinResponse,
    OfflineAnswerRequest,
    OfflineCompleteRequest,
    OfflineResultsResponse,
)
from features.quiz import offline_poll_service_async as svc
from shared.exceptions.quiz import QuizNotFoundError, QuizValidationError
from core.auth.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/offline-poll", tags=["offline-poll"])


class JoinRequest(BaseModel):
    display_name: Optional[str] = None
    session_token: Optional[str] = None  # provided for resume


@router.get("/{slug}", response_model=OfflinePollInfoResponse)
async def get_poll_info(slug: str, db: AsyncSession = Depends(get_async_db)):
    """Get public info about an offline poll (status, dates, question count)."""
    try:
        return await svc.get_poll_info(db, slug)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{slug}/join", response_model=OfflinePollJoinResponse)
async def join_poll(slug: str, body: JoinRequest, db: AsyncSession = Depends(get_async_db)):
    """Create or resume a participation session for an offline poll."""
    try:
        return await svc.join_or_resume(db, slug, body.display_name, body.session_token)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{slug}/answer")
async def save_answer(slug: str, body: OfflineAnswerRequest, db: AsyncSession = Depends(get_async_db)):
    """Save (upsert) a single answer for an offline poll."""
    try:
        return await svc.save_answer(
            db, slug, body.session_token, body.question_id,
            body.selected_option_index, body.text_answer
        )
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{slug}/complete")
async def complete_poll(slug: str, body: OfflineCompleteRequest, db: AsyncSession = Depends(get_async_db)):
    """Mark a participant's poll submission as completed."""
    try:
        return await svc.complete_poll(db, slug, body.session_token)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{slug}/results", response_model=OfflineResultsResponse)
async def get_results(
    slug: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get aggregated results for an offline poll (authenticated host only)."""
    try:
        return await svc.get_results(db, slug, current_user)
    except QuizNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except QuizValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
