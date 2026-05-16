"""
AI generation endpoints — question generation via Google Gemini; other AI via local ollama.
Restricted to admin and super_admin roles.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from core.auth.dependencies import require_admin, get_current_user, CurrentUser
from core.config.settings import settings
from core.ai.ollama_service import (
    generate_distractors,
    generate_poll_prompt,
    rewrite_text,
    list_available_models,
    OllamaError,
)
from core.ai.gemini_service import (
    generate_questions as gemini_generate_questions,
    validate_quiz_prompt,
    GeminiError,
)

router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Request / Response schemas ───────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="Detailed description of the questions to generate")
    count: int = Field(5, ge=1, le=100, description="Number of questions to generate")
    language: str = Field("en", max_length=10, description="Language code, e.g. en, hi, fr")
    # Legacy field — ignored, kept for backward compatibility
    topic: Optional[str] = Field(None, description="Deprecated: use prompt instead")
    model: Optional[str] = Field(None, description="Ignored — Gemini model is used")


class GeneratedQuestion(BaseModel):
    text: str
    options: list[str]
    correct_answer_index: int
    explanation: Optional[str] = None


class GenerateQuestionsResponse(BaseModel):
    questions: list[GeneratedQuestion]
    model: str


class GenerateDistractorsRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    correct_answer: str = Field(..., min_length=1, max_length=200)
    count: int = Field(3, ge=1, le=5)
    model: Optional[str] = None


class GenerateDistractorsResponse(BaseModel):
    distractors: list[str]
    model: str


class GeneratePollPromptRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    language: str = Field("en", max_length=10)
    model: Optional[str] = None


class GeneratePollPromptResponse(BaseModel):
    prompt: str
    model: str


class ModelsResponse(BaseModel):
    models: list[str]
    default_model: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelsResponse)
async def get_models(current_user: CurrentUser = Depends(require_admin)):
    """List available ollama models on this server."""
    models = await list_available_models()
    return ModelsResponse(models=models, default_model=settings.ollama.model)


@router.post("/generate/questions", response_model=GenerateQuestionsResponse)
async def api_generate_questions(
    req: GenerateQuestionsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate MCQ quiz questions using Google Gemini from a detailed user prompt.
    Returns questions with 4 options each and the correct answer index.
    """
    # Support legacy callers that send topic instead of prompt
    prompt = req.prompt or req.topic or ""
    if not prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prompt is required")

    # Step 1: fast guard — check the prompt is appropriate for quiz generation
    valid, reason = await validate_quiz_prompt(prompt.strip(), language=req.language)
    if not valid:
        # Use Gemini's localised reason when available; sentinel triggers frontend i18n fallback
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "__PROMPT_NOT_FOR_QUIZ__",
        )

    # Step 2: generate questions with enriched context
    try:
        questions = await gemini_generate_questions(
            prompt=prompt.strip(),
            count=req.count,
            language=req.language,
        )
    except GeminiError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid questions were generated — try refining your prompt",
        )

    return GenerateQuestionsResponse(
        questions=[GeneratedQuestion(**q) for q in questions],
        model=settings.gemini.model,
    )


@router.post("/generate/options", response_model=GenerateDistractorsResponse)
async def api_generate_distractors(
    req: GenerateDistractorsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate plausible wrong answer options (distractors) for an MCQ question.
    Useful when you already have a question and correct answer but need the wrong options.
    """
    model = req.model or settings.ollama.model
    try:
        distractors = await generate_distractors(
            question=req.question,
            correct_answer=req.correct_answer,
            count=req.count,
            model=model,
        )
    except OllamaError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return GenerateDistractorsResponse(distractors=distractors, model=model)


@router.post("/generate/poll-prompt", response_model=GeneratePollPromptResponse)
async def api_generate_poll_prompt(
    req: GeneratePollPromptRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate a short open-ended word cloud poll question for a given topic.
    Designed to elicit single/two-word responses from the audience.
    """
    model = req.model or settings.ollama.model
    try:
        prompt = await generate_poll_prompt(
            topic=req.topic,
            language=req.language,
            model=model,
        )
    except OllamaError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return GeneratePollPromptResponse(prompt=prompt, model=model)


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    context: str = Field("quiz question", max_length=60)
    language: str = Field("en", max_length=10)
    model: Optional[str] = None


class RewriteResponse(BaseModel):
    rewritten: str
    model: str


@router.post("/rewrite", response_model=RewriteResponse)
async def api_rewrite(
    req: RewriteRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Rewrite a piece of text to be clearer and better suited for a quiz context."""
    model = req.model or settings.ollama.fallback_model
    try:
        rewritten = await rewrite_text(
            text=req.text,
            context=req.context,
            language=req.language,
            model=model,
        )
    except OllamaError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return RewriteResponse(rewritten=rewritten, model=model)
