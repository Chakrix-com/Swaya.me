"""
Async service for global app feedback
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import CurrentUser
from persistence.models.app_feedback import AppFeedback
from features.app_feedback.schemas import (
    AppFeedbackSubmitRequest,
    AppFeedbackListResponse,
    AppFeedbackResponse,
)
from shared.utils.content_filter import check_content


class AppFeedbackServiceAsync:

    async def submit(
        self,
        db: AsyncSession,
        request: AppFeedbackSubmitRequest,
        current_user: Optional[CurrentUser],
        user_agent: Optional[str],
    ) -> AppFeedback:
        # Strip plain text from HTML for profanity check
        import re
        plain_text = re.sub(r'<[^>]+>', '', request.feedback_text).strip()
        if plain_text:
            check_content(plain_text, "feedback_text")

        if current_user:
            source_type = "user"
            user_id = current_user.user_id
            tenant_id = current_user.tenant_id
            user_email = current_user.email
            display_name = request.display_name or current_user.user.display_name if hasattr(current_user.user, 'display_name') else request.display_name
        else:
            source_type = "anonymous"
            user_id = None
            tenant_id = None
            user_email = None
            display_name = request.display_name

        feedback = AppFeedback(
            page_url=request.page_url,
            feedback_text=request.feedback_text,
            rating=request.rating,
            source_type=source_type,
            user_id=user_id,
            tenant_id=tenant_id,
            display_name=display_name,
            user_email=user_email,
            user_agent=user_agent,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    async def list_feedback(
        self,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        source_type: Optional[str] = None,
        rating: Optional[int] = None,
        search: Optional[str] = None,
        page_url_contains: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> AppFeedbackListResponse:
        filters = []
        if source_type:
            filters.append(AppFeedback.source_type == source_type)
        if rating is not None:
            filters.append(AppFeedback.rating == rating)
        if search:
            filters.append(AppFeedback.feedback_text.ilike(f'%{search}%'))
        if page_url_contains:
            filters.append(AppFeedback.page_url.ilike(f'%{page_url_contains}%'))
        if date_from:
            filters.append(AppFeedback.created_at >= date_from)
        if date_to:
            filters.append(AppFeedback.created_at <= date_to)

        count_q = select(func.count()).select_from(AppFeedback)
        if filters:
            count_q = count_q.where(and_(*filters))
        total_result = await db.execute(count_q)
        total = total_result.scalar_one()

        query = select(AppFeedback).order_by(AppFeedback.created_at.desc()).limit(limit).offset(offset)
        if filters:
            query = query.where(and_(*filters))
        result = await db.execute(query)
        items = result.scalars().all()

        return AppFeedbackListResponse(
            items=[AppFeedbackResponse.from_orm(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
