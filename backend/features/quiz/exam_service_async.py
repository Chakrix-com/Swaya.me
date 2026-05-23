"""
Exam Service — handles self-paced, scored exam participation.
All operations are async. Public endpoints do not require authentication.
"""
import asyncio
import logging
import os
import random
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from persistence.models.quiz import (
    Quiz, QuizType, QuizStatus, QuizSession, QuizSessionStatus,
    Question, QuestionType, Participant, Answer,
)
from features.quiz.schemas import (
    ExamInfoResponse,
    ExamStartResponse,
    ExamQuestionResponse,
    ExamSubmitResponse,
    ExamQuestionResult,
    ExamResultsResponse,
    ExamLeaderboardEntry,
    ExamQuestionAnalytics,
    ExamPublishResponse,
    ParticipantDetailResponse,
    ParticipantQuestionResult,
)
from shared.exceptions.quiz import QuizNotFoundError, QuizValidationError, InvalidQuizStatusError, ProctoringViolationError
from core.auth.dependencies import CurrentUser
from core.storage import ImageService

logger = logging.getLogger(__name__)

_BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')
_GRACE_PERIOD_SECONDS = 600  # 10 minutes


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _exam_status(quiz: Quiz) -> str:
    now = _utcnow()
    if not quiz.exam_slug:
        return "not_published"
    if quiz.exam_start_at and now < quiz.exam_start_at:
        return "upcoming"
    if quiz.exam_end_at and now > quiz.exam_end_at:
        return "closed"
    return "open"


def _to_exam_question_response(q: Question) -> ExamQuestionResponse:
    return ExamQuestionResponse(
        id=q.id,
        text=q.text,
        options=q.options,
        order=q.order,
        question_image_url=ImageService.to_absolute_url(q.question_image_url, _BASE_URL),
        option_images={
            k: ImageService.to_absolute_url(v, _BASE_URL)
            for k, v in (q.option_images or {}).items()
        } if q.option_images else None,
        points=q.points,
        max_time_seconds=q.max_time_seconds,
    )


async def get_exam_info(db: AsyncSession, slug: str) -> ExamInfoResponse:
    """Public — return basic info about an exam."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.exam_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    status = _exam_status(quiz)
    has_per_q_timers = any(q.max_time_seconds for q in quiz.questions)

    # Compute scoring summary
    qs = quiz.questions
    points_values = [getattr(q, 'points', 1) or 1 for q in qs]
    neg_values = [getattr(q, 'negative_points', 0) or 0 for q in qs]
    from collections import Counter
    most_common_points = Counter(points_values).most_common(1)[0][0] if points_values else 1
    most_common_neg = Counter(neg_values).most_common(1)[0][0] if neg_values else 0
    scoring_varies = len(set(points_values)) > 1 or len(set(neg_values)) > 1

    return ExamInfoResponse(
        quiz_id=quiz.id,
        slug=slug,
        title=quiz.title,
        description=quiz.description,
        status=status,
        starts_at=quiz.exam_start_at,
        ends_at=quiz.exam_end_at,
        question_count=len(quiz.questions),
        time_limit_seconds=quiz.exam_time_limit_seconds,
        has_per_question_timers=has_per_q_timers,
        require_email=bool(quiz.exam_require_email),
        points_per_correct=most_common_points,
        negative_points_per_wrong=most_common_neg,
        scoring_varies=scoring_varies,
    )


async def request_exam_otp(
    db: AsyncSession,
    slug: str,
    display_name: str,
    email: str,
    redis,
) -> dict:
    """Public — generate and email a 6-digit OTP. Rate-limited to 3 requests per email per 10 min."""
    from core.auth.email_service import send_email

    result = await db.execute(select(Quiz).filter(Quiz.exam_slug == slug))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    if not quiz.exam_require_email:
        raise HTTPException(status_code=400, detail="Email verification is not enabled for this exam")

    status = _exam_status(quiz)
    if status not in ("open",):
        raise HTTPException(status_code=410, detail="Exam is not currently open")

    email_lower = email.lower()

    if quiz.exam_allowed_domains:
        allowed = [d.strip().lower().lstrip('@') for d in quiz.exam_allowed_domains.split(',') if d.strip()]
        email_domain = email_lower.split('@')[-1]
        if allowed and email_domain not in allowed:
            domain_list = ', '.join(f'@{d}' for d in allowed)
            raise HTTPException(
                status_code=403,
                detail=f"Only {domain_list} email addresses are accepted for this exam"
            )

    rate_key = f"exam_otp_rate:{slug}:{email_lower}"
    count = await redis.increment(rate_key)
    if count == 1:
        await redis.expire(rate_key, 600)
    if count > 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait 10 minutes.")

    otp = str(random.randint(100000, 999999))
    otp_key = f"exam_otp:{slug}:{email_lower}"
    await redis.set_json(otp_key, {"otp": otp, "display_name": display_name}, expire=600)

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto">
      <h2 style="color:#1677ff">Your Exam OTP</h2>
      <p>Hi {display_name},</p>
      <p>Use the code below to start your exam <strong>{quiz.title}</strong>:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:10px;text-align:center;
                  padding:20px;background:#f5f5f5;border-radius:8px;margin:20px 0">
        {otp}
      </div>
      <p style="color:#888;font-size:13px">This code expires in 10 minutes. Do not share it.</p>
    </div>
    """
    await send_email(
        subject=f"Your exam OTP — {quiz.title}",
        recipients=[email],
        html_body=html_body,
    )
    return {"sent": True}


