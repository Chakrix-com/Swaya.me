"""
Abstract base for all AI providers.

Each provider implements this surface. Methods that a provider cannot support
raise NotImplementedError — the router falls back to the other tier's provider.
validate_quiz_prompt and grade_text_answer have safe no-op defaults so callers
never crash if a lightweight provider skips them.
"""
from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised by any provider on a recoverable error (HTTP failure, parse error, timeout)."""
    pass


class BaseAIProvider(ABC):

    # ── Primary tier ──────────────────────────────────────────────────────────

    @abstractmethod
    async def generate_questions(
        self,
        prompt: str,
        count: int,
        language: str,
        quiz_type: str,
        existing_questions: list[str] | None = None,
        allowed_question_types: list[str] | None = None,
    ) -> dict:
        """
        Returns:
        {
            "title": str,
            "description": str,
            "suggested_exam_duration_minutes": int | None,
            "suggested_proctoring": bool | None,
            "questions": [
                {
                    "question_type": str,
                    "text": str,
                    "options": list[str] | None,
                    "correct_answer_index": int | None,
                    "explanation": str | None,
                    "image_suggestion": str | None,
                    "option_image_suggestions": list[str] | None,
                },
                ...
            ]
        }
        """

    async def validate_quiz_prompt(self, prompt: str, language: str) -> tuple[bool, str]:
        """Fast guard. Returns (True, '') if prompt is suitable, (False, reason) if not.
        Default: always passes — providers that can afford a cheap guard call override this."""
        return True, ""

    async def generate_participant_summary(self, **kwargs) -> str:
        """HTML fragment for an individual exam result. Raises AIProviderError if not supported."""
        raise AIProviderError("generate_participant_summary not supported by this provider")

    async def analyze_exam_results(
        self, results: dict, custom_prompt: str | None = None
    ) -> str:
        """Markdown report across all exam participants. Raises AIProviderError if not supported."""
        raise AIProviderError("analyze_exam_results not supported by this provider")

    # ── Light tier ────────────────────────────────────────────────────────────

    @abstractmethod
    async def generate_distractors(
        self, question: str, correct_answer: str, count: int = 3
    ) -> list[str]:
        """Plausible-but-wrong MCQ options for a given question + correct answer."""

    @abstractmethod
    async def generate_poll_prompt(self, topic: str, language: str = "en") -> str:
        """Short open-ended word-cloud question for a live audience."""

    @abstractmethod
    async def rewrite_text(self, text: str, context: str, language: str) -> str:
        """Fix grammar/phrasing for quiz context. Returns corrected string."""

    async def grade_text_answer(
        self, participant_answer: str, expected_answer: str
    ) -> bool:
        """Semantic equivalence check. Default: exact match (safe fallback)."""
        return participant_answer.strip().lower() == expected_answer.strip().lower()

    async def evaluate_code(
        self,
        language: str,
        code: str,
        problem_statement: str,
        grading_rubric: str,
    ) -> dict:
        """
        Simulate code execution and return a competitive-programming verdict.
        Returns: {"verdict": "AC|WA|PE|RE|CE|TLE", "output": str, "explanation": str}
        Default: always WA (safe fallback when no AI provider is configured).
        """
        return {"verdict": "WA", "output": "", "explanation": "AI evaluation unavailable"}

    async def assess_coding_challenge(
        self,
        problem_statement: str,
        grading_rubric: str,
        final_code_snapshot: str,
        candidate_prompts: str,
        usage_summary: dict,
        weights: dict = None,
    ) -> dict:
        """
        Judge the 4 LLM-scored coding-challenge criteria (AI-usage efficiency, prompt
        quality, code quality, architecture) from curated, pre-digested inputs — NOT
        the raw commit timeline / full transcript dump. Does NOT judge functional
        correctness (deterministic from test results, kept out of the LLM's hands so
        grading integrity doesn't depend on the model resisting a prompt-injection
        attempt embedded in candidate-authored content) or validation_discipline
        (moved to a fully deterministic pattern-match 2026-08-09 — see
        grading_service_async._compute_validation_discipline — it doesn't need or
        benefit from LLM judgment, and removing it shrinks what has to go through
        this call at all).

        Revised 2026-08-09 (deterministic-first grading redesign — a fully AI-judged,
        uncalibrated call was producing near-100% scores regardless of actual outcome,
        and the old code_timeline/ai_transcript inputs were unbounded — one real
        session's git log alone reached 13.6MB, over Gemini's own input limit):
          - final_code_snapshot: the code AS SUBMITTED, not a reconstruction from
            diff history — this is what code_quality/architecture should be judged
            against anyway, and it's naturally bounded by repo size rather than
            session length.
          - candidate_prompts: only the candidate's own typed prompts (extracted from
            the transcript), not the full JSONL including every tool call/response.
          - usage_summary: pre-computed session stats (prompt count, commit counts,
            test-run count) instead of asking the model to do that counting itself.

        `weights` is the (already-resolved, host-override-or-platform-default) weight
        dict for all 7 scoring criteria — only the 4 this method judges are meaningful
        to include in a provider's prompt; the rest (functional_correctness, time_taken,
        validation_discipline) are computed elsewhere and shouldn't be shown as if they
        were this call's concern. Passing the same resolved weights the caller will
        actually use to combine scores (rather than recomputing/guessing at defaults
        here) keeps what the model is told in sync with what's actually applied.

        Returns: {"ai_usage_efficiency": int, "prompt_quality": int,
                  "code_quality": int, "architecture": int, "rationale": str} —
        each score 0-100. rationale is newline-delimited short bullet points
        (providers should ask the model for an array and join with "\n"), not one
        long paragraph. Default: neutral mid-score fallback when no AI provider is
        configured.
        """
        return {
            "ai_usage_efficiency": 50,
            "prompt_quality": 50,
            "code_quality": 50,
            "architecture": 50,
            "rationale": "AI assessment unavailable",
        }

    async def list_available_models(self) -> list[str]:
        """Return model IDs available via this provider. Empty list if not applicable."""
        return []

    async def generate_coding_challenge_problem(self, topic: str, language: str = "en") -> str:
        """
        Generate a complete coding-challenge problem statement (Background/Task/
        Requirements/Constraints & Scale/Examples) from a short host-supplied topic.
        Unlike rewrite_text, this generates fresh content rather than polishing
        existing text, and needs a larger output budget than a short rewrite.
        Default: raises, since not every provider is worth wiring up for this —
        callers should surface the error rather than silently doing nothing.
        """
        raise AIProviderError("Problem generation is not supported by the configured AI provider")
