"""
Answer Service - Submit and aggregate answers (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import json
import os

from persistence.models.quiz import (
    QuizSession, Participant, Answer, Question,
    QuizSessionStatus, QuestionStatus, QuestionType
)
from features.quiz.schemas import (
    AnswerSubmitRequest, AnswerSubmitResponse,
    QuestionResultsResponse, SessionResultsResponse,
    WordCloudAnswerSubmitRequest, WordCloudResultsResponse
)
from shared.exceptions.quiz import (
    SessionNotFoundError, ParticipantNotFoundError, QuestionNotFoundError,
    DuplicateAnswerError, QuestionNotOpenError
)
from shared.utils.redis_client import RedisClient
from core.storage import ImageService


class AnswerServiceAsync:
    """Async service for answer submission and aggregation"""
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
    
    async def submit_answer(
        self,
        db: AsyncSession,
        session_token: str,
        request: AnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        """
        Submit answer to current question
        
        Args:
            db: Database session
            session_token: Participant session token
            request: Answer data
            
        Returns:
            Submission confirmation
            
        Raises:
            ParticipantNotFoundError: If token invalid
            QuestionNotOpenError: If question not accepting answers
            DuplicateAnswerError: If already answered
        """
        # Get participant
        result = await db.execute(
            select(Participant).filter(Participant.session_token == session_token)
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise ParticipantNotFoundError("Invalid session token")
        
        session = participant.session
        
        # Check if question is open
        if session.current_question_status != QuestionStatus.OPEN:
            raise QuestionNotOpenError("Question is not open for answers")
        
        # Get current question
        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        if session.current_question_index >= len(questions):
            raise QuestionNotOpenError("No active question")
        
        current_question = questions[session.current_question_index]
        
        # Validate question_id matches current question
        if current_question.id != request.question_id:
            raise QuestionNotOpenError("Question is not currently active")
        
        # Verify this is an MCQ question
        if current_question.question_type != QuestionType.MCQ:
            raise ValueError("This endpoint is for MCQ questions only")
        
        # Check if already answered (MCQ only - one answer per participant)
        result = await db.execute(
            select(Answer).filter(
                Answer.session_id == session.id,
                Answer.participant_id == participant.id,
                Answer.question_id == request.question_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise DuplicateAnswerError("You have already answered this question")
        
        # Validate option index
        if request.selected_option_index < 0 or request.selected_option_index > 3:
            raise ValueError("Invalid option index")
        
        # Check if answer is correct
        is_correct = request.selected_option_index == current_question.correct_answer_index
        
        # Create answer
        answer = Answer(
            session_id=session.id,
            participant_id=participant.id,
            question_id=request.question_id,
            selected_option_index=request.selected_option_index,
            is_correct=is_correct
        )
        
        db.add(answer)
        await db.commit()
        
        # Update aggregation in Redis
        await self._update_aggregation(session.id, request.question_id, request.selected_option_index)
        
        return AnswerSubmitResponse(
            success=True,
            message="Answer submitted successfully",
            is_correct=None  # Don't reveal until question closes
        )
    
    async def submit_word_cloud_answer(
        self,
        db: AsyncSession,
        session_token: str,
        request: WordCloudAnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        """
        Submit word cloud answer (unlimited submissions allowed)
        
        Args:
            db: Database session
            session_token: Participant session token
            request: Word cloud answer data
            
        Returns:
            Submission confirmation
            
        Raises:
            ParticipantNotFoundError: If token invalid
            QuestionNotOpenError: If question not accepting answers
        """
        # Get participant
        result = await db.execute(
            select(Participant).filter(Participant.session_token == session_token)
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise ParticipantNotFoundError("Invalid session token")
        
        session = participant.session
        
        # Check if question is open
        if session.current_question_status != QuestionStatus.OPEN:
            raise QuestionNotOpenError("Question is not open for answers")
        
        # Get current question
        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        if session.current_question_index >= len(questions):
            raise QuestionNotOpenError("No active question")
        
        current_question = questions[session.current_question_index]
        
        # Validate question_id matches current question
        if current_question.id != request.question_id:
            raise QuestionNotOpenError("Question is not currently active")
        
        # Verify this is a word cloud question
        if current_question.question_type != QuestionType.WORD_CLOUD:
            raise ValueError("This endpoint is for word cloud questions only")
        
        # NO duplicate check - unlimited submissions allowed for word cloud
        
        # Normalize text: replace one or more newlines with a single space
        import re
        normalized_text = re.sub(r'\n+', ' ', request.text_answer.strip())
        
        # Create answer
        answer = Answer(
            session_id=session.id,
            participant_id=participant.id,
            question_id=request.question_id,
            text_answer=normalized_text,
            selected_option_index=None,
            is_correct=None
        )
        
        db.add(answer)
        await db.commit()
        
        # Update word cloud aggregation in Redis
        await self._update_word_cloud_aggregation(
            session.id,
            request.question_id,
            request.text_answer.strip()
        )
        
        return AnswerSubmitResponse(
            success=True,
            message="Word submitted successfully",
            is_correct=None
        )
    
    async def get_word_cloud_results(
        self,
        db: AsyncSession,
        session_id: int,
        question_id: int
    ) -> WordCloudResultsResponse:
        """
        Get aggregated word cloud results
        
        Args:
            db: Database session
            session_id: Session ID
            question_id: Question ID
            
        Returns:
            Word frequencies and statistics
        """
        # Get question
        result = await db.execute(select(Question).filter(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            raise QuestionNotFoundError("Question not found")
        
        if question.question_type != QuestionType.WORD_CLOUD:
            raise ValueError("Not a word cloud question")
        
        # Get all text answers
        result = await db.execute(
            select(Answer).filter(
                Answer.session_id == session_id,
                Answer.question_id == question_id
            )
        )
        answers = result.scalars().all()
        
        # Aggregate word frequencies (case-insensitive)
        word_frequencies = {}
        for answer in answers:
            if answer.text_answer:
                # Normalize: lowercase and strip
                word = answer.text_answer.lower().strip()
                word_frequencies[word] = word_frequencies.get(word, 0) + 1
        
        # Sort by frequency (descending)
        sorted_words = dict(sorted(
            word_frequencies.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        return WordCloudResultsResponse(
            question_id=question.id,
            question_text=question.text,
            word_frequencies=sorted_words,
            total_submissions=len(answers),
            unique_words=len(word_frequencies)
        )
    
    async def get_question_results(
        self,
        db: AsyncSession,
        session_id: int,
        question_id: int,
        participant_token: Optional[str] = None
    ) -> QuestionResultsResponse:
        """
        Get results for a closed question
        
        Args:
            db: Database session
            session_id: Session ID
            question_id: Question ID
            participant_token: Optional participant token to include their answer
            
        Returns:
            Question results with distribution
        """
        # Get question
        result = await db.execute(select(Question).filter(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            raise QuestionNotFoundError("Question not found")
        
        # Get answer distribution
        result = await db.execute(
            select(
                Answer.selected_option_index,
                func.count(Answer.id).label('count')
            ).filter(
                Answer.session_id == session_id,
                Answer.question_id == question_id
            ).group_by(Answer.selected_option_index)
        )
        answers = result.all()
        
        # Build distribution array [count_option_0, count_option_1, count_option_2, count_option_3]
        distribution = [0, 0, 0, 0]
        total_answers = 0
        
        for option_idx, count in answers:
            distribution[option_idx] = count
            total_answers += count
        
        # Get participant's answer if token provided
        participant_answer = None
        if participant_token:
            result = await db.execute(
                select(Participant).filter(Participant.session_token == participant_token)
            )
            participant = result.scalar_one_or_none()
            
            if participant:
                result = await db.execute(
                    select(Answer).filter(
                        Answer.session_id == session_id,
                        Answer.participant_id == participant.id,
                        Answer.question_id == question_id
                    )
                )
                answer = result.scalar_one_or_none()
                
                if answer:
                    participant_answer = answer.selected_option_index
        
        return QuestionResultsResponse(
            question_id=question.id,
            question_text=question.text,
            options=question.options,
            correct_answer_index=question.correct_answer_index,
            answer_distribution=distribution,
            total_answers=total_answers,
            participant_answer=participant_answer
        )
    
    async def get_session_results(
        self,
        db: AsyncSession,
        session_id: int,
        participant_token: Optional[str] = None
    ) -> SessionResultsResponse:
        """
        Get final results for entire session
        
        Args:
            db: Database session
            session_id: Session ID
            participant_token: Optional participant token for their score
            
        Returns:
            Complete session results
        """
        # Get session
        result = await db.execute(select(QuizSession).filter(QuizSession.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        # Get all questions
        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        
        # Calculate participant score if token provided
        participant_score = None
        participant_correct = None
        
        if participant_token:
            result = await db.execute(
                select(Participant).filter(Participant.session_token == participant_token)
            )
            participant = result.scalar_one_or_none()
            
            if participant:
                result = await db.execute(
                    select(func.count(Answer.id)).filter(
                        Answer.session_id == session_id,
                        Answer.participant_id == participant.id,
                        Answer.is_correct == True
                    )
                )
                correct_answers = result.scalar()
                
                result = await db.execute(
                    select(func.count(Answer.id)).filter(
                        Answer.session_id == session_id,
                        Answer.participant_id == participant.id
                    )
                )
                total_answered = result.scalar()
                
                participant_correct = correct_answers
                participant_score = total_answered
        
        # Get results for each question
        question_results = []
        for question in questions:
            try:
                results = await self.get_question_results(
                    db,
                    session_id,
                    question.id,
                    participant_token
                )
                question_results.append(results)
            except Exception:
                pass
        
        # Get current question if session is active
        current_question = None
        if session.current_question_index >= 0 and session.current_question_index < len(questions):
            question_obj = questions[session.current_question_index]
            
            try:
                # Handle based on question type
                if question_obj.question_type.value == 'mcq':
                    # For MCQ, get full results with distribution
                    question_result = await self.get_question_results(
                        db,
                        session_id,
                        question_obj.id,
                        participant_token
                    )
                    
                    # Transform to format expected by host frontend
                    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
                    options = json.loads(question_obj.options) if isinstance(question_obj.options, str) else question_obj.options
                    correct_letter = chr(65 + question_obj.correct_answer_index) if question_obj.correct_answer_index is not None else None
                    
                    current_question = {
                        "id": question_obj.id,
                        "text": question_obj.text,
                        "question_type": question_obj.question_type.value,
                        "option_a": options[0] if options and len(options) > 0 else "",
                        "option_b": options[1] if options and len(options) > 1 else "",
                        "option_c": options[2] if options and len(options) > 2 else "",
                        "option_d": options[3] if options and len(options) > 3 else "",
                        "correct_answer": correct_letter,
                        "question_id": question_result.question_id,
                        "question_text": question_result.question_text,
                        "options": question_result.options,
                        "correct_answer_index": question_result.correct_answer_index,
                        "answer_distribution": question_result.answer_distribution,
                        "total_answers": question_result.total_answers,
                        "question_image_url": ImageService.to_absolute_url(
                            question_obj.question_image_url, base_url
                        ),
                        "option_images": {
                            key: ImageService.to_absolute_url(path, base_url)
                            for key, path in (question_obj.option_images or {}).items()
                        } if question_obj.option_images else None
                    }
                else:
                    # Word Cloud question - no need for get_question_results
                    # Just count total text answers
                    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
                    result = await db.execute(
                        select(func.count(Answer.id)).filter(
                            Answer.session_id == session_id,
                            Answer.question_id == question_obj.id
                        )
                    )
                    total_answers = result.scalar()
                    
                    current_question = {
                        "id": question_obj.id,
                        "text": question_obj.text,
                        "question_type": question_obj.question_type.value,
                        "question_id": question_obj.id,
                        "question_text": question_obj.text,
                        "total_answers": total_answers,
                        "question_image_url": ImageService.to_absolute_url(
                            question_obj.question_image_url, base_url
                        )
                    }
            except Exception as e:
                print(f"Error loading current question: {e}")
                import traceback
                traceback.print_exc()
                pass
        
        # Count total participants in session
        result = await db.execute(
            select(func.count(Participant.id)).filter(Participant.session_id == session_id)
        )
        total_participants = result.scalar()
        
        return SessionResultsResponse(
            session_id=session.id,
            quiz_title=session.quiz.title,
            total_questions=len(questions),
            total_participants=total_participants,
            participant_score=participant_score,
            participant_correct=participant_correct,
            question_results=question_results,
            status=session.status.value,
            current_question_index=session.current_question_index,
            current_question=current_question
        )
    
    async def _update_aggregation(
        self,
        session_id: int,
        question_id: int,
        selected_option: int
    ):
        """Update answer aggregation in Redis for live updates"""
        key = f"session:{session_id}:question:{question_id}:option:{selected_option}"
        await self.redis.increment(key)
        await self.redis.expire(key, 86400)  # 24 hours
    
    async def _update_word_cloud_aggregation(
        self,
        session_id: int,
        question_id: int,
        word: str
    ):
        """Update word cloud aggregation in Redis for live updates"""
        # Normalize word (case-insensitive)
        normalized_word = word.lower().strip()
        key = f"session:{session_id}:question:{question_id}:wordcloud:{normalized_word}"
        await self.redis.increment(key)
        await self.redis.expire(key, 86400)  # 24 hours
