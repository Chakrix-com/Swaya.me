"""
One-off: send exam result email to a specific participant.
Usage: python scripts/send_one_exam_email.py <quiz_id> <participant_id>
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENV_FILE", "/www/wwwroot/swaya-live/backend/.env")

# Load production .env before importing settings
from dotenv import load_dotenv
load_dotenv("/www/wwwroot/swaya-live/backend/.env", override=True)

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from persistence.database_async import AsyncSessionLocal
from persistence.models.quiz import Quiz, Participant, Answer
from features.quiz.schemas import ExamQuestionResult
from core.auth.email_service import send_exam_result_email
from core.ai.gemini_service import generate_participant_summary, GeminiError
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(quiz_id: int, participant_id: int):
    async with AsyncSessionLocal() as db:
        quiz_res = await db.execute(
            select(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id)
        )
        quiz = quiz_res.scalar_one_or_none()
        if not quiz:
            print(f"Quiz {quiz_id} not found")
            return

        p_res = await db.execute(select(Participant).filter(Participant.id == participant_id))
        participant = p_res.scalar_one_or_none()
        if not participant:
            print(f"Participant {participant_id} not found")
            return

        if not participant.email:
            print("Participant has no email")
            return

        questions = sorted(quiz.questions, key=lambda q: q.order)

        a_res = await db.execute(
            select(Answer).filter(
                Answer.participant_id == participant.id,
                Answer.session_id == quiz.exam_session_id,
            )
        )
        answers_by_qid = {a.question_id: a for a in a_res.scalars().all()}

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

        time_taken_seconds = None
        if participant.started_at and participant.completed_at:
            time_taken_seconds = (participant.completed_at - participant.started_at).total_seconds()

        print(f"Score: {total_score}/{max_score} ({percentage}%), correct={correct_count}, wrong={wrong_count}, skipped={unanswered_count}")
        print(f"Time taken: {time_taken_seconds}s")
        print("Generating AI summary...")

        ai_summary = None
        try:
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
            print("AI summary generated.")
        except Exception as e:
            print(f"AI summary skipped: {e}")

        print(f"Sending email to {participant.email}...")
        ok = await send_exam_result_email(
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
        print("Email sent!" if ok else "Email FAILED.")


if __name__ == "__main__":
    quiz_id = int(sys.argv[1]) if len(sys.argv) > 1 else 185
    participant_id = int(sys.argv[2]) if len(sys.argv) > 2 else 15602
    asyncio.run(main(quiz_id, participant_id))
