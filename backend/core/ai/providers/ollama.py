"""
Ollama provider — implements BaseAIProvider using a local Ollama daemon.
Optimised for the light tier (distractors, rewrite, grading).
Can also be used as the primary provider for fully local/air-gapped deployments.
"""
import json
import logging
import re

import httpx

from core.ai.base import AIProviderError, BaseAIProvider
from core.ai.prompts import (
    build_distractor_messages,
    build_grade_messages,
    build_poll_prompt_messages,
    build_question_generation_content,
    build_rewrite_messages,
    _parse_json,
    parse_question_response,
)
from core.config.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(300.0, connect=10.0)
_GRADE_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Preamble patterns models add despite being told not to
_PREAMBLE_RE = re.compile(
    r'^('
    r'here(?:\'s| is) the (?:corrected|rewritten|improved|fixed|revised|updated) (?:text|version|sentence|question|answer|title|description)\s*[:\-]?\s*'
    r'|corrected\s*[:\-]\s*'
    r'|rewritten\s*[:\-]\s*'
    r'|improved\s*[:\-]\s*'
    r'|fixed\s*[:\-]\s*'
    r'|output\s*[:\-]\s*'
    r')',
    re.IGNORECASE,
)


def _clean_rewrite(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r'^```[^\n]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()
    text = _PREAMBLE_RE.sub('', text).strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    return text


class OllamaProvider(BaseAIProvider):
    """
    Light-tier provider backed by a local Ollama daemon.
    Set AI_LIGHT_PROVIDER=ollama (default) to use this for distractors/rewrite/grading.
    Set AI_PRIMARY_PROVIDER=ollama for a fully local deployment (basic MCQ only).
    """

    def __init__(self, model: str | None = None, fallback_model: str | None = None):
        cfg = settings.ollama
        self._base_url = cfg.base_url.rstrip("/")
        self._model = model or cfg.model
        self._fallback_model = fallback_model or cfg.fallback_model

    async def _generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        fmt: str = "json",
        timeout: httpx.Timeout = _TIMEOUT,
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if fmt:
            payload["format"] = fmt
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
            except httpx.ConnectError:
                raise AIProviderError(f"Cannot connect to Ollama daemon at {self._base_url}")
            except httpx.ReadTimeout:
                raise AIProviderError(f"Ollama request timed out after {timeout.read}s")
            except httpx.HTTPStatusError as e:
                raise AIProviderError(f"Ollama returned HTTP {e.response.status_code}")
        return resp.json()["response"]

    # ── Primary tier (basic, local-only) ──────────────────────────────────────

    async def generate_questions(
        self,
        prompt: str,
        count: int,
        language: str,
        quiz_type: str,
        existing_questions: list[str] | None = None,
    ) -> dict:
        """
        Basic MCQ generation via Ollama. Only supports quiz/exam types reliably.
        poll/offline_poll types are attempted but local models may struggle with the schema.
        """
        count = min(max(count, 1), 10)
        _, user_message = build_question_generation_content(
            prompt, count, language, quiz_type, existing_questions
        )
        raw = await self._generate(user_message, self._model, max_tokens=4096)
        try:
            return parse_question_response(raw, quiz_type)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Ollama question parse failed: %s | raw: %.200s", e, raw)
            raise AIProviderError("Ollama returned malformed JSON — try again or reduce question count")

    # validate_quiz_prompt: inherits no-op default (True, "") — correct for local models

    # generate_participant_summary / analyze_exam_results: inherit NotImplementedError

    # ── Light tier ────────────────────────────────────────────────────────────

    async def generate_distractors(self, question: str, correct_answer: str, count: int = 3) -> list[str]:
        count = min(max(count, 1), 5)
        msgs = build_distractor_messages(question, correct_answer, count)
        prompt = f"{msgs[0]['content']}\n\n{msgs[1]['content']}"
        raw = await self._generate(prompt, self._model, max_tokens=512)
        try:
            data = _parse_json(raw)
            return [str(d) for d in data["distractors"] if d][:count]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Ollama distractor parse failed: %s | raw: %.200s", e, raw)
            raise AIProviderError("Ollama returned malformed JSON — try again")

    async def generate_poll_prompt(self, topic: str, language: str = "en") -> str:
        msgs = build_poll_prompt_messages(topic, language)
        prompt = f"{msgs[0]['content']}\n\n{msgs[1]['content']}"
        raw = await self._generate(prompt, self._model, max_tokens=256)
        try:
            data = _parse_json(raw)
            return str(data["prompt"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Ollama poll-prompt parse failed: %s | raw: %.200s", e, raw)
            raise AIProviderError("Ollama returned malformed JSON — try again")

    async def rewrite_text(self, text: str, context: str, language: str) -> str:
        msgs = build_rewrite_messages(text, context, language)
        raw = await self._generate(
            msgs[0]["content"], self._fallback_model, temperature=0.4, max_tokens=256, fmt=""
        )
        return _clean_rewrite(raw)

    async def grade_text_answer(self, participant_answer: str, expected_answer: str) -> bool:
        msgs = build_grade_messages(participant_answer, expected_answer)
        prompt = f"{msgs[0]['content']}\n\n{msgs[1]['content']}"
        try:
            raw = await self._generate(
                prompt, self._fallback_model, temperature=0.0, max_tokens=4, fmt="", timeout=_GRADE_TIMEOUT
            )
            verdict = raw.strip().split()[0].upper() if raw.strip() else "NO"
            return verdict == "YES"
        except Exception:
            logger.warning(
                "Ollama grading unavailable — falling back to exact match. expected=%r participant=%r",
                expected_answer, participant_answer,
            )
            return participant_answer.strip().lower() == expected_answer.strip().lower()

    async def list_available_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                return [m["name"] for m in resp.json().get("models", [])]
            except Exception:
                return []
