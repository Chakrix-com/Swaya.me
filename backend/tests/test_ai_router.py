"""
Unit tests for core.ai.base and core.ai.router.
No real HTTP calls — provider constructors are mocked.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clear_cache():
    from core.ai.router import get_primary_provider, get_light_provider
    get_primary_provider.cache_clear()
    get_light_provider.cache_clear()


def _provider_module(class_name: str) -> str:
    return {
        "GeminiProvider": "gemini",
        "OpenAICompatProvider": "openai_compat",
        "AnthropicProvider": "anthropic",
        "OllamaProvider": "ollama",
    }[class_name]


# ── BaseAIProvider ─────────────────────────────────────────────────────────────

def test_base_provider_defaults():
    from core.ai.base import BaseAIProvider, AIProviderError

    class MinimalProvider(BaseAIProvider):
        async def generate_questions(self, *a, **kw): return {}
        async def generate_distractors(self, *a, **kw): return []
        async def generate_poll_prompt(self, *a, **kw): return ""
        async def rewrite_text(self, *a, **kw): return ""

    p = MinimalProvider()

    # validate_quiz_prompt defaults to (True, "")
    assert asyncio.run(p.validate_quiz_prompt("anything", "en")) == (True, "")

    # grade_text_answer defaults to exact match
    assert asyncio.run(p.grade_text_answer("hello", "HELLO")) is True
    assert asyncio.run(p.grade_text_answer("hello", "world")) is False

    # list_available_models defaults to []
    assert asyncio.run(p.list_available_models()) == []

    # unsupported primary methods raise AIProviderError
    with pytest.raises(AIProviderError):
        asyncio.run(p.generate_participant_summary())

    with pytest.raises(AIProviderError):
        asyncio.run(p.analyze_exam_results({}))


# ── Router provider selection ──────────────────────────────────────────────────

@pytest.mark.parametrize("provider_name,expected_class", [
    ("gemini",        "GeminiProvider"),
    ("openai",        "OpenAICompatProvider"),
    ("openai_compat", "OpenAICompatProvider"),
    ("anthropic",     "AnthropicProvider"),
    ("ollama",        "OllamaProvider"),
])
def test_get_primary_provider_selects_correct_class(provider_name, expected_class):
    _clear_cache()
    mod = _provider_module(expected_class)
    with patch(f"core.ai.providers.{mod}.{expected_class}") as MockCls, \
         patch("core.ai.router.settings") as mock_settings:
        mock_settings.ai.primary_provider = provider_name
        MockCls.return_value = MagicMock()
        from core.ai.router import get_primary_provider
        get_primary_provider.cache_clear()
        get_primary_provider()
        MockCls.assert_called_once()


@pytest.mark.parametrize("provider_name,expected_class", [
    ("ollama",        "OllamaProvider"),
    ("openai",        "OpenAICompatProvider"),
    ("openai_compat", "OpenAICompatProvider"),
    ("gemini",        "GeminiProvider"),
    ("anthropic",     "AnthropicProvider"),
])
def test_get_light_provider_selects_correct_class(provider_name, expected_class):
    _clear_cache()
    mod = _provider_module(expected_class)
    with patch(f"core.ai.providers.{mod}.{expected_class}") as MockCls, \
         patch("core.ai.router.settings") as mock_settings:
        mock_settings.ai.light_provider = provider_name
        MockCls.return_value = MagicMock()
        from core.ai.router import get_light_provider
        get_light_provider.cache_clear()
        get_light_provider()
        MockCls.assert_called_once()


def test_router_raises_on_unknown_primary_provider():
    _clear_cache()
    with patch("core.ai.router.settings") as mock_settings:
        mock_settings.ai.primary_provider = "nonexistent_llm"
        from core.ai.router import get_primary_provider
        get_primary_provider.cache_clear()
        with pytest.raises(ValueError, match="AI_PRIMARY_PROVIDER"):
            get_primary_provider()


def test_router_raises_on_unknown_light_provider():
    _clear_cache()
    with patch("core.ai.router.settings") as mock_settings:
        mock_settings.ai.light_provider = "magic_cloud"
        from core.ai.router import get_light_provider
        get_light_provider.cache_clear()
        with pytest.raises(ValueError, match="AI_LIGHT_PROVIDER"):
            get_light_provider()


def test_router_lru_cache_returns_same_instance():
    _clear_cache()
    from core.ai.router import get_primary_provider, get_light_provider
    assert get_primary_provider() is get_primary_provider()
    assert get_light_provider() is get_light_provider()


# ── Module-level wrappers ─────────────────────────────────────────────────────

def test_router_exposes_all_wrapper_functions():
    from core.ai import router as ai_router
    required = [
        "generate_questions", "validate_quiz_prompt", "generate_participant_summary",
        "analyze_exam_results", "generate_distractors", "generate_poll_prompt",
        "rewrite_text", "grade_text_answer", "list_available_models",
    ]
    for fn in required:
        assert callable(getattr(ai_router, fn, None)), f"router missing: {fn}"
