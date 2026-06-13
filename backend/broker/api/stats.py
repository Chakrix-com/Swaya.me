from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timedelta

from persistence.database_async import get_async_db
from core.auth.dependencies import get_current_user, CurrentUser, require_super_admin
from core.stats.service_async import StatsServiceAsync
from core.stats.schemas import StatsResponse
from persistence.models.core import UserRole
from features.quiz.feedback_service_async import FeedbackServiceAsync
from features.quiz.schemas import FeedbackListResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get application statistics
    - Super Admin: Platform-wide stats (all tenants)
    - Admin: Tenant-specific stats
    - Regular users: 403 Forbidden
    """
    if current_user.user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access statistics"
        )
    
    service = StatsServiceAsync(db)
    
    if current_user.user.role == UserRole.super_admin:
        return await service.get_platform_stats()
    
    return await service.get_tenant_stats(current_user.tenant_id)


@router.get("/stats/weekly-active-hosts")
async def get_weekly_active_hosts(
    days: int = Query(7, ge=1, le=30),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Returns daily active host counts for the last N days.
    Super admin: platform-wide. Admin: tenant-scoped.
    A host is counted on a day if they ran at least one quiz session that day.
    """
    if current_user.user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Admins only")

    if current_user.user.role == UserRole.admin:
        sql = text("""
            SELECT
                DATE(qs.created_at) AS day,
                COUNT(DISTINCT e.creator_id) AS active_hosts
            FROM quiz_sessions qs
            JOIN quizzes q ON q.id = qs.quiz_id
            JOIN events e ON e.id = q.event_id
            WHERE qs.created_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
              AND qs.tenant_id = :tenant_id
            GROUP BY DATE(qs.created_at)
            ORDER BY day ASC
        """)
        result = await db.execute(sql, {"days": days, "tenant_id": current_user.tenant_id})
    else:
        sql = text("""
            SELECT
                DATE(qs.created_at) AS day,
                COUNT(DISTINCT e.creator_id) AS active_hosts
            FROM quiz_sessions qs
            JOIN quizzes q ON q.id = qs.quiz_id
            JOIN events e ON e.id = q.event_id
            WHERE qs.created_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            GROUP BY DATE(qs.created_at)
            ORDER BY day ASC
        """)
        result = await db.execute(sql, {"days": days})
    rows = result.fetchall()
    return [{"day": str(row.day), "active_hosts": row.active_hosts} for row in rows]


@router.get("/feedback", response_model=FeedbackListResponse)
async def get_feedback(
    limit: int = 50,
    offset: int = 0,
    quiz_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    source_type: Optional[str] = Query(None, pattern="^(participant|user)$"),
    rating: Optional[int] = Query(None, ge=1, le=5),
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    _: object = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get quiz feedback entries (super admin only)"""
    bounded_limit = max(1, min(limit, 200))
    bounded_offset = max(0, offset)
    service = FeedbackServiceAsync()
    return await service.list_feedback(
        db=db,
        limit=bounded_limit,
        offset=bounded_offset,
        quiz_id=quiz_id,
        tenant_id=tenant_id,
        source_type=source_type,
        rating=rating,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
