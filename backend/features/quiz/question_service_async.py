"""
Question Management Service - Add, edit, delete, reorder questions (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, contains_eager
from typing import List

from persistence.models.quiz import Quiz, Question, QuizStatus, QuestionType
from features.quiz.schemas import QuestionCreate, QuestionUpdate, QuestionResponse
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, InvalidQuizStatusError,
    TierLimitExceededError
)
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser


class QuestionServiceAsync:
    """Async service for question management"""
    
    def __init__(self, tier_service: TierService):
        self.tier_service = tier_service
    
    async def add_question(
        self,
        db: AsyncSession,
        quiz_id: int,
        request: QuestionCreate,
        current_user: CurrentUser
    ) -> QuestionResponse:
        """
        Add question to quiz
        
        Args:
            db: Database session
            quiz_id: Quiz ID
            request: Question data
            current_user: Current user
            
        Returns:
            Created question
            
        Raises:
            QuizNotFoundError: If quiz not found
            InvalidQuizStatusError: If quiz not in DRAFT
            TierLimitExceededError: If question limit reached
        """
        # Get quiz
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
            raise InvalidQuizStatusError("Can only add questions to DRAFT quizzes")
        
        # Check tier limits
        current_count = len(quiz.questions)
        tier = current_user.tenant.tier
        
        can_add = await self.tier_service.check_question_limit(
            current_user.tenant_id,
            quiz_id,
            tier,
            current_count
        )
        
        if not can_add:
            raise TierLimitExceededError(
                f"Question limit reached for {tier.value} tier"
            )
        
        # Calculate next order
        max_order = max([q.order for q in quiz.questions], default=-1)
        next_order = max_order + 1
        
        # Create question
        question = Question(
            quiz_id=quiz_id,
            question_type=request.question_type,
            text=request.text,
            options=request.options,
            correct_answer_index=request.correct_answer_index,
            order=next_order
        )
        
        db.add(question)
        await db.commit()
        await db.refresh(question)
        
        return self._to_question_response(question)
    
    async def update_question(
        self,
        db: AsyncSession,
        question_id: int,
        request: QuestionUpdate,
        current_user: CurrentUser
    ) -> QuestionResponse:
        """Update question"""
        result = await db.execute(
            select(Question).join(Quiz).filter(
                Question.id == question_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        question = result.scalar_one_or_none()
        
        if not question:
            raise QuestionNotFoundError("Question not found")
        
        if question.quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only edit questions in DRAFT quizzes")
        
        # Update fields
        if request.question_type is not None:
            question.question_type = request.question_type
        if request.text is not None:
            question.text = request.text
        if request.options is not None:
            question.options = request.options
        if request.correct_answer_index is not None:
            question.correct_answer_index = request.correct_answer_index
        
        await db.commit()
        await db.refresh(question)
        
        return self._to_question_response(question)
    
    async def delete_question(
        self,
        db: AsyncSession,
        question_id: int,
        current_user: CurrentUser
    ):
        """Delete question"""
        result = await db.execute(
            select(Question)
            .join(Quiz)
            .filter(
                Question.id == question_id,
                Quiz.tenant_id == current_user.tenant_id
            )
            .options(contains_eager(Question.quiz))
        )
        question = result.scalar_one_or_none()
        
        if not question:
            raise QuestionNotFoundError("Question not found")
        
        if question.quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only delete questions from DRAFT quizzes")
        
        quiz_id = question.quiz_id
        deleted_order = question.order
        
        # Delete question
        await db.delete(question)
        await db.flush()
        
        # Reorder remaining questions
        result = await db.execute(
            select(Question).filter(
                Question.quiz_id == quiz_id,
                Question.order > deleted_order
            )
        )
        remaining = result.scalars().all()
        
        for q in remaining:
            q.order -= 1
        
        await db.commit()
    
    async def reorder_questions(
        self,
        db: AsyncSession,
        quiz_id: int,
        question_orders: List[tuple[int, int]],
        current_user: CurrentUser
    ):
        """
        Reorder questions
        
        Args:
            question_orders: List of (question_id, new_order) tuples
        """
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
            raise InvalidQuizStatusError("Can only reorder questions in DRAFT quizzes")
        
        # Update orders
        for question_id, new_order in question_orders:
            result = await db.execute(
                select(Question).filter(
                    Question.id == question_id,
                    Question.quiz_id == quiz_id
                )
            )
            question = result.scalar_one_or_none()
            
            if question:
                question.order = new_order
        
        await db.commit()
    
    def _to_question_response(self, question: Question) -> QuestionResponse:
        """Convert question to response model"""
        return QuestionResponse(
            id=question.id,
            question_type=question.question_type,
            text=question.text,
            options=question.options,
            order=question.order,
            correct_answer_index=question.correct_answer_index
        )
