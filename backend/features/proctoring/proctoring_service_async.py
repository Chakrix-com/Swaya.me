"""
Proctoring service — session management and violation tracking.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.config.settings import settings

from persistence.models.proctoring import ProctoringSession, ProctoringEvent
from features.proctoring.schemas import (
    ProctoringContext, SessionInitResponse, ViolationEventResponse, ResolvedRuleSet,
)
from features.proctoring.context_resolver import ProctoringContextResolver

_resolver = ProctoringContextResolver()

REDIS_SESSION_TTL = 86400  # 24 hours


def _session_key(token: str) -> str:
    return f"proctor:session:{token}"


async def _get_redis_session(redis: "RedisClient", token: str) -> dict | None:
    try:
        raw = await redis.get(_session_key(token))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _set_redis_session(redis: "RedisClient", token: str, data: dict) -> None:
    try:
        await redis.set_json(_session_key(token), data, expire=REDIS_SESSION_TTL)
    except Exception:
        pass


async def init_session(
    participant_id: int,
    quiz_id: int,
    tenant_id: int,
    context: ProctoringContext,
    quiz_proctoring_policy: dict | None,
    browser_fingerprint: str,
    ip_address: str,
    user_agent: str,
    webcam_granted: bool,
    session_token: str,
    db: AsyncSession,
    redis: "RedisClient",
) -> SessionInitResponse:
    rule_set = await _resolver.resolve(context, quiz_proctoring_policy, db, redis)
    lock_threshold = rule_set.escalation.get("lock_on_violation_count", 3)

    # Idempotent — return existing session if already created
    existing = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.participant_id == participant_id,
            ProctoringSession.quiz_id == quiz_id,
        )
    )
    sess = existing.scalar_one_or_none()

    if sess is None:
        sess = ProctoringSession(
            participant_id=participant_id,
            quiz_id=quiz_id,
            tenant_id=tenant_id,
            active_rule_set=rule_set.model_dump(),
            violation_count=0,
            integrity_score=100,
            is_locked=False,
            browser_fingerprint=browser_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            webcam_required=rule_set.webcam_required,
            webcam_granted=webcam_granted,
            session_started_at=datetime.now(timezone.utc),
        )
        db.add(sess)
        await db.commit()

    redis_data = {
        "violation_count": sess.violation_count,
        "is_locked": sess.is_locked,
        "fingerprint": browser_fingerprint,
        "ip": ip_address,
        "integrity_score": sess.integrity_score,
        "lock_threshold": lock_threshold,
        "quiz_id": quiz_id,
        "tenant_id": tenant_id,
        "participant_id": participant_id,
    }
    await _set_redis_session(redis, session_token, redis_data)

    return SessionInitResponse(session_token=session_token, rule_set=rule_set)


async def update_webcam_granted(session_token: str, db: AsyncSession) -> bool:
    from persistence.models.quiz import Participant
    part_res = await db.execute(select(Participant).where(Participant.session_token == session_token))
    participant = part_res.scalar_one_or_none()
    if not participant:
        return False
    sess_res = await db.execute(
        select(ProctoringSession).where(ProctoringSession.participant_id == participant.id)
    )
    sess = sess_res.scalar_one_or_none()
    if not sess:
        return False
    sess.webcam_granted = True
    await db.commit()
    return True


async def record_snapshot_receipt(session_token: str, redis: "RedisClient") -> None:
    """Increment the received snapshot counter for this session."""
    key = f"proctor:snapshots:{session_token}"
    await redis.increment(key)
    await redis.expire(key, REDIS_SESSION_TTL)


async def get_snapshot_count(session_token: str, redis: "RedisClient") -> int:
    """Return the number of snapshots received for this session."""
    key = f"proctor:snapshots:{session_token}"
    val = await redis.get(key)
    return int(val) if val else 0


async def get_config(
    quiz_id: int,
    tenant_id: int,
    context: ProctoringContext,
    quiz_proctoring_policy: dict | None,
    db: AsyncSession,
    redis: "RedisClient",
) -> ResolvedRuleSet:
    return await _resolver.resolve(context, quiz_proctoring_policy, db, redis)


async def log_violation(
    session_token: str,
    rule_id: str,
    event_type: str,
    metadata: dict,
    db: AsyncSession,
    redis: "RedisClient",
) -> ViolationEventResponse:
    redis_data = await _get_redis_session(redis, session_token)
    if not redis_data:
        # Session not found — look up in DB
        return ViolationEventResponse(logged=False, is_locked=False, violations_remaining=None, silent=False)

    if redis_data.get("is_locked"):
        return ViolationEventResponse(logged=True, is_locked=True, violations_remaining=0, silent=True)

    # Write event to DB
    event = ProctoringEvent(
        quiz_id=redis_data["quiz_id"],
        tenant_id=redis_data["tenant_id"],
        participant_id=redis_data["participant_id"],
        session_token=session_token,
        rule_id=rule_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        event_metadata=metadata,
    )
    db.add(event)

    # Escalation
    result = await _check_escalation(session_token, redis_data, rule_id, event_type, db, redis)
    await db.commit()

    return result


async def _check_escalation(
    session_token: str,
    redis_data: dict,
    rule_id: str,
    event_type: str,
    db: AsyncSession,
    redis,
) -> ViolationEventResponse:
    lock_events = {
        "MULTI_TAB_DETECTED", "BOT_SIGNAL_DETECTED",
        "FINGERPRINT_MISMATCH", "IP_MISMATCH",
        "HONEYPOT_OPTION_CLICKED", "HONEYPOT_FIELD_FILLED",
        "HONEYPOT_INSTRUCTION_FOLLOWED", "HONEYPOT_ENDPOINT_HIT",
        "WEBCAM_STREAM_ENDED",
    }

    # Immediate lock events
    if event_type in lock_events:
        await lock_session(session_token, event_type, db, redis, redis_data=redis_data)
        return ViolationEventResponse(logged=True, is_locked=True, violations_remaining=0, silent=True)

    lock_threshold = redis_data.get("lock_threshold", 3)
    new_count = redis_data.get("violation_count", 0) + 1
    redis_data["violation_count"] = new_count
    await _set_redis_session(redis, session_token, redis_data)

    # Update DB violation count
    result = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.participant_id == redis_data["participant_id"],
            ProctoringSession.quiz_id == redis_data["quiz_id"],
        )
    )
    sess = result.scalar_one_or_none()
    if sess:
        sess.violation_count = new_count

    if new_count >= lock_threshold:
        await lock_session(session_token, "MAX_VIOLATIONS_REACHED", db, redis, redis_data=redis_data)
        return ViolationEventResponse(logged=True, is_locked=True, violations_remaining=0, silent=False)

    remaining = lock_threshold - new_count
    return ViolationEventResponse(
        logged=True,
        is_locked=False,
        violations_remaining=remaining,
        silent=False,
    )


async def lock_session(
    session_token: str,
    reason: str,
    db: AsyncSession,
    redis: "RedisClient",
    redis_data: dict | None = None,
) -> None:
    if redis_data is None:
        redis_data = await _get_redis_session(redis, session_token)
    if redis_data is None:
        return

    redis_data["is_locked"] = True
    await _set_redis_session(redis, session_token, redis_data)

    result = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.participant_id == redis_data["participant_id"],
            ProctoringSession.quiz_id == redis_data["quiz_id"],
        )
    )
    sess = result.scalar_one_or_none()
    if sess:
        sess.is_locked = True
        sess.locked_at = datetime.now(timezone.utc)
        sess.lock_reason = reason[:100]

    lock_event = ProctoringEvent(
        quiz_id=redis_data["quiz_id"],
        tenant_id=redis_data["tenant_id"],
        participant_id=redis_data["participant_id"],
        session_token=session_token,
        rule_id=None,
        event_type="SESSION_LOCKED",
        occurred_at=datetime.now(timezone.utc),
        event_metadata={"reason": reason},
    )
    db.add(lock_event)


async def unlock_session(
    session_token: str,
    db: AsyncSession,
    redis: "RedisClient",
) -> None:
    redis_data = await _get_redis_session(redis, session_token)
    if redis_data is None:
        return

    redis_data["is_locked"] = False
    redis_data["violation_count"] = 0
    await _set_redis_session(redis, session_token, redis_data)

    result = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.participant_id == redis_data["participant_id"],
            ProctoringSession.quiz_id == redis_data["quiz_id"],
        )
    )
    sess = result.scalar_one_or_none()
    if sess:
        sess.is_locked = False
        sess.violation_count = 0

    unlock_event = ProctoringEvent(
        quiz_id=redis_data["quiz_id"],
        tenant_id=redis_data["tenant_id"],
        participant_id=redis_data["participant_id"],
        session_token=session_token,
        rule_id=None,
        event_type="SESSION_UNLOCKED_BY_ADMIN",
        occurred_at=datetime.now(timezone.utc),
        event_metadata={},
    )
    db.add(unlock_event)
    await db.commit()


async def check_integrity(
    session_token: str,
    fingerprint: str,
    ip: str,
    db: AsyncSession,
    redis: "RedisClient",
) -> dict:
    redis_data = await _get_redis_session(redis, session_token)
    if not redis_data:
        return {"ok": False}

    issues = []
    if redis_data.get("fingerprint") and redis_data["fingerprint"] != fingerprint:
        await log_violation(session_token, "browser_fingerprint_bind", "FINGERPRINT_MISMATCH", {}, db, redis)
        issues.append("fingerprint_mismatch")

    if redis_data.get("ip") and redis_data["ip"] != ip:
        await log_violation(session_token, "ip_bind", "IP_MISMATCH", {"stored": redis_data["ip"], "current": ip}, db, redis)
        issues.append("ip_mismatch")

    return {"ok": len(issues) == 0, "issues": issues}


def _has_snapshots(quiz_id: int, participant_id: int) -> bool:
    snap_dir = Path(settings.app.uploads_base_dir) / "proctoring" / str(quiz_id) / str(participant_id)
    return snap_dir.is_dir() and any(snap_dir.glob("*.jpg"))


async def get_violation_report(quiz_id: int, tenant_id: int, db: AsyncSession) -> list[dict]:
    from persistence.models.quiz import Quiz, QuizSession, Participant

    # Fetch proctoring sessions (may be empty if session/init was never called)
    sessions_result = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.quiz_id == quiz_id,
            ProctoringSession.tenant_id == tenant_id,
        )
    )
    sessions = sessions_result.scalars().all()
    session_by_participant = {s.participant_id: s for s in sessions}

    # Fall back to all completed exam participants when no proctoring sessions exist
    quiz_result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = quiz_result.scalar_one_or_none()
    webcam_required = False
    if quiz and quiz.proctoring_policy:
        policy = quiz.proctoring_policy
        rules = policy.get("rules", {})
        # rules may be a dict {rule_id: config} or a list [{rule_id, ...}]
        if isinstance(rules, dict):
            wc = rules.get("webcam_monitoring", {})
            webcam_required = policy.get("enabled", False) and wc.get("enabled", False)
        else:
            webcam_required = policy.get("enabled", False) and any(
                r.get("rule_id") == "webcam_monitoring" for r in rules
            )

    participant_ids_from_sessions = set(session_by_participant.keys())
    extra_participant_ids: set[int] = set()

    if quiz and quiz.exam_session_id:
        qs_result = await db.execute(
            select(QuizSession).where(
                QuizSession.quiz_id == quiz_id,
                QuizSession.id == quiz.exam_session_id,
            )
        )
        quiz_sessions = qs_result.scalars().all()
        for qs in quiz_sessions:
            p_result = await db.execute(
                select(Participant).where(
                    Participant.session_id == qs.id,
                    Participant.completed_at.isnot(None),
                )
            )
            for p in p_result.scalars().all():
                if p.id not in participant_ids_from_sessions:
                    extra_participant_ids.add(p.id)

    all_participant_ids = list(participant_ids_from_sessions) + list(extra_participant_ids)

    # Load all participant rows so we can include name + email in the report
    all_participants_result = await db.execute(
        select(Participant).where(Participant.id.in_(all_participant_ids))
    )
    participant_by_id = {p.id: p for p in all_participants_result.scalars().all()}

    report = []
    for pid in all_participant_ids:
        sess = session_by_participant.get(pid)
        participant = participant_by_id.get(pid)

        events_result = await db.execute(
            select(ProctoringEvent).where(
                ProctoringEvent.participant_id == pid,
                ProctoringEvent.quiz_id == quiz_id,
            ).order_by(ProctoringEvent.occurred_at)
        )
        events = events_result.scalars().all()

        report.append({
            "participant_id": pid,
            "display_name": participant.display_name if participant else None,
            "email": participant.email if participant else None,
            "integrity_score": sess.integrity_score if sess else 100,
            "violation_count": sess.violation_count if sess else len(events),
            "is_locked": sess.is_locked if sess else False,
            "lock_reason": sess.lock_reason if sess else None,
            "webcam_required": sess.webcam_required if sess else webcam_required,
            "webcam_granted": sess.webcam_granted if sess else _has_snapshots(quiz_id, pid),
            "session_started_at": sess.session_started_at.isoformat() if sess and sess.session_started_at else None,
            "events": [
                {
                    "event_type": e.event_type,
                    "rule_id": e.rule_id,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "metadata": e.event_metadata,
                }
                for e in events
            ],
        })

    return report


async def ingest_biometric_sample(
    session_token: str,
    sample,
    db: AsyncSession,
    redis: "RedisClient",
) -> bool:
    """Returns True if the session was locked as a result of this sample."""
    from features.proctoring.integrity_scorer import IntegrityScorer

    redis_data = await _get_redis_session(redis, session_token)
    if not redis_data:
        return False
    if redis_data.get("is_locked"):
        return True

    current_score = redis_data.get("integrity_score", 100)
    new_score = IntegrityScorer().score(sample, current_score)
    redis_data["integrity_score"] = new_score
    await _set_redis_session(redis, session_token, redis_data)

    result = await db.execute(
        select(ProctoringSession).where(
            ProctoringSession.participant_id == redis_data["participant_id"],
            ProctoringSession.quiz_id == redis_data["quiz_id"],
        )
    )
    sess = result.scalar_one_or_none()
    if sess:
        sess.integrity_score = new_score

    locked = False
    if new_score < 40:
        violation_result = await log_violation(session_token, "behavioral_biometrics", "LOW_INTEGRITY_SCORE",
                            {"score": new_score}, db, redis)
        locked = violation_result.is_locked

    await db.commit()
    return locked