async def start_exam(
    db: AsyncSession,
    slug: str,
    display_name: str,
    email: Optional[str],
    otp: Optional[str],
    redis,
) -> ExamStartResponse:
    """
    Public — create a new participant session and return all questions.
    Validates exam window and blocks re-entry after grace period.
    """
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.exam_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    status = _exam_status(quiz)
    if status == "upcoming":
        raise HTTPException(status_code=410, detail="Exam has not started yet")
    if status == "closed":
        raise HTTPException(status_code=410, detail="Exam has closed")
    if status != "open":
        raise HTTPException(status_code=410, detail="Exam is not available")

    # Verify OTP when the exam requires email verification
    verified_email = None
    if quiz.exam_require_email:
        if not email or not otp:
            raise HTTPException(status_code=400, detail="Email and OTP are required for this exam")
        email_lower = email.lower()
        otp_key = f"exam_otp:{slug}:{email_lower}"
        stored = await redis.get_json(otp_key)
        if not stored or stored.get("otp") != otp:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        await redis.delete(otp_key)
        verified_email = email

    questions = sorted(quiz.questions, key=lambda q: q.order)
    now = _utcnow()

    new_token = secrets.token_urlsafe(32)
    participant = Participant(
        session_id=quiz.exam_session_id,
        display_name=display_name,
        email=verified_email,
        session_token=new_token,
        is_active=True,
        started_at=now,
        last_activity_at=now,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)

    # Use timezone-aware datetime in response so the browser parses it as UTC
    started_at_utc = datetime.now(timezone.utc)
    return ExamStartResponse(
        session_token=new_token,
        participant_id=participant.id,
        quiz_title=quiz.title,
        questions=[_to_exam_question_response(q) for q in questions],
        started_at=started_at_utc,
        time_limit_seconds=quiz.exam_time_limit_seconds,
        ends_at=quiz.exam_end_at,
    )


