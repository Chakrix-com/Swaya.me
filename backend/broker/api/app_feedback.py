"""
Global app feedback API endpoints
"""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from persistence.database_async import get_async_db
from core.auth.dependencies import get_optional_user, require_super_admin, CurrentUser
from features.app_feedback.schemas import (
    AppFeedbackSubmitRequest,
    AppFeedbackResponse,
    AppFeedbackListResponse,
)
from features.app_feedback.service_async import AppFeedbackServiceAsync
from features.app_feedback import attachments as feedback_attachments
from persistence.models.app_feedback import AppFeedback
from shared.utils.rate_limiter import limiter

# Public endpoint (no auth prefix)
router = APIRouter(prefix="/feedback", tags=["feedback"])

# Admin endpoint (mounted under /admin)
admin_router = APIRouter(tags=["admin"])


@router.post("/app", response_model=AppFeedbackResponse, status_code=201)
async def submit_app_feedback(
    body: AppFeedbackSubmitRequest,
    request: Request,
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Submit app-level feedback from any page.
    Works for both anonymous visitors and authenticated users.
    """
    user_agent = request.headers.get("user-agent")
    service = AppFeedbackServiceAsync()
    feedback = await service.submit(db, body, current_user, user_agent)
    return AppFeedbackResponse.from_orm(feedback)


@router.post("/app/with-attachments", response_model=AppFeedbackResponse, status_code=201)
@limiter.limit("10/hour")
async def submit_app_feedback_with_attachments(
    request: Request,
    payload: str = Form(..., description="AppFeedbackSubmitRequest as JSON"),
    files: List[UploadFile] = File(...),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Feedback with up to 3 screenshots (multipart). Same rules as /app for the text."""
    try:
        body = AppFeedbackSubmitRequest.model_validate(json.loads(payload))
    except (ValueError, ValidationError):
        raise HTTPException(status_code=422, detail="Invalid feedback payload")
    # Validate images before the feedback row exists, so a bad upload stores nothing
    images = await feedback_attachments.read_and_validate(files)

    service = AppFeedbackServiceAsync()
    feedback = await service.submit(db, body, current_user, request.headers.get("user-agent"))
    if images:
        feedback.attachments = feedback_attachments.save(feedback.id, images)
        await db.commit()
        await db.refresh(feedback)
    return AppFeedbackResponse.from_orm(feedback)


@admin_router.get("/app-feedback/{feedback_id}/attachments/{name}")
async def get_app_feedback_attachment(
    feedback_id: int,
    name: str,
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Serve one feedback screenshot. Super admin only."""
    feedback = await db.get(AppFeedback, feedback_id)
    if not feedback or name not in (feedback.attachments or []):
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path=str(feedback_attachments.resolve(feedback_id, name)), media_type="image/png")


@admin_router.get("/app-feedback", response_model=AppFeedbackListResponse)
async def list_app_feedback(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source_type: Optional[str] = Query(None, description="'anonymous' or 'user'"),
    rating: Optional[int] = Query(None, ge=1, le=5),
    search: Optional[str] = Query(None),
    page_url_contains: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all app feedback submissions. Super admin only.
    """
    service = AppFeedbackServiceAsync()
    return await service.list_feedback(
        db=db,
        limit=limit,
        offset=offset,
        source_type=source_type,
        rating=rating,
        search=search,
        page_url_contains=page_url_contains,
        date_from=date_from,
        date_to=date_to,
    )
