"""
Unit tests for AnthropicProvider.
All httpx calls are mocked.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.ai.providers.anthropic import ANTHROPIC_API_URL, ANTHROPIC_VERSION


def _make_provider(api_key="sk-ant-test", model="claude-haiku-4-5-20251001"):
    with patch("core.ai.providers.anthropic.settings") as mock_s:
        mock_s.ai.anthropic.api_key = api_key
        mock_s.ai.anthropic.model = model
        mock_s.ai.anthropic.model_fast = model
        mock_s.ai.anthropic.timeout_seconds = 30
        from core.ai.providers.anthropic import AnthropicProvider
        return AnthropicProvider()


def _anthropic_response(text: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"content": [{"text": text}]}
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = json.dumps({"content": [{"text": text}]})
    return mock_resp


# ── Request shape ─────────────────────────────────────────────────────────────

def test_post_sends_anthropic_headers():
    provider = _make_provider()
    resp = _anthropic_response("hello")

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=resp)
            MockClient.return_value = mock_ctx

            result = await provider._post(
                system="you are helpful",
                messages=[{"role": "user", "content": "hi"}],
            )
            assert result == "hello"

            call_kwargs = mock_ctx.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs.args[1]
            assert headers["x-api-key"] == "sk-ant-test"
            assert headers["anthropic-version"] == ANTHROPIC_VERSION
            assert call_kwargs.args[0] == ANTHROPIC_API_URL

    asyncio.run(run())


def test_post_raises_when_no_api_key():
    from core.ai.base import AIProviderError
    provider = _make_provider(api_key="")

    async def run():
        with pytest.raises(AIProviderError, match="ANTHROPIC_API_KEY"):
            await provider._post("system", [{"role": "user", "content": "x"}])

    asyncio.run(run())


def test_post_raises_on_http_error():
    import httpx
    from core.ai.base import AIProviderError
    provider = _make_provider()

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_raw = MagicMock()
            mock_raw.status_code = 401
            mock_raw.text = "unauthorized"
            mock_ctx.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_raw)
            )
            MockClient.return_value = mock_ctx

            with pytest.raises(AIProviderError, match="401"):
                await provider._post("sys", [{"role": "user", "content": "x"}])

    asyncio.run(run())


# ── Message format conversion ─────────────────────────────────────────────────

def test_to_anthropic_messages_separates_system():
    provider = _make_provider()
    openai_msgs = [
        {"role": "system", "content": "be helpful"},
        {"role": "user", "content": "hello"},
    ]
    system, msgs = provider._to_anthropic_messages(openai_msgs)
    assert system == "be helpful"
    assert msgs == [{"role": "user", "content": "hello"}]


def test_to_anthropic_messages_combines_multiple_system_parts():
    provider = _make_provider()
    openai_msgs = [
        {"role": "system", "content": "part one"},
        {"role": "system", "content": "part two"},
        {"role": "user", "content": "go"},
    ]
    system, msgs = provider._to_anthropic_messages(openai_msgs)
    assert "part one" in system
    assert "part two" in system
    assert len(msgs) == 1


def test_to_anthropic_messages_adds_default_user_when_missing():
    provider = _make_provider()
    openai_msgs = [{"role": "system", "content": "sys"}]
    _, msgs = provider._to_anthropic_messages(openai_msgs)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


# ── JSON parsing without json_mode ────────────────────────────────────────────

def test_generate_distractors_strips_fences_and_parses():
    provider = _make_provider()
    raw = '```json\n{"distractors": ["A", "B", "C"]}\n```'

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value=raw)):
            result = await provider.generate_distractors("Q?", "correct", 3)
            assert result == ["A", "B", "C"]

    asyncio.run(run())


def test_grade_text_answer_returns_false_on_no():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(return_value="NO")):
            assert await provider.grade_text_answer("wrong", "right") is False

    asyncio.run(run())


def test_grade_text_answer_falls_back_on_exception():
    provider = _make_provider()

    async def run():
        with patch.object(provider, "_chat", AsyncMock(side_effect=Exception("timeout"))):
            assert await provider.grade_text_answer("Paris", "Paris") is True
            assert await provider.grade_text_answer("London", "Paris") is False

    asyncio.run(run())


# ── list_available_models ─────────────────────────────────────────────────────

def test_list_available_models_returns_known_list():
    from core.ai.providers.anthropic import _KNOWN_MODELS
    provider = _make_provider()

    async def run():
        models = await provider.list_available_models()
        assert set(models) == set(_KNOWN_MODELS)
        assert "claude-haiku-4-5-20251001" in models

    asyncio.run(run())
