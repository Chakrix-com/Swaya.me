"""
Quiz Builder Service - Business logic for quiz CRUD operations
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from persistence.models.quiz import Quiz, Question, QuizStatus, QuizType, QuestionType
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


class QuizBuilderService:
    """Service for quiz builder operations"""
    
    def __init__(self, tier_service: TierService):
        self.tier_service = tier_service
    
    def create_quiz(
        self,
        db: Session,
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
            db.flush()
            event_id = event.id
        else:
            # Verify event exists and belongs to tenant
            event = db.query(Event).filter(
                Event.id == event_id,
                Event.tenant_id == current_user.tenant_id
            ).first()
            
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
        db.commit()
        db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    def get_quiz(
        self,
        db: Session,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Get quiz by ID"""
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        return self._to_quiz_response(quiz)
    
    def list_quizzes(
        self,
        db: Session,
        current_user: CurrentUser,
        event_id: Optional[int] = None
    ) -> List[QuizListResponse]:
        """List quizzes for tenant"""
        query = db.query(Quiz).filter(Quiz.tenant_id == current_user.tenant_id)
        
        if event_id:
            query = query.filter(Quiz.event_id == event_id)
        
        quizzes = query.order_by(Quiz.created_at.desc()).all()
        
        return [
            QuizListResponse(
                id=q.id,
                event_id=q.event_id,
                title=q.title,
                quiz_type=q.quiz_type,
                status=q.status,
                question_count=len(q.questions),
                created_at=q.created_at.isoformat()
            )
            for q in quizzes
        ]
    
    def update_quiz(
        self,
        db: Session,
        quiz_id: int,
        request: QuizUpdate,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Update quiz (only in DRAFT status)"""
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
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
        
        db.commit()
        db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    def delete_quiz(
        self,
        db: Session,
        quiz_id: int,
        current_user: CurrentUser
    ):
        """Delete quiz (only in DRAFT status)"""
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only delete quizzes in DRAFT status")
        
        db.delete(quiz)
        db.commit()
    
    def publish_quiz(
        self,
        db: Session,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Publish quiz (validate and change status to READY)"""
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already published")
        
        # Validate quiz
        self._validate_quiz(quiz)
        
        # Change status
        quiz.status = QuizStatus.READY
        db.commit()
        db.refresh(quiz)
        
        return self._to_quiz_response(quiz)
    
    def unpublish_quiz(
        self,
        db: Session,
        quiz_id: int,
        current_user: CurrentUser
    ) -> QuizResponse:
        """Unpublish quiz (revert status to DRAFT for editing)"""
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status == QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Quiz is already in DRAFT status")
        
        # Change status back to DRAFT
        quiz.status = QuizStatus.DRAFT
        db.commit()
        db.refresh(quiz)
        
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
                if not question.options or len(question.options) < 2:
                    raise QuizValidationError("MCQ questions must have at least 2 options")
                if len(question.options) > 10:
                    raise QuizValidationError("MCQ questions can have at most 10 options")
                if (
                    question.correct_answer_index is not None
                    and not (0 <= question.correct_answer_index < len(question.options))
                ):
                    raise QuizValidationError("MCQ questions must have valid correct answer index")
                if quiz.quiz_type != QuizType.POLL and question.correct_answer_index is None:
                    raise QuizValidationError("MCQ questions must have a correct answer for quiz mode")
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
            quiz_type=quiz.quiz_type,
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
                    } if q.option_images else None,
                    points=q.points,
                    max_time_seconds=q.max_time_seconds,
                )
                for q in sorted(quiz.questions, key=lambda x: x.order)
            ],
            question_count=len(quiz.questions),
            created_at=quiz.created_at.isoformat(),
            updated_at=quiz.updated_at.isoformat()
        )
