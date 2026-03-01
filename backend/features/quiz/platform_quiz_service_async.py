"""
Platform-wide quiz listing service (super admin)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from features.quiz.schemas import PlatformQuizListItemResponse, PlatformQuizListResponse
from persistence.models.core import Tenant
from persistence.models.quiz import Question, Quiz, QuizStatus


class PlatformQuizServiceAsync:
    """Async service for platform quiz listing with filters and sorting"""

    async def list_platform_quizzes(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        search: Optional[str] = None,
        tenant_id: Optional[int] = None,
        status: Optional[str] = None,
        min_questions: Optional[int] = None,
        max_questions: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PlatformQuizListResponse:
        question_count_subq = (
            select(
                Question.quiz_id.label("quiz_id"),
                func.count(Question.id).label("question_count"),
            )
            .group_by(Question.quiz_id)
            .subquery()
        )

        question_count_expr = func.coalesce(question_count_subq.c.question_count, 0)

        stmt = (
            select(
                Quiz.id,
                Quiz.event_id,
                Quiz.tenant_id,
                Tenant.name.label("tenant_name"),
                Quiz.title,
                Quiz.status,
                question_count_expr.label("question_count"),
                Quiz.created_at,
                Quiz.updated_at,
            )
            .join(Tenant, Tenant.id == Quiz.tenant_id)
            .outerjoin(question_count_subq, question_count_subq.c.quiz_id == Quiz.id)
        )

        if search:
            stmt = stmt.filter(Quiz.title.ilike(f"%{search.strip()}%"))
        if tenant_id:
            stmt = stmt.filter(Quiz.tenant_id == tenant_id)
        if status:
            try:
                status_enum = QuizStatus(status)
                stmt = stmt.filter(Quiz.status == status_enum)
            except ValueError:
                stmt = stmt.filter(False)
        if min_questions is not None:
            stmt = stmt.filter(question_count_expr >= min_questions)
        if max_questions is not None:
            stmt = stmt.filter(question_count_expr <= max_questions)
        if date_from:
            stmt = stmt.filter(Quiz.created_at >= date_from)
        if date_to:
            stmt = stmt.filter(Quiz.created_at <= date_to)

        sortable_columns = {
            "created_at": Quiz.created_at,
            "updated_at": Quiz.updated_at,
            "title": Quiz.title,
            "status": Quiz.status,
            "tenant_name": Tenant.name,
            "question_count": question_count_expr,
        }
        sort_column = sortable_columns.get(sort_by, Quiz.created_at)
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc(), Quiz.id.asc())
        else:
            stmt = stmt.order_by(sort_column.desc(), Quiz.id.desc())

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        data_result = await db.execute(stmt.limit(limit).offset(offset))
        rows = data_result.all()

        items = [
            PlatformQuizListItemResponse(
                id=row.id,
                event_id=row.event_id,
                tenant_id=row.tenant_id,
                tenant_name=row.tenant_name,
                title=row.title,
                status=row.status,
                question_count=row.question_count or 0,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

        return PlatformQuizListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
