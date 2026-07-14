"""
AI generation endpoints — provider-agnostic via core.ai.router.
Which backend is used is determined by AI_PRIMARY_PROVIDER and AI_LIGHT_PROVIDER in .env.
Defaults: primary=gemini, light=ollama (unchanged from original behaviour).
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator

from core.auth.dependencies import require_admin, get_current_user, CurrentUser
from shared.utils.rate_limiter import limiter, get_user_id_key

logger = logging.getLogger(__name__)
from core.config.settings import settings
from core.ai.base import AIProviderError
from core.ai import router as ai_router

router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Request / Response schemas ───────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="Detailed description of the questions to generate")
    count: int = Field(5, ge=1, le=100, description="Number of questions to generate")
    language: str = Field("en", max_length=10, description="Language code, e.g. en, hi, fr")
    quiz_type: str = Field("quiz", max_length=20, description="Type of quiz: quiz, exam, poll, offline_poll")
    existing_questions: Optional[list[str]] = Field(None, description="Texts of already-existing questions to avoid duplicating")
    allowed_question_types: Optional[list[str]] = Field(None, description="Restrict generation to these question types; omit/None for the full default mix for quiz_type")
    # Legacy field — ignored, kept for backward compatibility
    topic: Optional[str] = Field(None, description="Deprecated: use prompt instead")
    model: Optional[str] = Field(None, description="Ignored — Gemini model is used")


class GeneratedQuestion(BaseModel):
    text: str
    question_type: str = "mcq"
    options: Optional[list[str]] = None
    correct_answer_index: Optional[int] = None
    correct_answer_indices: Optional[list[int]] = None
    explanation: Optional[str] = None
    image_suggestion: Optional[str] = None
    option_image_suggestions: Optional[list[str]] = None


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
    models = await ai_router.list_available_models()
    return ModelsResponse(models=models, default_model=settings.ai.light_provider)


@router.post("/generate/questions", response_model=GenerateQuestionsResponse)
@limiter.limit("20/minute", key_func=get_user_id_key)
async def api_generate_questions(
    request: Request,
    req: GenerateQuestionsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate quiz questions using the configured AI provider.
    Returns questions with 4 options each and the correct answer index.
    """
    # Support legacy callers that send topic instead of prompt
    prompt = req.prompt or req.topic or ""
    if not prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prompt is required")

    # Step 1: fast guard — check the prompt is appropriate for quiz generation
    valid, reason = await ai_router.validate_quiz_prompt(prompt.strip(), language=req.language)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "__PROMPT_NOT_FOR_QUIZ__",
        )

    # Step 2: generate questions
    try:
        result = await ai_router.generate_questions(
            prompt=prompt.strip(),
            count=req.count,
            language=req.language,
            quiz_type=req.quiz_type,
            existing_questions=req.existing_questions or None,
            allowed_question_types=req.allowed_question_types or None,
        )
    except AIProviderError as e:
        logger.error("AI question generation failed: %s", e)
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
        model=settings.ai.primary_provider,
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

    valid, reason = await ai_router.validate_quiz_prompt(prompt.strip(), language=req.language)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason or "__PROMPT_NOT_FOR_QUIZ__",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        # Run generation in a background task and send SSE keep-alive pings every 15 s
        # to prevent nginx proxy_read_timeout on long generations (10+ questions can take 60-120 s).
        task = asyncio.create_task(
            ai_router.generate_questions(
                prompt=prompt.strip(),
                count=req.count,
                language=req.language,
                quiz_type=req.quiz_type,
                existing_questions=req.existing_questions or None,
                allowed_question_types=req.allowed_question_types or None,
            )
        )
        try:
            while not task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # SSE comment — ignored by clients, resets nginx timeout
            result = await task
            for q in result["questions"]:
                yield f"data: {json.dumps(q)}\n\n"
            yield f"data: {json.dumps({'done': True, 'title': result.get('title'), 'description': result.get('description'), 'suggested_exam_duration_minutes': result.get('suggested_exam_duration_minutes'), 'suggested_proctoring': result.get('suggested_proctoring')})}\n\n"
        except AIProviderError as e:
            logger.error("AI streaming failed: %s", e)
            if not task.done():
                task.cancel()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("Unexpected AI stream error: %s", e)
            if not task.done():
                task.cancel()
            yield f"data: {json.dumps({'error': 'Generation failed. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


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
    try:
        distractors = await ai_router.generate_distractors(
            question=req.question,
            correct_answer=req.correct_answer,
            count=req.count,
        )
    except AIProviderError as e:
        logger.error("AI distractor generation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")

    return GenerateDistractorsResponse(distractors=distractors, model=settings.ai.light_provider)


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
    try:
        prompt = await ai_router.generate_poll_prompt(
            topic=req.topic,
            language=req.language,
        )
    except AIProviderError as e:
        logger.error("AI poll-prompt generation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")

    return GeneratePollPromptResponse(prompt=prompt, model=settings.ai.light_provider)


class ExtractTextResponse(BaseModel):
    text: str
    char_count: int
    source_label: str


_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/extract-text", response_model=ExtractTextResponse)
@limiter.limit("10/minute", key_func=get_user_id_key)
async def api_extract_text(
    request: Request,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Extract plain text from an uploaded PDF/DOCX/TXT file or a public URL.
    The returned text can be used as the prompt for /generate/questions/stream.
    Requires BASIC tier or above.
    """
    if current_user.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="upgrade_required",
        )

    if file is None and not url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide either a file or a url.")
    if file is not None and url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide either a file or a url, not both.")

    from core.ai.document_extractor import extract_from_file, extract_from_url

    if file is not None:
        # Enforce max file size before reading the whole body
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit.")
        data = await file.read()
        if len(data) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit.")
        # Put the data back so the extractor can read it
        import io
        file.file = io.BytesIO(data)
        await file.seek(0)
        text, source_label = await extract_from_file(file)
    else:
        text, source_label = await extract_from_url(url.strip())

    return ExtractTextResponse(text=text, char_count=len(text), source_label=source_label)


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
    try:
        rewritten = await ai_router.rewrite_text(
            text=req.text,
            context=req.context,
            language=req.language,
        )
    except AIProviderError as e:
        logger.error("AI rewrite failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service temporarily unavailable. Please try again.")
    return RewriteResponse(rewritten=rewritten, model=settings.ai.light_provider)
