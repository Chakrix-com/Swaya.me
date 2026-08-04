"""
Unit tests for assess_coding_challenge: prompt construction (GeminiProvider) and
response parsing, plus router-level delegation. No real HTTP calls — the provider's
_post is mocked throughout.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.ai.base import BaseAIProvider
from core.ai.providers.gemini import GeminiProvider


def _provider_with_key() -> GeminiProvider:
    provider = GeminiProvider()
    provider._key = "fake-key-for-tests"
    return provider


def _gemini_response(json_text: str) -> dict:
    """Shape a fake Gemini REST response whose extracted text is `json_text`."""
    return {"candidates": [{"content": {"parts": [{"text": json_text}]}}]}


# ── BaseAIProvider default fallback ─────────────────────────────────────────

def test_base_provider_default_is_neutral_fallback():
    class MinimalProvider(BaseAIProvider):
        async def generate_questions(self, *a, **kw): return {}
        async def generate_distractors(self, *a, **kw): return []
        async def generate_poll_prompt(self, *a, **kw): return ""
        async def rewrite_text(self, *a, **kw): return ""

    result = asyncio.run(MinimalProvider().assess_coding_challenge("p", "r", "t", "a"))
    assert result["ai_usage_efficiency"] == 50
    assert result["prompt_quality"] == 50
    assert result["validation_discipline"] == 50
    assert result["code_quality"] == 50
    assert result["architecture"] == 50
    assert "rationale" in result


# ── GeminiProvider: prompt construction ─────────────────────────────────────

def test_gemini_prompt_includes_all_four_inputs():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 80, "prompt_quality": 70, '
                                 '"validation_discipline": 60, "code_quality": 90, '
                                 '"architecture": 85, "rationale": "solid work"}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge(
            problem_statement="Implement FizzBuzz",
            grading_rubric="Must handle edge cases",
            code_timeline="commit abc: ai-edit ...",
            ai_transcript='{"role": "user", "content": "help me"}',
        ))

    user_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "Implement FizzBuzz" in user_text
    assert "Must handle edge cases" in user_text
    assert "commit abc: ai-edit" in user_text
    assert "help me" in user_text


def test_gemini_prompt_does_not_ask_for_functional_correctness():
    """Functional correctness must stay a deterministic backend calculation, never
    delegated to the LLM (design's anti-prompt-injection stance)."""
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"validation_discipline": 50, "code_quality": 50, '
                                 '"architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    assert "functional" not in system_text.lower() or "not your concern" in system_text.lower() \
        or "deterministically" in system_text.lower()
    assert "test_output" not in system_text


def test_gemini_prompt_includes_host_weights_when_provided():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"validation_discipline": 50, "code_quality": 50, '
                                 '"architecture": 50, "rationale": ""}')

    weights = {
        "functional_correctness": 25, "ai_usage_efficiency": 20, "prompt_quality": 15,
        "validation_discipline": 15, "code_quality": 10, "architecture": 5,
        "time_taken": 5, "proctoring": 5,
    }
    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a", weights))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    # All 5 AI-judged criteria's weights show up...
    assert "ai_usage_efficiency: 20 points" in system_text
    assert "prompt_quality: 15 points" in system_text
    assert "validation_discipline: 15 points" in system_text
    assert "code_quality: 10 points" in system_text
    assert "architecture: 5 points" in system_text
    # ...but the 3 criteria this call doesn't judge are never shown as if they were its concern
    assert "functional_correctness: 25" not in system_text
    assert "time_taken: 5 points" not in system_text
    assert "proctoring: 5 points" not in system_text
    # anti-anchoring instruction must be present, not just the raw numbers
    assert "do not let" in system_text.lower() or "not let a criterion" in system_text.lower()


def test_gemini_prompt_omits_weights_section_when_none_provided():
    """No weights passed (e.g. an older caller) — prompt must still be valid and
    must not claim to have weight info it doesn't have."""
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"validation_discipline": 50, "code_quality": 50, '
                                 '"architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a", weights=None))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    assert "weighted these 5 criteria" not in system_text
    assert ": 20 points" not in system_text  # no stray weight-line syntax with nothing to fill it


def test_gemini_uses_json_mode_and_zero_temperature():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"validation_discipline": 50, "code_quality": 50, '
                                 '"architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))

    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["payload"]["generationConfig"]["temperature"] == 0.0


# ── GeminiProvider: response parsing ────────────────────────────────────────

def test_gemini_parses_all_five_scores_and_rationale():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"ai_usage_efficiency": 72, "prompt_quality": 88, '
                                 '"validation_discipline": 45, "code_quality": 91, '
                                 '"architecture": 60, "rationale": "Good iteration pattern"}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))

    assert result == {
        "ai_usage_efficiency": 72,
        "prompt_quality": 88,
        "validation_discipline": 45,
        "code_quality": 91,
        "architecture": 60,
        "rationale": "Good iteration pattern",
    }


def test_gemini_clamps_out_of_range_scores():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"ai_usage_efficiency": 150, "prompt_quality": -20, '
                                 '"validation_discipline": 50, "code_quality": 50, '
                                 '"architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))

    assert result["ai_usage_efficiency"] == 100
    assert result["prompt_quality"] == 0


def test_gemini_defaults_missing_score_fields_to_50():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"rationale": "incomplete response"}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))

    assert result["ai_usage_efficiency"] == 50
    assert result["code_quality"] == 50


def test_gemini_no_key_returns_fallback_without_calling_api():
    provider = GeminiProvider()
    provider._key = ""
    with patch.object(provider, "_post", AsyncMock(side_effect=AssertionError("should not be called"))):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))
    assert result["rationale"] == "AI assessment unavailable"


def test_gemini_propagates_exception_on_api_failure():
    """Unlike evaluate_code, this must NOT swallow failures — the grading job's
    retry-then-partial_failed logic depends on catching a real exception."""
    provider = _provider_with_key()

    async def failing_post(payload, model, timeout=None):
        raise RuntimeError("Gemini API unreachable")

    with patch.object(provider, "_post", failing_post):
        with pytest.raises(RuntimeError, match="Gemini API unreachable"):
            asyncio.run(provider.assess_coding_challenge("p", "r", "t", "a"))


# ── Router-level delegation ─────────────────────────────────────────────────

def test_router_assess_coding_challenge_delegates_to_primary_provider():
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(return_value={"rationale": "ok"})
    weights = {"prompt_quality": 15}

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        result = asyncio.run(ai_router.assess_coding_challenge("p", "r", "t", "a", weights))

    mock_provider.assess_coding_challenge.assert_called_once_with("p", "r", "t", "a", weights)
    assert result == {"rationale": "ok"}


def test_router_assess_coding_challenge_weights_default_to_none():
    """Callers that don't pass weights (e.g. existing/older call sites) must not break."""
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(return_value={"rationale": "ok"})

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        asyncio.run(ai_router.assess_coding_challenge("p", "r", "t", "a"))

    mock_provider.assess_coding_challenge.assert_called_once_with("p", "r", "t", "a", None)


def test_router_assess_coding_challenge_propagates_provider_exception():
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(ai_router.assess_coding_challenge("p", "r", "t", "a"))