async def _get_active_participant(
    db: AsyncSession,
    quiz: Quiz,
    session_token: str,
) -> Participant:
    """Load participant, enforce grace period, reject completed/abandoned."""
    p_result = await db.execute(
        select(Participant).filter(
            Participant.session_token == session_token,
            Participant.session_id == quiz.exam_session_id,
        )
    )
    participant = p_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=403, detail="Invalid session token")

    if participant.completed_at:
        raise HTTPException(status_code=400, detail="Exam already submitted")

    if participant.is_abandoned:
        raise HTTPException(status_code=403, detail="Exam session has expired (abandoned)")

    # Check grace period
    if participant.last_activity_at:
        idle_seconds = (_utcnow() - participant.last_activity_at).total_seconds()
        if idle_seconds > _GRACE_PERIOD_SECONDS:
            participant.is_abandoned = True
            await db.commit()
            raise HTTPException(status_code=403, detail="Exam session expired (10-minute inactivity)")

    # Check total time limit
    if quiz.exam_time_limit_seconds and participant.started_at:
        elapsed = (_utcnow() - participant.started_at).total_seconds()
        if elapsed > quiz.exam_time_limit_seconds:
            if not participant.completed_at:
                participant.completed_at = _utcnow()
                await db.commit()
            raise HTTPException(status_code=410, detail="Exam time limit exceeded")

    return participant


