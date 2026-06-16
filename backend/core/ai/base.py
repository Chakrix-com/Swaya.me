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

    async def list_available_models(self) -> list[str]:
        """Return model IDs available via this provider. Empty list if not applicable."""
        return []
