"""
Session Management Service - Start, control, and end quiz sessions
"""
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import string

from persistence.models.quiz import (
    Quiz, QuizSession, Participant, Question,
    QuizStatus, QuizSessionStatus, QuestionStatus
)
from persistence.models.core import Event, Tenant
from features.quiz.schemas import (
    SessionStartRequest, SessionResponse, SessionJoinRequest, SessionJoinResponse
)
from shared.exceptions.quiz import (
    QuizNotFoundError, SessionNotFoundError, ParticipantNotFoundError,
    InvalidQuizStatusError, InvalidSessionStatusError, TierLimitExceededError
)
from shared.utils.redis_client import RedisClient
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser


class SessionService:
    """Service for quiz session management"""
    
    def __init__(self, redis: RedisClient, tier_service: TierService):
        self.redis = redis
        self.tier_service = tier_service
    
    def _generate_join_code(self) -> str:
        """Generate unique 6-character join code"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    
    def _generate_session_token(self) -> str:
        """Generate unique session token for participant"""
        return secrets.token_urlsafe(32)
    
    async def start_session(
        self,
        db: Session,
        quiz_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """
        Start new quiz session
        
        Args:
            db: Database session
            quiz_id: Quiz to start
            current_user: Host user
            
        Returns:
            Created session with join code
            
        Raises:
            QuizNotFoundError: If quiz not found
            InvalidQuizStatusError: If quiz not READY
            TierLimitExceededError: If concurrent event limit reached
        """
        # Get quiz
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id
        ).first()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.READY:
            raise InvalidQuizStatusError("Quiz must be in READY status to start")
        
        # Check concurrent events limit
        can_create = await self.tier_service.check_concurrent_events_limit(
            db,
            current_user.tenant_id,
            current_user.tenant.tier
        )
        
        if not can_create:
            raise TierLimitExceededError("Concurrent events limit reached")
        
        # Invalidate participants from previous sessions of this quiz
        # This forces them to rejoin when a new session starts
        previous_sessions = db.query(QuizSession.id).filter(
            QuizSession.quiz_id == quiz_id,
            QuizSession.tenant_id == current_user.tenant_id
        ).all()
        
        if previous_sessions:
            session_ids = [s.id for s in previous_sessions]
            db.query(Participant).filter(
                Participant.session_id.in_(session_ids)
            ).update(
                {"is_active": False},
                synchronize_session=False
            )
            db.commit()
        
        # Generate unique join code
        join_code = self._generate_join_code()
        while db.query(Event).filter(Event.join_code == join_code).first():
            join_code = self._generate_join_code()
        
        # Update event with join code
        event = db.query(Event).filter(Event.id == quiz.event_id).first()
        event.join_code = join_code
        
        # Create session
        session = QuizSession(
            tenant_id=current_user.tenant_id,
            quiz_id=quiz_id,
            status=QuizSessionStatus.CREATED,
            current_question_index=-1,
            current_question_status=QuestionStatus.PENDING
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Cache session in Redis
        await self.redis.set_json(
            f"session:{session.id}:info",
            {
                "quiz_id": quiz_id,
                "status": session.status.value,
                "current_question_index": -1,
                "join_code": join_code
            },
            expire=86400  # 24 hours
        )
        
        return SessionResponse(
            id=session.id,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            status=session.status,
            current_question_index=session.current_question_index,
            current_question_status=session.current_question_status,
            join_code=join_code,
            participant_count=0
        )
    
    async def join_session(
        self,
        db: Session,
        request: SessionJoinRequest
    ) -> SessionJoinResponse:
        """
        Join session as participant (anonymous)
        
        Args:
            db: Database session
            request: Join request with code
            
        Returns:
            Session token for participant
            
        Raises:
            SessionNotFoundError: If join code invalid
            TierLimitExceededError: If participant limit reached
        """
        # Find event by join code
        event = db.query(Event).filter(Event.join_code == request.join_code).first()
        if not event:
            raise SessionNotFoundError("Invalid join code")
        
        # Find active session - get the LATEST one, not the first
        session = db.query(QuizSession).join(Quiz).filter(
            Quiz.event_id == event.id,
            QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE])
        ).order_by(QuizSession.id.desc()).first()
        
        if not session:
            raise SessionNotFoundError("No active session found")
        
        # Get tenant to check tier
        tenant = db.query(Tenant).filter(Tenant.id == session.tenant_id).first()
        if not tenant:
            raise SessionNotFoundError("Tenant not found")
        
        # Check participant limit
        can_join = await self.tier_service.check_participant_limit(
            session.tenant_id,
            session.id,
            tenant.tier
        )
        
        if not can_join:
            raise TierLimitExceededError("Participant limit reached")
        
        # Create participant
        session_token = self._generate_session_token()
        
        participant = Participant(
            session_id=session.id,
            display_name=request.display_name,
            session_token=session_token,
            is_active=True
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        # Increment participant count in Redis
        await self.tier_service.increment_participant_count(session.id)
        
        return SessionJoinResponse(
            session_id=session.id,
            session_token=session_token,
            participant_id=participant.id,
            quiz_title=session.quiz.title,
            status=session.status
        )
    
    async def advance_question(
        self,
        db: Session,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """
        Advance to next question
        
        Opens next question for answers
        """
        session = db.query(QuizSession).filter(
            QuizSession.id == session_id,
            QuizSession.tenant_id == current_user.tenant_id
        ).first()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status == QuizSessionStatus.ENDED:
            raise InvalidSessionStatusError("Session has ended")
        
        # Close current question if open
        if session.current_question_status == QuestionStatus.OPEN:
            session.current_question_status = QuestionStatus.CLOSED
        
        # Advance to next
        session.current_question_index += 1
        
        # Check if more questions available
        if session.current_question_index >= len(session.quiz.questions):
            # No more questions, end session
            session.status = QuizSessionStatus.ENDED
            session.current_question_status = None
        else:
            # Open new question
            session.status = QuizSessionStatus.ACTIVE
            session.current_question_status = QuestionStatus.OPEN
        
        db.commit()
        db.refresh(session)
        
        # Update Redis cache
        await self.redis.set_json(
            f"session:{session.id}:info",
            {
                "status": session.status.value,
                "current_question_index": session.current_question_index,
                "current_question_status": session.current_question_status.value if session.current_question_status else None
            },
            expire=86400
        )
        
        return await self._to_session_response(db, session)
    
    async def back_question(
        self,
        db: Session,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """
        Go back to previous question
        
        Closes current question and reopens previous one for answers
        """
        session = db.query(QuizSession).filter(
            QuizSession.id == session_id,
            QuizSession.tenant_id == current_user.tenant_id
        ).first()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status == QuizSessionStatus.ENDED:
            raise InvalidSessionStatusError("Session has ended")
        
        # Can't go back before first question
        if session.current_question_index <= 0:
            raise InvalidSessionStatusError("Already at first question")
        
        # Close current question if open
        if session.current_question_status == QuestionStatus.OPEN:
            session.current_question_status = QuestionStatus.CLOSED
        
        # Go back to previous
        session.current_question_index -= 1
        
        # Reopen previous question
        session.status = QuizSessionStatus.ACTIVE
        session.current_question_status = QuestionStatus.OPEN
        
        db.commit()
        db.refresh(session)
        
        # Update Redis cache
        await self.redis.set_json(
            f"session:{session.id}:info",
            {
                "status": session.status.value,
                "current_question_index": session.current_question_index,
                "current_question_status": session.current_question_status.value if session.current_question_status else None
            },
            expire=86400
        )
        
        return await self._to_session_response(db, session)
    
    async def end_session(
        self,
        db: Session,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """End session manually"""
        session = db.query(QuizSession).filter(
            QuizSession.id == session_id,
            QuizSession.tenant_id == current_user.tenant_id
        ).first()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        session.status = QuizSessionStatus.ENDED
        session.current_question_status = None
        
        db.commit()
        db.refresh(session)
        
        # Update Redis
        await self.redis.set_json(
            f"session:{session.id}:info",
            {"status": "ended"},
            expire=86400
        )
        
        return await self._to_session_response(db, session)
    
    async def _to_session_response(self, db: Session, session: QuizSession) -> SessionResponse:
        """Convert session to response"""
        # Get participant count from Redis
        count_key = f"session:{session.id}:participants:count"
        count = await self.redis.get(count_key)
        participant_count = int(count) if count else 0
        
        # Get join code
        event = db.query(Event).filter(Event.id == session.quiz.event_id).first()
        
        return SessionResponse(
            id=session.id,
            quiz_id=session.quiz_id,
            quiz_title=session.quiz.title,
            status=session.status,
            current_question_index=session.current_question_index,
            current_question_status=session.current_question_status,
            join_code=event.join_code if event else "",
            participant_count=participant_count
        )
