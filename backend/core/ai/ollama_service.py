"""
Backward-compatibility shim — delegates to OllamaProvider.

All new code should import from core.ai.router instead.
This module is preserved so existing callers (answer_service_async, scripts) don't break.
"""
from core.ai.base import AIProviderError
from core.ai.providers.ollama import OllamaProvider as _OllamaProvider

# Re-export the error class under the old name
OllamaError = AIProviderError

_inst = _OllamaProvider()


async def generate_questions(topic: str, count: int = 5, language: str = "en", model: str = None) -> list[dict]:
    result = await _inst.generate_questions(topic, count, language, "quiz")
    return result.get("questions", [])


async def generate_distractors(
    question: str, correct_answer: str, count: int = 3, model: str = None
) -> list[str]:
    return await _inst.generate_distractors(question, correct_answer, count)


async def generate_poll_prompt(topic: str, language: str = "en", model: str = None) -> str:
    return await _inst.generate_poll_prompt(topic, language)


async def rewrite_text(
    text: str, context: str = "quiz question", language: str = "en", model: str = None
) -> str:
    return await _inst.rewrite_text(text, context, language)


async def grade_text_answer(participant_answer: str, expected_answer: str) -> bool:
    return await _inst.grade_text_answer(participant_answer, expected_answer)


async def list_available_models() -> list[str]:
    return await _inst.list_available_models()
