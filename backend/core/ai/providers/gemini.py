"""
Google Gemini provider — implements BaseAIProvider using Gemini's REST API.
Uses httpx directly to avoid SDK version dependency issues.
"""
import html as _html_mod
import json
import logging
import re as _re_mod

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
    # Deprecated models — redirect to current equivalents
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
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
        import asyncio as _asyncio
        _FALLBACK_CHAIN = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
        models_to_try = [model]
        for fb in _FALLBACK_CHAIN:
            if fb != model:
                models_to_try.append(fb)

        last_error = None
        async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
            for model_idx, attempt_model in enumerate(models_to_try):
                for retry in range(3):
                    try:
                        resp = await client.post(self._url(attempt_model), json=payload)
                        if resp.status_code == 503:
                            last_error = AIProviderError(f"Gemini 503 on {attempt_model}")
                            sleep_s = 2.0 * (retry + 1) + model_idx * 1.0
                            logger.debug("Gemini 503 on %s retry=%d, sleeping %.1fs", attempt_model, retry, sleep_s)
                            await _asyncio.sleep(sleep_s)
                            continue
                        resp.raise_for_status()
                        return resp.json()
                    except httpx.HTTPStatusError as e:
                        sc = e.response.status_code
                        if sc in (503, 429):
                            last_error = AIProviderError(f"Gemini {sc} on {attempt_model}")
                            sleep_s = 2.0 * (retry + 1) + model_idx * 1.0
                            await _asyncio.sleep(sleep_s)
                        elif sc == 404:
                            # Model deprecated/removed — skip all retries, try next model
                            last_error = AIProviderError(f"Gemini model not found: {attempt_model}")
                            break
                        else:
                            raise AIProviderError(f"Gemini API HTTP {sc}: {e.response.text[:200]}")
                    except httpx.ConnectError:
                        raise AIProviderError("Cannot connect to Gemini API — check network")
                    except httpx.ReadTimeout:
                        raise AIProviderError("Gemini request timed out")
                # all retries on this model exhausted — try next model
        raise last_error or AIProviderError("All Gemini models unavailable")

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

    async def evaluate_code(
        self,
        language: str,
        code: str,
        problem_statement: str,
        grading_rubric: str,
    ) -> dict:
        if not self._key:
            return {"verdict": "WA", "output": "", "explanation": "AI evaluation unavailable"}
        system = (
            "You are a strict programming judge. Your job is to check whether the submitted code "
            "CORRECTLY SOLVES THE SPECIFIC PROBLEM stated in the prompt — not just whether it runs.\n\n"
            "IMPORTANT: If the code solves a completely different problem (e.g. fibonacci code submitted "
            "for a prime-checking question), that is WA — Wrong Answer — regardless of whether the code "
            "itself is correct for that other problem.\n\n"
            "Verdict rules:\n"
            "- AC: code runs AND its output correctly answers the problem for all test cases\n"
            "- WA: code runs but output is wrong OR the code solves a different problem entirely\n"
            "- CE: syntax/compile error — cannot run at all\n"
            "- RE: crashes / raises exception during execution\n"
            "- TLE: infinite loop or hopelessly slow\n\n"
            "Output field — simulate the code on these test cases (skip if CE, show error message if CE):\n"
            "  If the code requires input: test with typical, boundary, and negative values appropriate "
            "  for the problem. One line per test: 'n=<val>: <actual output or ERROR: <msg>>'.\n"
            "  Show what the code ACTUALLY outputs — do NOT invent correct answers.\n"
            "  Format as plain multi-line text (NOT a JSON array).\n\n"
            "efficiency field (for host/teacher): 2-3 sentences on time complexity, space complexity, "
            "optimality, and edge-case handling. If verdict is WA because wrong problem was solved, "
            "state that clearly.\n\n"
            "Return ONLY valid JSON: {\"verdict\": \"...\", \"output\": \"...\", \"efficiency\": \"...\"}"
        )
        user = (
            f"Language: {language}\n\n"
            f"Problem:\n{problem_statement}\n\n"
            f"Grading context:\n{grading_rubric}\n\n"
            f"Submitted code:\n```{language}\n{code}\n```"
        )
        # gemini-2.5-flash is a thinking model — needs large token budget for hidden reasoning + output
        payload = self._gemini_payload(system, user, temperature=0.0, max_tokens=8192, json_mode=True)
        try:
            data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(60.0, connect=10.0))
            raw = self._extract_text(data)
            parsed = _parse_json(raw)
            verdict = str(parsed.get("verdict", "WA")).upper()
            if verdict not in {"AC", "WA", "PE", "RE", "CE", "TLE"}:
                verdict = "WA"
            raw_output = parsed.get("output", "")
            if isinstance(raw_output, list):
                raw_output = "\n".join(str(x) for x in raw_output)
            return {
                "verdict": verdict,
                "output": str(raw_output),
                "efficiency": str(parsed.get("efficiency", "")),
            }
        except Exception as e:
            logger.warning("Gemini evaluate_code failed: %s", e)
            return {"verdict": "ERR", "output": "", "explanation": "AI evaluator temporarily unavailable — please try again in a moment"}

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return text
        text = _re_mod.sub(r'<[^>]+>', ' ', str(text))
        text = _html_mod.unescape(text)
        return _re_mod.sub(r'\s+', ' ', text).strip()

    async def generate_interview_sheet(self, participant_data: dict, quiz_title: str) -> str:
        """Generate a structured interview question sheet in Markdown from exam results."""
        if not self._key:
            raise AIProviderError("GEMINI_KEY is not configured")

        from datetime import datetime as _dt
        today = _dt.now().strftime("%B %d, %Y")

        name = participant_data.get("display_name", "Candidate")
        score = participant_data.get("score", 0)
        max_score = participant_data.get("max_score", 0)
        percentage = participant_data.get("percentage", 0)
        questions = participant_data.get("questions", [])

        correct_qs = [q for q in questions if q.get("is_correct") is True]
        wrong_qs = [q for q in questions if q.get("is_correct") is not True]

        sh = self._strip_html

        def _fmt_opts(opts):
            if not opts:
                return "  (no options)"
            return "\n".join(f"  {chr(65 + i)}. {sh(o)}" for i, o in enumerate(opts))

        correct_section = ""
        for i, q in enumerate(correct_qs):
            opts = q.get("options") or []
            ci = q.get("correct_answer_index") or 0
            correct_text = sh(opts[ci]) if opts and ci < len(opts) else "N/A"
            correct_section += (
                f"\nQ{i + 1}: {sh(q.get('question_text', ''))}\n"
                f"Options:\n{_fmt_opts(opts)}\n"
                f"Correct: Option {chr(65 + ci)} — {correct_text}\n"
            )

        wrong_section = ""
        for i, q in enumerate(wrong_qs):
            opts = q.get("options") or []
            ci = q.get("correct_answer_index") or 0
            correct_text = sh(opts[ci]) if opts and ci < len(opts) else "N/A"
            participant_idx = q.get("participant_answer")
            if participant_idx is not None and opts and participant_idx < len(opts):
                chosen_text = sh(opts[participant_idx])
            else:
                chosen_text = "Did not answer"
            wrong_section += (
                f"\nQ{i + 1}: {sh(q.get('question_text', ''))}\n"
                f"Options:\n{_fmt_opts(opts)}\n"
                f"Correct: Option {chr(65 + ci)} — {correct_text}\n"
                f"Candidate chose: {chosen_text}\n"
            )

        est_minutes = max(len(questions) * 3, 10)

        system = "You are an expert technical interviewer."
        user = f"""Given an exam result for a candidate, generate a structured interview question sheet in Markdown.

Exam: {quiz_title}
Candidate: {name}
Score: {score}/{max_score} ({percentage}%)
Date: {today}

=== QUESTIONS ANSWERED CORRECTLY ({len(correct_qs)}) ===
{correct_section.strip() if correct_section else "(None — candidate did not answer any questions correctly)"}

=== QUESTIONS ANSWERED INCORRECTLY OR SKIPPED ({len(wrong_qs)}) ===
{wrong_section.strip() if wrong_section else "(None — candidate answered all questions correctly)"}

---
INSTRUCTIONS:
1. For correctly answered questions: write 1–2 depth-probe questions per question.
   Ask WHY the answer is correct, ask for edge cases, ask for real-world application.
   Include the ideal expected answer.

2. For incorrectly answered / skipped questions: write 1–2 gap-probe questions per question.
   Approach from first principles. Surface the likely misconception.
   Include the ideal expected answer AND the common misconception to watch for.

3. Group by PART A (correct) and PART B (wrong/skipped).
   If Part A has no questions, note "No correctly answered questions" and proceed to Part B.
   If Part B has no questions, note "All questions answered correctly" and skip Part B.

4. Add a PART C — Synthesis: 1 paragraph summarising the candidate's profile,
   apparent strengths, concerning gaps, and a hire/train/pass recommendation.

5. Start with a header: # Technical Interview — {name}
   Include: Exam, Score, Recommended Duration (~{est_minutes} minutes).

6. Output ONLY the Markdown. No preamble, no explanation, no code blocks wrapping the output."""

        payload = self._gemini_payload(system, user, temperature=0.5, max_tokens=8192)
        data = await self._post(payload, self._model_fast, timeout=httpx.Timeout(120.0, connect=10.0))
        return self._extract_text(data).strip()

    async def list_available_models(self) -> list[str]:
        return []
