"""
Question Management Service - Add, edit, delete, reorder questions (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, contains_eager
from typing import List

from persistence.models.quiz import (
    Quiz,
    Question,
    Answer,
    SessionQuestionTiming,
    QuizStatus,
    QuestionType,
)
from features.quiz.schemas import QuestionCreate, QuestionUpdate, QuestionResponse
from shared.exceptions.quiz import (
    QuizNotFoundError, QuestionNotFoundError, InvalidQuizStatusError,
    TierLimitExceededError
)
from shared.utils.content_filter import check_content
from shared.utils.html_sanitizer import sanitize_html, sanitize_plain
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser
from core.storage import ImageService


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
            db,
            current_user.tenant_id,
            quiz_id,
            tier,
            current_count
        )
        
        if not can_add:
            raise TierLimitExceededError(
                f"Question limit reached for {tier.value} tier"
            )
        
        # Content filter + HTML sanitization (skip for AI-generated content — Gemini has its own safety filters)
        if not getattr(request, 'from_ai', False):
            check_content(request.text, "Question text")
            if request.options:
                for i, opt in enumerate(request.options):
                    check_content(opt, f"Option {i + 1}")

        sanitized_text = sanitize_html(request.text)
        sanitized_options = [sanitize_plain(o) for o in request.options] if request.options else request.options
        sanitized_explanation = sanitize_html(request.answer_explanation) if request.answer_explanation else request.answer_explanation

        # Calculate next order
        max_order = max([q.order for q in quiz.questions], default=-1)
        next_order = max_order + 1

        # Create question
        question = Question(
            quiz_id=quiz_id,
            question_type=request.question_type,
            text=sanitized_text,
            options=sanitized_options,
            correct_answer_index=request.correct_answer_index,
            correct_answer_indices=request.correct_answer_indices,
            reveal_answer_count=request.reveal_answer_count,
            question_image_url=request.question_image_url,
            question_video_url=request.question_video_url,
            option_images=request.option_images,
            points=request.points,
            max_time_seconds=request.max_time_seconds,
            negative_points=request.negative_points,
            is_required=request.is_required,
            answer_explanation=sanitized_explanation,
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
            raise InvalidQuizStatusError("Can only edit questions in DRAFT quizzes")

        # Content filter + HTML sanitization (skip for AI-generated content — Gemini has its own safety filters)
        if not getattr(request, 'from_ai', False):
            if "text" in request.model_fields_set:
                check_content(request.text, "Question text")
            if "options" in request.model_fields_set and request.options:
                for i, opt in enumerate(request.options):
                    check_content(opt, f"Option {i + 1}")

        # Update fields
        if "question_type" in request.model_fields_set:
            question.question_type = request.question_type
        if "text" in request.model_fields_set:
            question.text = sanitize_html(request.text)
        if "options" in request.model_fields_set:
            question.options = [sanitize_plain(o) for o in request.options] if request.options else request.options
        if "correct_answer_index" in request.model_fields_set:
            question.correct_answer_index = request.correct_answer_index
        if "correct_answer_indices" in request.model_fields_set:
            question.correct_answer_indices = request.correct_answer_indices
        if "reveal_answer_count" in request.model_fields_set:
            question.reveal_answer_count = request.reveal_answer_count
        if "question_image_url" in request.model_fields_set:
            question.question_image_url = request.question_image_url
        if "question_video_url" in request.model_fields_set:
            question.question_video_url = request.question_video_url
        if "option_images" in request.model_fields_set:
            question.option_images = request.option_images
        if "points" in request.model_fields_set:
            question.points = request.points
        if "max_time_seconds" in request.model_fields_set:
            question.max_time_seconds = request.max_time_seconds
        if "negative_points" in request.model_fields_set:
            question.negative_points = request.negative_points
        if "is_required" in request.model_fields_set:
            question.is_required = request.is_required
        if "answer_explanation" in request.model_fields_set:
            question.answer_explanation = sanitize_html(request.answer_explanation) if request.answer_explanation else request.answer_explanation

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

        # Remove dependent rows first to avoid FK nullification errors on async flush.
        await db.execute(delete(Answer).filter(Answer.question_id == question_id))
        await db.execute(delete(SessionQuestionTiming).filter(SessionQuestionTiming.question_id == question_id))

        # Best-effort cleanup of image files.
        if question.question_image_url:
            ImageService.delete_image(question.question_image_url)
        if question.option_images:
            for image_path in question.option_images.values():
                if image_path:
                    ImageService.delete_image(image_path)
        
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
    
    async def duplicate_question(
        self,
        db: AsyncSession,
        quiz_id: int,
        question_id: int,
        current_user: CurrentUser
    ) -> QuestionResponse:
        """Duplicate a question, appending the copy after the original."""
        result = await db.execute(
            select(Question)
            .join(Quiz)
            .filter(
                Question.id == question_id,
                Question.quiz_id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id,
            )
            .options(contains_eager(Question.quiz))
        )
        question = result.scalar_one_or_none()
        if not question:
            raise QuestionNotFoundError("Question not found")
        if question.quiz.status != QuizStatus.DRAFT:
            raise InvalidQuizStatusError("Can only duplicate questions in DRAFT quizzes")

        # Shift all questions after this one down by 1
        await db.execute(
            select(Question).filter(
                Question.quiz_id == quiz_id,
                Question.order > question.order,
            )
        )
        after_result = await db.execute(
            select(Question).filter(
                Question.quiz_id == quiz_id,
                Question.order > question.order,
            )
        )
        for q in after_result.scalars().all():
            q.order += 1

        new_order = question.order + 1
        copy = Question(
            quiz_id=question.quiz_id,
            question_type=question.question_type,
            text=question.text,
            order=new_order,
            options=list(question.options) if question.options else None,
            correct_answer_index=question.correct_answer_index,
            correct_answer_indices=list(question.correct_answer_indices) if question.correct_answer_indices else None,
            reveal_answer_count=getattr(question, 'reveal_answer_count', False) or False,
            question_image_url=None,
            question_video_url=question.question_video_url,
            option_images=None,
            points=question.points,
            max_time_seconds=question.max_time_seconds,
            negative_points=getattr(question, 'negative_points', 0) or 0,
            is_required=getattr(question, 'is_required', False) or False,
            answer_explanation=question.answer_explanation,
        )
        db.add(copy)
        await db.commit()
        await db.refresh(copy)
        return self._to_question_response(copy)

    def _to_question_response(self, question: Question) -> QuestionResponse:
        """Convert question to response model"""
        return QuestionResponse(
            id=question.id,
            question_type=question.question_type,
            text=question.text,
            options=question.options,
            order=question.order,
            correct_answer_index=question.correct_answer_index,
            correct_answer_indices=question.correct_answer_indices,
            reveal_answer_count=getattr(question, 'reveal_answer_count', False) or False,
            question_image_url=question.question_image_url,
            question_video_url=question.question_video_url,
            option_images=question.option_images,
            points=question.points,
            max_time_seconds=question.max_time_seconds,
            negative_points=getattr(question, 'negative_points', 0) or 0,
            is_required=getattr(question, 'is_required', False) or False,
            answer_explanation=question.answer_explanation,
        )
