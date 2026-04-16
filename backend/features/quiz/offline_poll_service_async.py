"""
Offline Poll Service — handles self-service participation in offline polls.
All operations are async. Public endpoints do not require authentication.
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from persistence.models.quiz import (
    Quiz, QuizType, QuizSession, QuizSessionStatus,
    Question, QuestionType, Participant, Answer,
)
from features.quiz.schemas import (
    QuestionResponse,
    OfflinePollInfoResponse,
    OfflinePollJoinResponse,
    OfflineResultsResponse,
    OfflineResultsQuestionResponse,
)
from shared.exceptions.quiz import QuizNotFoundError, QuizValidationError
from core.storage import ImageService
import os

logger = logging.getLogger(__name__)

_BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _poll_status(quiz: Quiz) -> str:
    now = _utcnow()
    if not quiz.poll_slug:
        return "not_published"
    if quiz.offline_start_at and now < quiz.offline_start_at:
        return "not_started"
    if quiz.offline_end_at and now > quiz.offline_end_at:
        return "closed"
    return "active"


def _to_question_response(q: Question) -> QuestionResponse:
    return QuestionResponse(
        id=q.id,
        question_type=q.question_type,
        text=q.text,
        options=q.options,
        order=q.order,
        correct_answer_index=None,  # Never reveal to participants
        question_image_url=ImageService.to_absolute_url(q.question_image_url, _BASE_URL),
        option_images={
            k: ImageService.to_absolute_url(v, _BASE_URL)
            for k, v in (q.option_images or {}).items()
        } if q.option_images else None,
        points=q.points,
        max_time_seconds=q.max_time_seconds,
        is_required=getattr(q, 'is_required', False) or False,
    )


async def get_poll_info(db: AsyncSession, slug: str) -> OfflinePollInfoResponse:
    """Public — return basic info about an offline poll."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.poll_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Poll not found")

    status = _poll_status(quiz)
    return OfflinePollInfoResponse(
        slug=slug,
        title=quiz.title,
        description=quiz.description,
        status=status,
        starts_at=quiz.offline_start_at,
        ends_at=quiz.offline_end_at,
        question_count=len(quiz.questions),
    )


async def join_or_resume(
    db: AsyncSession,
    slug: str,
    display_name: Optional[str] = None,
    session_token: Optional[str] = None,
) -> OfflinePollJoinResponse:
    """
    Public — create or resume a participant session for an offline poll.
    Returns all questions and any previously saved answers.
    """
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.poll_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Poll not found")

    status = _poll_status(quiz)
    if status != "active":
        from fastapi import HTTPException
        if status == "not_started":
            raise HTTPException(status_code=410, detail="Poll has not started yet")
        elif status == "closed":
            raise HTTPException(status_code=410, detail="Poll has closed")
        else:
            raise HTTPException(status_code=410, detail="Poll is not available")

    questions = sorted(quiz.questions, key=lambda q: q.order)

    # Try to resume an existing participant
    if session_token:
        participant_result = await db.execute(
            select(Participant)
            .options(selectinload(Participant.answers))
            .filter(Participant.session_token == session_token)
        )
        participant = participant_result.scalar_one_or_none()

        if participant and participant.session_id == quiz.offline_session_id:
            saved_answers = [
                {
                    "question_id": a.question_id,
                    "selected_option_index": a.selected_option_index,
                    "text_answer": a.text_answer,
                }
                for a in participant.answers
            ]
            return OfflinePollJoinResponse(
                session_token=participant.session_token,
                participant_id=participant.id,
                quiz_title=quiz.title,
                questions=[_to_question_response(q) for q in questions],
                saved_answers=saved_answers,
                ends_at=quiz.offline_end_at,
            )

    # Create new participant
    new_token = secrets.token_urlsafe(32)
    participant = Participant(
        session_id=quiz.offline_session_id,
        display_name=display_name or "Anonymous",
        session_token=new_token,
        is_active=True,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)

    return OfflinePollJoinResponse(
        session_token=new_token,
        participant_id=participant.id,
        quiz_title=quiz.title,
        questions=[_to_question_response(q) for q in questions],
        saved_answers=[],
        ends_at=quiz.offline_end_at,
    )


