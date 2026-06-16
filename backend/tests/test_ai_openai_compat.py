"""
Unit tests for OpenAICompatProvider.
All httpx calls are mocked — no real network requests.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_provider(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini"):
    """Return a provider with mocked settings."""
    with patch("core.ai.providers.openai_compat.settings") as mock_s:
        mock_s.ai.openai.api_key = api_key
        mock_s.ai.openai.base_url = base_url
        mock_s.ai.openai.model = model
        mock_s.ai.openai.model_fast = model
        mock_s.ai.openai.timeout_seconds = 30
        from core.ai.providers.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider()


def _chat_response(content: str) -> MagicMock:
    """Build a fake httpx response that looks like an OpenAI chat completion."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ── _chat ─────────────────────────────────────────────────────────────────────

def test_chat_sends_correct_payload():
    from core.ai.providers.openai_compat import OpenAICompatProvider
    from core.ai.base import AIProviderError

    provider = _make_provider()
    messages = [{"role": "user", "content": "hello"}]
    expected_response = _chat_response("world")

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=expected_response)
            MockClient.return_value = mock_ctx

            result = await provider._chat(messages, temperature=0.5, max_tokens=100)
            assert result == "world"

            call_kwargs = mock_ctx.post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
            assert payload["model"] == "gpt-4o-mini"
            assert payload["messages"] == messages
            assert payload["temperature"] == 0.5
            assert payload["max_tokens"] == 100
            assert "response_format" not in payload  # json_mode=False

    asyncio.run(run())


def test_chat_sets_json_mode_when_requested():
    provider = _make_provider()
    resp = _chat_response('{"key": "val"}')

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=resp)
            MockClient.return_value = mock_ctx

            await provider._chat([{"role": "user", "content": "x"}], json_mode=True)

            payload = mock_ctx.post.call_args.kwargs.get("json") or mock_ctx.post.call_args.args[1]
            assert payload.get("response_format") == {"type": "json_object"}

    asyncio.run(run())


def test_chat_raises_ai_provider_error_on_http_error():
    import httpx
    from core.ai.base import AIProviderError
    provider = _make_provider()

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)

            mock_raw_resp = MagicMock()
            mock_raw_resp.status_code = 429
            mock_raw_resp.text = "rate limited"
            mock_ctx.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_raw_resp)
            )
            MockClient.return_value = mock_ctx

            with pytest.raises(AIProviderError, match="429"):
                await provider._chat([{"role": "user", "content": "x"}])

    asyncio.run(run())


def test_chat_raises_ai_provider_error_on_connect_error():
    import httpx
    from core.ai.base import AIProviderError
    provider = _make_provider()

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            MockClient.return_value = mock_ctx

            with pytest.raises(AIProviderError, match="Cannot connect"):
                await provider._chat([{"role": "user", "content": "x"}])

    asyncio.run(run())


def test_chat_raises_when_no_api_key():
    from core.ai.base import AIProviderError
    provider = _make_provider(api_key="")

    async def run():
        with pytest.raises(AIProviderError, match="OPENAI_API_KEY"):
            await provider._chat([{"role": "user", "content": "x"}])

    asyncio.run(run())


# ── generate_distractors ───────────────────────────────────────────────────────

def test_generate_distractors_parses_response():
    provider = _make_provider()
    resp_content = json.dumps({"distractors": ["wrong A", "wrong B", "wrong C"]})

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value=resp_content)):
            result = await provider.generate_distractors("What is 2+2?", "4", count=3)
            assert result == ["wrong A", "wrong B", "wrong C"]

    asyncio.run(run())


def test_generate_distractors_raises_on_bad_json():
    from core.ai.base import AIProviderError
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value="not json at all")):
            with pytest.raises(AIProviderError):
                await provider.generate_distractors("Q?", "A", 3)

    asyncio.run(run())


# ── grade_text_answer ──────────────────────────────────────────────────────────

def test_grade_text_answer_returns_true_on_yes():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value="YES")):
            assert await provider.grade_text_answer("Paris", "Paris") is True

    asyncio.run(run())


def test_grade_text_answer_returns_false_on_no():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value="NO")):
            assert await provider.grade_text_answer("London", "Paris") is False

    asyncio.run(run())


def test_grade_text_answer_falls_back_to_exact_match_on_exception():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(side_effect=Exception("timeout"))):
            assert await provider.grade_text_answer("Paris", "Paris") is True
            assert await provider.grade_text_answer("London", "paris") is False

    asyncio.run(run())


# ── validate_quiz_prompt ───────────────────────────────────────────────────────

def test_validate_quiz_prompt_passes_valid():
    provider = _make_provider()
    resp = json.dumps({"valid": True})

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value=resp)):
            ok, reason = await provider.validate_quiz_prompt("Python decorators", "en")
            assert ok is True
            assert reason == ""

    asyncio.run(run())


def test_validate_quiz_prompt_rejects_invalid():
    provider = _make_provider()
    resp = json.dumps({"valid": False, "reason": "Not a quiz topic"})

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value=resp)):
            ok, reason = await provider.validate_quiz_prompt("make me a pizza", "en")
            assert ok is False
            assert "Not a quiz topic" in reason

    asyncio.run(run())


def test_validate_quiz_prompt_fails_open_on_exception():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(side_effect=Exception("network error"))):
            ok, reason = await provider.validate_quiz_prompt("anything", "en")
            assert ok is True  # fail open

    asyncio.run(run())


def test_validate_quiz_prompt_returns_true_when_no_key():
    provider = _make_provider(api_key="")

    async def run():
        ok, reason = await provider.validate_quiz_prompt("anything", "en")
        assert ok is True

    asyncio.run(run())


# ── list_available_models ─────────────────────────────────────────────────────

def test_list_available_models_returns_ids():
    provider = _make_provider()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
    mock_resp.raise_for_status = MagicMock()

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_ctx

            result = await provider.list_available_models()
            assert result == ["gpt-4o", "gpt-4o-mini"]

    asyncio.run(run())


def test_list_available_models_returns_empty_on_failure():
    provider = _make_provider()

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=Exception("network error"))
            MockClient.return_value = mock_ctx

            result = await provider.list_available_models()
            assert result == []

    asyncio.run(run())