async def save_answer(
    db: AsyncSession,
    slug: str,
    session_token: str,
    question_id: int,
    selected_option_index: Optional[int],
) -> dict:
    """Public — upsert a single answer during an exam."""
    result = await db.execute(
        select(Quiz)
        .filter(Quiz.exam_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    # Allow saving answers even after window closes (grace for last question)
    participant = await _get_active_participant(db, quiz, session_token)

    # Block answer saves if proctoring has locked the session
    from persistence.models.proctoring import ProctoringSession
    ps_result = await db.execute(
        select(ProctoringSession).where(ProctoringSession.participant_id == participant.id)
    )
    ps = ps_result.scalar_one_or_none()
    if ps and ps.is_locked:
        raise HTTPException(status_code=423, detail="Session is locked")

    # Load question
    q_result = await db.execute(
        select(Question).filter(
            Question.id == question_id,
            Question.quiz_id == quiz.id,
        )
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise QuizNotFoundError("Question not found")

    is_correct = None
    if selected_option_index is not None:
        is_correct = (selected_option_index == question.correct_answer_index)

    # Upsert answer
    existing_result = await db.execute(
        select(Answer).filter(
            Answer.participant_id == participant.id,
            Answer.question_id == question_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.selected_option_index = selected_option_index
        existing.is_correct = is_correct
    else:
        answer = Answer(
            session_id=quiz.exam_session_id,
            participant_id=participant.id,
            question_id=question_id,
            selected_option_index=selected_option_index,
            is_correct=is_correct,
        )
        db.add(answer)

    participant.last_activity_at = _utcnow()
    await db.commit()
    return {"saved": True}


async def submit_exam(
    db: AsyncSession,
    slug: str,
    session_token: str,
    redis=None,
) -> ExamSubmitResponse:
    """Public — submit the exam, calculate score, return breakdown."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.exam_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    # Check proctoring — log a warning but never block submission.
    # Blocking here would leave answers saved but completed_at unset, permanently
    # stranding the participant as "in progress" with no recovery path.
    policy = quiz.proctoring_policy or {}
    webcam_enabled = policy.get("rules", {}).get("webcam_monitoring", {}).get("enabled", False)
    if policy.get("enabled") and webcam_enabled and redis:
        from features.proctoring.proctoring_service_async import get_snapshot_count
        count = await get_snapshot_count(session_token, redis)
        if count == 0:
            logger.warning(f"Proctoring flag for {session_token}: no webcam snapshots received — submission accepted, host review required")

    participant = await _get_active_participant(db, quiz, session_token)

    # Load all answers for this participant
    answers_result = await db.execute(
        select(Answer).filter(
            Answer.participant_id == participant.id,
            Answer.session_id == quiz.exam_session_id,
        )
    )
    answers = answers_result.scalars().all()
    answers_by_qid = {a.question_id: a for a in answers}

    questions = sorted(quiz.questions, key=lambda q: q.order)
    question_results = []
    total_score = 0
    max_score = 0
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0

    for q in questions:
        max_score += q.points
        answer = answers_by_qid.get(q.id)
        participant_ans = answer.selected_option_index if answer else None
        is_correct = answer.is_correct if answer else None

        points_earned = 0
        neg_applied = 0

        if participant_ans is None:
            unanswered_count += 1
        elif is_correct:
            correct_count += 1
            points_earned = q.points
            total_score += q.points
        else:
            wrong_count += 1
            neg_applied = q.negative_points
            total_score -= q.negative_points

        question_results.append(ExamQuestionResult(
            question_id=q.id,
            question_text=q.text,
            options=q.options,
            correct_answer_index=q.correct_answer_index,
            participant_answer=participant_ans,
            is_correct=is_correct,
            points_earned=points_earned,
            points_possible=q.points,
            negative_points_applied=neg_applied,
            answer_explanation=q.answer_explanation,
        ))

    # Floor at 0
    total_score = max(0, total_score)
    percentage = round((total_score / max_score * 100) if max_score > 0 else 0.0, 2)

    participant.completed_at = _utcnow()
    await db.commit()

    return ExamSubmitResponse(
        total_score=total_score,
        max_score=max_score,
        percentage=percentage,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unanswered_count=unanswered_count,
        question_results=question_results,
    )


async def get_my_result(
    db: AsyncSession,
    slug: str,
    session_token: str,
) -> ExamSubmitResponse:
    """Public — re-fetch a participant's own result after submission."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.exam_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    p_result = await db.execute(
        select(Participant).filter(
            Participant.session_token == session_token,
            Participant.session_id == quiz.exam_session_id,
        )
    )
    participant = p_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=403, detail="Invalid session token")
    if not participant.completed_at:
        raise HTTPException(status_code=400, detail="Exam not yet submitted")

    answers_result = await db.execute(
        select(Answer).filter(
            Answer.participant_id == participant.id,
            Answer.session_id == quiz.exam_session_id,
        )
    )
    answers = answers_result.scalars().all()
    answers_by_qid = {a.question_id: a for a in answers}

    questions = sorted(quiz.questions, key=lambda q: q.order)
    question_results = []
    total_score = 0
    max_score = 0
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0

    for q in questions:
        max_score += q.points
        answer = answers_by_qid.get(q.id)
        participant_ans = answer.selected_option_index if answer else None
        is_correct = answer.is_correct if answer else None

        points_earned = 0
        neg_applied = 0

        if participant_ans is None:
            unanswered_count += 1
        elif is_correct:
            correct_count += 1
            points_earned = q.points
            total_score += q.points
        else:
            wrong_count += 1
            neg_applied = q.negative_points
            total_score -= q.negative_points

        question_results.append(ExamQuestionResult(
            question_id=q.id,
            question_text=q.text,
            options=q.options,
            correct_answer_index=q.correct_answer_index,
            participant_answer=participant_ans,
            is_correct=is_correct,
            points_earned=points_earned,
            points_possible=q.points,
            negative_points_applied=neg_applied,
            answer_explanation=q.answer_explanation,
        ))

    total_score = max(0, total_score)
    percentage = round((total_score / max_score * 100) if max_score > 0 else 0.0, 2)

    return ExamSubmitResponse(
        total_score=total_score,
        max_score=max_score,
        percentage=percentage,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unanswered_count=unanswered_count,
        question_results=question_results,
    )


async def get_exam_results(
    db: AsyncSession,
    quiz_id: int,
    current_user: CurrentUser,
) -> ExamResultsResponse:
    """Auth-required — full results for host: leaderboard + per-question analytics."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    if quiz.quiz_type != QuizType.EXAM:
        raise QuizValidationError("Quiz is not an exam")

    if not quiz.exam_session_id:
        raise QuizValidationError("Exam has not been published yet")

    questions = sorted(quiz.questions, key=lambda q: q.order)
    max_score = sum(q.points for q in questions)

    # Load all participants
    participants_result = await db.execute(
        select(Participant).filter(
            Participant.session_id == quiz.exam_session_id,
        )
    )
    participants = participants_result.scalars().all()

    total_started = len(participants)
    total_completed = sum(1 for p in participants if p.completed_at)
    total_abandoned = sum(1 for p in participants if p.is_abandoned)

    # Load all answers for this session
    answers_result = await db.execute(
        select(Answer).filter(
            Answer.session_id == quiz.exam_session_id,
        )
    )
    all_answers = answers_result.scalars().all()

    # Build per-participant answer map
    answers_by_participant: dict[int, dict[int, Answer]] = {}
    for a in all_answers:
        answers_by_participant.setdefault(a.participant_id, {})[a.question_id] = a

    # Build leaderboard — completed participants ranked, then in-progress at the bottom
    completed_entries = []
    in_progress_entries = []
    score_sum = 0

    for p in participants:
        p_answers = answers_by_participant.get(p.id, {})
        score = 0
        correct = 0
        for q in questions:
            ans = p_answers.get(q.id)
            if ans and ans.is_correct:
                score += q.points
                correct += 1
            elif ans and ans.is_correct is False:
                score -= q.negative_points
        score = max(0, score)
        time_taken = None
        if p.started_at and p.completed_at:
            time_taken = (p.completed_at - p.started_at).total_seconds()

        entry = {
            "participant_id": p.id,
            "display_name": p.display_name or "Anonymous",
            "email": p.email,
            "score": score,
            "correct": correct,
            "time_taken": time_taken,
            "completed_at": p.completed_at,
            "is_abandoned": p.is_abandoned,
            "is_completed": p.completed_at is not None,
        }
        if p.completed_at:
            score_sum += score
            completed_entries.append(entry)
        else:
            in_progress_entries.append(entry)

    # Sort completed by score desc, then time asc
    completed_entries.sort(key=lambda x: (-x["score"], x["time_taken"] or 9999999))

    leaderboard = []
    for rank, entry in enumerate(completed_entries, start=1):
        leaderboard.append(ExamLeaderboardEntry(
            participant_id=entry["participant_id"],
            rank=rank,
            display_name=entry["display_name"],
            email=entry["email"],
            score=entry["score"],
            max_score=max_score,
            percentage=round((entry["score"] / max_score * 100) if max_score > 0 else 0.0, 2),
            correct_count=entry["correct"],
            time_taken_seconds=entry["time_taken"],
            completed_at=entry["completed_at"],
            is_abandoned=entry["is_abandoned"],
            is_completed=True,
        ))
    for entry in in_progress_entries:
        leaderboard.append(ExamLeaderboardEntry(
            participant_id=entry["participant_id"],
            rank=None,
            display_name=entry["display_name"],
            email=entry["email"],
            score=0,
            max_score=max_score,
            percentage=0.0,
            correct_count=0,
            time_taken_seconds=None,
            completed_at=None,
            is_abandoned=entry["is_abandoned"],
            is_completed=False,
        ))

    avg_score = round(score_sum / total_completed, 2) if total_completed > 0 else 0.0

    # Per-question analytics
    question_analytics = []
    for q in questions:
        num_options = len(q.options) if q.options else 4
        distribution = [0] * num_options
        correct_count_q = 0
        total_answers_q = 0

        for a in all_answers:
            if a.question_id == q.id:
                total_answers_q += 1
                if a.selected_option_index is not None and 0 <= a.selected_option_index < num_options:
                    distribution[a.selected_option_index] += 1
                if a.is_correct:
                    correct_count_q += 1

        question_analytics.append(ExamQuestionAnalytics(
            question_id=q.id,
            question_text=q.text,
            options=q.options,
            correct_answer_index=q.correct_answer_index,
            answer_distribution=distribution,
            correct_count=correct_count_q,
            total_answers=total_answers_q,
            percent_correct=round(
                (correct_count_q / total_answers_q * 100) if total_answers_q > 0 else 0.0, 2
            ),
        ))

    is_open = _exam_status(quiz) == "open"

    return ExamResultsResponse(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        slug=quiz.exam_slug,
        exam_start_at=quiz.exam_start_at,
        exam_end_at=quiz.exam_end_at,
        is_open=is_open,
        total_started=total_started,
        total_completed=total_completed,
        total_abandoned=total_abandoned,
        average_score=avg_score,
        max_score=max_score,
        leaderboard=leaderboard,
        question_analytics=question_analytics,
    )


async def get_participant_detail(
    db: AsyncSession,
    quiz_id: int,
    participant_id: int,
    current_user: CurrentUser,
) -> ParticipantDetailResponse:
    """Auth-required — per-participant question breakdown for host."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Exam not found")

    if not quiz.exam_session_id:
        raise QuizValidationError("Exam has not been published yet")

    part_result = await db.execute(
        select(Participant).filter(
            Participant.id == participant_id,
            Participant.session_id == quiz.exam_session_id,
        )
    )
    participant = part_result.scalar_one_or_none()
    if not participant:
        raise QuizNotFoundError("Participant not found")

    answers_result = await db.execute(
        select(Answer).filter(
            Answer.session_id == quiz.exam_session_id,
            Answer.participant_id == participant_id,
        )
    )
    answers = {a.question_id: a for a in answers_result.scalars().all()}

    questions = sorted(quiz.questions, key=lambda q: q.order)
    max_score = sum(q.points for q in questions)

    score = 0
    correct = wrong = unanswered = 0
    question_results = []

    for q in questions:
        ans = answers.get(q.id)
        points_earned = 0
        if ans and ans.is_correct:
            points_earned = q.points
            score += points_earned
            correct += 1
        elif ans and ans.is_correct is False:
            points_earned = -q.negative_points
            score -= q.negative_points
            wrong += 1
        elif ans is None:
            unanswered += 1

        question_results.append(ParticipantQuestionResult(
            question_id=q.id,
            order=q.order,
            question_text=q.text,
            options=q.options,
            correct_answer_index=q.correct_answer_index,
            participant_answer=ans.selected_option_index if ans else None,
            is_correct=ans.is_correct if ans else None,
            points_earned=max(0, points_earned),
            points_possible=q.points,
        ))

    score = max(0, score)
    time_taken = None
    if participant.started_at and participant.completed_at:
        time_taken = (participant.completed_at - participant.started_at).total_seconds()

    return ParticipantDetailResponse(
        participant_id=participant.id,
        display_name=participant.display_name or "Anonymous",
        email=participant.email,
        score=score,
        max_score=max_score,
        percentage=round((score / max_score * 100) if max_score > 0 else 0.0, 2),
        correct_count=correct,
        wrong_count=wrong,
        unanswered_count=unanswered,
        time_taken_seconds=time_taken,
        completed_at=participant.completed_at,
        questions=question_results,
    )


async def publish_exam(
    db: AsyncSession,
    quiz_id: int,
    current_user: CurrentUser,
) -> ExamPublishResponse:
    """Auth-required — publish an exam: create session, generate slug."""
    from apscheduler.triggers.date import DateTrigger
    from core.stats import scheduler as stats_scheduler

    result = await db.execute(
        select(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.tenant_id == current_user.tenant_id)
        .options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Quiz not found")

    if quiz.quiz_type != QuizType.EXAM:
        raise InvalidQuizStatusError("Quiz is not an exam")

    if quiz.status not in (QuizStatus.DRAFT, QuizStatus.READY):
        raise InvalidQuizStatusError("Exam is already archived")

    if quiz.exam_slug:
        raise InvalidQuizStatusError("Exam is already published")

    if not quiz.exam_start_at or not quiz.exam_end_at:
        raise QuizValidationError("Exam must have start and end dates set")

    if quiz.exam_end_at <= quiz.exam_start_at:
        raise QuizValidationError("End date must be after start date")

    if not quiz.questions:
        raise QuizValidationError("Exam must have at least one question")

    # Generate unique slug
    slug = None
    for _ in range(3):
        candidate = secrets.token_urlsafe(8)
        existing = await db.execute(
            select(Quiz).filter(Quiz.exam_slug == candidate)
        )
        if not existing.scalar_one_or_none():
            slug = candidate
            break

    if not slug:
        raise QuizValidationError("Failed to generate unique exam slug, please try again")

    # Create permanent ACTIVE session
    session = QuizSession(
        quiz_id=quiz.id,
        tenant_id=quiz.tenant_id,
        status=QuizSessionStatus.ACTIVE,
        current_question_index=-1,
        leaderboard_visible=False,
    )
    db.add(session)
    await db.flush()

    quiz.exam_slug = slug
    quiz.exam_session_id = session.id
    quiz.status = QuizStatus.READY
    await db.commit()

    # Schedule results email if configured
    if quiz.exam_results_email and quiz.exam_end_at:
        try:
            stats_scheduler.add_job(
                send_results_email,
                trigger=DateTrigger(run_date=quiz.exam_end_at),
                args=[quiz.id],
                id=f"exam_results_email_{quiz.id}",
                replace_existing=True,
            )
        except Exception as e:
            logger.warning(f"Could not schedule exam results email: {e}")

    frontend_url = os.getenv('FRONTEND_URL', 'https://www.swaya.me')
    exam_url = f"{frontend_url}/e/{slug}"

    return ExamPublishResponse(
        exam_url=exam_url,
        exam_slug=slug,
        quiz_id=quiz.id,
    )


async def unpublish_exam(
    db: AsyncSession,
    quiz_id: int,
    current_user: CurrentUser,
) -> dict:
    """Auth-required — unpublish an exam (revert to DRAFT, invalidate slug)."""
    result = await db.execute(
        select(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.tenant_id == current_user.tenant_id,
        )
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Quiz not found")

    if quiz.quiz_type != QuizType.EXAM:
        raise InvalidQuizStatusError("Quiz is not an exam")

    quiz.exam_slug = None
    quiz.exam_session_id = None
    quiz.status = QuizStatus.DRAFT
    await db.commit()
    return {"unpublished": True}


async def send_results_email(quiz_id: int) -> None:
    """Called by APScheduler at exam_end_at to email results to host."""
    from persistence.database_async import AsyncSessionLocal
    from core.auth.email_service import send_email

    logger.info(f"Sending exam results email for quiz {quiz_id}")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Quiz).filter(Quiz.id == quiz_id)
            )
            quiz = result.scalar_one_or_none()
            if not quiz or not quiz.exam_results_email:
                logger.info(f"No email configured for exam {quiz_id}, skipping")
                return

            class _FakeUser:
                tenant_id = quiz.tenant_id

            results = await get_exam_results(db, quiz_id, _FakeUser())

        frontend_url = os.getenv('FRONTEND_URL', 'https://www.swaya.me')
        results_url = f"{frontend_url}/quiz/{quiz_id}/exam-results"

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto">
          <h2>Exam Results: {quiz.title}</h2>
          <p>
            <strong>Total started:</strong> {results.total_started}<br>
            <strong>Completed:</strong> {results.total_completed}<br>
            <strong>Abandoned:</strong> {results.total_abandoned}<br>
            <strong>Average score:</strong> {results.average_score} / {results.max_score}
          </p>
          <p style="margin-top:24px">
            <a href="{results_url}">View full results on Swaya.me</a>
          </p>
        </div>
        """
        await send_email(
            subject=f"Exam Results: {quiz.title}",
            recipients=[quiz.exam_results_email],
            html_body=html_body,
        )
        logger.info(f"Exam results email sent to {quiz.exam_results_email} for quiz {quiz_id}")
    except Exception as e:
        logger.error(f"Failed to send exam results email for quiz {quiz_id}: {e}", exc_info=True)


async def send_participant_results_emails(quiz_id: int) -> list:
    """Nightly batch — emails detailed results to every completed participant of a quiz.

    Returns a list of dicts for any per-participant failures:
        [{"email": "...", "error": "..."}]
    Raises on quiz-level failures (DB errors etc.) so the caller can track them.
    """
    from persistence.database_async import AsyncSessionLocal
    from core.auth.email_service import send_exam_result_email

    logger.info(f"Sending participant results emails for quiz {quiz_id}")
    failures = []

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id)
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            logger.warning(f"Quiz {quiz_id} not found for participant emails")
            return failures

        p_result = await db.execute(
            select(Participant).filter(
                Participant.session_id == quiz.exam_session_id,
                Participant.completed_at.isnot(None),
                Participant.email.isnot(None),
            )
        )
        participants = p_result.scalars().all()
        if not participants:
            logger.info(f"No completed participants with emails for quiz {quiz_id}")
            return failures

        questions = sorted(quiz.questions, key=lambda q: q.order)

        for participant in participants:
            try:
                a_result = await db.execute(
                    select(Answer).filter(
                        Answer.participant_id == participant.id,
                        Answer.session_id == quiz.exam_session_id,
                    )
                )
                answers_by_qid = {a.question_id: a for a in a_result.scalars().all()}

                question_results = []
                total_score = max_score = correct_count = wrong_count = unanswered_count = 0

                for q in questions:
                    max_score += q.points
                    answer = answers_by_qid.get(q.id)
                    participant_ans = answer.selected_option_index if answer else None
                    is_correct = answer.is_correct if answer else None
                    points_earned = neg_applied = 0

                    if participant_ans is None:
                        unanswered_count += 1
                    elif is_correct:
                        correct_count += 1
                        points_earned = q.points
                        total_score += q.points
                    else:
                        wrong_count += 1
                        neg_applied = q.negative_points
                        total_score -= q.negative_points

                    question_results.append(ExamQuestionResult(
                        question_id=q.id,
                        question_text=q.text,
                        options=q.options,
                        correct_answer_index=q.correct_answer_index,
                        participant_answer=participant_ans,
                        is_correct=is_correct,
                        points_earned=points_earned,
                        points_possible=q.points,
                        negative_points_applied=neg_applied,
                        answer_explanation=q.answer_explanation,
                    ))

                total_score = max(0, total_score)
                percentage = round((total_score / max_score * 100) if max_score > 0 else 0.0, 2)

                # Time taken
                time_taken_seconds = None
                if participant.started_at and participant.completed_at:
                    delta = participant.completed_at - participant.started_at
                    time_taken_seconds = delta.total_seconds()

                # AI personal summary — fail silently so email still sends
                ai_summary = None
                try:
                    from core.ai.gemini_service import generate_participant_summary, GeminiError
                    ai_summary = await generate_participant_summary(
                        name=participant.display_name or '',
                        quiz_title=quiz.title,
                        total_score=total_score,
                        max_score=max_score,
                        percentage=percentage,
                        correct_count=correct_count,
                        wrong_count=wrong_count,
                        unanswered_count=unanswered_count,
                        time_taken_seconds=time_taken_seconds,
                        started_at=participant.started_at.isoformat() if participant.started_at else None,
                        completed_at=participant.completed_at.isoformat() if participant.completed_at else None,
                        question_results=question_results,
                    )
                except Exception as ai_err:
                    logger.warning(f"AI summary skipped for participant {participant.id}: {ai_err}")

                await send_exam_result_email(
                    email=participant.email,
                    name=participant.display_name,
                    quiz_title=quiz.title,
                    total_score=total_score,
                    max_score=max_score,
                    percentage=percentage,
                    correct_count=correct_count,
                    wrong_count=wrong_count,
                    unanswered_count=unanswered_count,
                    question_results=question_results,
                    started_at=participant.started_at,
                    completed_at=participant.completed_at,
                    time_taken_seconds=time_taken_seconds,
                    ai_summary=ai_summary,
                )
                logger.info(f"Sent results email to participant {participant.id} for quiz {quiz_id}")
                await asyncio.sleep(0.5)  # throttle: ~120 emails/min, within Titan SMTP limits
            except Exception as e:
                err_str = str(e)
                logger.error(
                    f"Failed to send results email to participant {participant.id}: {err_str}",
                    exc_info=True,
                )
                failures.append({"email": participant.email, "error": err_str})

    return failures
