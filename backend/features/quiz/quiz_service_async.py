"""
Quiz Builder Service - Business logic for quiz CRUD operations (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import os

from persistence.models.quiz import (
    Quiz,
    Question,
    QuizStatus,
    QuizType,
    QuestionType,
    TemplateScope,
    QuizSession,
    QuizSessionStatus,
)
from persistence.models.core import Event, UserRole
from features.quiz.schemas import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    TemplateDesignationRequest, TemplateQuizListItemResponse
)
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, QuizValidationError,
    InvalidQuizStatusError, TierLimitExceededError
)
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser
from core.storage import ImageService


class QuizBuilderServiceAsync:
    """Async service for quiz builder operations"""
    
    def __init__(self, tier_service: TierService):
        self.tier_service = tier_service
    
    async def create_quiz(
        self,
        db: AsyncSession,
        request: QuizCreate,
        current_user: CurrentUser
    ) -> QuizResponse:
        """
        Create new quiz in DRAFT status
        
        Args:
            db: Database session
            request: Quiz creation data
            current_user: Current authenticated user
            
        Returns:
            Created quiz
            
        Raises:
            QuizNotFoundError: If event not found
        """
        # Auto-create event if not provided
        event_id = request.event_id
        
        if not event_id:
            # Create a default event for this quiz
            event = Event(
                tenant_id=current_user.tenant_id,
                creator_id=current_user.user_id,
                title=f"Quiz Session - {request.title}",
                description=None,
                join_code=None
            )
            db.add(event)
            await db.flush()
            event_id = event.id
        else:
            # Verify event exists and belongs to tenant
            result = await db.execute(
                select(Event).filter(
                    Event.id == event_id,
                    Event.tenant_id == current_user.tenant_id
                )
            )
            event = result.scalar_one_or_none()
            
            if not event:
                raise QuizNotFoundError("Event not found")
        
        # Create quiz
        quiz = Quiz(
            tenant_id=current_user.tenant_id,
            event_id=event_id,
            title=request.title,
            description=request.description,
            quiz_type=QuizType(request.quiz_type.value),
            status=QuizStatus.DRAFT
        )
        
        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    async def get_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Get quiz by ID"""
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        return self._to_quiz_response(quiz)
    
    async def list_quizzes(
        self,
        db: AsyncSession,
        current_user: CurrentUser,
        event_id: Optional[int] = None
    ) -> List[QuizListResponse]:
        """List quizzes for tenant"""
        query = select(Quiz).filter(Quiz.tenant_id == current_user.tenant_id)
        
        if event_id:
            query = query.filter(Quiz.event_id == event_id)
        
        # Eagerly load questions to avoid lazy loading in async context
        query = query.options(selectinload(Quiz.questions))
        query = query.order_by(Quiz.created_at.desc())
        result = await db.execute(query)
        quizzes = result.scalars().all()

        active_session_rows = await db.execute(
            select(
                QuizSession.quiz_id,
                func.max(QuizSession.id).label("active_session_id")
            ).filter(
                QuizSession.tenant_id == current_user.tenant_id,
                QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE])
            ).group_by(QuizSession.quiz_id)
        )
        active_session_map = {
            row.quiz_id: row.active_session_id
            for row in active_session_rows
        }
        
        return [
            QuizListResponse(
                id=q.id,
                event_id=q.event_id,
                title=q.title,
                quiz_type=q.quiz_type,
                status=q.status,
                is_template=q.is_template,
                template_scope=q.template_scope,
                question_count=len(q.questions),
                has_active_session=q.id in active_session_map,
                active_session_id=active_session_map.get(q.id),
                created_at=q.created_at.isoformat()
            )
            for q in quizzes
        ]

    async def set_template_status(
        self,
        db: AsyncSession,
        quiz_id: int,
        request: TemplateDesignationRequest,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Mark/unmark a quiz as template"""
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        if request.is_template:
            quiz.is_template = True
            if current_user.user.role == UserRole.super_admin:
                quiz.template_scope = TemplateScope.GLOBAL
            else:
                quiz.template_scope = TemplateScope.TENANT
        else:
            quiz.is_template = False
            quiz.template_scope = TemplateScope.TENANT

        await db.commit()
        await db.refresh(quiz)
        return self._to_quiz_response(quiz)

    async def list_available_templates(
        self,
        db: AsyncSession,
        current_user: CurrentUser
    ) -> List[TemplateQuizListItemResponse]:
        """List templates visible to current user"""
        result = await db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .order_by(Quiz.updated_at.desc())
        )
        all_quizzes = result.scalars().all()
        templates = []
        for quiz in all_quizzes:
            scope_value = quiz.template_scope.value if hasattr(quiz.template_scope, "value") else str(quiz.template_scope)
            if not quiz.is_template:
                continue
            if quiz.tenant_id == current_user.tenant_id or scope_value == TemplateScope.GLOBAL.value:
                templates.append(quiz)

        return [
            TemplateQuizListItemResponse(
                id=q.id,
                title=q.title,
                description=q.description,
                quiz_type=q.quiz_type,
                status=q.status,
                question_count=len(q.questions),
                template_scope=q.template_scope,
                tenant_id=q.tenant_id,
                created_at=q.created_at,
            )
            for q in templates
        ]

    async def create_quiz_from_template(
        self,
        db: AsyncSession,
        template_quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Create a new draft quiz from a visible template"""
        template_result = await db.execute(
            select(Quiz)
            .filter(Quiz.id == template_quiz_id)
            .options(selectinload(Quiz.questions))
        )
        template_quiz = template_result.scalar_one_or_none()
        if not template_quiz or not template_quiz.is_template:
            raise QuizNotFoundError("Template quiz not found")
        scope_value = template_quiz.template_scope.value if hasattr(template_quiz.template_scope, "value") else str(template_quiz.template_scope)
        if template_quiz.tenant_id != current_user.tenant_id and scope_value != TemplateScope.GLOBAL.value:
            raise QuizNotFoundError("Template quiz not found")

        tier_limits = await self.tier_service.get_tier_config(db, current_user.tenant.tier)
        max_questions = tier_limits["max_questions"]
        if len(template_quiz.questions) > max_questions:
            raise TierLimitExceededError(f"Template has {len(template_quiz.questions)} questions, but your tier allows {max_questions}")

        event = Event(
            tenant_id=current_user.tenant_id,
            creator_id=current_user.user_id,
            title=f"Template Session - {template_quiz.title}",
            description=None,
            join_code=None
        )
        db.add(event)
        await db.flush()

        copy_title = f"{template_quiz.title} (Template Copy)"
        if len(copy_title) > 255:
            copy_title = f"{template_quiz.title[:239]} (Template Copy)"

        new_quiz = Quiz(
            tenant_id=current_user.tenant_id,
            event_id=event.id,
            title=copy_title,
            description=template_quiz.description,
            quiz_type=template_quiz.quiz_type,
            status=QuizStatus.DRAFT,
            is_template=False,
            template_scope=TemplateScope.TENANT,
        )
        db.add(new_quiz)
        await db.flush()

        for question in sorted(template_quiz.questions, key=lambda q: q.order):
            db.add(
                Question(
                    quiz_id=new_quiz.id,
                    question_type=question.question_type,
                    text=question.text,
                    order=question.order,
                    options=list(question.options) if question.options else None,
                    correct_answer_index=question.correct_answer_index,
                    question_image_url=question.question_image_url,
                    option_images=dict(question.option_images) if question.option_images else None,
                )
            )

        await db.commit()

        quiz_result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == new_quiz.id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        created_quiz = quiz_result.scalar_one()
        return self._to_quiz_response(created_quiz)
    
    async def update_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        request: QuizUpdate,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Update quiz (only in DRAFT status)"""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only edit quizzes in DRAFT status")
        
        # Update fields
        if request.title is not None:
            quiz.title = request.title
        if request.description is not None:
            quiz.description = request.description
        if request.quiz_type is not None:
            quiz.quiz_type = QuizType(request.quiz_type.value)
        
        await db.commit()
        await db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    async def delete_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ):
        """Delete quiz (only in DRAFT status)"""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only delete quizzes in DRAFT status")
        
        await db.delete(quiz)
        await db.commit()
    
    async def publish_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Publish quiz (validate and change status to READY)"""
        result = await db.execute(
            select(Quiz)
            .filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(selectinload(Quiz.questions))
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already published")
        
        # Validate quiz
        self._validate_quiz(quiz)
        
        # Change status
        quiz.status = QuizStatus.READY
        await db.commit()
        await db.refresh(quiz)
        
        return self._to_quiz_response(quiz)

    async def duplicate_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Duplicate quiz and all its questions as a new DRAFT quiz"""
        try:
            result = await db.execute(
                select(Quiz)
                .filter(
                    Quiz.id == quiz_id,
                    Quiz.tenant_id == current_user.tenant_id
                )
                .options(selectinload(Quiz.questions))
            )
            source_quiz = result.scalar_one_or_none()

            if not source_quiz:
                raise QuizNotFoundError("Quiz not found")

            duplicate_title = f"{source_quiz.title} (Copy)"
            if len(duplicate_title) > 255:
                duplicate_title = f"{source_quiz.title[:248]} (Copy)"

            duplicated_quiz = Quiz(
                tenant_id=current_user.tenant_id,
                event_id=source_quiz.event_id,
                title=duplicate_title,
                description=source_quiz.description,
                quiz_type=source_quiz.quiz_type,
                status=QuizStatus.DRAFT
            )
            db.add(duplicated_quiz)
            await db.flush()

            for question in sorted(source_quiz.questions, key=lambda q: q.order):
                db.add(
                    Question(
                        quiz_id=duplicated_quiz.id,
                        question_type=question.question_type,
                        text=question.text,
                        order=question.order,
                        options=list(question.options) if question.options else None,
                        correct_answer_index=question.correct_answer_index,
                        question_image_url=question.question_image_url,
                        option_images=dict(question.option_images) if question.option_images else None,
                    )
                )

            await db.commit()

            duplicated_result = await db.execute(
                select(Quiz)
                .filter(
                    Quiz.id == duplicated_quiz.id,
                    Quiz.tenant_id == current_user.tenant_id
                )
                .options(selectinload(Quiz.questions))
            )
            duplicated_quiz = duplicated_result.scalar_one()

            return self._to_quiz_response(duplicated_quiz)
        except QuizNotFoundError:
            raise
        except Exception as e:
            await db.rollback()
            raise QuizValidationError(f"Failed to duplicate quiz: {str(e)}")
    
    async def unpublish_quiz(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Unpublish quiz (revert status to DRAFT for editing)"""
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status == QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already in DRAFT status")
        
        # Change status back to DRAFT
        quiz.status = QuizStatus.DRAFT
        await db.commit()
        await db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    def _validate_quiz(self, quiz: Quiz):
        """Validate quiz before publishing"""
        if not quiz.questions:
            raise QuizValidationError("Quiz must have at least one question")
        
        if len(quiz.questions) < 1:
            raise QuizValidationError("Quiz must have at least one question")
        
        # Validate each question
        for question in quiz.questions:
            if not question.text or not question.text.strip():
                raise QuizValidationError("All questions must have text")
            
            # Validate based on question type
            if question.question_type == QuestionType.MCQ:
                if not question.options or len(question.options) != 4:
                    raise QuizValidationError("MCQ questions must have exactly 4 options")
                if (
                    question.correct_answer_index is not None
                    and (question.correct_answer_index < 0 or question.correct_answer_index > 3)
                ):
                    raise QuizValidationError("MCQ questions must have valid correct answer index")
                if quiz.quiz_type != QuizType.POLL and question.correct_answer_index is None:
                    raise QuizValidationError("MCQ questions must have a correct answer for quiz mode")
            elif question.question_type == QuestionType.SCALE:
                if not question.options or len(question.options) != 5:
                    raise QuizValidationError("Scale questions must have exactly 5 options")
                if (
                    question.correct_answer_index is not None
                    and (question.correct_answer_index < 0 or question.correct_answer_index > 4)
                ):
                    raise QuizValidationError("Scale questions must have a valid correct answer index")
                if quiz.quiz_type != QuizType.POLL and question.correct_answer_index is None:
                    raise QuizValidationError("Scale questions must have a correct answer for quiz mode")
            elif question.question_type == QuestionType.WORD_CLOUD:
                # Word cloud questions don't need options or correct answer
                pass
            elif question.question_type in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH):
                if question.options is not None and len(question.options) > 1:
                    raise QuizValidationError("Text questions can have at most one expected answer")
                if question.correct_answer_index is not None:
                    raise QuizValidationError("Text questions cannot have a correct answer index")
    
    def _to_quiz_response(self, quiz: Quiz) -> QuizResponse:
        """Convert quiz to response model"""
        # Get base URL from environment
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        loaded_questions = quiz.__dict__.get("questions") or []
        
        return QuizResponse(
            id=quiz.id,
            event_id=quiz.event_id,
            title=quiz.title,
            description=quiz.description,
            quiz_type=quiz.quiz_type,
            status=quiz.status,
            is_template=quiz.is_template,
            template_scope=quiz.template_scope,
            questions=[
                QuestionResponse(
                    id=q.id,
                    question_type=q.question_type,
                    text=q.text,
                    options=q.options,
                    order=q.order,
                    correct_answer_index=q.correct_answer_index,
                    question_image_url=ImageService.to_absolute_url(
                        q.question_image_url, base_url
                    ),
                    option_images={
                        key: ImageService.to_absolute_url(path, base_url)
                        for key, path in (q.option_images or {}).items()
                    } if q.option_images else None
                )
                for q in sorted(loaded_questions, key=lambda x: x.order)
            ],
            question_count=len(loaded_questions),
            created_at=quiz.created_at.isoformat(),
            updated_at=quiz.updated_at.isoformat()
        )
