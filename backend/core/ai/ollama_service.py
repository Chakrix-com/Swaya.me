"""
Ollama AI service — async client for local LLM text generation.
Models are expected to be running via the ollama daemon at 127.0.0.1:11434.
"""
import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
FALLBACK_MODEL = "llama3.2:1b"

# Generous timeout — CPU inference is slower than GPU
TIMEOUT = httpx.Timeout(120.0, connect=5.0)


class OllamaError(Exception):
    pass


async def _generate(prompt: str, model: str, temperature: float = 0.7, max_tokens: int = 1024, fmt: str = "json") -> str:
    """Raw generate call; returns the response text string."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if fmt:
        payload["format"] = fmt
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError:
            raise OllamaError("Cannot connect to ollama daemon at 127.0.0.1:11434")
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"Ollama returned HTTP {e.response.status_code}")
    return resp.json()["response"]


def _parse_json(raw: str) -> Any:
    """
    Parse JSON from model output.
    Models sometimes wrap JSON in markdown fences — strip those first.
    """
    # Strip markdown code fences if present
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def generate_questions(
    topic: str,
    count: int = 5,
    language: str = "en",
    model: str = DEFAULT_MODEL,
) -> list[dict]:
    """
    Generate MCQ quiz questions for a given topic.

    Returns a list of dicts:
        [{"text": str, "options": [str, str, str, str], "correct_answer_index": int}, ...]
    """
    count = min(max(count, 1), 10)  # clamp 1-10

    prompt = f"""You are a quiz generator. Output ONLY valid JSON, no explanations, no markdown.

Generate exactly {count} multiple-choice quiz questions about the topic: "{topic}".
Write all questions and answers in language: {language}.

JSON schema:
{{"questions": [{{"text": string, "options": [string, string, string, string], "correct_answer_index": integer}}]}}

Requirements:
- Each question must have exactly 4 answer options (real answer text, not letters).
- correct_answer_index is 0-based: 0 means options[0] is correct, 1 means options[1], etc.
- All 4 options must be different from each other.
- Wrong options must be plausible but clearly incorrect.
- Output exactly {count} questions.
"""
    raw = await _generate(prompt, model, max_tokens=2048)
    try:
        data = _parse_json(raw)
        questions = data["questions"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse questions from model output: %s | raw: %s", e, raw[:200])
        raise OllamaError("Model returned malformed JSON — try again")

    # Sanitise and validate each question
    result = []
    for q in questions:
        opts = q.get("options", [])
        idx = q.get("correct_answer_index", 0)
        if not q.get("text") or len(opts) < 2:
            continue
        # Pad to 4 options if model gave fewer
        while len(opts) < 4:
            opts.append("")
        result.append({
            "text": str(q["text"]),
            "options": [str(o) for o in opts[:4]],
            "correct_answer_index": int(idx) if 0 <= int(idx) <= 3 else 0,
        })

    return result


async def generate_distractors(
    question: str,
    correct_answer: str,
    count: int = 3,
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """
    Generate plausible-but-wrong MCQ distractors for a given question + correct answer.

    Returns a list of distractor strings.
    """
    count = min(max(count, 1), 5)

    prompt = f"""For the following quiz question, generate {count} plausible but incorrect answer options (distractors).

Question: {question}
Correct answer: {correct_answer}

Respond ONLY with valid JSON, no extra text:
{{
  "distractors": ["<wrong answer 1>", "<wrong answer 2>", "<wrong answer 3>"]
}}

Rules:
- Distractors must be clearly wrong but believable.
- Do NOT include the correct answer.
- Keep each distractor brief (similar length to the correct answer).
"""
    raw = await _generate(prompt, model)
    try:
        data = _parse_json(raw)
        distractors = [str(d) for d in data["distractors"] if d]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse distractors: %s | raw: %s", e, raw[:200])
        raise OllamaError("Model returned malformed JSON — try again")

    return distractors[:count]


async def generate_poll_prompt(
    topic: str,
    language: str = "en",
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate a short, open-ended word cloud poll question for a given topic.

    Returns a single question string.
    """
    prompt = f"""Generate a single short, open-ended poll question suitable for a live audience word cloud activity.
Topic: "{topic}"
Language: {language}

The question should encourage one or two word answers that work well in a word cloud.

Respond ONLY with valid JSON, no extra text:
{{
  "prompt": "<your poll question here>"
}}
"""
    raw = await _generate(prompt, model)
    try:
        data = _parse_json(raw)
        return str(data["prompt"])
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse poll prompt: %s | raw: %s", e, raw[:200])
        raise OllamaError("Model returned malformed JSON — try again")


async def rewrite_text(
    text: str,
    context: str = "quiz question",
    language: str = "en",
    model: str = FALLBACK_MODEL,
) -> str:
    """
    Rewrite the given text to be clearer and better suited for the quiz context.
    Uses the fast 1B model by default for low latency.
    Returns the rewritten string.
    """
    prompt = (
        f"Fix spelling, grammar, and phrasing of the text below for use as a {context}. "
        f"Write in {language}. Return ONLY the corrected text, nothing else.\n\n"
        f"{text}"
    )
    raw = await _generate(prompt, model, temperature=0.4, max_tokens=256, fmt="")
    return _clean_rewrite(raw)


# Common preamble patterns models add despite being told not to
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


GRADING_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def grade_text_answer(participant_answer: str, expected_answer: str) -> bool:
    """
    Use the LLM to semantically compare a participant's text answer against
    the expected answer. Returns True if the meaning matches, False otherwise.
    Falls back to exact-match comparison if Ollama is unavailable or times out.
    """
    prompt = (
        "You are a quiz answer grader.\n\n"
        f"Expected answer: {expected_answer}\n"
        f"Participant answer: {participant_answer}\n\n"
        "Does the participant's answer convey the same meaning as the expected answer, "
        "allowing for minor spelling mistakes, synonyms, different word order, or "
        "extra/missing articles?\n\n"
        "Reply with exactly one word: YES or NO."
    )
    try:
        raw = await _generate(prompt, FALLBACK_MODEL, temperature=0.0, max_tokens=4, fmt="")
        verdict = raw.strip().split()[0].upper() if raw.strip() else "NO"
        return verdict == "YES"
    except Exception:
        logger.warning(
            "Ollama unavailable for answer grading — falling back to exact match. "
            "expected=%r participant=%r", expected_answer, participant_answer
        )
        return participant_answer.strip().lower() == expected_answer.strip().lower()


def _clean_rewrite(raw: str) -> str:
    """Strip preambles, surrounding quotes, and markdown fences from model rewrite output."""
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r'^```[^\n]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()
    # Strip common preamble lines (e.g. "Here is the corrected text:")
    text = _PREAMBLE_RE.sub('', text).strip()
    # If the model wrapped in quotes, remove them
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    return text



async def list_available_models() -> list[str]:
    """Return names of models currently pulled in ollama."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
