"""
Unit tests for assess_coding_challenge: prompt construction (GeminiProvider) and
response parsing, plus router-level delegation. No real HTTP calls — the provider's
_post is mocked throughout.

Revised 2026-08-09 (deterministic-first grading redesign): signature changed from
(problem_statement, grading_rubric, code_timeline, ai_transcript, weights) to
(problem_statement, grading_rubric, final_code_snapshot, candidate_prompts,
usage_summary, weights) — validation_discipline moved out entirely (now computed
deterministically in grading_service_async, see test_coding_challenge_grading.py).
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.ai.base import BaseAIProvider
from core.ai.providers.gemini import GeminiProvider

_FAKE_USAGE_SUMMARY = {
    "total_human_prompts": 4,
    "total_ai_driven_commits": 3,
    "total_manual_snapshot_commits": 1,
    "total_test_runs_via_ai_chat": 2,
}


def _provider_with_key() -> GeminiProvider:
    provider = GeminiProvider()
    provider._key = "fake-key-for-tests"
    return provider


def _gemini_response(json_text: str) -> dict:
    """Shape a fake Gemini REST response whose extracted text is `json_text`."""
    return {"candidates": [{"content": {"parts": [{"text": json_text}]}}]}


def _ok_response():
    return _gemini_response('{"ai_usage_efficiency": 80, "prompt_quality": 70, '
                             '"code_quality": 90, "architecture": 85, "rationale": "solid work"}')


# ── BaseAIProvider default fallback ─────────────────────────────────────────

def test_base_provider_default_is_neutral_fallback():
    class MinimalProvider(BaseAIProvider):
        async def generate_questions(self, *a, **kw): return {}
        async def generate_distractors(self, *a, **kw): return []
        async def generate_poll_prompt(self, *a, **kw): return ""
        async def rewrite_text(self, *a, **kw): return ""

    result = asyncio.run(MinimalProvider().assess_coding_challenge("p", "r", "code", "prompts", {}))
    assert result["ai_usage_efficiency"] == 50
    assert result["prompt_quality"] == 50
    assert result["code_quality"] == 50
    assert result["architecture"] == 50
    assert "validation_discipline" not in result  # deterministic now, not this call's concern
    assert "rationale" in result


# ── GeminiProvider: prompt construction ─────────────────────────────────────

def test_gemini_prompt_includes_curated_inputs():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _ok_response()

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge(
            problem_statement="Implement FizzBuzz",
            grading_rubric="Must handle edge cases",
            final_code_snapshot="=== FILE: fizzbuzz.py ===\ndef fizzbuzz(n): ...",
            candidate_prompts="write fizzbuzz with tests",
            usage_summary=_FAKE_USAGE_SUMMARY,
        ))

    user_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "Implement FizzBuzz" in user_text
    assert "Must handle edge cases" in user_text
    assert "fizzbuzz.py" in user_text
    assert "write fizzbuzz with tests" in user_text
    assert "Total prompts the candidate typed: 4" in user_text
    assert "Commits from AI-driven edits: 3" in user_text


def test_gemini_truncates_oversized_final_code_snapshot():
    """Real incident 2026-08-09 that prompted this redesign: the OLD unbounded
    code_timeline input reached 13.6MB. final_code_snapshot is bounded by repo
    size already (harvest-time head -c cap), but this is the provider-side
    safety net on top of that — truncates the tail, keeping whatever was
    listed first."""
    from core.ai.providers.gemini import CODING_CHALLENGE_CODE_SNAPSHOT_MAX_CHARS

    provider = _provider_with_key()
    captured = {}
    huge_snapshot = "=== FILE: first.py ===\n" + ("x" * (CODING_CHALLENGE_CODE_SNAPSHOT_MAX_CHARS + 500_000))

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _ok_response()

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge(
            problem_statement="p", grading_rubric="r",
            final_code_snapshot=huge_snapshot, candidate_prompts="short prompts",
            usage_summary=_FAKE_USAGE_SUMMARY,
        ))

    user_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "first.py" in user_text  # head kept
    assert len(user_text) < len(huge_snapshot)
    assert "truncated" in user_text


def test_gemini_truncates_oversized_candidate_prompts_keeping_most_recent():
    """Prompts are chronological (oldest first) — truncation drops the HEAD
    (earliest prompts) and keeps the TAIL (prompts closest to submission)."""
    from core.ai.providers.gemini import CODING_CHALLENGE_PROMPTS_MAX_CHARS

    provider = _provider_with_key()
    captured = {}
    huge_prompts = ("x" * (CODING_CHALLENGE_PROMPTS_MAX_CHARS + 50_000)) + "\nfinal-prompt-marker"

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _ok_response()

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge(
            problem_statement="p", grading_rubric="r",
            final_code_snapshot="short code", candidate_prompts=huge_prompts,
            usage_summary=_FAKE_USAGE_SUMMARY,
        ))

    user_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "final-prompt-marker" in user_text  # tail kept
    assert len(user_text) < len(huge_prompts)
    assert "truncated" in user_text


def test_gemini_does_not_truncate_normal_sized_inputs():
    """Guards against an overly aggressive cap silently mangling the common case."""
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _ok_response()

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge(
            problem_statement="p", grading_rubric="r",
            final_code_snapshot="=== FILE: a.py ===\nprint('hi')",
            candidate_prompts="a normal prompt",
            usage_summary=_FAKE_USAGE_SUMMARY,
        ))

    user_text = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "a.py" in user_text
    assert "a normal prompt" in user_text
    assert "truncated" not in user_text


def test_gemini_prompt_does_not_ask_for_functional_correctness_or_validation_discipline():
    """Functional correctness and validation_discipline must stay deterministic
    backend calculations, never delegated to the LLM."""
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    assert "not your concern" in system_text.lower() or "deterministically" in system_text.lower()
    assert '"validation_discipline"' not in system_text


def test_gemini_prompt_includes_host_weights_when_provided():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    weights = {
        "functional_correctness": 30, "ai_usage_efficiency": 20, "prompt_quality": 15,
        "validation_discipline": 15, "code_quality": 10, "architecture": 5, "time_taken": 5,
    }
    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}, weights))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    # All 4 AI-judged criteria's weights show up...
    assert "ai_usage_efficiency: 20 points" in system_text
    assert "prompt_quality: 15 points" in system_text
    assert "code_quality: 10 points" in system_text
    assert "architecture: 5 points" in system_text
    # ...but the criteria this call doesn't judge are never shown as if they were its concern
    assert "functional_correctness: 30" not in system_text
    assert "time_taken: 5 points" not in system_text
    assert "validation_discipline: 15 points" not in system_text
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
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}, weights=None))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"]
    assert "weighted these 4 criteria" not in system_text
    assert ": 20 points" not in system_text  # no stray weight-line syntax with nothing to fill it


def test_gemini_prompt_has_calibration_guidance():
    """The whole point of this redesign — prompt must actually instruct the model
    not to inflate scores, not just ask it to score nicely as before."""
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    system_text = captured["payload"]["system_instruction"]["parts"][0]["text"].lower()
    assert "40-75" in system_text or "calibration" in system_text
    assert "85" in system_text  # the "reserve 85+ for exceptional work" anchor


def test_gemini_uses_json_mode_and_zero_temperature():
    provider = _provider_with_key()
    captured = {}

    async def fake_post(payload, model, timeout=None):
        captured["payload"] = payload
        return _gemini_response('{"ai_usage_efficiency": 50, "prompt_quality": 50, '
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["payload"]["generationConfig"]["temperature"] == 0.0


# ── GeminiProvider: response parsing ────────────────────────────────────────

def test_gemini_parses_all_four_scores_and_rationale():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"ai_usage_efficiency": 72, "prompt_quality": 88, '
                                 '"code_quality": 91, "architecture": 60, '
                                 '"rationale": "Good iteration pattern"}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    assert result == {
        "ai_usage_efficiency": 72,
        "prompt_quality": 88,
        "code_quality": 91,
        "architecture": 60,
        "rationale": "Good iteration pattern",
    }


def test_gemini_clamps_out_of_range_scores():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"ai_usage_efficiency": 150, "prompt_quality": -20, '
                                 '"code_quality": 50, "architecture": 50, "rationale": ""}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    assert result["ai_usage_efficiency"] == 100
    assert result["prompt_quality"] == 0


def test_gemini_defaults_missing_score_fields_to_50():
    provider = _provider_with_key()

    async def fake_post(payload, model, timeout=None):
        return _gemini_response('{"rationale": "incomplete response"}')

    with patch.object(provider, "_post", fake_post):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))

    assert result["ai_usage_efficiency"] == 50
    assert result["code_quality"] == 50


def test_gemini_no_key_returns_fallback_without_calling_api():
    provider = GeminiProvider()
    provider._key = ""
    with patch.object(provider, "_post", AsyncMock(side_effect=AssertionError("should not be called"))):
        result = asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))
    assert result["rationale"] == "AI assessment unavailable"


def test_gemini_propagates_exception_on_api_failure():
    """Unlike evaluate_code, this must NOT swallow failures — the grading job's
    retry-then-partial_failed logic depends on catching a real exception."""
    provider = _provider_with_key()

    async def failing_post(payload, model, timeout=None):
        raise RuntimeError("Gemini API unreachable")

    with patch.object(provider, "_post", failing_post):
        with pytest.raises(RuntimeError, match="Gemini API unreachable"):
            asyncio.run(provider.assess_coding_challenge("p", "r", "code", "prompts", {}))


# ── Router-level delegation ─────────────────────────────────────────────────

def test_router_assess_coding_challenge_delegates_to_primary_provider():
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(return_value={"rationale": "ok"})
    weights = {"prompt_quality": 15}

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        result = asyncio.run(
            ai_router.assess_coding_challenge("p", "r", "code", "prompts", {}, weights)
        )

    mock_provider.assess_coding_challenge.assert_called_once_with(
        "p", "r", "code", "prompts", {}, weights
    )
    assert result == {"rationale": "ok"}


def test_router_assess_coding_challenge_weights_default_to_none():
    """Callers that don't pass weights (e.g. existing/older call sites) must not break."""
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(return_value={"rationale": "ok"})

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        asyncio.run(ai_router.assess_coding_challenge("p", "r", "code", "prompts", {}))

    mock_provider.assess_coding_challenge.assert_called_once_with(
        "p", "r", "code", "prompts", {}, None
    )


def test_router_assess_coding_challenge_propagates_provider_exception():
    from core.ai import router as ai_router

    mock_provider = AsyncMock()
    mock_provider.assess_coding_challenge = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("core.ai.router.get_primary_provider", return_value=mock_provider):
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(ai_router.assess_coding_challenge("p", "r", "code", "prompts", {}))
