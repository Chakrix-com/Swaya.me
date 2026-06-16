"""
AI provider router — picks the right provider based on AI_PRIMARY_PROVIDER and
AI_LIGHT_PROVIDER settings, then exposes module-level async functions that
broker/api/ai.py and feature services can call directly.

Usage:
    from core.ai import router as ai_router
    result = await ai_router.generate_questions(...)

Default (no env vars needed):
    AI_PRIMARY_PROVIDER=gemini   → GeminiProvider
    AI_LIGHT_PROVIDER=ollama     → OllamaProvider

Self-hosted alternatives:
    AI_PRIMARY_PROVIDER=openai_compat   + OPENAI_API_KEY, OPENAI_BASE_URL
    AI_PRIMARY_PROVIDER=anthropic       + ANTHROPIC_API_KEY
    AI_PRIMARY_PROVIDER=ollama          (fully local, no cloud keys needed)
"""
from functools import lru_cache

from core.ai.base import BaseAIProvider
from core.config.settings import settings

_VALID_PROVIDERS = {"gemini", "openai", "openai_compat", "anthropic", "ollama"}


@lru_cache(maxsize=1)
def get_primary_provider() -> BaseAIProvider:
    """Return the configured primary (quality-sensitive) provider. Cached after first call."""
    name = settings.ai.primary_provider.strip().lower()
    if name == "gemini":
        from core.ai.providers.gemini import GeminiProvider
        return GeminiProvider(use_fast_model=False)
    if name in ("openai", "openai_compat"):
        from core.ai.providers.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(use_fast_model=False)
    if name == "anthropic":
        from core.ai.providers.anthropic import AnthropicProvider
        return AnthropicProvider(use_fast_model=False)
    if name == "ollama":
        from core.ai.providers.ollama import OllamaProvider
        return OllamaProvider()
    raise ValueError(
        f"Unknown AI_PRIMARY_PROVIDER: '{name}'. Valid values: {sorted(_VALID_PROVIDERS)}"
    )


@lru_cache(maxsize=1)
def get_light_provider() -> BaseAIProvider:
    """Return the configured light (speed-sensitive) provider. Cached after first call."""
    name = settings.ai.light_provider.strip().lower()
    if name == "ollama":
        from core.ai.providers.ollama import OllamaProvider
        return OllamaProvider()
    if name in ("openai", "openai_compat"):
        from core.ai.providers.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(use_fast_model=True)
    if name == "gemini":
        from core.ai.providers.gemini import GeminiProvider
        return GeminiProvider(use_fast_model=True)
    if name == "anthropic":
        from core.ai.providers.anthropic import AnthropicProvider
        return AnthropicProvider(use_fast_model=True)
    raise ValueError(
        f"Unknown AI_LIGHT_PROVIDER: '{name}'. Valid values: {sorted(_VALID_PROVIDERS)}"
    )


# ── Module-level convenience wrappers ─────────────────────────────────────────
# All callers import from here; they don't need to know which provider is active.

async def generate_questions(
    prompt: str,
    count: int,
    language: str,
    quiz_type: str,
    existing_questions: list[str] | None = None,
) -> dict:
    return await get_primary_provider().generate_questions(
        prompt, count, language, quiz_type, existing_questions
    )


async def validate_quiz_prompt(prompt: str, language: str = "en") -> tuple[bool, str]:
    return await get_primary_provider().validate_quiz_prompt(prompt, language)


async def generate_participant_summary(**kwargs) -> str:
    return await get_primary_provider().generate_participant_summary(**kwargs)


async def analyze_exam_results(results: dict, custom_prompt: str | None = None) -> str:
    return await get_primary_provider().analyze_exam_results(results, custom_prompt)


async def generate_distractors(
    question: str, correct_answer: str, count: int = 3
) -> list[str]:
    return await get_light_provider().generate_distractors(question, correct_answer, count)


async def generate_poll_prompt(topic: str, language: str = "en") -> str:
    return await get_light_provider().generate_poll_prompt(topic, language)


async def rewrite_text(text: str, context: str = "quiz question", language: str = "en") -> str:
    return await get_light_provider().rewrite_text(text, context, language)


async def grade_text_answer(participant_answer: str, expected_answer: str) -> bool:
    return await get_light_provider().grade_text_answer(participant_answer, expected_answer)


async def list_available_models() -> list[str]:
    return await get_light_provider().list_available_models()
