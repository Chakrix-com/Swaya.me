"""
Backward-compatibility shim — delegates to GeminiProvider.

All new code should import from core.ai.router instead.
This module is preserved so existing callers (exam_service_async, scripts) don't break.
"""
from core.ai.base import AIProviderError
from core.ai.providers.gemini import GeminiProvider as _GeminiProvider

# Re-export the error class under the old name
GeminiError = AIProviderError

_primary = _GeminiProvider(use_fast_model=False)
_fast = _GeminiProvider(use_fast_model=True)


async def generate_questions(
    prompt: str,
    count: int = 5,
    language: str = "en",
    quiz_type: str = "quiz",
    existing_questions: list[str] | None = None,
) -> dict:
    return await _primary.generate_questions(prompt, count, language, quiz_type, existing_questions)


async def generate_questions_stream(
    prompt: str,
    count: int = 5,
    language: str = "en",
    quiz_type: str = "quiz",
    existing_questions: list[str] | None = None,
):
    """Polyfill: generates all questions then yields them one by one."""
    import asyncio
    result = await generate_questions(
        prompt=prompt, count=count, language=language,
        quiz_type=quiz_type, existing_questions=existing_questions,
    )
    for q in result["questions"]:
        yield q
        await asyncio.sleep(0)
    yield {
        "done": True,
        "title": result["title"],
        "description": result["description"],
        "suggested_exam_duration_minutes": result.get("suggested_exam_duration_minutes"),
        "suggested_proctoring": result.get("suggested_proctoring"),
    }


async def validate_quiz_prompt(prompt: str, language: str = "en") -> tuple[bool, str]:
    return await _fast.validate_quiz_prompt(prompt, language)


async def generate_participant_summary(
    name: str,
    quiz_title: str,
    total_score: int,
    max_score: int,
    percentage: float,
    correct_count: int,
    wrong_count: int,
    unanswered_count: int,
    time_taken_seconds,
    started_at,
    completed_at,
    question_results: list,
) -> str:
    return await _fast.generate_participant_summary(
        name=name, quiz_title=quiz_title, total_score=total_score, max_score=max_score,
        percentage=percentage, correct_count=correct_count, wrong_count=wrong_count,
        unanswered_count=unanswered_count, time_taken_seconds=time_taken_seconds,
        started_at=started_at, completed_at=completed_at, question_results=question_results,
    )


async def analyze_exam_results(results: dict, custom_prompt: str | None = None) -> str:
    return await _primary.analyze_exam_results(results, custom_prompt)


async def generate_interview_sheet(participant_data: dict, quiz_title: str) -> str:
    return await _fast.generate_interview_sheet(participant_data, quiz_title)
