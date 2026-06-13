"""
Proctoring API — participant and admin endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pathlib import Path
import shutil, os, json

from core.config.settings import settings
from persistence.database_async import get_async_db
from shared.utils.redis_client import redis_client, get_redis, RedisClient
from core.auth.dependencies import get_current_user, CurrentUser, require_super_admin
from persistence.models.core import UserRole
from persistence.models.quiz import Quiz, QuizType
from persistence.models.core import Tenant
from persistence.models.proctoring import PlatformProctoringRule, TenantProctoringPolicy

from features.proctoring.schemas import (
    SessionInitRequest, SessionInitResponse,
    ViolationEventRequest, ViolationEventResponse,
    BiometricSample, AnswerTimingRequest, AnswerTimingResponse,
    TenantPolicyUpdate, PlatformRuleUpdate,
)
from features.proctoring import proctoring_service_async as svc
from features.proctoring.context_resolver import ProctoringContext
from features.proctoring.honeypot_service import honeypot_service

router = APIRouter(prefix="/proctoring", tags=["proctoring"])


async def _resolve_context(quiz: Quiz, tenant: Tenant) -> ProctoringContext:
    policy = quiz.proctoring_policy or {}
    return ProctoringContext(
        quiz_id=quiz.id,
        tenant_id=quiz.tenant_id,
        quiz_type=quiz.quiz_type.value if hasattr(quiz.quiz_type, 'value') else str(quiz.quiz_type),
        tier=tenant.tier.value if hasattr(tenant.tier, 'value') else str(tenant.tier),
        host_enabled=policy.get("enabled", False),
    )


@router.post("/session/init", response_model=SessionInitResponse)
async def init_session(
    body: SessionInitRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — participant initializes proctoring session."""
    # Resolve quiz and participant from request
    # The participant session_token must be provided via X-Session-Token header or body
    session_token = request.headers.get("X-Session-Token", "")
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing session token")

    result = await db.execute(select(Quiz).where(Quiz.id == body.quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == quiz.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Resolve participant_id from session_token
    from persistence.models.quiz import Participant
    part_result = await db.execute(
        select(Participant).where(Participant.session_token == session_token)
    )
    participant = part_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    context = await _resolve_context(quiz, tenant)

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent", "")

    return await svc.init_session(
        participant_id=participant.id,
        quiz_id=body.quiz_id,
        tenant_id=quiz.tenant_id,
        context=context,
        quiz_proctoring_policy=quiz.proctoring_policy,
        browser_fingerprint=body.browser_fingerprint,
        ip_address=ip,
        user_agent=ua,
        webcam_granted=body.webcam_granted,
        session_token=session_token,
        db=db,
        redis=redis,
    )


@router.post("/session/webcam-granted")
async def mark_webcam_granted(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Public — called after participant grants webcam permission."""
    session_token = request.headers.get("X-Session-Token", "")
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    updated = await svc.update_webcam_granted(session_token=session_token, db=db)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/config/{quiz_id}")
async def get_config(
    quiz_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — get resolved rule set for a quiz."""
    session_token = request.headers.get("X-Session-Token", "")

    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == quiz.tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    context = await _resolve_context(quiz, tenant)
    rule_set = await svc.get_config(quiz_id, quiz.tenant_id, context, quiz.proctoring_policy, db, redis)

    # Include honeypot config if session_token present
    honeypot_config = None
    if session_token and rule_set.enabled:
        from persistence.models.quiz import Participant
        part_result = await db.execute(
            select(Participant).where(Participant.session_token == session_token)
        )
        participant = part_result.scalar_one_or_none()
        if participant:
            honeypot_rule = next((r for r in rule_set.rules if r.rule_id == "honeypot_traps"), None)
            if honeypot_rule:
                honeypot_config = await honeypot_service.generate(quiz_id, participant.id, "mcq", redis)

    return {**rule_set.model_dump(), "honeypot_config": honeypot_config}


@router.post("/event", response_model=ViolationEventResponse)
async def log_event(
    body: ViolationEventRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — log a proctoring violation event."""
    return await svc.log_violation(
        body.session_token, body.rule_id, body.event_type, body.metadata, db, redis
    )


@router.api_route("/honeypot", methods=["GET", "POST"])
async def honeypot_endpoint(
    request: Request,
    trap: Optional[str] = Query(None),
    t: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — silent honeypot; always returns 200."""
    try:
        session_token = request.headers.get("X-Session-Token", "")
        if session_token and trap:
            await honeypot_service.validate_hit(session_token, trap, db, redis)
    except Exception:
        pass
    return JSONResponse(content={})


@router.post("/answer-timing", response_model=AnswerTimingResponse)
async def answer_timing(
    body: AnswerTimingRequest,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — validate that participant spent enough time on answer."""
    redis_data = None
    try:
        raw = await redis.get(f"proctor:session:{body.session_token}")
        if raw:
            redis_data = json.loads(raw)
    except Exception:
        pass

    if not redis_data:
        return AnswerTimingResponse(accepted=True)

    # Find answer_timing_enforce rule config
    rule_set_data = None
    try:
        from persistence.models.quiz import Participant
        part_result = await db.execute(
            select(Participant).where(Participant.session_token == body.session_token)
        )
        participant = part_result.scalar_one_or_none()
        if participant:
            from persistence.models.proctoring import ProctoringSession
            sess_result = await db.execute(
                select(ProctoringSession).where(
                    ProctoringSession.participant_id == participant.id
                ).order_by(ProctoringSession.id.desc())
            )
            sess = sess_result.scalar_one_or_none()
            if sess:
                rule_set_data = sess.active_rule_set
    except Exception:
        pass

    min_ms_per_word = 150
    if rule_set_data:
        rules = rule_set_data.get("rules", [])
        for r in rules:
            if r.get("rule_id") == "answer_timing_enforce":
                min_ms_per_word = r.get("config", {}).get("min_ms_per_word", 150)
                break

    min_ms = body.question_word_count * min_ms_per_word
    if body.elapsed_ms < min_ms:
        await svc.log_violation(
            body.session_token, "answer_timing_enforce", "ANSWER_TOO_FAST",
            {"elapsed_ms": body.elapsed_ms, "min_ms": min_ms}, db, redis
        )
        wait_ms = min_ms - body.elapsed_ms
        return AnswerTimingResponse(accepted=False, reason="Answer submitted too quickly", wait_ms=wait_ms)

    return AnswerTimingResponse(accepted=True)


@router.post("/biometrics")
async def ingest_biometrics(
    body: BiometricSample,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — receive behavioral biometric batch."""
    is_locked = await svc.ingest_biometric_sample(body.session_token, body, db, redis)
    return {"ok": True, "is_locked": is_locked}


@router.post("/snapshot")
async def upload_snapshot(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Public — participant webcam snapshot upload (session token via header)."""
    session_token = request.headers.get("X-Session-Token", "")
    redis_data = None
    if session_token:
        try:
            raw = await redis.get(f"proctor:session:{session_token}")
            if raw:
                redis_data = json.loads(raw)
        except Exception:
            pass

    quiz_id = redis_data.get("quiz_id", 0) if redis_data else 0
    participant_id = redis_data.get("participant_id", 0) if redis_data else 0

    # DB fallback: when Redis has no session data, resolve IDs from the participants table
    if (not quiz_id or not participant_id) and session_token:
        try:
            from persistence.models.quiz import Participant, QuizSession
            part_result = await db.execute(
                select(Participant).where(Participant.session_token == session_token)
            )
            participant_row = part_result.scalar_one_or_none()
            if participant_row:
                participant_id = participant_row.id
                sess_result = await db.execute(
                    select(QuizSession).where(QuizSession.id == participant_row.session_id)
                )
                quiz_session = sess_result.scalar_one_or_none()
                if quiz_session:
                    quiz_id = quiz_session.quiz_id
        except Exception:
            pass

    # Reject uploads with no resolvable participant — prevents writing to 0/0/
    if not quiz_id or not participant_id:
        return {"ok": False}

    uploads_base = Path(settings.app.uploads_base_dir)
    snap_dir = uploads_base / "proctoring" / str(quiz_id) / str(participant_id)
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Strip all path components from the filename to prevent path traversal
    raw_name = Path(file.filename or "").name or f"snap_{__import__('time').time_ns()}.jpg"
    # Keep only alphanumerics, dots, hyphens, underscores
    import re as _re
    safe_name = _re.sub(r"[^\w.\-]", "_", raw_name)
    dest = snap_dir / safe_name

    # Confirm resolved path stays inside snap_dir
    try:
        dest.resolve().relative_to(snap_dir.resolve())
    except ValueError:
        return {"ok": False}

    try:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # Increment server-side receipt counter
        if session_token:
            await svc.record_snapshot_receipt(session_token, redis)
    except Exception:
        pass

    return {"ok": True}


@router.get("/report/{quiz_id}")
async def get_report(
    quiz_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Admin — get violation report for a quiz."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return await svc.get_violation_report(quiz_id, current_user.tenant_id, db)


@router.get("/snapshots/{quiz_id}/{participant_id}")
async def list_snapshots(
    quiz_id: int,
    participant_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Admin — list webcam snapshot URLs for a participant."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz or quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    snap_dir = Path(settings.app.uploads_base_dir) / "proctoring" / str(quiz_id) / str(participant_id)
    if not snap_dir.exists():
        return {"snapshots": []}

    snapshots = []
    for f in sorted(snap_dir.glob("*.jpg")):
        try:
            ts_ms = int(f.stem.split("_")[1])
        except (IndexError, ValueError):
            ts_ms = 0
        snapshots.append({
            "url": f"/api/uploads/proctoring/{quiz_id}/{participant_id}/{f.name}",
            "filename": f.name,
            "timestamp_ms": ts_ms,
        })

    return {"snapshots": snapshots}


@router.post("/lock/{session_token}")
async def lock_session(
    session_token: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Admin — manually lock a participant session."""
    await svc.lock_session(session_token, "ADMIN_LOCK", db, redis)
    await db.commit()
    return {"ok": True}


@router.post("/unlock/{session_token}")
async def unlock_session(
    session_token: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis)
):
    """Admin — unlock a participant session."""
    await svc.unlock_session(session_token, db, redis)
    return {"ok": True}


@router.get("/rules")
async def get_rules_for_user(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Auth — list platform rules available to the current tenant's tier."""
    from features.proctoring.context_resolver import TIER_ORDER
    tenant_tier = current_user.tier
    result = await db.execute(
        select(PlatformProctoringRule).where(PlatformProctoringRule.is_active == True)
    )
    rules = result.scalars().all()
    return [
        {
            "rule_id": r.rule_id,
            "display_name": r.display_name,
            "description": r.description,
            "tier_minimum": r.tier_minimum,
            "severity": r.severity,
            "is_silent": r.is_silent,
            "is_active": r.is_active,
            "default_config": r.default_config,
            "applies_to": r.applies_to,
        }
        for r in rules
        if TIER_ORDER.get(tenant_tier, 0) >= TIER_ORDER.get(r.tier_minimum, 0)
    ]


@router.get("/admin/rules")
async def get_platform_rules(
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Super admin — list all platform rules."""
    result = await db.execute(select(PlatformProctoringRule))
    rules = result.scalars().all()
    return [
        {
            "rule_id": r.rule_id,
            "display_name": r.display_name,
            "description": r.description,
            "tier_minimum": r.tier_minimum,
            "severity": r.severity,
            "is_silent": r.is_silent,
            "is_active": r.is_active,
            "default_config": r.default_config,
            "applies_to": r.applies_to,
        }
        for r in rules
    ]


@router.put("/admin/rules/{rule_id}")
async def update_platform_rule(
    rule_id: str,
    body: PlatformRuleUpdate,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Super admin — update a platform rule."""
    result = await db.execute(
        select(PlatformProctoringRule).where(PlatformProctoringRule.rule_id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.tier_minimum is not None:
        rule.tier_minimum = body.tier_minimum
    if body.default_config is not None:
        rule.default_config = body.default_config
    if body.severity is not None:
        rule.severity = body.severity

    await db.commit()
    return {"ok": True}


@router.get("/admin/tenant-policy/{tenant_id}")
async def get_tenant_policy(
    tenant_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Admin — get tenant proctoring policies. Tenant admins can only view their own tenant."""
    if current_user.user.role not in (UserRole.super_admin, UserRole.admin):
        raise HTTPException(status_code=403, detail="Admin access required")
    if current_user.user.role == UserRole.admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(TenantProctoringPolicy).where(TenantProctoringPolicy.tenant_id == tenant_id)
    )
    policies = result.scalars().all()
    return [
        {
            "rule_id": p.rule_id,
            "is_enabled": p.is_enabled,
            "enabled_for": p.enabled_for,
            "config_override": p.config_override,
        }
        for p in policies
    ]


@router.put("/admin/tenant-policy/{tenant_id}")
async def update_tenant_policy(
    tenant_id: int,
    body: TenantPolicyUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Admin — upsert a tenant proctoring policy. Tenant admins can only modify their own tenant."""
    if current_user.user.role not in (UserRole.super_admin, UserRole.admin):
        raise HTTPException(status_code=403, detail="Admin access required")
    if current_user.user.role == UserRole.admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    from datetime import datetime, timezone

    result = await db.execute(
        select(TenantProctoringPolicy).where(
            TenantProctoringPolicy.tenant_id == tenant_id,
            TenantProctoringPolicy.rule_id == body.rule_id,
        )
    )
    policy = result.scalar_one_or_none()

    if policy is None:
        policy = TenantProctoringPolicy(
            tenant_id=tenant_id,
            rule_id=body.rule_id,
            enabled_for=body.enabled_for,
            is_enabled=body.is_enabled,
            config_override=body.config_override,
            updated_at=datetime.now(timezone.utc),
            updated_by=current_user.user_id,
        )
        db.add(policy)
    else:
        policy.is_enabled = body.is_enabled
        policy.enabled_for = body.enabled_for
        policy.config_override = body.config_override
        policy.updated_at = datetime.now(timezone.utc)
        policy.updated_by = current_user.user_id

    await db.commit()
    return {"ok": True}
