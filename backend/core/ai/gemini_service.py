"""
Gemini AI service — question generation via Google Gemini REST API.
Uses httpx directly to avoid SDK version dependency issues.
"""
import html
import json
import logging
import re
from typing import Any

import httpx

from core.config.settings import settings

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_timeout() -> httpx.Timeout:
    """Build httpx.Timeout from settings so GEMINI_TIMEOUT_SECONDS in .env is respected."""
    secs = float(settings.gemini.timeout_seconds or 120)
    return httpx.Timeout(secs, connect=10.0)

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


def _md_to_html(text: str) -> str:
    """
    Convert markdown code syntax (as returned by Gemini) to HTML
    for storage and rendering by RichTextRenderer.

    Handles:
      - Fenced code blocks: ```lang\\ncode\\n``` → <pre><code class="language-lang">…</code></pre>
      - Inline code: `expr` → <code>expr</code>
      - Bold: **text** → <strong>text</strong>
      - Paragraph/newline structure when code blocks are present
    """
    if not text:
        return text

    # Check if text has any markdown we care about before doing any work
    has_fence = '```' in text
    has_inline = re.search(r'`[^`\n]+`', text)
    has_bold = '**' in text

    if not has_fence and not has_inline and not has_bold:
        return text  # plain text — leave untouched

    # Split on fenced code blocks, preserving them as alternating non-code / code parts
    fence_re = re.compile(r'```([\w]*)\n([\s\S]*?)```', re.DOTALL)
    parts = fence_re.split(text)
    # split produces: [before, lang, code, between, lang, code, …, after]

    result_parts: list[str] = []
    i = 0
    while i < len(parts):
        if i % 3 == 0:
            # Plain text segment — apply inline transforms
            segment = parts[i]
            # HTML-escape first so Gemini can't inject arbitrary markup
            segment = html.escape(segment)
            # Inline code (content was already escaped above)
            segment = re.sub(r'`([^`\n]+)`', lambda m: f'<code>{m.group(1)}</code>', segment)
            # Bold
            segment = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', segment)
            # Wrap double-newline paragraphs if there's structural content
            if has_fence:
                paras = segment.strip().split('\n\n')
                if len(paras) > 1:
                    segment = ''.join(
                        f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paras if p.strip()
                    )
                else:
                    segment = segment.replace('\n', '<br>') if segment.strip() else segment
            result_parts.append(segment)
        elif i % 3 == 1:
            # Language label from the split group
            lang = parts[i].strip().lower()
        else:
            # Code content
            code = html.escape(parts[i].rstrip('\n'))
            lang_attr = f' class="language-{lang}"' if lang else ''
            result_parts.append(f'<pre><code{lang_attr}>{code}</code></pre>')
        i += 1

    return ''.join(result_parts)


async def validate_quiz_prompt(prompt: str, language: str = "en") -> tuple[bool, str]:
    """
    Fast guard using the cheap model: returns (True, "") if the prompt is suitable
    for quiz generation, or (False, reason) if it is off-topic or inappropriate.
    Fails open on any error so legitimate users are never blocked.
    """
    key = settings.gemini.key
    if not key:
        return True, ""

    model = _resolve_model(settings.gemini.model_fast or _DEFAULT_MODEL)

    system_instruction = (
        "You are a content validator for an online quiz platform. "
        "Decide whether a user's request is suitable for generating quiz or test questions. "
        "Output ONLY valid JSON — nothing else."
    )

    user_message = f"""Determine whether the following prompt is appropriate for generating educational quiz or test questions.

A VALID prompt:
- Describes a topic, subject, concept, or skill (e.g. "Python decorators", "World War II causes", "HR interview questions")
- Could reasonably produce factual, conceptual, or applied questions

An INVALID prompt:
- Asks for something unrelated to quizzes (recipes, creative writing, code programs, personal advice, jokes, etc.)
- Is offensive, harmful, or inappropriate
- Is pure gibberish or not a recognisable human language

Output format (strict JSON):
{{"valid": true}} if valid
{{"valid": false, "reason": "<one concise sentence explaining why, written in language code: {language}>"}} if invalid

User's prompt:
{prompt}"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": user_message}], "role": "user"}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 256,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _parse_json(raw)
        if parsed.get("valid") is False:
            return False, str(parsed.get("reason", ""))
        return True, ""
    except Exception:
        return True, ""


async def analyze_exam_results(results: dict) -> str:
    """
    Analyse exam results quantitatively and qualitatively via Gemini.
    Returns a markdown string.
    """
    key = settings.gemini.key
    if not key:
        raise GeminiError("GEMINI_KEY is not set in .env")

    model = _resolve_model(settings.gemini.model or _DEFAULT_MODEL)

    # Build compact stats block
    total_started = results.get("total_started", 0)
    total_completed = results.get("total_completed", 0)
    total_abandoned = results.get("total_abandoned", 0)
    avg_score = results.get("average_score", 0)
    max_score = results.get("max_score", 0)

    leaderboard = results.get("leaderboard", [])
    scores = [e["score"] for e in leaderboard if e.get("is_completed")]
    times = [e["time_taken_seconds"] for e in leaderboard if e.get("is_completed") and e.get("time_taken_seconds")]

    score_min = min(scores) if scores else 0
    score_max = max(scores) if scores else 0
    avg_time_min = round(sum(times) / len(times) / 60, 1) if times else None
    pass_threshold = max_score * 0.6

    q_analytics = results.get("question_analytics", [])
    q_lines = []
    for i, q in enumerate(q_analytics):
        import re as _re
        plain_text = _re.sub(r'<[^>]+>', '', q.get("question_text", ""))[:120]
        dist = q.get("answer_distribution", [])
        opts = q.get("options", [])
        opt_dist = ""
        for j, (o, c) in enumerate(zip(opts, dist)):
            plain_opt = _re.sub(r'<[^>]+>', '', o)[:40]
            marker = " ✓" if j == q.get("correct_answer_index") else ""
            opt_dist += f"    {chr(65+j)}: {plain_opt}{marker} ({c} responses)\n"
        q_lines.append(
            f"Q{i+1} [{q.get('percent_correct', 0):.0f}% correct, {q.get('total_answers',0)} responses]: {plain_text}\n{opt_dist}"
        )

    stats_block = f"""Quiz: "{results.get('quiz_title', 'Exam')}"
