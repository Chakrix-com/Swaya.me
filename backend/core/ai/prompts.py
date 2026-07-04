"""
Shared AI prompt construction and response parsing.

All providers use these utilities so prompts stay consistent regardless of which
backend is configured. Each builder returns (system_instruction: str, user_message: str)
— Gemini adapts that pair to its REST shape; OpenAI/Anthropic providers call
build_*_messages() which wraps the same strings into [{role, content}] format.
"""
import html as _html_mod
import json
import re
from typing import Any


# ── Text utilities ─────────────────────────────────────────────────────────────

def strip_html_tags(text: str) -> str:
    """Strip HTML tags to plain text. Used when building prompts from stored question content."""
    return re.sub(r'<[^>]+>', '', text or '').strip()


def _parse_json(raw: str) -> Any:
    """Strip markdown fences (if present) and parse JSON."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def md_to_html(text: str) -> str:
    """
    Convert markdown code syntax (as returned by LLMs) to HTML
    for storage and rendering by RichTextRenderer.

    Handles:
      - Fenced code blocks: ```lang\\ncode\\n``` → <pre><code class="language-lang">…</code></pre>
      - Inline code: `expr` → <code>expr</code>
      - Bold: **text** → <strong>text</strong>
    """
    if not text:
        return text

    has_fence = '```' in text
    has_inline = re.search(r'`[^`\n]+`', text)
    has_bold = '**' in text

    if not has_fence and not has_inline and not has_bold:
        return text

    fence_re = re.compile(r'```([\w]*)\n([\s\S]*?)```', re.DOTALL)
    parts = fence_re.split(text)

    result_parts: list[str] = []
    i = 0
    while i < len(parts):
        if i % 3 == 0:
            segment = parts[i]
            segment = _html_mod.escape(segment)
            segment = re.sub(r'`([^`\n]+)`', lambda m: f'<code>{m.group(1)}</code>', segment)
            segment = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', segment)
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
            lang = parts[i].strip().lower()
        else:
            code = _html_mod.escape(parts[i].rstrip('\n'))
            lang_attr = f' class="language-{lang}"' if lang else ''
            result_parts.append(f'<pre><code{lang_attr}>{code}</code></pre>')
        i += 1

    return ''.join(result_parts)


# ── Question generation ────────────────────────────────────────────────────────

def _build_question_fields_and_schema(quiz_type: str) -> tuple[str, str]:
    """Returns (question_fields, output_schema) for the given quiz type."""
    if quiz_type == "poll":
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
        return question_fields, output_schema

    if quiz_type == "offline_poll":
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
        return question_fields, output_schema

    # quiz or exam
    is_exam = quiz_type == "exam"
    question_fields = (
        "Field requirements — each question must have question_type set to one of: \"mcq\", \"single_line\", or \"code\".\n"
        "Generate a mix: approximately 60% mcq, 25% single_line, 15% code (adjust based on topic suitability).\n\n"

        "MCQ (question_type: \"mcq\"):\n"
        "- text: question text with HTML formatting (<strong>, <em>). "
        "Any code snippet MUST be wrapped in <pre><code class=\"language-X\">…</code></pre>. "
        "Inline code references use <code>name</code>.\n"
        "- options: exactly 4 distinct answer choices (same code formatting rules apply).\n"
        "- correct_answer_index: 0-based index. CRITICAL: spread across ALL positions 0–3 roughly equally.\n"
        "- explanation: 2-3 plain-text sentences on why the correct answer is right.\n"
        "- image_suggestion: short image search query if a diagram would help, else null.\n"
        "- option_image_suggestions: array of image search queries (one per option) if options are "
        "visual identities (people, places, logos); else null.\n\n"

        "SINGLE_LINE (question_type: \"single_line\") — short text answer graded by AI:\n"
        "- text: a question whose answer is a short phrase, number, name, or term.\n"
        "- options: array with exactly ONE string — the expected correct answer (used for AI grading). "
        "E.g. [\"O(log n)\"] or [\"mitochondria\"].\n"
        "- correct_answer_index: null.\n"
        "- explanation: 1-2 sentences explaining the correct answer.\n"
        "- image_suggestion: null.\n"
        "- option_image_suggestions: null.\n\n"

        "CODE (question_type: \"code\") — participant writes code to solve a programming problem:\n"
        "- text: a clear programming problem statement. Include examples if helpful.\n"
        "- options: array of 1–3 allowed programming languages from: "
        "[\"python\", \"java\", \"cpp\", \"javascript\", \"typescript\", \"go\", \"rust\", \"csharp\"]. "
        "Default to [\"python\"] unless the topic implies a specific language.\n"
        "- grading_rubric: describe what correct code should output for key test inputs "
        "(e.g. \"For n=7: True, n=4: False, n=1: False, n=-1: False\"). Be specific.\n"
        "- correct_answer_index: null.\n"
        "- explanation: null.\n"
        "- image_suggestion: null.\n"
        "- option_image_suggestions: null.\n"
    )
    if is_exam:
        question_fields += (
            "\n\nFor the top-level object, also include:\n"
            "- suggested_exam_duration_minutes: integer estimate of total exam duration in minutes "
            "based on the number and difficulty of questions. null if not determinable.\n"
            "- suggested_proctoring: boolean — true if this exam topic/context typically requires "
            "anti-cheating measures (e.g. hiring tests, certification exams), false for casual use."
        )
        exam_schema_fields = '"suggested_exam_duration_minutes": <int | null>, "suggested_proctoring": <true | false>, '
    else:
        exam_schema_fields = ""

    output_schema = (
        f'{{"title": "<quiz title>", "description": "<brief description of what this quiz covers>", '
        f'{exam_schema_fields}'
        f'"questions": ['
        f'{{"question_type": "mcq", "text": "<question>", '
        f'"options": ["<A>", "<B>", "<C>", "<D>"], "correct_answer_index": 2, '
        f'"explanation": "<why correct>", "image_suggestion": null, "option_image_suggestions": null, "grading_rubric": null}}, '
        f'{{"question_type": "single_line", "text": "<question>", '
        f'"options": ["<expected answer>"], "correct_answer_index": null, '
        f'"explanation": "<why this is the answer>", "image_suggestion": null, "option_image_suggestions": null, "grading_rubric": null}}, '
        f'{{"question_type": "code", "text": "<problem statement>", '
        f'"options": ["python"], "correct_answer_index": null, '
        f'"explanation": null, "image_suggestion": null, "option_image_suggestions": null, '
        f'"grading_rubric": "<expected outputs for key test cases>"}}]}}'
    )
    return question_fields, output_schema


def build_question_generation_content(
    prompt: str,
    count: int,
    language: str,
    quiz_type: str,
    existing_questions: list[str] | None = None,
) -> tuple[str, str]:
    """Returns (system_instruction, user_message) for question generation."""
    question_fields, output_schema = _build_question_fields_and_schema(quiz_type)

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

    user_message = (
        f"Generate exactly {count} questions based on the instructions below.\n"
        f"Write all questions, options, and explanations in language code: {language}.\n\n"
        f"Output format (strict JSON, no other text):\n{output_schema}\n\n"
        f"Rules:\n"
        f"- Output exactly {count} questions, no more, no less.\n"
        f"- Each question must have exactly 4 options. Wrong options must be plausible but clearly incorrect.\n"
        f"- correct_answer_index MUST vary — do not use the same index for every question. "
        f"Spread correct answers across positions 0, 1, 2, and 3 throughout the set.\n"
        f"{existing_context}\n"
        f"User instructions:\n{prompt}"
    )

    return system_instruction, user_message


def build_question_generation_messages(
    prompt: str,
    count: int,
    language: str,
    quiz_type: str,
    existing_questions: list[str] | None = None,
) -> list[dict]:
    """OpenAI/Anthropic [{role, content}] format for question generation."""
    system, user = build_question_generation_content(prompt, count, language, quiz_type, existing_questions)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_question_response(raw: str, quiz_type: str) -> dict:
    """
    Parse and normalise a question-generation JSON response from any provider.

    Returns the canonical result dict:
    {
        "title": str,
        "description": str,
        "suggested_exam_duration_minutes": int | None,
        "suggested_proctoring": bool | None,
        "questions": [...]
    }
    Raises ValueError on parse failure (callers convert to AIProviderError).
    """
    parsed = _parse_json(raw)
    questions_raw = parsed.get("questions")
    if not isinstance(questions_raw, list):
        raise ValueError("Response missing 'questions' list")

    result = []
    for q in questions_raw:
        q_type = q.get("question_type", "mcq")
        text = q.get("text", "")
        if not text:
            continue

        if q_type in ("word_cloud", "paragraph", "scale"):
            result.append({
                "question_type": q_type,
                "text": md_to_html(str(text)),
                "options": None,
                "correct_answer_index": None,
                "explanation": None,
                "image_suggestion": None,
                "option_image_suggestions": None,
                "grading_rubric": None,
            })
        elif q_type == "single_line":
            opts = q.get("options") or []
            expected = str(opts[0]).strip() if opts else ""
            explanation = q.get("explanation") or ""
            result.append({
                "question_type": "single_line",
                "text": md_to_html(str(text)),
                "options": [expected] if expected else None,
                "correct_answer_index": None,
                "explanation": md_to_html(explanation) if explanation else None,
                "image_suggestion": None,
                "option_image_suggestions": None,
                "grading_rubric": None,
            })
        elif q_type == "code":
            opts = q.get("options") or ["python"]
            valid_langs = {"python", "java", "cpp", "javascript", "typescript", "go", "rust", "csharp"}
            langs = [str(o).lower() for o in opts if str(o).lower() in valid_langs] or ["python"]
            rubric = q.get("grading_rubric") or ""
            result.append({
                "question_type": "code",
                "text": md_to_html(str(text)),
                "options": langs,
                "correct_answer_index": None,
                "explanation": None,
                "image_suggestion": None,
                "option_image_suggestions": None,
                "grading_rubric": str(rubric)[:2000] if rubric else None,
            })
        else:
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
                "text": md_to_html(str(text)),
                "options": [md_to_html(str(o)) for o in opts],
                "correct_answer_index": idx,
                "explanation": md_to_html(explanation) if explanation else None,
                "image_suggestion": image_suggestion,
                "option_image_suggestions": option_image_suggestions,
                "grading_rubric": None,
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


# ── Prompt validation ──────────────────────────────────────────────────────────

def build_validation_content(prompt: str, language: str) -> tuple[str, str]:
    """Returns (system_instruction, user_message) for quiz-prompt validation."""
    system_instruction = (
        "You are a content validator for an online quiz platform. "
        "Decide whether a user's request is suitable for generating quiz or test questions. "
        "Output ONLY valid JSON — nothing else."
    )
    user_message = (
        f"Determine whether the following prompt is appropriate for generating educational quiz or test questions.\n\n"
        f"A VALID prompt:\n"
        f"- Describes a topic, subject, concept, or skill (e.g. \"Python decorators\", \"World War II causes\", \"HR interview questions\")\n"
        f"- Could reasonably produce factual, conceptual, or applied questions\n\n"
        f"An INVALID prompt:\n"
        f"- Asks for something unrelated to quizzes (recipes, creative writing, code programs, personal advice, jokes, etc.)\n"
        f"- Is offensive, harmful, or inappropriate\n"
        f"- Is pure gibberish or not a recognisable human language\n\n"
        f"Output format (strict JSON):\n"
        f'{{\"valid\": true}} if valid\n'
        f'{{\"valid\": false, \"reason\": \"<one concise sentence explaining why, written in language code: {language}>\"}} if invalid\n\n'
        f"User's prompt:\n{prompt}"
    )
    return system_instruction, user_message


def build_validation_messages(prompt: str, language: str) -> list[dict]:
    """OpenAI/Anthropic [{role, content}] format for prompt validation."""
    system, user = build_validation_content(prompt, language)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ── Participant summary ────────────────────────────────────────────────────────

def build_participant_summary_content(
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
) -> tuple[str, str]:
    """Returns (system_instruction, user_prompt) for exam participant summary (HTML fragment)."""
    pct_int = int(round(percentage))
    time_str = ""
    if time_taken_seconds is not None:
        m, s = divmod(int(time_taken_seconds), 60)
        time_str = f"{m}m {s}s"

    q_lines = []
    for i, qr in enumerate(question_results, 1):
        status = "correct" if qr.is_correct else ("skipped" if qr.participant_answer is None else "wrong")
        opts = qr.options or []
        your_ans = strip_html_tags(opts[qr.participant_answer]) if qr.participant_answer is not None and qr.participant_answer < len(opts) else "—"
        correct_ans = strip_html_tags(opts[qr.correct_answer_index]) if qr.correct_answer_index is not None and qr.correct_answer_index < len(opts) else "—"
        q_lines.append(
            f"Q{i} [{status}]: {strip_html_tags(qr.question_text)[:120]} | Your answer: {your_ans} | Correct: {correct_ans}"
        )

    stats = (
        f"Participant: {name or 'Candidate'}\n"
        f"Exam: {quiz_title}\n"
        f"Score: {total_score}/{max_score} ({pct_int}%)\n"
        f"Correct: {correct_count} | Wrong: {wrong_count} | Skipped: {unanswered_count}\n"
        f"Time taken: {time_str or 'unknown'}\n"
        f"Started: {started_at or 'unknown'} | Completed: {completed_at or 'unknown'}\n\n"
        f"Per-question detail:\n" + "\n".join(q_lines)
    )

    system_instruction = (
        "You are an expert coach. Output only the HTML fragment requested — "
        "no markdown, no prose outside the HTML."
    )

    user_prompt = (
        f"You are an expert coach writing a personalised performance report for a candidate "
        f"who just completed an online screening exam.\n\n"
        f"{stats}\n\n"
        f"Write a warm, encouraging yet honest personal summary in HTML (no <html>/<body> wrapper, "
        f"just inner content). Use this structure exactly:\n\n"
        f'<h3 style="color:#1677ff;margin:0 0 12px;">Your Performance Summary</h3>\n'
        f"<p>One opening sentence addressing the candidate by first name, acknowledging their score warmly.</p>\n\n"
        f'<h4 style="margin:16px 0 6px;color:#1a1a1a;">Strengths</h4>\n'
        f"<ul>2-3 bullet points about what they did well, based on which questions they got right</ul>\n\n"
        f'<h4 style="margin:16px 0 6px;color:#1a1a1a;">Areas to Improve</h4>\n'
        f"<ul>2-3 bullet points about topics or question types where they struggled, specific to wrong/skipped answers</ul>\n\n"
        f'<h4 style="margin:16px 0 6px;color:#1a1a1a;">How to Improve</h4>\n'
        f"<ul>2-3 concrete, actionable study suggestions based on the specific weak areas identified</ul>\n\n"
        f'<h4 style="margin:16px 0 6px;color:#1a1a1a;">Time & Pacing</h4>\n'
        f"<p>One sentence on their time management. Was it fast, slow, or well-paced for the number of questions?</p>\n\n"
        f'<p style="margin-top:16px;color:#595959;font-size:13px;">One closing sentence of encouragement.</p>\n\n'
        f"Rules:\n"
        f"- Address the candidate by first name throughout\n"
        f"- Be specific to their actual answers — don't be generic\n"
        f"- Keep it concise and easy to read\n"
        f"- Output ONLY the HTML fragment above, nothing else"
    )

    return system_instruction, user_prompt


def build_participant_summary_messages(
    name: str, quiz_title: str, total_score: int, max_score: int, percentage: float,
    correct_count: int, wrong_count: int, unanswered_count: int,
    time_taken_seconds: float | None, started_at: str | None, completed_at: str | None,
    question_results: list,
) -> list[dict]:
    """OpenAI/Anthropic [{role, content}] format for participant summary."""
    system, user = build_participant_summary_content(
        name, quiz_title, total_score, max_score, percentage,
        correct_count, wrong_count, unanswered_count,
        time_taken_seconds, started_at, completed_at, question_results,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ── Exam analysis ─────────────────────────────────────────────────────────────

def build_exam_analysis_content(results: dict, custom_prompt: str | None = None) -> tuple[str, str]:
    """Returns (system_instruction, user_prompt) for cohort-level exam analysis (markdown)."""
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
        plain_text = strip_html_tags(q.get("question_text", ""))[:120]
        dist = q.get("answer_distribution", [])
        opts = q.get("options", [])
        opt_dist = ""
        for j, (o, c) in enumerate(zip(opts, dist)):
            plain_opt = strip_html_tags(o)[:40]
            marker = " ✓" if j == q.get("correct_answer_index") else ""
            opt_dist += f"    {chr(65+j)}: {plain_opt}{marker} ({c} responses)\n"
        q_lines.append(
            f"Q{i+1} [{q.get('percent_correct', 0):.0f}% correct, {q.get('total_answers',0)} responses]: {plain_text}\n{opt_dist}"
        )

    stats_block = (
        f'Quiz: "{results.get("quiz_title", "Exam")}"\n'
        f"Participants: {total_started} started | {total_completed} completed | {total_abandoned} abandoned\n"
        f"Scores: avg {avg_score}/{max_score} ({round(avg_score/max_score*100) if max_score else 0}%) | "
        f"min {score_min} | max {score_max}\n"
        f"Pass threshold (60%): {pass_threshold:.0f} pts | "
        f"Passed: {sum(1 for s in scores if s >= pass_threshold)}/{len(scores)}\n"
        + (f"Avg time: {avg_time_min} min\n" if avg_time_min else "")
        + f"\nPer-question breakdown:\n" + "\n".join(q_lines)
    )

    default_instructions = (
        "Your report MUST contain exactly these sections:\n"
        "## 1. Score Summary\n"
        "Quantitative overview: average, median (estimate from distribution), pass rate, score spread.\n\n"
        "## 2. Question Difficulty Ranking\n"
        "List questions from hardest to easiest with % correct. Highlight any question where < 40% got it right (needs review) or > 90% got it right (possibly too easy).\n\n"
        "## 3. Common Mistake Patterns\n"
        "For the hardest questions, which wrong answer was most chosen and what misconception does that suggest?\n\n"
        "## 4. Qualitative Insights\n"
        "What topics or skills are participants weakest/strongest in, based on the question content and results?\n\n"
        "## 5. Recommendations\n"
        "Concrete actionable suggestions: which topics need more training, which questions should be revised, any anomalies to investigate.\n\n"
        "Be concise. Use bullet points. Do not repeat raw numbers already obvious from the dashboard."
    )

    instructions = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else default_instructions

    system_instruction = (
        "You are an expert educational analyst. "
        "Output clean markdown only — no preamble, no trailing commentary."
    )
    user_prompt = (
        f"You are an expert educational analyst. Analyse the following exam results and produce a clear, structured report in markdown.\n\n"
        f"{stats_block}\n\n"
        f"{instructions}"
    )
    return system_instruction, user_prompt


def build_exam_analysis_messages(results: dict, custom_prompt: str | None = None) -> list[dict]:
    """OpenAI/Anthropic [{role, content}] format for exam analysis."""
    system, user = build_exam_analysis_content(results, custom_prompt)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ── Light-tier helpers ─────────────────────────────────────────────────────────

def build_distractor_messages(question: str, correct_answer: str, count: int) -> list[dict]:
    return [
        {"role": "system", "content": "You are a quiz generator. Output only valid JSON, no extra text."},
        {"role": "user", "content": (
            f"Generate {count} plausible but clearly wrong answer options (distractors) for:\n"
            f"Question: {question}\n"
            f"Correct answer: {correct_answer}\n\n"
            f'Respond with JSON only: {{"distractors": ["<wrong 1>", "<wrong 2>", "<wrong 3>"]}}\n\n'
            f"Rules: distractors must be believable, different from each other, and NOT include the correct answer."
        )},
    ]


def build_poll_prompt_messages(topic: str, language: str) -> list[dict]:
    return [
        {"role": "system", "content": "You are a poll question generator. Output only valid JSON, no extra text."},
        {"role": "user", "content": (
            f"Generate a single short, open-ended poll question for a live audience word cloud activity.\n"
            f"Topic: \"{topic}\"\n"
            f"Language: {language}\n\n"
            f"The question should encourage one or two word answers that work well in a word cloud.\n\n"
            f'Respond with JSON only: {{"prompt": "<your poll question here>"}}'
        )},
    ]


def build_rewrite_messages(text: str, context: str, language: str) -> list[dict]:
    return [
        {"role": "user", "content": (
            f"Fix spelling, grammar, and phrasing of the text below for use as a {context}. "
            f"Write in {language}. Return ONLY the corrected text, nothing else.\n\n{text}"
        )},
    ]


def build_grade_messages(participant_answer: str, expected_answer: str) -> list[dict]:
    return [
        {"role": "system", "content": "You are a quiz answer grader. Reply with exactly one word: YES or NO."},
        {"role": "user", "content": (
            f"Expected answer: {expected_answer}\n"
            f"Participant answer: {participant_answer}\n\n"
            f"Does the participant's answer convey the same meaning as the expected answer, "
            f"allowing for minor spelling mistakes, synonyms, different word order, or "
            f"extra/missing articles?"
        )},
    ]
