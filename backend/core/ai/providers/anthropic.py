"""
Anthropic Claude provider — implements BaseAIProvider using the Anthropic Messages API.
Uses httpx directly (no SDK dependency). Works with claude-haiku, claude-sonnet, claude-opus.

Configure with:
  ANTHROPIC_API_KEY=sk-ant-...
  ANTHROPIC_MODEL=claude-sonnet-4-6          (primary/complex tasks)
  ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001  (light/fast tasks)
  AI_PRIMARY_PROVIDER=anthropic
  AI_LIGHT_PROVIDER=anthropic
"""
import json
import logging

import httpx

from core.ai.base import AIProviderError, BaseAIProvider
from core.ai.prompts import (
    build_distractor_messages,
    build_exam_analysis_messages,
    build_grade_messages,
    build_participant_summary_messages,
    build_poll_prompt_messages,
    build_question_generation_messages,
    build_rewrite_messages,
    build_validation_messages,
    _parse_json,
    parse_question_response,
)
from core.config.settings import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

_KNOWN_MODELS = [
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-8",
    "claude-fable-5",
]


class AnthropicProvider(BaseAIProvider):
    """
    Implements BaseAIProvider using Anthropic's Messages API (/v1/messages).
    No SDK required — uses httpx directly for minimal dependencies.

    Note: Anthropic has no native json_mode. We instruct via system prompt and
    parse defensively (fence-stripping + json.loads).
    """

    def __init__(self, use_fast_model: bool = False):
        cfg = settings.ai.anthropic
        self._api_key = cfg.api_key
        self._model = cfg.model_fast if use_fast_model else cfg.model
        self._timeout = httpx.Timeout(float(cfg.timeout_seconds or 120), connect=10.0)

    async def _post(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: httpx.Timeout | None = None,
    ) -> str:
        """POST to /v1/messages and return the text content block."""
        if not self._api_key:
            raise AIProviderError("ANTHROPIC_API_KEY is not configured")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "system": system,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
            try:
                resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise AIProviderError(
                    f"Anthropic API error {e.response.status_code}: {e.response.text[:200]}"
                )
            except httpx.ConnectError:
                raise AIProviderError("Cannot connect to Anthropic API")
            except httpx.ReadTimeout:
                raise AIProviderError("Anthropic request timed out")

        try:
            return resp.json()["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Unexpected Anthropic response structure: {e} — {resp.text[:200]}")

    def _to_anthropic_messages(self, openai_msgs: list[dict]) -> tuple[str, list[dict]]:
        """
        Convert OpenAI-format messages to Anthropic format.
        Anthropic separates system from the messages list.
        Returns (system_str, user_messages_list).
        """
        system_parts = []
        user_messages = []
        for m in openai_msgs:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                user_messages.append({"role": m["role"], "content": m["content"]})
        system = "\n\n".join(system_parts) if system_parts else "You are a helpful assistant."
        # Anthropic requires messages to start with role=user
        if not user_messages:
            user_messages = [{"role": "user", "content": "Please proceed."}]
        return system, user_messages

    async def _chat(
        self,
        openai_msgs: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: httpx.Timeout | None = None,
    ) -> str:
        system, messages = self._to_anthropic_messages(openai_msgs)
        return await self._post(system, messages, temperature=temperature,
                                max_tokens=max_tokens, timeout=timeout)

    # ── Primary tier ──────────────────────────────────────────────────────────

    async def generate_questions(
        self,
        prompt: str,
        count: int,
        language: str,
        quiz_type: str,
        existing_questions: list[str] | None = None,
        allowed_question_types: list[str] | None = None,
    ) -> dict:
        msgs = build_question_generation_messages(prompt, count, language, quiz_type, existing_questions, allowed_question_types)
        # Prepend JSON-only instruction to system (Anthropic has no json_mode)
        msgs[0]["content"] = "Output ONLY valid JSON — no markdown, no prose, no fences.\n\n" + msgs[0]["content"]
        raw = await self._chat(msgs, temperature=0.7, max_tokens=16384)
        try:
            return parse_question_response(raw, quiz_type, allowed_question_types)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Anthropic question parse failed: %s | raw: %.300s", e, raw)
            raise AIProviderError(
                "AI response was truncated or malformed. Try fewer questions or a simpler prompt."
            )

    async def validate_quiz_prompt(self, prompt: str, language: str) -> tuple[bool, str]:
        if not self._api_key:
            return True, ""
        msgs = build_validation_messages(prompt, language)
        msgs[0]["content"] = "Output ONLY valid JSON — no prose.\n\n" + msgs[0]["content"]
        try:
            raw = await self._chat(msgs, temperature=0, max_tokens=256,
                                   timeout=httpx.Timeout(15.0, connect=5.0))
            parsed = _parse_json(raw)
            if parsed.get("valid") is False:
                return False, str(parsed.get("reason", ""))
            return True, ""
        except Exception:
            return True, ""

    async def generate_participant_summary(self, **kwargs) -> str:
        msgs = build_participant_summary_messages(**kwargs)
        return await self._chat(msgs, temperature=0.5, max_tokens=2048,
                                timeout=httpx.Timeout(60.0, connect=10.0))

    async def analyze_exam_results(self, results: dict, custom_prompt: str | None = None) -> str:
        msgs = build_exam_analysis_messages(results, custom_prompt)
        return await self._chat(msgs, temperature=0.4, max_tokens=8192)

    # ── Light tier ────────────────────────────────────────────────────────────

    async def generate_distractors(self, question: str, correct_answer: str, count: int = 3) -> list[str]:
        msgs = build_distractor_messages(question, correct_answer, count)
        msgs[0]["content"] = "Output ONLY valid JSON.\n\n" + msgs[0]["content"]
        raw = await self._chat(msgs, temperature=0.6, max_tokens=512,
                               timeout=httpx.Timeout(20.0, connect=5.0))
        try:
            return _parse_json(raw)["distractors"][:count]
        except (json.JSONDecodeError, KeyError) as e:
            raise AIProviderError(f"Failed to parse distractors: {e}")

    async def generate_poll_prompt(self, topic: str, language: str = "en") -> str:
        msgs = build_poll_prompt_messages(topic, language)
        msgs[0]["content"] = "Output ONLY valid JSON.\n\n" + msgs[0]["content"]
        raw = await self._chat(msgs, temperature=0.7, max_tokens=256,
                               timeout=httpx.Timeout(15.0, connect=5.0))
        try:
            return str(_parse_json(raw)["prompt"])
        except (json.JSONDecodeError, KeyError) as e:
            raise AIProviderError(f"Failed to parse poll prompt: {e}")

    async def rewrite_text(self, text: str, context: str, language: str) -> str:
        msgs = build_rewrite_messages(text, context, language)
        return await self._chat(msgs, temperature=0.3, max_tokens=512,
                                timeout=httpx.Timeout(15.0, connect=5.0))

    async def grade_text_answer(self, participant_answer: str, expected_answer: str) -> bool:
        msgs = build_grade_messages(participant_answer, expected_answer)
        try:
            raw = await self._chat(msgs, temperature=0.0, max_tokens=4,
                                   timeout=httpx.Timeout(10.0, connect=5.0))
            return raw.strip().upper().startswith("YES")
        except Exception:
            return participant_answer.strip().lower() == expected_answer.strip().lower()

    async def list_available_models(self) -> list[str]:
        return list(_KNOWN_MODELS)
