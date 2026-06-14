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


async def generate_participant_summary(
    name: str,
    quiz_title: str,
    total_score: int,
    max_score: int,
    percentage: float,
    correct_count: int,
    wrong_count: int,
    unanswered_count: int,
    time_taken_seconds: float | None,
    started_at: str | None,
    completed_at: str | None,
    question_results: list,
) -> str:
    """
    Generate a personalised AI summary for a participant's exam result.
    Returns an HTML string (safe for email insertion).
    Fails silently — caller should catch GeminiError and skip the section.
    """
    key = settings.gemini.key
    if not key:
        raise GeminiError("GEMINI_KEY is not set in .env")

    model = _resolve_model(settings.gemini.model_fast or _DEFAULT_MODEL)

    import re as _re

    def _plain(t: str) -> str:
        return _re.sub(r'<[^>]+>', '', t or '').strip()

    pct_int = int(round(percentage))
    time_str = ""
    if time_taken_seconds is not None:
        m, s = divmod(int(time_taken_seconds), 60)
        time_str = f"{m}m {s}s"

    q_lines = []
    for i, qr in enumerate(question_results, 1):
        status = "correct" if qr.is_correct else ("skipped" if qr.participant_answer is None else "wrong")
        opts = qr.options or []
        your_ans = _plain(opts[qr.participant_answer]) if qr.participant_answer is not None and qr.participant_answer < len(opts) else "—"
        correct_ans = _plain(opts[qr.correct_answer_index]) if qr.correct_answer_index is not None and qr.correct_answer_index < len(opts) else "—"
        q_lines.append(
            f"Q{i} [{status}]: {_plain(qr.question_text)[:120]} | Your answer: {your_ans} | Correct: {correct_ans}"
        )

    stats = f"""Participant: {name or 'Candidate'}
Exam: {quiz_title}
Score: {total_score}/{max_score} ({pct_int}%)
Correct: {correct_count} | Wrong: {wrong_count} | Skipped: {unanswered_count}
Time taken: {time_str or 'unknown'}
Started: {started_at or 'unknown'} | Completed: {completed_at or 'unknown'}

Per-question detail:
{chr(10).join(q_lines)}"""

    prompt = f"""You are an expert coach writing a personalised performance report for a candidate who just completed an online screening exam.

{stats}

Write a warm, encouraging yet honest personal summary in HTML (no <html>/<body> wrapper, just inner content). Use this structure exactly:

<h3 style="color:#1677ff;margin:0 0 12px;">Your Performance Summary</h3>
<p>One opening sentence addressing the candidate by first name, acknowledging their score warmly.</p>

<h4 style="margin:16px 0 6px;color:#1a1a1a;">Strengths</h4>
<ul>2-3 bullet points about what they did well, based on which questions they got right</ul>

<h4 style="margin:16px 0 6px;color:#1a1a1a;">Areas to Improve</h4>
<ul>2-3 bullet points about topics or question types where they struggled, specific to wrong/skipped answers</ul>

<h4 style="margin:16px 0 6px;color:#1a1a1a;">How to Improve</h4>
<ul>2-3 concrete, actionable study suggestions based on the specific weak areas identified</ul>

<h4 style="margin:16px 0 6px;color:#1a1a1a;">Time & Pacing</h4>
<p>One sentence on their time management. Was it fast, slow, or well-paced for the number of questions?</p>

<p style="margin-top:16px;color:#595959;font-size:13px;">One closing sentence of encouragement.</p>

Rules:
- Address the candidate by first name throughout
- Be specific to their actual answers — don't be generic
- Keep it concise and easy to read
- Output ONLY the HTML fragment above, nothing else"""

    payload = {
        "system_instruction": {"parts": [{"text": "You are an expert coach. Output only the HTML fragment requested — no markdown, no prose outside the HTML."}]},
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 2048,
        },
    }

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GeminiError(f"Gemini API returned HTTP {e.response.status_code}: {e.response.text[:200]}")
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            raise GeminiError(f"Gemini request failed: {e}")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Unexpected Gemini response structure: {e}")


async def analyze_exam_results(results: dict, custom_prompt: str | None = None) -> str:
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

    default_instructions = """Your report MUST contain exactly these sections:
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

    instructions = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else default_instructions

    prompt = f"""You are an expert educational analyst. Analyse the following exam results and produce a clear, structured report in markdown.

{stats_block}

