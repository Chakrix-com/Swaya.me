"""
Quiz Builder Service - Business logic for quiz CRUD operations (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import os

from persistence.models.quiz import Quiz, Question, QuizStatus, QuestionType
from persistence.models.core import Event
from features.quiz.schemas import (
    QuizCreate, QuizUpdate, QuizResponse, QuizListResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse
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
        
        return [
            QuizListResponse(
                id=q.id,
                event_id=q.event_id,
                title=q.title,
                status=q.status,
                question_count=len(q.questions),
                created_at=q.created_at.isoformat()
            )
            for q in quizzes
        ]
    
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
                
                if question.correct_answer_index is None or question.correct_answer_index < 0 or question.correct_answer_index > 3:
                    raise QuizValidationError("MCQ questions must have valid correct answer index")
            elif question.question_type == QuestionType.WORD_CLOUD:
                # Word cloud questions don't need options or correct answer
                pass
    
    def _to_quiz_response(self, quiz: Quiz) -> QuizResponse:
        """Convert quiz to response model"""
        # Get base URL from environment
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        
        return QuizResponse(
            id=quiz.id,
            event_id=quiz.event_id,
            title=quiz.title,
            description=quiz.description,
            status=quiz.status,
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
                for q in sorted(quiz.questions, key=lambda x: x.order)
            ],
            question_count=len(quiz.questions),
            created_at=quiz.created_at.isoformat(),
            updated_at=quiz.updated_at.isoformat()
        )
