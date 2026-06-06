#!/usr/bin/env python3
"""Send a demo result email to a review address using real participant data."""
import asyncio, sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

OVERRIDE_EMAIL = 'nishant.verma@natwest.com'
OVERRIDE_NAME  = 'Nishant (preview)'

# Gokulnath Nagarajan, C9 (quiz 200, session 444) — 3 attempts, violations
QUIZ_ID      = 200
TARGET_EMAIL = 'gokulnath.nagarajan@natwest.com'

async def main():
    from collections import defaultdict
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from persistence.database_async import AsyncSessionLocal
    from persistence.models.quiz import Quiz, Participant, Answer
    from persistence.models.proctoring import ProctoringSession, ProctoringEvent
    from features.quiz.schemas import ExamQuestionResult
    from core.auth.email_service import send_exam_result_email
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        # Load quiz + questions
        res = await db.execute(
            select(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == QUIZ_ID)
        )
        quiz = res.scalar_one()
        questions = sorted(quiz.questions, key=lambda q: q.order)
        max_score = sum(q.points for q in questions)

        all_session_ids = []
        if quiz.exam_session_id:
            all_session_ids.append(quiz.exam_session_id)
        all_session_ids += [e['session_id'] for e in (quiz.linked_exam_session_ids or [])]

        # Load all attempts for this email
        p_res = await db.execute(
            select(Participant).filter(
                Participant.session_id.in_(all_session_ids),
                Participant.completed_at.isnot(None),
                Participant.email == TARGET_EMAIL,
            )
        )
        participants = p_res.scalars().all()
        print(f"Found {len(participants)} attempt(s) for {TARGET_EMAIL}")

        all_pids = [p.id for p in participants]

        # All answers
        a_res = await db.execute(
            select(Answer).filter(
                Answer.participant_id.in_(all_pids),
                Answer.session_id.in_(all_session_ids),
            )
        )
        answers_by_pid = defaultdict(dict)
        for a in a_res.scalars().all():
            answers_by_pid[a.participant_id][a.question_id] = a

        # Proctoring
        ps_res = await db.execute(
            select(ProctoringSession).filter(
                ProctoringSession.quiz_id == QUIZ_ID,
                ProctoringSession.participant_id.in_(all_pids),
            )
        )
        proctoring_by_pid = {ps.participant_id: ps for ps in ps_res.scalars().all()}

        pe_res = await db.execute(
            select(ProctoringEvent.participant_id, ProctoringEvent.event_type).filter(
                ProctoringEvent.quiz_id == QUIZ_ID,
                ProctoringEvent.participant_id.in_(all_pids),
            ).distinct()
        )
        violations_by_pid = defaultdict(list)
        for pid, etype in pe_res.all():
            violations_by_pid[pid].append(etype)

        def _score(p):
            s = 0
            for q in questions:
                a = answers_by_pid.get(p.id, {}).get(q.id)
                if a and a.is_correct:
                    s += q.points
                elif a and a.is_correct == 0:
                    s -= q.negative_points
            return max(0, s)

        def _time(p):
            if p.started_at and p.completed_at:
                return (p.completed_at - p.started_at).total_seconds()
            return None

        # Score all attempts, pick best
        scored = [(p, _score(p), _time(p)) for p in participants]
        scored.sort(key=lambda x: (-x[1], x[2] or 9_999_999))
        best_p, best_score, best_time = scored[0]

        all_attempts = [
            {'score': sc, 'max_score': max_score, 'time_taken_seconds': tt, 'completed_at': p.completed_at}
            for p, sc, tt in scored
        ]

        # Build question results for best attempt
        p_ans = answers_by_pid.get(best_p.id, {})
        question_results = []
        correct_count = wrong_count = unanswered_count = 0
        for q in questions:
            answer = p_ans.get(q.id)
            participant_ans = answer.selected_option_index if answer else None
            is_correct      = answer.is_correct if answer else None
            points_earned = neg_applied = 0
            if participant_ans is None:
                unanswered_count += 1
            elif is_correct:
                correct_count += 1
                points_earned = q.points
            else:
                wrong_count += 1
                neg_applied = q.negative_points
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

        percentage = round((best_score / max_score * 100) if max_score > 0 else 0.0, 2)

        ps = proctoring_by_pid.get(best_p.id)
        integrity_score  = ps.integrity_score if ps else None
        violation_count  = ps.violation_count if ps else 0
        is_locked        = bool(ps.is_locked) if ps else False
        violation_types  = violations_by_pid.get(best_p.id, [])

        print(f"Best attempt: pid={best_p.id}, score={best_score}/{max_score}, time={best_time}s")
        print(f"Integrity: {integrity_score}, violations: {violation_count}, locked: {is_locked}")
        print(f"Violation types: {violation_types}")
        print(f"Sending to: {OVERRIDE_EMAIL}")

        ok = await send_exam_result_email(
            email=OVERRIDE_EMAIL,
            name=OVERRIDE_NAME,
            quiz_title=quiz.title,
            total_score=best_score,
            max_score=max_score,
            percentage=percentage,
            correct_count=correct_count,
            wrong_count=wrong_count,
            unanswered_count=unanswered_count,
            question_results=question_results,
            started_at=best_p.started_at,
            completed_at=best_p.completed_at,
            time_taken_seconds=best_time,
            attempt_count=len(participants),
            all_attempts=all_attempts,
            integrity_score=integrity_score,
            violation_count=violation_count,
            is_locked=is_locked,
            violation_types=violation_types,
        )
        print("Email sent!" if ok else "Email FAILED")

asyncio.run(main())