{instructions}"""

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
    quiz_type: str = "quiz",
    existing_questions: list[str] | None = None,
) -> dict:
    """
    Generate questions from a detailed user prompt via Gemini REST API.

    Returns:
        {
            "title": str,
            "description": str,
            "suggested_exam_duration_minutes": int | None,
            "suggested_proctoring": bool | None,
            "questions": [{"text", "options", "correct_answer_index", "explanation", "question_type", "image_suggestion"}, ...]
        }
    """
    key = settings.gemini.key
    if not key:
        raise GeminiError("GEMINI_KEY is not set in .env")

    model = _resolve_model(settings.gemini.model or _DEFAULT_MODEL)
    count = max(1, count)

    is_poll = quiz_type == "poll"
    is_offline_poll = quiz_type == "offline_poll"

    if is_poll:
        question_fields = (
            "Field requirements for every question:\n"
            "- question_type: must be either \"word_cloud\" or \"mcq\".\n"
            "  * word_cloud: open-ended, short-answer prompts (e.g. 'What one word describes your leadership style?'). "
            "No options or correct_answer_index needed — set both to null.\n"
            "  * mcq: standard multiple-choice opinion poll question.\n"
            "- text: the question text.\n"
            "- options: array of 2-6 choices for mcq; null for word_cloud.\n"
            "- correct_answer_index: null (polls have no single correct answer).\n"
            "- explanation: null.\n"
            "Generate a mix: approximately 40% word_cloud and 60% mcq."
        )
        output_schema = (
            '{"title": "<poll title>", "description": "<brief description>", '
            '"questions": [{"question_type": "word_cloud"|"mcq", "text": "<question>", '
            '"options": ["<A>", "<B>", "..."] | null, "correct_answer_index": null, "explanation": null}]}'
        )
    elif is_offline_poll:
        question_fields = (
            "Field requirements for every question:\n"
            "- question_type: must be \"scale\", \"paragraph\", or \"mcq\".\n"
            "  * scale: Likert-style rating (e.g. 'Rate your satisfaction 1-5'). "
            "No options or correct_answer_index needed — set both to null.\n"
            "  * paragraph: open-ended text response (e.g. 'What could we improve?'). "
            "No options or correct_answer_index needed — set both to null.\n"
            "  * mcq: standard multiple-choice question.\n"
            "- text: the question text.\n"
            "- options: array of 2-6 choices for mcq; null for scale and paragraph.\n"
            "- correct_answer_index: null (surveys have no single correct answer).\n"
            "- explanation: null.\n"
            "Generate a mix: approximately 30% scale, 30% paragraph, 40% mcq."
        )
        output_schema = (
            '{"title": "<survey title>", "description": "<brief description>", '
            '"questions": [{"question_type": "scale"|"paragraph"|"mcq", "text": "<question>", '
            '"options": ["<A>", "<B>", "..."] | null, "correct_answer_index": null, "explanation": null}]}'
        )
    else:
        is_exam = quiz_type == "exam"
        question_fields = (
            "Field requirements for every question:\n"
            "- question_type: \"mcq\".\n"
            "- text: the question text. Use HTML for formatting: <strong>, <em>. "
            "IMPORTANT: any code snippet — even a single line or expression — MUST be wrapped in "
            "<pre><code class=\"language-X\">…</code></pre> where X is the detected language "
            "(e.g. language-python, language-sql, language-javascript, language-java, language-bash). "
            "Short inline references to variable names, functions, or keywords use <code>name</code>.\n"
            "- options: an array of exactly 4 distinct answer choices. "
            "Apply the same code formatting rules to any option that contains code.\n"
            "- correct_answer_index: 0-based index of the single correct option. "
            "CRITICAL: distribute correct answers across ALL positions (0, 1, 2, 3) — "
            "do NOT place the correct answer at index 0 for every question. "
            "Across the full question set each position should appear roughly equally.\n"
            "- explanation: 2-3 plain-text sentences explaining why the correct answer is right "
            "and why the main wrong answers are incorrect. No HTML in explanation.\n"
            "- image_suggestion: if a diagram, chart, map, or graph would genuinely help students "
            "understand or answer this question, provide a short image search query (e.g. "
            "'mitosis cell division stages diagram'). Otherwise set to null.\n"
            "- option_image_suggestions: if the visual identity of an option IS the answer "
            "(person, place, logo, product), set this to an array of short Google Image Search "
            "queries, one per option (same length as the options array). "
            "For all other questions, set it to null."
        )
        if is_exam:
            exam_fields = (
                "\n\nFor the top-level object, also include:\n"
                "- suggested_exam_duration_minutes: integer estimate of total exam duration in minutes "
                "based on the number and difficulty of questions. null if not determinable.\n"
                "- suggested_proctoring: boolean — true if this exam topic/context typically requires "
                "anti-cheating measures (e.g. hiring tests, certification exams), false for casual use."
            )
            exam_schema_fields = (
                '"suggested_exam_duration_minutes": <int | null>, '
                '"suggested_proctoring": <true | false>, '
            )
        else:
            exam_fields = ""
            exam_schema_fields = ""
        output_schema = (
            f'{{"title": "<quiz title>", "description": "<brief description of what this quiz covers>", '
            f'{exam_schema_fields}'
            f'"questions": [{{"question_type": "mcq", "text": "<question>", '
            f'"options": ["<option1>", "<option2>", "<option3>", "<option4>"], "correct_answer_index": 2, '
            f'"explanation": "<why correct is right>", "image_suggestion": null | "<search query>", '
            f'"option_image_suggestions": null | ["<query_A>", "<query_B>", "<query_C>", "<query_D>"]}}]}}'
        )
        question_fields += exam_fields

    system_instruction = (
        "You are an expert quiz generator for an online quiz platform. "
        "Follow the user's instructions exactly when creating questions. "
        "Output ONLY valid JSON — no markdown fences, no prose, nothing else.\n\n"
        "At the top level, always include:\n"
        "- title: a concise, descriptive title for this quiz/poll (max 80 chars).\n"
        "- description: 1-2 sentences describing what this quiz covers and who it's for.\n"
        "- questions: the array of question objects.\n\n"
        + question_fields
    )

    existing_context = ""
    if existing_questions:
        cleaned = [q.strip()[:120] for q in existing_questions if q.strip()][:30]
        if cleaned:
            existing_context = (
                "\n\nIMPORTANT — these topics are ALREADY covered in the quiz. "
                "Do NOT generate questions that repeat or overlap them:\n"
                + "\n".join(f"- {q}" for q in cleaned)
                + "\nGenerate only fresh, non-overlapping questions."
            )

    user_message = f"""Generate exactly {count} questions based on the instructions below.
