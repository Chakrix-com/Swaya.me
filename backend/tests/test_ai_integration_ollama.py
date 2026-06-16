"""
Integration smoke tests for OllamaProvider against a real local Ollama daemon.
Skipped automatically if Ollama is unreachable at the configured base URL.
Run these on the dev server where Ollama is running.
"""
import asyncio
import httpx
import pytest

from core.config.settings import settings


def _ollama_reachable() -> bool:
    try:
        resp = httpx.get(f"{settings.ollama.base_url}/api/tags", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


SKIP_IF_NO_OLLAMA = pytest.mark.skipif(
    not _ollama_reachable(),
    reason=f"Ollama not reachable at {settings.ollama.base_url}",
)


@SKIP_IF_NO_OLLAMA
def test_list_available_models_returns_something():
    from core.ai.providers.ollama import OllamaProvider
    provider = OllamaProvider()
    models = asyncio.run(provider.list_available_models())
    assert isinstance(models, list)
    # At least one model should be pulled
    assert len(models) > 0, "No models found in Ollama — pull at least one model first"


@SKIP_IF_NO_OLLAMA
def test_grade_text_answer_exact_match():
    from core.ai.providers.ollama import OllamaProvider
    provider = OllamaProvider()
    # Semantically equivalent — should return True
    result = asyncio.run(provider.grade_text_answer("Paris", "Paris, France"))
    assert isinstance(result, bool)


@SKIP_IF_NO_OLLAMA
def test_rewrite_text_returns_non_empty():
    from core.ai.providers.ollama import OllamaProvider
    provider = OllamaProvider()
    result = asyncio.run(provider.rewrite_text("teh qeustion", "quiz question", "en"))
    assert isinstance(result, str)
    assert len(result) > 0


@SKIP_IF_NO_OLLAMA
def test_generate_distractors_returns_list():
    from core.ai.providers.ollama import OllamaProvider
    provider = OllamaProvider()
    result = asyncio.run(
        provider.generate_distractors("What is the capital of France?", "Paris", count=3)
    )
    assert isinstance(result, list)
    assert len(result) >= 1
    for d in result:
        assert isinstance(d, str)
        assert d.strip() != "Paris"


@SKIP_IF_NO_OLLAMA
def test_generate_poll_prompt_returns_string():
    from core.ai.providers.ollama import OllamaProvider
    provider = OllamaProvider()
    result = asyncio.run(provider.generate_poll_prompt("team collaboration", "en"))
    assert isinstance(result, str)
    assert len(result) > 10  # Should be an actual question


# ── Backward-compat shim ──────────────────────────────────────────────────────

def test_ollama_shim_exports_same_functions():
    """Verify ollama_service.py shim still exports all original function names."""
    import core.ai.ollama_service as shim
    required = ["generate_questions", "generate_distractors", "generate_poll_prompt",
                "rewrite_text", "grade_text_answer", "list_available_models", "OllamaError"]
    for name in required:
        assert hasattr(shim, name), f"ollama_service shim missing: {name}"


def test_ollama_shim_error_class_is_ai_provider_error():
    from core.ai.ollama_service import OllamaError
    from core.ai.base import AIProviderError
    assert OllamaError is AIProviderError


def test_gemini_shim_exports_same_functions():
    """Verify gemini_service.py shim still exports all original function names."""
    import core.ai.gemini_service as shim
    required = ["generate_questions", "generate_questions_stream", "validate_quiz_prompt",
                "generate_participant_summary", "analyze_exam_results", "GeminiError"]
    for name in required:
        assert hasattr(shim, name), f"gemini_service shim missing: {name}"


def test_gemini_shim_error_class_is_ai_provider_error():
    from core.ai.gemini_service import GeminiError
    from core.ai.base import AIProviderError
    assert GeminiError is AIProviderError