async def save_answer(
    db: AsyncSession,
    slug: str,
    session_token: str,
    question_id: int,
    selected_option_index: Optional[int] = None,
    text_answer: Optional[str] = None,
) -> dict:
    """Public — upsert a single answer for an offline poll participant."""
    # Load quiz
    result = await db.execute(
        select(Quiz).filter(Quiz.poll_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Poll not found")

    if _poll_status(quiz) != "active":
        from fastapi import HTTPException
        raise HTTPException(status_code=410, detail="Poll window is not active")

    # Validate participant
    p_result = await db.execute(
        select(Participant).filter(
            Participant.session_token == session_token,
            Participant.session_id == quiz.offline_session_id,
        )
    )
    participant = p_result.scalar_one_or_none()
    if not participant:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid session token")

    if participant.completed_at:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Poll already completed")

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

    # Compute is_correct for MCQ
    is_correct = None
    if question.question_type == QuestionType.MCQ and selected_option_index is not None:
        is_correct = (selected_option_index == question.correct_answer_index)

    # Content filter for text answers
    if text_answer:
        try:
            from better_profanity import profanity
            if profanity.contains_profanity(text_answer):
                text_answer = profanity.censor(text_answer)
        except Exception:
            pass

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
        existing.text_answer = text_answer
        existing.is_correct = is_correct
    else:
        answer = Answer(
            session_id=quiz.offline_session_id,
            participant_id=participant.id,
            question_id=question_id,
            selected_option_index=selected_option_index,
            text_answer=text_answer,
            is_correct=is_correct,
        )
        db.add(answer)

    await db.commit()
    return {"saved": True}


async def complete_poll(
    db: AsyncSession,
    slug: str,
    session_token: str,
) -> dict:
    """Public — mark the participant's poll as completed."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.poll_slug == slug)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Poll not found")

    # Allow completing even after window closed (last-minute submissions)
    p_result = await db.execute(
        select(Participant)
        .options(selectinload(Participant.answers))
        .filter(
            Participant.session_token == session_token,
            Participant.session_id == quiz.offline_session_id,
        )
    )
    participant = p_result.scalar_one_or_none()
    if not participant:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid session token")

    if participant.completed_at:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Poll already completed")

    # Enforce required questions
    required_questions = [q for q in quiz.questions if getattr(q, 'is_required', False)]
    if required_questions:
        answered_question_ids = {a.question_id for a in participant.answers}
        missing = [q.text[:60] for q in required_questions if q.id not in answered_question_ids]
        if missing:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail=f"Required question(s) not answered: {'; '.join(missing)}"
            )

    participant.completed_at = _utcnow()
    await db.commit()

    # Count completed participants for this poll
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(Participant.id)).filter(
            Participant.session_id == quiz.offline_session_id,
            Participant.completed_at.isnot(None),
        )
    )
    completed_count = count_result.scalar_one()

    return {"completed": True, "submitted_count": completed_count}


async def get_results(
    db: AsyncSession,
    slug: str,
    current_user,
) -> OfflineResultsResponse:
    """Auth-required — return aggregated results for an offline poll."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.poll_slug == slug, Quiz.tenant_id == current_user.tenant_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundError("Poll not found")

    if not quiz.offline_session_id:
        raise QuizValidationError("Poll has not been published yet")

    from sqlalchemy import func
    # Count total & completed participants
    total_result = await db.execute(
        select(func.count(Participant.id)).filter(
            Participant.session_id == quiz.offline_session_id,
        )
    )
    total_participants = total_result.scalar_one()

    completed_result = await db.execute(
        select(func.count(Participant.id)).filter(
            Participant.session_id == quiz.offline_session_id,
            Participant.completed_at.isnot(None),
        )
    )
    completed_participants = completed_result.scalar_one()

    # Aggregate per-question results
    questions = sorted(quiz.questions, key=lambda q: q.order)
    question_results = []

    for question in questions:
        answers_result = await db.execute(
            select(Answer).filter(
                Answer.session_id == quiz.offline_session_id,
                Answer.question_id == question.id,
            )
        )
        answers = answers_result.scalars().all()

        if question.question_type == QuestionType.MCQ:
            num_options = len(question.options) if question.options else 4
            distribution = [0] * num_options
            for a in answers:
                if a.selected_option_index is not None and 0 <= a.selected_option_index < num_options:
                    distribution[a.selected_option_index] += 1
            question_results.append(OfflineResultsQuestionResponse(
                question_id=question.id,
                question_text=question.text,
                question_type=question.question_type.value,
                options=question.options,
                answer_distribution=distribution,
                word_frequencies=None,
                total_answers=len(answers),
            ))
        else:
            # Word cloud / text-based
            word_frequencies: dict = {}
            for a in answers:
                if a.text_answer:
                    for word in a.text_answer.lower().split():
                        word = word.strip(".,!?;:\"'")
                        if word:
                            word_frequencies[word] = word_frequencies.get(word, 0) + 1
            question_results.append(OfflineResultsQuestionResponse(
                question_id=question.id,
                question_text=question.text,
                question_type=question.question_type.value,
                options=None,
                answer_distribution=None,
                word_frequencies=dict(sorted(word_frequencies.items(), key=lambda x: -x[1])[:50]),
                total_answers=len(answers),
            ))

    is_open = _poll_status(quiz) == "active"

    return OfflineResultsResponse(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        slug=quiz.poll_slug,
        offline_start_at=quiz.offline_start_at,
        offline_end_at=quiz.offline_end_at,
        is_open=is_open,
        total_participants=total_participants,
        completed_participants=completed_participants,
        question_results=question_results,
    )


async def send_results_email(quiz_id: int) -> None:
    """Called by APScheduler at offline_end_at to email aggregated results."""
    from persistence.database_async import AsyncSessionLocal
    from core.auth.email_service import send_email
    from core.config.settings import settings

    logger.info(f"Sending offline poll results email for quiz {quiz_id}")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Quiz)
                .options(selectinload(Quiz.questions))
                .filter(Quiz.id == quiz_id)
            )
            quiz = result.scalar_one_or_none()
            if not quiz or not quiz.offline_results_email:
                logger.info(f"No email configured for quiz {quiz_id}, skipping")
                return

            # Build a simple class to pass as current_user stand-in
            class _FakeUser:
                tenant_id = quiz.tenant_id
                user_id = None

            results = await get_results(db, quiz.poll_slug, _FakeUser())

        frontend_url = os.getenv('FRONTEND_URL', 'https://www.swaya.me')
        results_url = f"{frontend_url}/quiz/{quiz_id}/offline-results"

        rows = ""
        for qr in results.question_results:
            rows += f"<tr><td style='padding:8px;border:1px solid #ddd'>{qr.question_text}</td>"
            if qr.answer_distribution and qr.options:
                dist = ", ".join(f"{opt}: {cnt}" for opt, cnt in zip(qr.options, qr.answer_distribution))
                rows += f"<td style='padding:8px;border:1px solid #ddd'>{dist}</td>"
            elif qr.word_frequencies:
                top = ", ".join(f"{w}({c})" for w, c in list(qr.word_frequencies.items())[:10])
                rows += f"<td style='padding:8px;border:1px solid #ddd'>{top}</td>"
            else:
                rows += "<td style='padding:8px;border:1px solid #ddd'>—</td>"
            rows += "</tr>"

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto">
          <h2>Offline Poll Results: {quiz.title}</h2>
          <p><strong>Total participants:</strong> {results.total_participants}<br>
             <strong>Completed:</strong> {results.completed_participants}</p>
          <table style="width:100%;border-collapse:collapse;margin-top:16px">
            <thead>
              <tr>
                <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Question</th>
                <th style="padding:8px;border:1px solid #ddd;background:#f5f5f5">Responses</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
          <p style="margin-top:24px">
            <a href="{results_url}">View full results on Swaya.me</a>
          </p>
        </div>
        """
        await send_email(
            subject=f"Offline Poll Results: {quiz.title}",
            recipients=[quiz.offline_results_email],
            html_body=html_body,
        )
        logger.info(f"Results email sent to {quiz.offline_results_email} for quiz {quiz_id}")
    except Exception as e:
        logger.error(f"Failed to send results email for quiz {quiz_id}: {e}", exc_info=True)
