"""
AI generation endpoints — question generation via Google Gemini; other AI via local ollama.
Restricted to admin and super_admin roles.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator

from core.auth.dependencies import require_admin, get_current_user, CurrentUser
from shared.utils.rate_limiter import limiter, get_user_id_key

logger = logging.getLogger(__name__)
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
    generate_questions_stream as gemini_generate_questions_stream,
    validate_quiz_prompt,
    GeminiError,
)

router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Request / Response schemas ───────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="Detailed description of the questions to generate")
    count: int = Field(5, ge=1, le=100, description="Number of questions to generate")
    language: str = Field("en", max_length=10, description="Language code, e.g. en, hi, fr")
    quiz_type: str = Field("quiz", max_length=20, description="Type of quiz: quiz, exam, poll, offline_poll")
    existing_questions: Optional[list[str]] = Field(None, description="Texts of already-existing questions to avoid duplicating")
    # Legacy field — ignored, kept for backward compatibility
    topic: Optional[str] = Field(None, description="Deprecated: use prompt instead")
    model: Optional[str] = Field(None, description="Ignored — Gemini model is used")


class GeneratedQuestion(BaseModel):
    text: str
    question_type: str = "mcq"
    options: Optional[list[str]] = None
    correct_answer_index: Optional[int] = None
    explanation: Optional[str] = None
    image_suggestion: Optional[str] = None


class GenerateQuestionsResponse(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    suggested_exam_duration_minutes: Optional[int] = None
    suggested_proctoring: Optional[bool] = None
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
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_generate_questions(
    request: Request,
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
        result = await gemini_generate_questions(
            prompt=prompt.strip(),
            count=req.count,
            language=req.language,
            quiz_type=req.quiz_type,
            existing_questions=req.existing_questions or None,
        )
    except GeminiError as e:
        logger.error("Gemini question generation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")

    questions = result.get("questions", [])
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid questions were generated — try refining your prompt",
        )

    return GenerateQuestionsResponse(
        title=result.get("title") or None,
        description=result.get("description") or None,
        suggested_exam_duration_minutes=result.get("suggested_exam_duration_minutes"),
        suggested_proctoring=result.get("suggested_proctoring"),
        questions=[GeneratedQuestion(**q) for q in questions],
        model=settings.gemini.model,
    )


@router.post("/generate/questions/stream")
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_generate_questions_stream(
    request: Request,
    req: GenerateQuestionsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Stream quiz questions as SSE events. Each event contains one question JSON.
    Final event: {"done": true, "title": "...", "description": "..."}.
    """
    prompt = req.prompt or req.topic or ""
    if not prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prompt is required")

    valid, reason = await validate_quiz_prompt(prompt.strip(), language=req.language)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "__PROMPT_NOT_FOR_QUIZ__",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for item in gemini_generate_questions_stream(
                prompt=prompt.strip(),
                count=req.count,
                language=req.language,
                quiz_type=req.quiz_type,
                existing_questions=req.existing_questions or None,
            ):
                yield f"data: {json.dumps(item)}\n\n"
        except GeminiError as e:
            logger.error("Gemini streaming failed: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/generate/options", response_model=GenerateDistractorsResponse)
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_generate_distractors(
    request: Request,
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
        logger.error("Ollama distractor generation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")

    return GenerateDistractorsResponse(distractors=distractors, model=model)


@router.post("/generate/poll-prompt", response_model=GeneratePollPromptResponse)
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_generate_poll_prompt(
    request: Request,
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
        logger.error("Ollama poll-prompt generation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")

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
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_rewrite(
    request: Request,
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
        logger.error("Ollama rewrite failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")
    return RewriteResponse(rewritten=rewritten, model=model)
