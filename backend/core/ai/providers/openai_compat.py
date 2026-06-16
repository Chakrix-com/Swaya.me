"""
OpenAI-compatible provider — works with any service that speaks /v1/chat/completions:

  - OpenAI           OPENAI_BASE_URL=https://api.openai.com/v1
  - Groq             OPENAI_BASE_URL=https://api.groq.com/openai/v1
  - Azure OpenAI     OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/deployments/<deployment>
  - Together.ai      OPENAI_BASE_URL=https://api.together.xyz/v1
  - LM Studio        OPENAI_BASE_URL=http://localhost:1234/v1
  - vLLM             OPENAI_BASE_URL=http://localhost:8080/v1
  - Mistral          OPENAI_BASE_URL=https://api.mistral.ai/v1

Set AI_PRIMARY_PROVIDER=openai_compat and AI_LIGHT_PROVIDER=openai_compat to use
this for all AI features. Configure with OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
OPENAI_MODEL_FAST.
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


class OpenAICompatProvider(BaseAIProvider):
    """
    Implements BaseAIProvider using the OpenAI Chat Completions API spec.
    The same class handles OpenAI, Groq, Azure, Together, LM Studio, vLLM, and Mistral
    by changing OPENAI_BASE_URL.
    """

    def __init__(self, use_fast_model: bool = False):
        cfg = settings.ai.openai
        self._api_key = cfg.api_key
        self._base_url = cfg.base_url.rstrip("/")
        self._model = cfg.model_fast if use_fast_model else cfg.model
        self._timeout = httpx.Timeout(float(cfg.timeout_seconds or 120), connect=10.0)

    async def _chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        timeout: httpx.Timeout | None = None,
    ) -> str:
        """POST to /v1/chat/completions and return the assistant message content."""
        if not self._api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            # Not all compat servers support this; they'll still return JSON if the prompt
            # says so — we parse defensively either way
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise AIProviderError(
                    f"OpenAI-compat API error {e.response.status_code}: {e.response.text[:200]}"
                )
            except httpx.ConnectError:
                raise AIProviderError(f"Cannot connect to {self._base_url}")
            except httpx.ReadTimeout:
                raise AIProviderError("OpenAI-compat request timed out")

        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Unexpected response structure: {e} — {resp.text[:200]}")

    # ── Primary tier ──────────────────────────────────────────────────────────

    async def generate_questions(
        self,
        prompt: str,
        count: int,
        language: str,
        quiz_type: str,
        existing_questions: list[str] | None = None,
    ) -> dict:
        msgs = build_question_generation_messages(prompt, count, language, quiz_type, existing_questions)
        raw = await self._chat(msgs, temperature=0.7, max_tokens=16384, json_mode=True)
        try:
            return parse_question_response(raw, quiz_type)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("OpenAI-compat question parse failed: %s | raw: %.300s", e, raw)
            raise AIProviderError(
                "AI response was truncated or malformed. Try fewer questions or a simpler prompt."
            )

    async def validate_quiz_prompt(self, prompt: str, language: str) -> tuple[bool, str]:
        if not self._api_key:
            return True, ""
        msgs = build_validation_messages(prompt, language)
        try:
            raw = await self._chat(
                msgs, temperature=0, max_tokens=256, json_mode=True,
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
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
        raw = await self._chat(msgs, temperature=0.6, max_tokens=512, json_mode=True,
                               timeout=httpx.Timeout(20.0, connect=5.0))
        try:
            return _parse_json(raw)["distractors"][:count]
        except (json.JSONDecodeError, KeyError) as e:
            raise AIProviderError(f"Failed to parse distractors: {e}")

    async def generate_poll_prompt(self, topic: str, language: str = "en") -> str:
        msgs = build_poll_prompt_messages(topic, language)
        raw = await self._chat(msgs, temperature=0.7, max_tokens=256, json_mode=True,
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
        """GET /v1/models — not all compat servers support it; returns [] on failure."""
        if not self._api_key:
            return []
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                resp = await client.get(f"{self._base_url}/models", headers=headers)
                resp.raise_for_status()
                return [m["id"] for m in resp.json().get("data", [])]
            except Exception:
                return []