Participants: {total_started} started | {total_completed} completed | {total_abandoned} abandoned
Scores: avg {avg_score}/{max_score} ({round(avg_score/max_score*100) if max_score else 0}%) | min {score_min} | max {score_max}
Pass threshold (60%): {pass_threshold:.0f} pts | Passed: {sum(1 for s in scores if s >= pass_threshold)}/{len(scores)}
{"Avg time: " + str(avg_time_min) + " min" if avg_time_min else ""}

Per-question breakdown:
{chr(10).join(q_lines)}"""

    prompt = f"""You are an expert educational analyst. Analyse the following exam results and produce a clear, structured report in markdown.

{stats_block}

Your report MUST contain exactly these sections:
## 1. Score Summary
Quantitative overview: average, median (estimate from distribution), pass rate, score spread.

## 2. Question Difficulty Ranking
List questions from hardest to easiest with % correct. Highlight any question where < 40% got it right (needs review) or > 90% got it right (possibly too easy).

## 3. Common Mistake Patterns
For the hardest questions, which wrong answer was most chosen and what misconception does that suggest?

## 4. Qualitative Insights
What topics or skills are participants weakest/strongest in, based on the question content and results?

## 5. Recommendations
Concrete actionable suggestions: which topics need more training, which questions should be revised, any anomalies to investigate.

Be concise. Use bullet points. Do not repeat raw numbers already obvious from the dashboard."""

    payload = {
        "system_instruction": {"parts": [{"text": "You are an expert educational analyst. Output clean markdown only — no preamble, no trailing commentary."}]},
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 8192,
        },
    }

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    async with httpx.AsyncClient(timeout=_get_timeout()) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GeminiError(f"Gemini API returned HTTP {e.response.status_code}: {e.response.text[:200]}")
        except httpx.ConnectError:
            raise GeminiError("Cannot connect to Gemini API — check network")
        except httpx.ReadTimeout:
            raise GeminiError("Gemini request timed out")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Unexpected Gemini response structure: {e}")


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
        "You are an expert quiz generator for an online quiz platform. "
        "Follow the user's instructions exactly when creating questions. "
        "Output ONLY valid JSON — no markdown fences, no prose, nothing else.\n\n"
        "Field requirements for every question:\n"
        "- text: the question text. Use HTML for formatting where helpful: "
        "<strong>, <em>, <code>, <pre><code class=\"language-X\">...</code></pre>.\n"
        "- options: an array of 2 to 10 distinct answer choices. "
        "Each option may also use HTML formatting.\n"
        "- correct_answer_index: 0-based index of the single correct option.\n"
        "- explanation: 2-3 plain-text sentences explaining why the correct answer is right "
        "and why the main wrong answers are incorrect. No HTML in explanation."
    )

    user_message = f"""Generate exactly {count} multiple-choice questions based on the instructions below.
Write all questions, options, and explanations in language code: {language}.

Output format (strict JSON, no other text):
{{"questions": [{{"text": "<question>", "options": ["<A>", "<B>", "..."], "correct_answer_index": 0, "explanation": "<why correct is right and why wrong answers are wrong>"}}]}}

Rules:
- Each question must have between 2 and 10 distinct answer options.
- correct_answer_index is 0-based.
- Wrong options must be plausible but clearly incorrect.
- Output exactly {count} questions, no more, no less.

User instructions:
{prompt}"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": user_message}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 65536,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    async with httpx.AsyncClient(timeout=_get_timeout()) as client:
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
        raise GeminiError(
            "Gemini response was truncated (output too long). "
            "Try reducing the number of questions or simplifying your prompt."
        )

    result = []
    for q in questions_raw:
        opts = q.get("options", [])
        idx = q.get("correct_answer_index", 0)
        if not q.get("text") or len(opts) < 2:
            continue
        opts = opts[:10]  # cap at platform maximum
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = 0
        if not (0 <= idx < len(opts)):
            idx = 0
        explanation = q.get("explanation") or ""
        result.append({
            "text": _md_to_html(str(q["text"])),
            "options": [_md_to_html(str(o)) for o in opts],
            "correct_answer_index": idx,
            "explanation": _md_to_html(explanation) if explanation else None,
        })

    return result
