"""
Feedback service for quiz participants and authenticated users (Async)
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import CurrentUser
from persistence.models.core import User, UserRole
from persistence.models.quiz import Participant, Quiz, QuizFeedback, QuizSession
from features.quiz.schemas import FeedbackListResponse, FeedbackResponse, FeedbackSubmitRequest
from shared.exceptions.quiz import ParticipantNotFoundError, QuizNotFoundError, SessionNotFoundError


class FeedbackServiceAsync:
    """Async service for quiz feedback"""

    async def submit_participant_feedback(
        self,
        db: AsyncSession,
        session_token: str,
        request: FeedbackSubmitRequest,
    ) -> dict:
        """Submit feedback from a participant identified by session token"""
        participant_result = await db.execute(
            select(Participant).filter(
                Participant.session_token == session_token,
                Participant.is_active == True,
            )
        )
        participant = participant_result.scalar_one_or_none()
        if not participant:
            raise ParticipantNotFoundError("Invalid or expired participant session")

        session_result = await db.execute(
            select(QuizSession).filter(QuizSession.id == participant.session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError("Session not found")

        quiz_result = await db.execute(
            select(Quiz).filter(Quiz.id == session.quiz_id)
        )
        quiz = quiz_result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        feedback = QuizFeedback(
            tenant_id=session.tenant_id,
            quiz_id=quiz.id,
            session_id=session.id,
            participant_id=participant.id,
            source_type="participant",
            display_name=request.display_name or participant.display_name,
            rating=request.rating,
            feedback_text=request.feedback_text.strip(),
        )
        db.add(feedback)
        await db.commit()
        return {"success": True, "message": "Feedback submitted"}

    async def submit_user_feedback(
        self,
        db: AsyncSession,
        current_user: CurrentUser,
        request: FeedbackSubmitRequest,
    ) -> dict:
        """Submit feedback from an authenticated user"""
        if not request.quiz_id:
            raise QuizNotFoundError("quiz_id is required for authenticated feedback")

        quiz_result = await db.execute(
            select(Quiz).filter(Quiz.id == request.quiz_id)
        )
        quiz = quiz_result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if current_user.user.role != UserRole.super_admin and quiz.tenant_id != current_user.tenant_id:
            raise QuizNotFoundError("Quiz not found")

        if request.session_id:
            session_result = await db.execute(
                select(QuizSession).filter(
                    QuizSession.id == request.session_id,
                    QuizSession.quiz_id == quiz.id,
                )
            )
            session = session_result.scalar_one_or_none()
            if not session:
                raise SessionNotFoundError("Session not found")

        feedback = QuizFeedback(
            tenant_id=quiz.tenant_id,
            quiz_id=quiz.id,
            session_id=request.session_id,
            user_id=current_user.user_id,
            source_type="user",
            display_name=request.display_name or current_user.user.full_name or current_user.user.email,
            rating=request.rating,
            feedback_text=request.feedback_text.strip(),
        )
        db.add(feedback)
        await db.commit()
        return {"success": True, "message": "Feedback submitted"}

    async def list_feedback(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        quiz_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        source_type: Optional[str] = None,
        rating: Optional[int] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> FeedbackListResponse:
        """List feedback entries (super admin only endpoint uses this)"""
        filters = []
        if quiz_id:
            filters.append(QuizFeedback.quiz_id == quiz_id)
        if tenant_id:
            filters.append(QuizFeedback.tenant_id == tenant_id)
        if source_type:
            filters.append(QuizFeedback.source_type == source_type)
        if rating:
            filters.append(QuizFeedback.rating == rating)
        if date_from:
            filters.append(QuizFeedback.created_at >= date_from)
        if date_to:
            filters.append(QuizFeedback.created_at <= date_to)
        if search:
            like_pattern = f"%{search.strip()}%"
            filters.append(QuizFeedback.feedback_text.ilike(like_pattern))

        total_stmt = select(func.count()).select_from(QuizFeedback)
        if filters:
            total_stmt = total_stmt.filter(*filters)
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(
                QuizFeedback,
                Quiz.title.label("quiz_title"),
                User.email.label("user_email"),
            )
            .join(Quiz, Quiz.id == QuizFeedback.quiz_id)
            .outerjoin(User, User.id == QuizFeedback.user_id)
            .order_by(QuizFeedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if filters:
            stmt = stmt.filter(*filters)

        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            feedback = row[0]
            items.append(
                FeedbackResponse(
                    id=feedback.id,
                    quiz_id=feedback.quiz_id,
                    quiz_title=row.quiz_title,
                    tenant_id=feedback.tenant_id,
                    session_id=feedback.session_id,
                    participant_id=feedback.participant_id,
                    user_id=feedback.user_id,
                    source_type=feedback.source_type,
                    display_name=feedback.display_name,
                    user_email=row.user_email,
                    rating=feedback.rating,
                    feedback_text=feedback.feedback_text,
                    created_at=feedback.created_at,
                )
            )

        return FeedbackListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
