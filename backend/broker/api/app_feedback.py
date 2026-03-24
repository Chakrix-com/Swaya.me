"""
Global app feedback API endpoints
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from persistence.database_async import get_async_db
from core.auth.dependencies import get_optional_user, require_super_admin, CurrentUser
from features.app_feedback.schemas import (
    AppFeedbackSubmitRequest,
    AppFeedbackResponse,
    AppFeedbackListResponse,
)
from features.app_feedback.service_async import AppFeedbackServiceAsync

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
