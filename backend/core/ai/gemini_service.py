"""
Gemini AI service — question generation via Google Gemini REST API.
Uses httpx directly to avoid SDK version dependency issues.
"""
import json
import logging
import re
from typing import Any

import httpx

from core.config.settings import settings

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

# Map configured model names to the API-level model IDs that are available.
# The user's .env may have old/preview names; we normalise to known-working IDs.
_MODEL_ALIASES = {
    "gemini-3.1-pro": "gemini-2.5-pro",
    "gemini-3.1-pro-preview": "gemini-2.5-pro",
    "gemini-3.1-flash-lite": "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview": "gemini-2.5-flash",
    "gemini-3-pro": "gemini-2.5-pro",
    "gemini-3-flash": "gemini-2.5-flash",
}
_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiError(Exception):
    pass


def _resolve_model(model: str) -> str:
    """Normalise a configured model name to a known-working Gemini model ID."""
    # Strip 'models/' prefix if present
    m = model.strip().removeprefix("models/")
    return _MODEL_ALIASES.get(m, m) or _DEFAULT_MODEL


def _parse_json(raw: str) -> Any:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def generate_questions(
    prompt: str,
    count: int = 5,
    language: str = "en",
) -> list[dict]:
    """
    Generate MCQ questions from a detailed user prompt via Gemini REST API.

    Returns:
        [{"text": str, "options": [str, str, str, str], "correct_answer_index": int}, ...]
    """
    key = settings.gemini.key
    if not key:
        raise GeminiError("GEMINI_KEY is not set in .env")

    model = _resolve_model(settings.gemini.model or _DEFAULT_MODEL)
    count = max(1, count)

    system_instruction = (
        "You are an expert quiz generator. "
        "Follow the user's instructions exactly when creating questions. "
        "Output ONLY valid JSON — no markdown, no explanations, nothing else."
    )

    user_message = f"""Generate exactly {count} multiple-choice questions based on the instructions below.
Write all questions and answer options in language code: {language}.

Output format (strict JSON, no other text):
{{"questions": [{{"text": "<question>", "options": ["<A>", "<B>", "<C>", "<D>"], "correct_answer_index": <0|1|2|3>}}]}}

Rules:
- Each question must have exactly 4 distinct answer options.
- correct_answer_index is 0-based (0 = first option is correct).
- Wrong options must be plausible but clearly incorrect.
- Output exactly {count} questions, no more, no less.

User instructions:
{prompt}"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": user_message}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 16384,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text[:300]
            raise GeminiError(f"Gemini API returned HTTP {e.response.status_code}: {body}")
        except httpx.ConnectError:
            raise GeminiError("Cannot connect to Gemini API — check network")
        except httpx.ReadTimeout:
            raise GeminiError("Gemini request timed out — try fewer questions")

    data = resp.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Unexpected Gemini response structure: {e} — {str(data)[:200]}")

    try:
        parsed = _parse_json(raw)
        questions_raw = parsed.get("questions")
        if not isinstance(questions_raw, list):
            raise GeminiError("Gemini response missing 'questions' list")
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse Gemini JSON: %s | raw: %.300s", e, raw)
        raise GeminiError("Gemini returned malformed JSON — try again")

    result = []
    for q in questions_raw:
        opts = q.get("options", [])
        idx = q.get("correct_answer_index", 0)
        if not q.get("text") or len(opts) < 2:
            continue
        while len(opts) < 4:
            opts.append("")
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = 0
        result.append({
            "text": str(q["text"]),
            "options": [str(o) for o in opts[:4]],
            "correct_answer_index": idx if 0 <= idx <= 3 else 0,
        })

    return result
