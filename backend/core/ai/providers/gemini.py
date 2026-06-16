"""
Google Gemini provider — implements BaseAIProvider using Gemini's REST API.
Uses httpx directly to avoid SDK version dependency issues.
"""
import json
import logging

import httpx

from core.ai.base import AIProviderError, BaseAIProvider
from core.ai.prompts import (
    build_exam_analysis_content,
    build_participant_summary_content,
    build_question_generation_content,
    build_validation_content,
    build_distractor_messages,
    build_poll_prompt_messages,
    build_rewrite_messages,
    build_grade_messages,
    parse_question_response,
    _parse_json,
)
from core.config.settings import settings

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_MODEL_ALIASES = {
    "gemini-3.1-pro": "gemini-2.5-pro",
    "gemini-3.1-pro-preview": "gemini-2.5-pro",
    "gemini-3.1-flash-lite": "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview": "gemini-2.5-flash",
    "gemini-3-pro": "gemini-2.5-pro",
    "gemini-3-flash": "gemini-2.5-flash",
}
_DEFAULT_MODEL = "gemini-2.5-flash"


def _resolve_model(model: str) -> str:
    m = model.strip().removeprefix("models/")
    return _MODEL_ALIASES.get(m, m) or _DEFAULT_MODEL


class GeminiProvider(BaseAIProvider):
    """
    Primary-tier provider backed by Google Gemini REST API.
    Uses the complex model for generation/analysis; fast model for validation.
    """

    def __init__(self, use_fast_model: bool = False):
        cfg = settings.gemini
        self._key = cfg.key
        self._model = _resolve_model(cfg.model_fast if use_fast_model else cfg.model or _DEFAULT_MODEL)
        self._model_fast = _resolve_model(cfg.model_fast or _DEFAULT_MODEL)
        secs = float(cfg.timeout_seconds or 120)
        self._timeout = httpx.Timeout(secs, connect=10.0)

    def _url(self, model: str) -> str:
        return f"{GEMINI_BASE}/{model}:generateContent?key={self._key}"

    async def _post(self, payload: dict, model: str, timeout: httpx.Timeout | None = None) -> dict:
        async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
            try:
                resp = await client.post(self._url(model), json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise AIProviderError(f"Gemini API HTTP {e.response.status_code}: {e.response.text[:200]}")
            except httpx.ConnectError:
                raise AIProviderError("Cannot connect to Gemini API — check network")
            except httpx.ReadTimeout:
                raise AIProviderError("Gemini request timed out")
        return resp.json()

    @staticmethod
    def _extract_text(data: dict) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Unexpected Gemini response structure: {e} — {str(data)[:200]}")

    def _gemini_payload(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 65536,
        json_mode: bool = False,
    ) -> dict:
        payload: dict = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}], "role": "user"}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        return payload

    # ── Primary tier ──────────────────────────────────────────────────────────

    async def generate_questions(
        self,
        prompt: str,
        count: int,
        language: str,
        quiz_type: str,
        existing_questions: list[str] | None = None,
    ) -> dict:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        system, user = build_question_generation_content(
            prompt, count, language, quiz_type, existing_questions
        )
        payload = self._gemini_payload(system, user, temperature=0.7, max_tokens=65536, json_mode=True)
        data = await self._post(payload, self._model)
        raw = self._extract_text(data)
        try:
            return parse_question_response(raw, quiz_type)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Gemini question parse failed: %s | raw: %.300s", e, raw)
            raise AIProviderError(
                "Gemini response was truncated (output too long). "
                "Try reducing the number of questions or simplifying your prompt."
            )

    async def validate_quiz_prompt(self, prompt: str, language: str) -> tuple[bool, str]:
        if not self._key:
            return True, ""
        system, user = build_validation_content(prompt, language)
        payload = self._gemini_payload(system, user, temperature=0, max_tokens=256, json_mode=True)
        try:
            data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(15.0, connect=5.0))
            raw = self._extract_text(data)
            parsed = _parse_json(raw)
            if parsed.get("valid") is False:
                return False, str(parsed.get("reason", ""))
            return True, ""
        except Exception:
            return True, ""

    async def generate_participant_summary(self, **kwargs) -> str:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        system, user = build_participant_summary_content(**kwargs)
        payload = self._gemini_payload(system, user, temperature=0.5, max_tokens=2048)
        data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(60.0, connect=10.0))
        return self._extract_text(data).strip()

    async def analyze_exam_results(self, results: dict, custom_prompt: str | None = None) -> str:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        system, user = build_exam_analysis_content(results, custom_prompt)
        payload = self._gemini_payload(system, user, temperature=0.4, max_tokens=8192)
        data = await self._post(payload, self._model)
        return self._extract_text(data)

    # ── Light tier ────────────────────────────────────────────────────────────

    async def generate_distractors(self, question: str, correct_answer: str, count: int = 3) -> list[str]:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        msgs = build_distractor_messages(question, correct_answer, count)
        system = msgs[0]["content"]
        user = msgs[1]["content"]
        payload = self._gemini_payload(system, user, temperature=0.6, max_tokens=512, json_mode=True)
        data = await self._post(payload, self._model_fast)
        raw = self._extract_text(data)
        try:
            return _parse_json(raw)["distractors"][:count]
        except Exception as e:
            raise AIProviderError(f"Failed to parse distractors: {e}")

    async def generate_poll_prompt(self, topic: str, language: str = "en") -> str:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        msgs = build_poll_prompt_messages(topic, language)
        system = msgs[0]["content"]
        user = msgs[1]["content"]
        payload = self._gemini_payload(system, user, temperature=0.7, max_tokens=256, json_mode=True)
        data = await self._post(payload, self._model_fast)
        raw = self._extract_text(data)
        try:
            return str(_parse_json(raw)["prompt"])
        except Exception as e:
            raise AIProviderError(f"Failed to parse poll prompt: {e}")

    async def rewrite_text(self, text: str, context: str, language: str) -> str:
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")
        msgs = build_rewrite_messages(text, context, language)
        system = "You are a writing assistant. Return ONLY the corrected text, nothing else."
        payload = self._gemini_payload(system, msgs[0]["content"], temperature=0.3, max_tokens=512)
        data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(15.0, connect=5.0))
        return self._extract_text(data).strip()

    async def grade_text_answer(self, participant_answer: str, expected_answer: str) -> bool:
        if not self._key:
            return participant_answer.strip().lower() == expected_answer.strip().lower()
        msgs = build_grade_messages(participant_answer, expected_answer)
        system = msgs[0]["content"]
        user = msgs[1]["content"]
        payload = self._gemini_payload(system, user, temperature=0.0, max_tokens=4)
        try:
            data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(10.0, connect=5.0))
            raw = self._extract_text(data).strip().split()[0].upper()
            return raw == "YES"
        except Exception:
            return participant_answer.strip().lower() == expected_answer.strip().lower()

    async def list_available_models(self) -> list[str]:
        return []
