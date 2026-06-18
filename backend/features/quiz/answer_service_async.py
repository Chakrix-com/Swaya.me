"""
Answer Service - Submit and aggregate answers (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

from persistence.models.quiz import (
    Quiz, QuizSession, Participant, Answer, Question, SessionQuestionTiming,
    QuizSessionStatus, QuestionStatus, QuestionType, QuizType
)
from features.quiz.schemas import (
    AnswerSubmitRequest, AnswerSubmitResponse,
    QuestionResultsResponse, SessionResultsResponse,
    WordCloudAnswerSubmitRequest, WordCloudResultsResponse,
    LeaderboardEntry, LeaderboardResponse
)
from shared.exceptions.quiz import (
    SessionNotFoundError, ParticipantNotFoundError, QuestionNotFoundError,
    DuplicateAnswerError, QuestionNotOpenError
)
from shared.utils.content_filter import check_content
from shared.utils.redis_client import RedisClient
from core.storage import ImageService


async def _write_answer_bg(
    session_id: int,
    participant_id: int,
    question_id: int,
    selected_option_index: int,
    is_correct: Optional[bool],
) -> None:
    """Fire-and-forget DB write for MCQ/scale answers. Response is already sent."""
    from persistence.database_async import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            db.add(Answer(
                session_id=session_id,
                participant_id=participant_id,
                question_id=question_id,
                selected_option_index=selected_option_index,
                is_correct=is_correct,
            ))
            await db.commit()
    except Exception as e:
        logger.error(
            "bg_answer_write_failed session=%s participant=%s question=%s: %s",
            session_id, participant_id, question_id, e,
        )


async def _write_text_answer_bg(
    session_id: int,
    participant_id: int,
    question_id: int,
    text_answer: str,
    is_correct: Optional[bool],
) -> None:
    """Fire-and-forget DB write for text/word-cloud answers. Response is already sent."""
    from persistence.database_async import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            db.add(Answer(
                session_id=session_id,
                participant_id=participant_id,
                question_id=question_id,
                text_answer=text_answer,
                selected_option_index=None,
                is_correct=is_correct,
            ))
            await db.commit()
    except Exception as e:
        logger.error(
            "bg_text_answer_write_failed session=%s participant=%s question=%s: %s",
            session_id, participant_id, question_id, e,
        )


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
        """Submit answer to current question.

        Hot path uses two Redis reads (participant info + session state) and one
        atomic Redis SET NX for deduplication, leaving a single DB INSERT as the
        only database operation.  Falls back to the original full-DB path on any
        cache miss so correctness is never compromised.
        """
        # ── Redis fast path ────────────────────────────────────────────────────
        p_info = await self.redis.get_json(f"session_token:{session_token}")
        state = await self.redis.get_json(
            f"session:{p_info['session_id']}:audience_state"
        ) if p_info else None

        if p_info and state:
            participant_id = p_info["participant_id"]
            session_id     = p_info["session_id"]

            if state.get("status") != "active":
                raise QuestionNotOpenError("Session is not active")
            if state.get("current_question_status") != "open":
                raise QuestionNotOpenError("Question is not open for answers")

            q_data = state.get("current_question")
            if not q_data:
                raise QuestionNotOpenError("No active question")
            if q_data["id"] != request.question_id:
                raise QuestionNotOpenError("Question is not currently active")

            q_type = q_data.get("question_type")
            if q_type not in ("mcq", "scale"):
                raise ValueError("This endpoint is for option-based questions only")

            options = q_data.get("options") or []
            option_count = len(options)
            if option_count == 0:
                raise ValueError("Question has no options configured")
            if not (0 <= request.selected_option_index < option_count):
                raise ValueError("Invalid option index")

            # Atomic dedup: SET NX replaces the SELECT for duplicate check.
            # The DB also has a unique constraint (uq_answer_participant_question)
            # as a safety net against race conditions.
            dedup_key = f"session:{session_id}:ans:{participant_id}:{request.question_id}"
            if not await self.redis.set_nx(dedup_key, "1", expire=86400):
                raise DuplicateAnswerError("You have already answered this question")

            correct_answer_index = q_data.get("correct_answer_index")
            is_correct = (
                request.selected_option_index == correct_answer_index
                if correct_answer_index is not None
                else None
            )

            asyncio.create_task(_write_answer_bg(
                session_id=session_id,
                participant_id=participant_id,
                question_id=request.question_id,
                selected_option_index=request.selected_option_index,
                is_correct=is_correct,
            ))

            await self._update_aggregation(session_id, request.question_id, request.selected_option_index)

            score_key = f"session_token:{session_token}:score"
            score_data = await self.redis.get_json(score_key) or {"score": 0, "correct": 0}
            if is_correct is True:
                points = q_data.get("points") or 1
                score_data["score"] = score_data.get("score", 0) + points
                score_data["correct"] = score_data.get("correct", 0) + 1
            await self.redis.set_json(score_key, score_data, expire=86400)

            return AnswerSubmitResponse(
                success=True,
                message="Answer submitted successfully",
                is_correct=None,
            )

        # ── DB fallback (cache miss — should be rare) ──────────────────────────
        return await self._submit_answer_db(db, session_token, request)

    async def _submit_answer_db(
        self,
        db: AsyncSession,
        session_token: str,
        request: AnswerSubmitRequest,
    ) -> AnswerSubmitResponse:
        """Original DB-only path for submit_answer, used when Redis cache is cold."""
        result = await db.execute(
            select(Participant)
            .filter(Participant.session_token == session_token)
            .options(
                joinedload(Participant.session)
                .joinedload(QuizSession.quiz)
                .selectinload(Quiz.questions)
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise ParticipantNotFoundError("Invalid session token")

        session = participant.session
        if session.current_question_status != QuestionStatus.OPEN:
            raise QuestionNotOpenError("Question is not open for answers")

        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        if session.current_question_index >= len(questions):
            raise QuestionNotOpenError("No active question")

        current_question = questions[session.current_question_index]
        if current_question.id != request.question_id:
            raise QuestionNotOpenError("Question is not currently active")
        if current_question.question_type not in (QuestionType.MCQ, QuestionType.SCALE):
            raise ValueError("This endpoint is for option-based questions only")

        result = await db.execute(
            select(Answer).filter(
                Answer.session_id == session.id,
                Answer.participant_id == participant.id,
                Answer.question_id == request.question_id,
            )
        )
        if result.scalar_one_or_none():
            raise DuplicateAnswerError("You have already answered this question")

        option_count = len(current_question.options or [])
        if option_count == 0:
            raise ValueError("Question has no options configured")
        if not (0 <= request.selected_option_index < option_count):
            raise ValueError("Invalid option index")

        is_correct = (
            request.selected_option_index == current_question.correct_answer_index
            if current_question.correct_answer_index is not None
            else None
        )

        db.add(Answer(
            session_id=session.id,
            participant_id=participant.id,
            question_id=request.question_id,
            selected_option_index=request.selected_option_index,
            is_correct=is_correct,
        ))
        await db.commit()

        await self._update_aggregation(session.id, request.question_id, request.selected_option_index)

        score_key = f"session_token:{session_token}:score"
        score_data = await self.redis.get_json(score_key) or {"score": 0, "correct": 0}
        if is_correct is True:
            points = current_question.points or 1
            score_data["score"] = score_data.get("score", 0) + points
            score_data["correct"] = score_data.get("correct", 0) + 1
        await self.redis.set_json(score_key, score_data, expire=86400)

        return AnswerSubmitResponse(
            success=True,
            message="Answer submitted successfully",
            is_correct=None,
        )
    
    async def submit_word_cloud_answer(
        self,
        db: AsyncSession,
        session_token: str,
        request: WordCloudAnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        """Submit a text/word-cloud answer.

        Same Redis-first strategy as submit_answer: participant identity and session
        state come from Redis; the DB only sees the final INSERT.
        """
        _TEXT_TYPES = ("word_cloud", "single_line", "paragraph", "one_word")

        # ── Redis fast path ────────────────────────────────────────────────────
        p_info = await self.redis.get_json(f"session_token:{session_token}")
        state = await self.redis.get_json(
            f"session:{p_info['session_id']}:audience_state"
        ) if p_info else None

        if p_info and state:
            participant_id = p_info["participant_id"]
            session_id     = p_info["session_id"]

            if state.get("status") != "active":
                raise QuestionNotOpenError("Session is not active")
            if state.get("current_question_status") != "open":
                raise QuestionNotOpenError("Question is not open for answers")

            q_data = state.get("current_question")
            if not q_data:
                raise QuestionNotOpenError("No active question")
            if q_data["id"] != request.question_id:
                raise QuestionNotOpenError("Question is not currently active")

            q_type = q_data.get("question_type")
            if q_type not in _TEXT_TYPES:
                raise ValueError("This endpoint is for text-based questions only")

            text = request.text_answer.strip()

            if q_type == "one_word":
                if not text or any(c in text for c in (' ', '\t', '\n', '\r')):
                    raise ValueError("One-word answers must be a single word with no spaces")

            # word_cloud allows unlimited; all others get dedup via Redis NX
            if q_type != "word_cloud":
                dedup_key = f"session:{session_id}:ans:{participant_id}:{request.question_id}"
                if not await self.redis.set_nx(dedup_key, "1", expire=86400):
                    raise DuplicateAnswerError("You have already answered this question")

            check_content(text, "Answer")

            options = q_data.get("options") or []
            expected_answer = options[0] if options else None

            is_text_scored = q_type in ("single_line", "paragraph")
            is_correct = None
            if is_text_scored and expected_answer:
                from core.ai import router as _ai_router
                is_correct = await _ai_router.grade_text_answer(
                    participant_answer=text,
                    expected_answer=str(expected_answer).strip(),
                )

            asyncio.create_task(_write_text_answer_bg(
                session_id=session_id,
                participant_id=participant_id,
                question_id=request.question_id,
                text_answer=text,
                is_correct=is_correct,
            ))

            await self._update_word_cloud_aggregation(session_id, request.question_id, text)

            return AnswerSubmitResponse(
                success=True,
                message="Response submitted successfully",
                is_correct=None,
            )

        # ── DB fallback ────────────────────────────────────────────────────────
        return await self._submit_word_cloud_answer_db(db, session_token, request)

    async def _submit_word_cloud_answer_db(
        self,
        db: AsyncSession,
        session_token: str,
        request: WordCloudAnswerSubmitRequest,
    ) -> AnswerSubmitResponse:
        """Original DB-only path for submit_word_cloud_answer, used on cache miss."""
        result = await db.execute(
            select(Participant)
            .filter(Participant.session_token == session_token)
            .options(
                joinedload(Participant.session)
                .joinedload(QuizSession.quiz)
                .selectinload(Quiz.questions)
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise ParticipantNotFoundError("Invalid session token")

        session = participant.session
        if session.current_question_status != QuestionStatus.OPEN:
            raise QuestionNotOpenError("Question is not open for answers")

        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        if session.current_question_index >= len(questions):
            raise QuestionNotOpenError("No active question")

        current_question = questions[session.current_question_index]
        if current_question.id != request.question_id:
            raise QuestionNotOpenError("Question is not currently active")
        if current_question.question_type not in (
            QuestionType.WORD_CLOUD,
            QuestionType.SINGLE_LINE,
            QuestionType.PARAGRAPH,
            QuestionType.ONE_WORD,
        ):
            raise ValueError("This endpoint is for text-based questions only")

        text = request.text_answer.strip()
        if current_question.question_type == QuestionType.ONE_WORD:
            if not text or any(c in text for c in (' ', '\t', '\n', '\r')):
                raise ValueError("One-word answers must be a single word with no spaces")

        if current_question.question_type != QuestionType.WORD_CLOUD:
            dup = await db.execute(
                select(Answer).filter(
                    Answer.session_id == session.id,
                    Answer.participant_id == participant.id,
                    Answer.question_id == request.question_id,
                )
            )
            if dup.scalar_one_or_none():
                raise DuplicateAnswerError("You have already answered this question")

        expected_answer = (current_question.options or [None])[0]
        check_content(text, "Answer")

        is_text_scored = current_question.question_type in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH)
        is_correct = None
        if is_text_scored and expected_answer:
            from core.ai import router as _ai_router
            is_correct = await _ai_router.grade_text_answer(
                participant_answer=text,
                expected_answer=str(expected_answer).strip(),
            )

        db.add(Answer(
            session_id=session.id,
            participant_id=participant.id,
            question_id=request.question_id,
            text_answer=text,
            selected_option_index=None,
            is_correct=is_correct,
        ))
        await db.commit()

        await self._update_word_cloud_aggregation(session.id, request.question_id, text)

        return AnswerSubmitResponse(
            success=True,
            message="Response submitted successfully",
            is_correct=None,
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
        
        if question.question_type not in (QuestionType.WORD_CLOUD, QuestionType.ONE_WORD):
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
        
        option_count = len(question.options or [])
        distribution = [0] * option_count
        total_answers = 0

        for option_idx, count in answers:
            if option_idx is not None and 0 <= option_idx < option_count:
                distribution[option_idx] = count
                total_answers += count

        # For text-based questions (word_cloud, single_line, paragraph) there are
        # no selected_option_index rows — count text_answer rows instead
        if option_count == 0:
            count_result = await db.execute(
                select(func.count(Answer.id)).filter(
                    Answer.session_id == session_id,
                    Answer.question_id == question_id,
                    Answer.text_answer.isnot(None)
                )
            )
            total_answers = count_result.scalar() or 0
        
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
    
    async def _get_session_results_from_cache(
        self,
        db: AsyncSession,
        session_id: int,
        participant_token: str,
    ) -> Optional[SessionResultsResponse]:
        """Serve audience-results entirely from Redis. Returns None on any cache miss."""
        try:
            # 1. Shared session+question state
            state = await self.redis.get_json(f"session:{session_id}:audience_state")
            if state is None:
                return None

            # 2. Live answer distribution from counters (always fresh)
            current_question = None
            q_data = state.get("current_question")
            if q_data:
                options = q_data.get("options") or []
                distribution, total_answers = await self._get_answer_distribution_from_redis(
                    session_id, q_data["id"], len(options)
                )
                is_poll = state.get("quiz_type") == "poll"
                is_closed = state.get("current_question_status") == "closed"
                ca_idx = q_data.get("correct_answer_index") if (is_closed and not is_poll) else None
                current_question = {
                    "id": q_data["id"],
                    "text": q_data["text"],
                    "question_type": q_data["question_type"],
                    "option_a": options[0] if len(options) > 0 else None,
                    "option_b": options[1] if len(options) > 1 else None,
                    "option_c": options[2] if len(options) > 2 else None,
                    "option_d": options[3] if len(options) > 3 else None,
                    "correct_answer": chr(65 + ca_idx) if ca_idx is not None else None,
                    "question_id": q_data["id"],
                    "question_text": q_data["text"],
                    "options": options,
                    "correct_answer_index": ca_idx,
                    "answer_distribution": distribution,
                    "total_answers": total_answers,
                    "question_image_url": q_data.get("question_image_url"),
                    "question_video_url": q_data.get("question_video_url"),
                    "option_images": q_data.get("option_images"),
                    "points": q_data.get("points", 1),
                    "max_time_seconds": q_data.get("max_time_seconds"),
                    "timer_started_at": q_data.get("timer_started_at"),
                }

            # 3. Participant-specific: score and current-question answer
            score_data = await self.redis.get_json(f"session_token:{participant_token}:score")
            participant_score = score_data.get("score") if score_data else None
            participant_correct = score_data.get("correct") if score_data else None

            # 4. Total participants from Redis counter
            count_raw = await self.redis.get(f"session:{session_id}:participants:count")
            total_participants = int(count_raw) if count_raw else 0

            return SessionResultsResponse(
                session_id=session_id,
                quiz_title=state["quiz_title"],
                quiz_type=state["quiz_type"],
                scoring_enabled=state.get("scoring_enabled", True),
                total_questions=state.get("total_questions", 0),
                total_participants=total_participants,
                participant_score=participant_score,
                participant_correct=participant_correct,
                question_results=[],
                status=state["status"],
                current_question_index=state.get("current_question_index", -1),
                current_question=current_question,
                leaderboard_visible=state.get("leaderboard_visible", False),
                skin=state.get("skin"),
                reaction_style=state.get("reaction_style"),
            )
        except Exception:
            # Any Redis error → fall back to DB path
            return None

    async def _get_answer_distribution_from_redis(
        self,
        session_id: int,
        question_id: int,
        option_count: int,
    ) -> tuple[list[int], int]:
        """Read answer counts from Redis counters written at submit time.
        Returns (distribution list, total_answers). Falls back to empty on miss."""
        if option_count == 0:
            return [], 0
        keys = [
            f"session:{session_id}:question:{question_id}:option:{i}"
            for i in range(option_count)
        ]
        values = await self.redis.mget(keys)
        distribution = [int(v) if v else 0 for v in values]
        return distribution, sum(distribution)

    async def get_session_results(
        self,
        db: AsyncSession,
        session_id: int,
        participant_token: Optional[str] = None,
        include_question_results: bool = True,
        include_text_responses: bool = True,
    ) -> SessionResultsResponse:
        """
        Get final results for entire session.

        Audience path (include_question_results=False): served from Redis caches
        with zero DB queries in steady state. Falls back to DB on cache miss.
        Host/full path: always hits DB for authoritative data.
        """
        # ── Redis fast-path (audience polling only) ──────────────────────────
        if not include_question_results and participant_token:
            result = await self._get_session_results_from_cache(
                db, session_id, participant_token
            )
            if result is not None:
                return result
        # ── DB path (host view, or audience cache miss) ───────────────────────

        # Get session with quiz and questions
        result = await db.execute(
            select(QuizSession)
            .filter(QuizSession.id == session_id)
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise SessionNotFoundError("Session not found")
        
        # Get all questions
        questions = sorted(session.quiz.questions, key=lambda q: q.order)
        question_by_id = {q.id: q for q in questions}
        is_poll = session.quiz.quiz_type == QuizType.POLL
        
        # Calculate participant score if token provided
        participant_score = None
        participant_correct = None
        
        if participant_token and not is_poll:
            result = await db.execute(
                select(Participant).filter(Participant.session_token == participant_token)
            )
            participant = result.scalar_one_or_none()
            
            if participant:
                result = await db.execute(
                    select(Answer).filter(
                        Answer.session_id == session_id,
                        Answer.participant_id == participant.id
                    )
                )
                participant_answers = result.scalars().all()
                import re
                correct_answers = 0
                weighted_score = 0
                for ans in participant_answers:
                    q = question_by_id.get(ans.question_id)
                    question_points = (q.points if q else 1) or 1
                    if ans.is_correct is True:
                        correct_answers += 1
                        weighted_score += question_points
                        continue
                    if not q or q.question_type not in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH):
                        continue
                    expected = (q.options or [None])[0]
                    if not expected or not ans.text_answer:
                        continue
                    
                    response_clean = ans.text_answer.strip().lower()
                    expected_clean = str(expected).strip().lower()
                    
                    if response_clean == expected_clean:
                        correct_answers += 1
                        weighted_score += question_points
                
                participant_correct = correct_answers
                participant_score = weighted_score
        
        # Get results for each question (host/full views only)
        question_results = []
        if include_question_results:
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
        
        # Get current question only for active sessions (never expose for ended sessions)
        current_question = None
        if session.status != QuizSessionStatus.ENDED and session.current_question_index >= 0 and session.current_question_index < len(questions):
            question_obj = questions[session.current_question_index]
            timing_row = (
                await db.execute(
                    select(SessionQuestionTiming)
                    .filter(
                        SessionQuestionTiming.session_id == session_id,
                        SessionQuestionTiming.question_index == session.current_question_index,
                        SessionQuestionTiming.closed_at == None,
                    )
                    .order_by(SessionQuestionTiming.opened_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            timer_started_at = timing_row.opened_at.isoformat() if timing_row and timing_row.opened_at else None
            
            try:
                # Handle based on question type
                if question_obj.question_type.value in ('mcq', 'scale'):
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
                    if (
                        not is_poll
                        and question_obj.correct_answer_index is not None
                        and options
                        and 0 <= question_obj.correct_answer_index < len(options)
                    ):
                        correct_display = (
                            chr(65 + question_obj.correct_answer_index)
                            if question_obj.question_type.value == 'mcq'
                            else options[question_obj.correct_answer_index]
                        )
                    else:
                        correct_display = None
                    
                    current_question = {
                        "id": question_obj.id,
                        "text": question_obj.text,
                        "question_type": question_obj.question_type.value,
                        "option_a": options[0] if options and len(options) > 0 else None,
                        "option_b": options[1] if options and len(options) > 1 else None,
                        "option_c": options[2] if options and len(options) > 2 else None,
                        "option_d": options[3] if options and len(options) > 3 else None,
                        "correct_answer": correct_display,
                        "question_id": question_result.question_id,
                        "question_text": question_result.question_text,
                        "options": question_result.options,
                        "correct_answer_index": None if is_poll else question_result.correct_answer_index,
                        "answer_distribution": question_result.answer_distribution,
                        "total_answers": question_result.total_answers,
                        "question_image_url": ImageService.to_absolute_url(
                            question_obj.question_image_url, base_url
                        ),
                        "question_video_url": question_obj.question_video_url,
                        "option_images": {
                            key: ImageService.to_absolute_url(path, base_url)
                            for key, path in (question_obj.option_images or {}).items()
                        } if question_obj.option_images else None,
                        "points": question_obj.points or 1,
                        "max_time_seconds": question_obj.max_time_seconds,
                        "timer_started_at": timer_started_at,
                    }
                else:
                    # Text-based question: expose live response count
                    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
                    result = await db.execute(
                        select(func.count(Answer.id)).filter(
                            Answer.session_id == session_id,
                            Answer.question_id == question_obj.id
                        )
                    )
                    total_answers = result.scalar()
                    text_responses = []
                    if include_text_responses and question_obj.question_type.value in ('single_line', 'paragraph'):
                        responses_result = await db.execute(
                            select(Answer.text_answer, Participant.display_name)
                            .join(Participant, Participant.id == Answer.participant_id)
                            .filter(
                                Answer.session_id == session_id,
                                Answer.question_id == question_obj.id,
                                Answer.text_answer.isnot(None),
                            )
                            .order_by(Answer.created_at.desc())
                            .limit(50)
                        )
                        text_responses = [
                            {"text": text, "participant_name": name or "Guest"}
                            for text, name in responses_result.all()
                            if text
                        ]
                    
                    current_question = {
                        "id": question_obj.id,
                        "text": question_obj.text,
                        "question_type": question_obj.question_type.value,
                        "question_id": question_obj.id,
                        "question_text": question_obj.text,
                        "total_answers": total_answers,
                        "text_responses": text_responses,
                        "question_image_url": ImageService.to_absolute_url(
                            question_obj.question_image_url, base_url
                        ),
                        "question_video_url": question_obj.question_video_url,
                        "points": question_obj.points or 1,
                        "max_time_seconds": question_obj.max_time_seconds,
                        "timer_started_at": timer_started_at,
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
            quiz_type=session.quiz.quiz_type,
            scoring_enabled=not is_poll,
            total_questions=len(questions),
            total_participants=total_participants,
            participant_score=participant_score,
            participant_correct=participant_correct,
            question_results=question_results,
            status=session.status.value,
            current_question_index=session.current_question_index,
            current_question=current_question,
            leaderboard_visible=(False if is_poll else session.leaderboard_visible),
            skin=getattr(session.quiz, 'skin', None),
            reaction_style=getattr(session.quiz, 'reaction_style', None),
        )

    async def get_leaderboard(
        self,
        db: AsyncSession,
        session_id: int,
        session_token: Optional[str] = None
    ) -> LeaderboardResponse:
        """
        Get ranked leaderboard for a session.
        Score = number of correct scored answers (MCQ + Scale + text with expected answer) per participant.
        Tiebreaker: earlier last-correct-answer time (faster responder ranks higher).
        """
        # Get session with quiz questions (to count scored questions)
        result = await db.execute(
            select(QuizSession)
            .filter(QuizSession.id == session_id)
            .options(joinedload(QuizSession.quiz).selectinload(Quiz.questions))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError("Session not found")
        if session.quiz.quiz_type == QuizType.POLL:
            participants_result = await db.execute(
                select(func.count(Participant.id))
                .filter(Participant.session_id == session_id, Participant.is_active == True)
            )
            participant_count = participants_result.scalar() or 0
            return LeaderboardResponse(
                session_id=session_id,
                entries=[],
                total_participants=participant_count,
                current_participant_rank=None,
                mcq_question_count=0,
            )

        scored_question_count = sum(
            (q.points or 1) for q in session.quiz.questions
            if q.question_type in (QuestionType.MCQ, QuestionType.SCALE, QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH)
        )
        question_by_id = {q.id: q for q in session.quiz.questions}

        # Resolve current participant
        current_participant_id = None
        if session_token:
            result = await db.execute(
                select(Participant).filter(Participant.session_token == session_token)
            )
            p = result.scalar_one_or_none()
            if p:
                current_participant_id = p.id

        # Load all closed scored-question timings for this session
        timings_result = await db.execute(
            select(SessionQuestionTiming)
            .join(Question, Question.id == SessionQuestionTiming.question_id)
            .filter(
                SessionQuestionTiming.session_id == session_id,
                Question.question_type.in_([QuestionType.MCQ, QuestionType.SCALE, QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH]),
            )
            .order_by(SessionQuestionTiming.question_id, SessionQuestionTiming.opened_at)
        )
        timings = timings_result.scalars().all()

        # Group timings by question_id — keep all windows (host may go back)
        from collections import defaultdict
        timings_by_question = defaultdict(list)
        for t in timings:
            timings_by_question[t.question_id].append(t)

        # Load all active participants
        participants_result = await db.execute(
            select(Participant)
            .filter(Participant.session_id == session_id, Participant.is_active == True)
            .order_by(Participant.id)
        )
        participants = participants_result.scalars().all()

        # Load all scored-question answers for this session (correct ones for score, all for timing)
        answers_result = await db.execute(
            select(Answer)
            .join(Question, Question.id == Answer.question_id)
            .filter(
                Answer.session_id == session_id,
                Question.question_type.in_([QuestionType.MCQ, QuestionType.SCALE, QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH]),
            )
        )
        all_answers = answers_result.scalars().all()

        # Index answers by (participant_id, question_id)
        answer_map: dict = {}
        for a in all_answers:
            answer_map[(a.participant_id, a.question_id)] = a

        def compute_time(participant_id: int) -> Optional[float]:
            """
            Sum of per-question response times:
              - Answered (right or wrong): answer_time - question opened_at, clamped to window
              - Not answered + window closed: full window duration (penalised for no response)
              - Not answered + window open: skipped (current question still in progress)
            Returns None only if no question windows exist yet.
            """
            if not timings_by_question:
                return None
            now = datetime.utcnow()
            total = 0.0
            for qid, windows in timings_by_question.items():
                answer = answer_map.get((participant_id, qid))
                if answer:
                    # Find the timing window active when the participant answered
                    matched = next(
                        (w for w in windows
                         if w.opened_at <= answer.created_at <= (w.closed_at or now)),
                        windows[-1]  # fallback to latest window
                    )
                    effective_close = matched.closed_at or now
                    delta = (answer.created_at - matched.opened_at).total_seconds()
                    window_dur = (effective_close - matched.opened_at).total_seconds()
                    total += max(0.0, min(delta, window_dur))
                else:
                    # Not answered: charge up to closed_at if closed, or now if still open
                    last = windows[-1]
                    effective_close = last.closed_at or now
                    total += (effective_close - last.opened_at).total_seconds()
            return round(total, 1)

        def question_points(question_id: int) -> int:
            q = question_by_id.get(question_id)
            return q.points if q and q.points else 1

        def count_correct(participant_id: int) -> int:
            import re
            total = 0
            for a in all_answers:
                if a.participant_id != participant_id:
                    continue
                if a.is_correct is True:
                    total += question_points(a.question_id)
                    continue
                q = question_by_id.get(a.question_id)
                if not q or q.question_type not in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH):
                    continue
                expected = (q.options or [None])[0]
                if not expected or not a.text_answer:
                    continue
                    
                response_clean = a.text_answer.strip().lower()
                expected_clean = str(expected).strip().lower()
                
                if response_clean == expected_clean:
                    total += question_points(a.question_id)
            return total

        # Build scored + timed entries, then sort
        scored = [
            (p, count_correct(p.id), compute_time(p.id))
            for p in participants
        ]
        # Sort: score DESC, time ASC (None → treated as infinity so they sort last), id ASC
        scored.sort(key=lambda x: (-x[1], x[2] if x[2] is not None else float('inf'), x[0].id))

        # Assign ranks (tied when score AND time are equal)
        entries = []
        current_rank = 1
        prev_key = None
        for i, (p, score, time_taken) in enumerate(scored):
            current_key = (score, round(time_taken, 3) if time_taken is not None else None)
            if prev_key is not None and current_key != prev_key:
                current_rank = i + 1
            entries.append(LeaderboardEntry(
                rank=current_rank,
                participant_id=p.id,
                display_name=p.display_name or 'Guest',
                score=score,
                is_current_participant=(p.id == current_participant_id),
                time_taken_seconds=round(time_taken, 1) if time_taken is not None else None,
            ))
            prev_key = current_key

        current_participant_rank = None
        for entry in entries:
            if entry.is_current_participant:
                current_participant_rank = entry.rank
                break

        return LeaderboardResponse(
            session_id=session_id,
            entries=entries,
            total_participants=len(entries),
            current_participant_rank=current_participant_rank,
            mcq_question_count=scored_question_count
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
