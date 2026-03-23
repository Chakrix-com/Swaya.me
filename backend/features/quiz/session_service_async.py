"""
Session Management Service - Start, control, and end quiz sessions (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from typing import Optional
import secrets
import string

from datetime import datetime, timedelta
from apscheduler.triggers.date import DateTrigger
from persistence.models.quiz import (
    Quiz, QuizSession, Participant, Question, Answer, SessionQuestionTiming,
    QuizStatus, QuizSessionStatus, QuestionStatus, QuestionType, QuizType
)
from persistence.models.core import Event, Tenant, UserRole
from features.quiz.schemas import (
    SessionStartRequest, SessionResponse, SessionJoinRequest, SessionJoinResponse,
    SessionListItemResponse, SessionListResponse, SessionStatusEnum,
    WhiteboardStateUpdateRequest, WhiteboardStateResponse
)
from shared.exceptions.quiz import (
    QuizNotFoundError, SessionNotFoundError, ParticipantNotFoundError,
    InvalidQuizStatusError, InvalidSessionStatusError, TierLimitExceededError
)
from shared.utils.redis_client import RedisClient
from core.config.tier_service import TierService
from core.auth.dependencies import CurrentUser
from core.stats import scheduler as stats_scheduler
from persistence.database_async import AsyncSessionLocal


class SessionServiceAsync:
    """Async service for quiz session management"""
    STALE_SESSION_TIMEOUT_HOURS = 4
    
    def __init__(self, redis: RedisClient, tier_service: TierService):
        self.redis = redis
        self.tier_service = tier_service

    def _timeout_job_id(self, session_id: int) -> str:
        return f"question-timeout:{session_id}"

    async def _cancel_question_timeout(self, session_id: int) -> None:
        scheduler = stats_scheduler.scheduler
        if scheduler is None:
            return
        job = scheduler.get_job(self._timeout_job_id(session_id))
        if job:
            scheduler.remove_job(job.id)

    async def _schedule_question_timeout(self, session_id: int, question_index: int, max_time_seconds: int) -> None:
        scheduler = stats_scheduler.scheduler
        if scheduler is None or max_time_seconds is None or max_time_seconds <= 0:
            return
        await self._cancel_question_timeout(session_id)
        scheduler.add_job(
            self._handle_question_timeout,
            trigger=DateTrigger(run_date=datetime.utcnow() + timedelta(seconds=max_time_seconds)),
            args=[session_id, question_index],
            id=self._timeout_job_id(session_id),
            replace_existing=True,
            misfire_grace_time=10,
        )

    async def _apply_timeout_transition(
        self,
        db: AsyncSession,
        session: QuizSession,
        questions: list[Question],
        now: datetime,
        expected_question_index: Optional[int] = None,
    ) -> bool:
        if session.status == QuizSessionStatus.ENDED:
            return False
        if session.current_question_status != QuestionStatus.OPEN:
            return False
        if expected_question_index is not None and session.current_question_index != expected_question_index:
            return False

        await db.execute(
            update(SessionQuestionTiming)
            .where(
                SessionQuestionTiming.session_id == session.id,
                SessionQuestionTiming.question_index == session.current_question_index,
                SessionQuestionTiming.closed_at == None,  # noqa: E711
            )
            .values(closed_at=now)
        )

        session.current_question_status = QuestionStatus.CLOSED
        session.current_question_index += 1

        if session.current_question_index >= len(questions):
            session.status = QuizSessionStatus.ENDED
            session.current_question_status = None
            await self._clear_event_join_code_if_no_active_sessions(
                db, session.tenant_id, session.quiz.event_id
            )
        else:
            session.status = QuizSessionStatus.ACTIVE
            session.current_question_status = QuestionStatus.OPEN
            next_question = questions[session.current_question_index]
            db.add(SessionQuestionTiming(
                session_id=session.id,
                question_id=next_question.id,
                question_index=session.current_question_index,
                opened_at=now,
            ))

        await db.commit()

        if session.status == QuizSessionStatus.ACTIVE:
            next_question = questions[session.current_question_index]
            if next_question.max_time_seconds:
                await self._schedule_question_timeout(
                    session.id,
                    session.current_question_index,
                    next_question.max_time_seconds
                )
        else:
            await self._cancel_question_timeout(session.id)

        await self.redis.set_json(
            f"session:{session.id}:info",
            {
                "status": session.status.value,
                "current_question_index": session.current_question_index,
                "current_question_status": session.current_question_status.value if session.current_question_status else None
            },
            expire=86400
        )
        return True

    async def _handle_question_timeout(self, session_id: int, question_index: int) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(QuizSession)
                .filter(QuizSession.id == session_id)
                .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
            )
            session = result.scalar_one_or_none()
            if not session:
                return
            questions = sorted(session.quiz.questions, key=lambda q: q.order)
            await self._apply_timeout_transition(
                db,
                session,
                questions,
                now=datetime.utcnow(),
                expected_question_index=question_index,
            )

    async def reconcile_timed_question_state(self, db: AsyncSession, session_id: int) -> None:
        """Heal/advance timed question state for running sessions (polling safety net).

        Optimised: two-phase check — lightweight session state read first, only loads
        quiz + questions if the session is ACTIVE with an OPEN question that has a timer.
        """
        # Phase 1: lightweight check — no joins, no question load
        row = (await db.execute(
            select(
                QuizSession.status,
                QuizSession.current_question_status,
                QuizSession.current_question_index,
                QuizSession.quiz_id,
            ).filter(QuizSession.id == session_id)
        )).first()

        if not row:
            return
        if row.status != QuizSessionStatus.ACTIVE:
            return
        if row.current_question_status != QuestionStatus.OPEN:
            return
        if row.current_question_index < 0:
            return

        # Phase 2: fetch only the current question (not all questions)
        q_result = await db.execute(
            select(Question.id, Question.max_time_seconds)
            .filter(Question.quiz_id == row.quiz_id, Question.order == row.current_question_index)
        )
        current_question = q_result.first()
        if not current_question:
            return
        max_seconds = current_question.max_time_seconds
        if not max_seconds or max_seconds <= 0:
            return

        # Need full session object for _apply_timeout_transition — load it now
        result = await db.execute(
            select(QuizSession)
            .filter(QuizSession.id == session_id)
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()
        if not session:
            return
        questions = sorted(session.quiz.questions, key=lambda q: q.order)

        q_index = row.current_question_index

        timing_row = (
            await db.execute(
                select(SessionQuestionTiming)
                .filter(
                    SessionQuestionTiming.session_id == session_id,
                    SessionQuestionTiming.question_index == q_index,
                    SessionQuestionTiming.closed_at == None,  # noqa: E711
                )
                .order_by(SessionQuestionTiming.opened_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        now = datetime.utcnow()
        if not timing_row:
            db.add(SessionQuestionTiming(
                session_id=session_id,
                question_id=current_question.id,
                question_index=q_index,
                opened_at=now,
            ))
            await db.commit()
            await self._schedule_question_timeout(session_id, q_index, max_seconds)
            return

        elapsed_seconds = (now - timing_row.opened_at).total_seconds()
        if elapsed_seconds >= max_seconds:
            await self._apply_timeout_transition(db, session, questions, now)
            return

        scheduler = stats_scheduler.scheduler
        if scheduler is not None and scheduler.get_job(self._timeout_job_id(session_id)) is None:
            remaining_seconds = max(1, int(max_seconds - elapsed_seconds))
            await self._schedule_question_timeout(session_id, q_index, remaining_seconds)
    
    def _generate_join_code(self) -> str:
        """Generate unique 6-character join code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def _generate_session_token(self) -> str:
        """Generate unique session token for participant"""
        return secrets.token_urlsafe(32)

    def _whiteboard_key(self, session_id: int, question_index: int) -> str:
        return f"session:{session_id}:whiteboard:{question_index}"

    async def _get_host_session_for_state(
        self,
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> QuizSession:
        result = await db.execute(
            select(QuizSession).filter(
                QuizSession.id == session_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError("Session not found")
        return session

    async def get_whiteboard_state(
        self,
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> WhiteboardStateResponse:
        session = await self._get_host_session_for_state(db, session_id, current_user)
        question_index = session.current_question_index
        payload = await self.redis.get_json(self._whiteboard_key(session_id, question_index))
        return WhiteboardStateResponse(
            session_id=session_id,
            question_index=question_index,
            enabled=bool(payload.get("enabled")) if payload else False,
            image_data=payload.get("image_data") if payload else None,
            updated_at=payload.get("updated_at") if payload else None,
        )

    async def get_public_whiteboard_state(
        self,
        db: AsyncSession,
        session_id: int,
        join_code: str
    ) -> WhiteboardStateResponse:
        session_result = await db.execute(
            select(QuizSession.current_question_index)
            .join(Quiz, Quiz.id == QuizSession.quiz_id)
            .join(Event, Event.id == Quiz.event_id)
            .filter(
                QuizSession.id == session_id,
                Event.join_code == join_code,
            )
        )
        question_index = session_result.scalar_one_or_none()
        if question_index is None:
            raise SessionNotFoundError("Session not found")

        payload = await self.redis.get_json(self._whiteboard_key(session_id, question_index))
        return WhiteboardStateResponse(
            session_id=session_id,
            question_index=question_index,
            enabled=bool(payload.get("enabled")) if payload else False,
            image_data=payload.get("image_data") if payload else None,
            updated_at=payload.get("updated_at") if payload else None,
        )

    async def update_whiteboard_state(
        self,
        db: AsyncSession,
        session_id: int,
        request: WhiteboardStateUpdateRequest,
        current_user: CurrentUser
    ) -> WhiteboardStateResponse:
        session = await self._get_host_session_for_state(db, session_id, current_user)
        if session.status == QuizSessionStatus.ENDED:
            raise InvalidSessionStatusError("Session has ended")
        if request.question_index != session.current_question_index:
            raise InvalidSessionStatusError("Question changed, reload presenter and try again")

        payload = {
            "enabled": request.enabled,
            "image_data": request.image_data,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        await self.redis.set_json(
            self._whiteboard_key(session_id, request.question_index),
            payload,
            expire=86400
        )
        return WhiteboardStateResponse(
            session_id=session_id,
            question_index=request.question_index,
            enabled=request.enabled,
            image_data=request.image_data,
            updated_at=payload["updated_at"],
        )

    async def _clear_event_join_code_if_no_active_sessions(
        self,
        db: AsyncSession,
        tenant_id: int,
        event_id: int
    ) -> None:
        """Clear join code when no open sessions remain for an event."""
        active_for_event = await db.execute(
            select(func.count(QuizSession.id))
            .join(Quiz, Quiz.id == QuizSession.quiz_id)
            .filter(
                QuizSession.tenant_id == tenant_id,
                Quiz.event_id == event_id,
                QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE]),
            )
        )
        if (active_for_event.scalar() or 0) == 0:
            await db.execute(
                update(Event)
                .where(Event.tenant_id == tenant_id, Event.id == event_id)
                .values(join_code=None)
            )

    async def _close_stale_sessions(
        self,
        db: AsyncSession,
        tenant_id: int
    ) -> int:
        """Auto-end stale created/active sessions and deactivate their participants."""
        cutoff = datetime.utcnow() - timedelta(hours=self.STALE_SESSION_TIMEOUT_HOURS)
        stale_rows = (
            await db.execute(
                select(QuizSession.id, Quiz.event_id)
                .join(Quiz, Quiz.id == QuizSession.quiz_id)
                .filter(
                    QuizSession.tenant_id == tenant_id,
                    QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE]),
                    QuizSession.updated_at < cutoff,
                )
            )
        ).all()
        if not stale_rows:
            return 0

        stale_session_ids = [row.id for row in stale_rows]
        stale_event_ids = {row.event_id for row in stale_rows}
        now = datetime.utcnow()

        await db.execute(
            update(QuizSession)
            .where(QuizSession.id.in_(stale_session_ids))
            .values(status=QuizSessionStatus.ENDED, current_question_status=None)
        )
        await db.execute(
            update(Participant)
            .where(Participant.session_id.in_(stale_session_ids))
            .values(is_active=False)
        )
        await db.execute(
            update(SessionQuestionTiming)
            .where(
                SessionQuestionTiming.session_id.in_(stale_session_ids),
                SessionQuestionTiming.closed_at == None,  # noqa: E711
            )
            .values(closed_at=now)
        )

        for event_id in stale_event_ids:
            await self._clear_event_join_code_if_no_active_sessions(db, tenant_id, event_id)
        for stale_session_id in stale_session_ids:
            await self._cancel_question_timeout(stale_session_id)

        return len(stale_session_ids)
    
    async def start_session(
        self,
        db: AsyncSession,
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
        # Clean stale sessions first so abandoned sessions do not block new starts.
        stale_closed_count = await self._close_stale_sessions(db, current_user.tenant_id)
        if stale_closed_count:
            await db.commit()

        # Get quiz
        result = await db.execute(
            select(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.tenant_id == current_user.tenant_id
            )
        )
        quiz = result.scalar_one_or_none()
        
        if not quiz:
            raise QuizNotFoundError("Quiz not found")
        
        if quiz.status != QuizStatus.READY:
            raise InvalidQuizStatusError("Quiz must be in READY status to start")

        # If this quiz already has an open session, reuse it so host can resume/stop it.
        existing = await db.execute(
            select(QuizSession)
            .filter(
                QuizSession.quiz_id == quiz_id,
                QuizSession.tenant_id == current_user.tenant_id,
                QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE]),
            )
            .options(joinedload(QuizSession.quiz))
            .order_by(QuizSession.id.desc())
        )
        existing_session = existing.scalars().first()
        if existing_session:
            return await self._to_session_response(db, existing_session)
        
        # Check concurrent events limit (super admins bypass this limit)
        if current_user.user.role != UserRole.super_admin:
            can_create = await self.tier_service.check_concurrent_events_limit(
                db,
                current_user.tenant_id,
                current_user.tenant.tier
            )
            if not can_create:
                raise TierLimitExceededError("Concurrent events limit reached")
        
        # Invalidate participants from previous sessions of this quiz
        # This forces them to rejoin when a new session starts
        result = await db.execute(
            select(QuizSession.id).filter(
                QuizSession.quiz_id == quiz_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
        )
        previous_sessions = result.scalars().all()
        
        if previous_sessions:
            session_ids = list(previous_sessions)
            await db.execute(
                update(Participant).filter(
                    Participant.session_id.in_(session_ids)
                ).values(is_active=False)
            )
            await db.commit()
        
        # Generate unique join code
        join_code = self._generate_join_code()
        result = await db.execute(select(Event).filter(Event.join_code == join_code))
        while result.scalar_one_or_none():
            join_code = self._generate_join_code()
            result = await db.execute(select(Event).filter(Event.join_code == join_code))
        
        # Update event with join code
        result = await db.execute(select(Event).filter(Event.id == quiz.event_id))
        event = result.scalar_one_or_none()
        event.join_code = join_code
        
        # Create session
        session = QuizSession(
            tenant_id=current_user.tenant_id,
            quiz_id=quiz_id,
            status=QuizSessionStatus.CREATED,
            current_question_index=-1,
            current_question_status=QuestionStatus.PENDING,
            leaderboard_visible=(quiz.quiz_type != QuizType.POLL),
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
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
        db: AsyncSession,
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
        try:
            # Find event by join code
            result = await db.execute(select(Event).filter(Event.join_code == request.join_code))
            event = result.scalar_one_or_none()
            
            if not event:
                raise SessionNotFoundError("Invalid join code")

            stale_closed_count = await self._close_stale_sessions(db, event.tenant_id)
            if stale_closed_count:
                await db.commit()
            
            # Find active session - get the LATEST one (in case multiple exist)
            result = await db.execute(
                select(QuizSession)
                .join(Quiz, Quiz.id == QuizSession.quiz_id)
                .filter(
                    Quiz.event_id == event.id,
                    QuizSession.status.in_([QuizSessionStatus.CREATED, QuizSessionStatus.ACTIVE])
                )
                .options(contains_eager(QuizSession.quiz))
                .order_by(QuizSession.id.desc())
            )
            session = result.scalars().first()
            
            if not session:
                raise SessionNotFoundError("No active session found")
            
            # Get tenant to check tier
            result = await db.execute(select(Tenant).filter(Tenant.id == session.tenant_id))
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise SessionNotFoundError("Tenant not found")
            
            # Check participant limit
            can_join = await self.tier_service.check_participant_limit(
                db,
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
            await db.flush()   # assigns participant.id without a round-trip SELECT
            await db.commit()

            # Increment participant count in Redis
            await self.tier_service.increment_participant_count(session.id)
            
            # Build response
            response = SessionJoinResponse(
                session_id=session.id,
                session_token=session_token,
                participant_id=participant.id,
                quiz_title=session.quiz.title,
                status=session.status
            )
            
            return response
            
        except (SessionNotFoundError, TierLimitExceededError):
            raise
        except Exception as e:
            raise

    async def leave_session(
        self,
        db: AsyncSession,
        session_token: str
    ) -> dict:
        """Mark participant inactive when they intentionally leave a session."""
        participant_result = await db.execute(
            select(Participant).filter(Participant.session_token == session_token)
        )
        participant = participant_result.scalar_one_or_none()
        if not participant:
            raise ParticipantNotFoundError("Invalid session token")

        if participant.is_active:
            participant.is_active = False
            await db.commit()
            await self.tier_service.decrement_participant_count(participant.session_id)

        return {"success": True, "message": "Left session successfully"}
    
    async def advance_question(
        self,
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """
        Advance to next question
        
        Opens next question for answers
        """
        result = await db.execute(
            select(QuizSession)
            .filter(
                QuizSession.id == session_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status == QuizSessionStatus.ENDED:
            raise InvalidSessionStatusError("Session has ended")
        
        now = datetime.utcnow()
        await self._cancel_question_timeout(session_id)
        questions = sorted(session.quiz.questions, key=lambda q: q.order)

        # Close timing for current question
        if session.current_question_index >= 0 and session.current_question_status == QuestionStatus.OPEN:
            session.current_question_status = QuestionStatus.CLOSED
            await db.execute(
                update(SessionQuestionTiming)
                .where(
                    SessionQuestionTiming.session_id == session_id,
                    SessionQuestionTiming.question_index == session.current_question_index,
                    SessionQuestionTiming.closed_at == None,
                )
                .values(closed_at=now)
            )

        # Advance to next
        session.current_question_index += 1

        # Check if more questions available
        if session.current_question_index >= len(questions):
            # No more questions, end session
            session.status = QuizSessionStatus.ENDED
            session.current_question_status = None
            await self._clear_event_join_code_if_no_active_sessions(
                db, session.tenant_id, session.quiz.event_id
            )
        else:
            # Open new question and record timing
            session.status = QuizSessionStatus.ACTIVE
            session.current_question_status = QuestionStatus.OPEN
            db.add(SessionQuestionTiming(
                session_id=session_id,
                question_id=questions[session.current_question_index].id,
                question_index=session.current_question_index,
                opened_at=now,
            ))

        await db.commit()
        await db.refresh(session)

        if (
            session.status == QuizSessionStatus.ACTIVE
            and 0 <= session.current_question_index < len(questions)
        ):
            current_question = questions[session.current_question_index]
            if current_question.max_time_seconds:
                await self._schedule_question_timeout(
                    session_id,
                    session.current_question_index,
                    current_question.max_time_seconds
                )
        
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
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """
        Go back to previous question
        
        Closes current question and reopens previous one for answers
        """
        result = await db.execute(
            select(QuizSession)
            .filter(
                QuizSession.id == session_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        if session.status == QuizSessionStatus.ENDED:
            raise InvalidSessionStatusError("Session has ended")
        
        # Can't go back before first question
        if session.current_question_index <= 0:
            raise InvalidSessionStatusError("Already at first question")
        
        now = datetime.utcnow()
        await self._cancel_question_timeout(session_id)
        questions = sorted(session.quiz.questions, key=lambda q: q.order)

        # Close timing for current question
        if session.current_question_status == QuestionStatus.OPEN:
            session.current_question_status = QuestionStatus.CLOSED
            await db.execute(
                update(SessionQuestionTiming)
                .where(
                    SessionQuestionTiming.session_id == session_id,
                    SessionQuestionTiming.question_index == session.current_question_index,
                    SessionQuestionTiming.closed_at == None,
                )
                .values(closed_at=now)
            )

        # Go back to previous
        session.current_question_index -= 1

        # Reopen previous question with a fresh timing entry
        session.status = QuizSessionStatus.ACTIVE
        session.current_question_status = QuestionStatus.OPEN
        db.add(SessionQuestionTiming(
            session_id=session_id,
            question_id=questions[session.current_question_index].id,
            question_index=session.current_question_index,
            opened_at=now,
        ))

        await db.commit()
        await db.refresh(session)

        current_question = questions[session.current_question_index]
        if current_question.max_time_seconds:
            await self._schedule_question_timeout(
                session_id,
                session.current_question_index,
                current_question.max_time_seconds
            )
        
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
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """End session manually"""
        result = await db.execute(
            select(QuizSession)
            .filter(
                QuizSession.id == session_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
            .options(joinedload(QuizSession.quiz))
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        now = datetime.utcnow()
        await self._cancel_question_timeout(session_id)

        # Close timing for current question if still open
        if session.current_question_index >= 0:
            await db.execute(
                update(SessionQuestionTiming)
                .where(
                    SessionQuestionTiming.session_id == session_id,
                    SessionQuestionTiming.closed_at == None,
                )
                .values(closed_at=now)
            )

        session.status = QuizSessionStatus.ENDED
        session.current_question_status = None
        await self._clear_event_join_code_if_no_active_sessions(
            db, session.tenant_id, session.quiz.event_id
        )

        await db.commit()
        await db.refresh(session)

        # Update Redis
        await self.redis.set_json(
            f"session:{session.id}:info",
            {"status": "ended"},
            expire=86400
        )
        
        return await self._to_session_response(db, session)
    
    async def toggle_leaderboard(
        self,
        db: AsyncSession,
        session_id: int,
        current_user: CurrentUser
    ) -> SessionResponse:
        """Toggle leaderboard visibility for participants"""
        result = await db.execute(
            select(QuizSession)
            .filter(
                QuizSession.id == session_id,
                QuizSession.tenant_id == current_user.tenant_id
            )
            .options(joinedload(QuizSession.quiz))
        )
        session = result.scalar_one_or_none()

        if not session:
            raise SessionNotFoundError("Session not found")

        if session.quiz.quiz_type == QuizType.POLL:
            if session.leaderboard_visible:
                session.leaderboard_visible = False
                await db.commit()
                await db.refresh(session)
            return await self._to_session_response(db, session)

        session.leaderboard_visible = not session.leaderboard_visible
        await db.commit()
        await db.refresh(session)

        return await self._to_session_response(db, session)

    async def list_sessions(
        self,
        db: AsyncSession,
        quiz_id: int,
        current_user: CurrentUser
    ) -> SessionListResponse:
        """List all past sessions for a quiz with participant and response counts"""
        # Verify quiz belongs to this tenant
        quiz_result = await db.execute(
            select(Quiz).filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
        )
        quiz = quiz_result.scalar_one_or_none()
        if not quiz:
            raise QuizNotFoundError("Quiz not found")

        # Single query: sessions joined with participant and answer counts
        rows = (await db.execute(
            select(
                QuizSession.id,
                QuizSession.status,
                QuizSession.created_at,
                QuizSession.updated_at,
                func.count(func.distinct(Participant.id)).label('participant_count'),
                func.count(Answer.id).label('total_responses'),
            )
            .outerjoin(Participant, Participant.session_id == QuizSession.id)
            .outerjoin(Answer, Answer.session_id == QuizSession.id)
            .filter(
                QuizSession.quiz_id == quiz_id,
                QuizSession.tenant_id == current_user.tenant_id,
            )
            .group_by(QuizSession.id, QuizSession.status, QuizSession.created_at, QuizSession.updated_at)
            .order_by(QuizSession.created_at.desc())
        )).all()

        sessions = [
            SessionListItemResponse(
                id=row.id,
                status=SessionStatusEnum(row.status.value),
                created_at=row.created_at,
                ended_at=row.updated_at if row.status == QuizSessionStatus.ENDED else None,
                participant_count=row.participant_count,
                total_responses=row.total_responses,
            )
            for row in rows
        ]

        return SessionListResponse(
            quiz_id=quiz_id,
            quiz_title=quiz.title,
            sessions=sessions,
            total=len(sessions),
        )

    async def _to_session_response(self, db: AsyncSession, session: QuizSession) -> SessionResponse:
        """Convert session to response"""
        # Get participant count from Redis
        count_key = f"session:{session.id}:participants:count"
        count = await self.redis.get(count_key)
        participant_count = int(count) if count else 0
        
        # Get join code
        result = await db.execute(select(Event).filter(Event.id == session.quiz.event_id))
        event = result.scalar_one_or_none()
        
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