Write all questions, options, and explanations in language code: {language}.

Output format (strict JSON, no other text):
{output_schema}

Rules:
- Output exactly {count} questions, no more, no less.
- Each question must have exactly 4 options. Wrong options must be plausible but clearly incorrect.
- correct_answer_index MUST vary — do not use the same index for every question. Spread correct answers across positions 0, 1, 2, and 3 throughout the set.
{existing_context}
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
        q_type = q.get("question_type", "mcq")
        text = q.get("text", "")
        if not text:
            continue

        if q_type in ("word_cloud", "paragraph", "scale"):
            result.append({
                "question_type": q_type,
                "text": _md_to_html(str(text)),
                "options": None,
                "correct_answer_index": None,
                "explanation": None,
                "image_suggestion": None,
            })
        else:
            # mcq (default)
            opts = q.get("options") or []
            idx = q.get("correct_answer_index", 0)
            if len(opts) < 2:
                continue
            opts = opts[:10]
            try:
                idx = int(idx) if idx is not None else 0
            except (TypeError, ValueError):
                idx = 0
            if not (0 <= idx < len(opts)):
                idx = 0
            explanation = q.get("explanation") or ""
            image_suggestion = q.get("image_suggestion")
            if isinstance(image_suggestion, str) and image_suggestion.strip():
                image_suggestion = image_suggestion.strip()[:200]
            else:
                image_suggestion = None
            raw_ois = q.get("option_image_suggestions")
            if isinstance(raw_ois, list) and len(raw_ois) == len(opts):
                option_image_suggestions = [
                    str(s).strip()[:200] if isinstance(s, str) and s.strip() else None
                    for s in raw_ois
                ]
                if all(s is None for s in option_image_suggestions):
                    option_image_suggestions = None
            else:
                option_image_suggestions = None
            result.append({
                "question_type": "mcq",
                "text": _md_to_html(str(text)),
                "options": [_md_to_html(str(o)) for o in opts],
                "correct_answer_index": idx,
                "explanation": _md_to_html(explanation) if explanation else None,
                "image_suggestion": image_suggestion,
                "option_image_suggestions": option_image_suggestions,
            })

    suggested_duration = parsed.get("suggested_exam_duration_minutes")
    suggested_proctoring = parsed.get("suggested_proctoring")
    try:
        suggested_duration = int(suggested_duration) if suggested_duration is not None else None
    except (TypeError, ValueError):
        suggested_duration = None
    if not isinstance(suggested_proctoring, bool):
        suggested_proctoring = None

    return {
        "title": parsed.get("title") or "",
        "description": parsed.get("description") or "",
        "suggested_exam_duration_minutes": suggested_duration,
        "suggested_proctoring": suggested_proctoring,
        "questions": result,
    }


async def generate_questions_stream(
    prompt: str,
    count: int = 5,
    language: str = "en",
    quiz_type: str = "quiz",
    existing_questions: list[str] | None = None,
):
    """
    Async generator that generates questions and yields each one individually.
    Yields dicts: question objects (same schema as generate_questions),
    then a final {"done": True, "title": ..., "description": ..., exam suggestions...} dict.
    Raises GeminiError on failure.
    """
    import asyncio
    result = await generate_questions(
        prompt=prompt,
        count=count,
        language=language,
        quiz_type=quiz_type,
        existing_questions=existing_questions,
    )
    for q in result["questions"]:
        yield q
        await asyncio.sleep(0)
    yield {
        "done": True,
        "title": result["title"],
        "description": result["description"],
        "suggested_exam_duration_minutes": result.get("suggested_exam_duration_minutes"),
        "suggested_proctoring": result.get("suggested_proctoring"),
    }
