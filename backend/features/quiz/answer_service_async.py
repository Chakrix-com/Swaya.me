"""
Answer Service - Submit and aggregate answers (Async)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from datetime import datetime
import json
import os

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
        # Get participant with session and quiz relationships
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
        
        # Verify this is an option-based question
        if current_question.question_type not in (QuestionType.MCQ, QuestionType.SCALE):
            raise ValueError("This endpoint is for option-based questions only")
        
        # Check if already answered (one answer per participant)
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
        
        # Validate option index against the current option count
        option_count = len(current_question.options or [])
        if option_count == 0:
            raise ValueError("Question has no options configured")
        if request.selected_option_index < 0 or request.selected_option_index >= option_count:
            raise ValueError("Invalid option index")
        
        # Option-based correctness (leaderboard still counts MCQ only)
        is_correct = (
            request.selected_option_index == current_question.correct_answer_index
            if (
                current_question.question_type in (QuestionType.MCQ, QuestionType.SCALE)
                and current_question.correct_answer_index is not None
            )
            else None
        )
        
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
        # Get participant with session and quiz relationships
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
        
        if current_question.question_type not in (
            QuestionType.WORD_CLOUD,
            QuestionType.SINGLE_LINE,
            QuestionType.PARAGRAPH,
        ):
            raise ValueError("This endpoint is for text-based questions only")

        # Only word cloud allows unlimited submissions
        if current_question.question_type != QuestionType.WORD_CLOUD:
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
        
        # Matches response with correct answer: strip whitespaces and convert to lowercase
        expected_answer = (current_question.options or [None])[0]
        is_text_scored = current_question.question_type in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH)
        
        is_correct = None
        if is_text_scored and expected_answer:
            response_clean = request.text_answer.strip().lower()
            expected_clean = str(expected_answer).strip().lower()
            is_correct = (response_clean == expected_clean)

        
        # Create answer
        answer = Answer(
            session_id=session.id,
            participant_id=participant.id,
            question_id=request.question_id,
            text_answer=request.text_answer.strip(),
            selected_option_index=None,
            is_correct=is_correct
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
            message="Response submitted successfully",
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
                total_answered = len(participant_answers)
                import re
                correct_answers = 0
                for ans in participant_answers:
                    if ans.is_correct is True:
                        correct_answers += 1
                        continue
                    q = question_by_id.get(ans.question_id)
                    if not q or q.question_type not in (QuestionType.SINGLE_LINE, QuestionType.PARAGRAPH):
                        continue
                    expected = (q.options or [None])[0]
                    if not expected or not ans.text_answer:
                        continue
                    
                    response_clean = ans.text_answer.strip().lower()
                    expected_clean = str(expected).strip().lower()
                    
                    if response_clean == expected_clean:
                        correct_answers += 1
                
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
                        "option_a": options[0] if options and len(options) > 0 else "",
                        "option_b": options[1] if options and len(options) > 1 else "",
                        "option_c": options[2] if options and len(options) > 2 else "",
                        "option_d": options[3] if options and len(options) > 3 else "",
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
                        "option_images": {
                            key: ImageService.to_absolute_url(path, base_url)
                            for key, path in (question_obj.option_images or {}).items()
                        } if question_obj.option_images else None
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
                    if question_obj.question_type.value in ('single_line', 'paragraph'):
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
            1 for q in session.quiz.questions
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

        def count_correct(participant_id: int) -> int:
            import re
            total = 0
            for a in all_answers:
                if a.participant_id != participant_id:
                    continue
                if a.is_correct is True:
                    total += 1
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
                    total += 1
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
