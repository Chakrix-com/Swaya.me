"""
Answer Service - Submit and aggregate answers
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from persistence.models.quiz import (
    QuizSession, Participant, Answer, Question,
    QuizSessionStatus, QuestionStatus
)
from features.quiz.schemas import (
    AnswerSubmitRequest, AnswerSubmitResponse,
    QuestionResultsResponse, SessionResultsResponse
)
from shared.exceptions.quiz import (
    SessionNotFoundError, ParticipantNotFoundError, QuestionNotFoundError,
    DuplicateAnswerError, QuestionNotOpenError
)
from shared.utils.redis_client import RedisClient


class AnswerService:
    """Service for answer submission and aggregation"""
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
    
    async def submit_answer(
        self,
        db: Session,
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
        participant = db.query(Participant).filter(
            Participant.session_token == session_token
        ).first()
        
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
        
        # Check if already answered
        existing = db.query(Answer).filter(
            Answer.session_id == session.id,
            Answer.participant_id == participant.id,
            Answer.question_id == request.question_id
        ).first()
        
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
        db.commit()
        
        # Update aggregation in Redis
        await self._update_aggregation(session.id, request.question_id, request.selected_option_index)
        
        return AnswerSubmitResponse(
            success=True,
            message="Answer submitted successfully",
            is_correct=None  # Don't reveal until question closes
        )
    
    async def get_question_results(
        self,
        db: Session,
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
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise QuestionNotFoundError("Question not found")
        
        # Get answer distribution
        answers = db.query(
            Answer.selected_option_index,
            func.count(Answer.id).label('count')
        ).filter(
            Answer.session_id == session_id,
            Answer.question_id == question_id
        ).group_by(Answer.selected_option_index).all()
        
        # Build distribution array [count_option_0, count_option_1, count_option_2, count_option_3]
        distribution = [0, 0, 0, 0]
        total_answers = 0
        
        for option_idx, count in answers:
            distribution[option_idx] = count
            total_answers += count
        
        # Get participant's answer if token provided
        participant_answer = None
        if participant_token:
            participant = db.query(Participant).filter(
                Participant.session_token == participant_token
            ).first()
            
            if participant:
                answer = db.query(Answer).filter(
                    Answer.session_id == session_id,
                    Answer.participant_id == participant.id,
                    Answer.question_id == question_id
                ).first()
                
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
    
    def get_session_results(
        self,
        db: Session,
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
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise SessionNotFoundError("Session not found")
        
        # Get all questions
        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        
        # Calculate participant score if token provided
        participant_score = None
        participant_correct = None
        
        if participant_token:
            participant = db.query(Participant).filter(
                Participant.session_token == participant_token
            ).first()
            
            if participant:
                correct_answers = db.query(Answer).filter(
                    Answer.session_id == session_id,
                    Answer.participant_id == participant.id,
                    Answer.is_correct == True
                ).count()
                
                total_answered = db.query(Answer).filter(
                    Answer.session_id == session_id,
                    Answer.participant_id == participant.id
                ).count()
                
                participant_correct = correct_answers
                participant_score = total_answered
        
        # Get results for each question
        question_results = []
        for question in questions:
            try:
                results = self.get_question_results(
                    db,
                    session_id,
                    question.id,
                    participant_token
                )
                question_results.append(results)
            except Exception:
                pass
        
        return SessionResultsResponse(
            session_id=session.id,
            quiz_title=session.quiz.title,
            total_questions=len(questions),
            participant_score=participant_score,
            participant_correct=participant_correct,
            question_results=question_results
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
