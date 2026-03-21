"""
Admin quiz APIs
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import require_super_admin
from features.quiz.platform_quiz_service_async import PlatformQuizServiceAsync
from features.quiz.schemas import PlatformQuizListResponse
from persistence.database_async import get_async_db

router = APIRouter()


@router.get("/quizzes", response_model=PlatformQuizListResponse)
async def list_platform_quizzes(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    tenant_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(draft|ready|archived)$"),
    min_questions: Optional[int] = Query(None, ge=0),
    max_questions: Optional[int] = Query(None, ge=0),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = Query(
        "created_at",
        pattern="^(created_at|updated_at|title|status|tenant_name|question_count)$",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    bounded_limit = max(1, min(limit, 200))
    bounded_offset = max(0, offset)
    service = PlatformQuizServiceAsync()
    return await service.list_platform_quizzes(
        db=db,
        limit=bounded_limit,
        offset=bounded_offset,
        search=search,
        tenant_id=tenant_id,
        status=status,
        min_questions=min_questions,
        max_questions=max_questions,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
