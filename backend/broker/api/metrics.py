"""
Lightweight analytics beacon — fire-and-forget, never blocks a client request.
"""
import json
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from persistence.models.quiz import PlatformEvent
from core.auth.dependencies import get_optional_user
from shared.utils.rate_limiter import limiter

router = APIRouter(prefix="/metrics", tags=["metrics"])

_ALLOWED_EVENT_TYPES = frozenset({
    "page_view", "quiz_start", "quiz_join", "quiz_leave", "quiz_submit",
    "session_start", "session_end", "question_view", "answer_submit",
    "exam_start", "exam_submit", "exam_abandon",
    "feature_use", "error",
})


class EventBeacon(BaseModel):
    event_type: str = Field(..., max_length=64)
    session_id: Optional[int] = None
    quiz_id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None

    @field_validator("properties")
    @classmethod
    def cap_properties_size(cls, v):
        if v is not None and len(json.dumps(v)) > 2048:
            raise ValueError("properties payload too large")
        return v


@router.post("/event", status_code=204)
@limiter.limit("120/minute")
async def record_event(
    request: Request,
    payload: EventBeacon,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_optional_user),
):
    """Store a platform event beacon. Never raises — failures are silently swallowed."""
    try:
        if payload.event_type not in _ALLOWED_EVENT_TYPES:
            return  # silently drop unknown event types
        tenant_id = current_user.tenant_id if current_user else None
        user_id = current_user.user_id if current_user else None
        event = PlatformEvent(
            event_type=payload.event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=payload.session_id,
            quiz_id=payload.quiz_id,
            properties=payload.properties,
        )
        db.add(event)
        await db.commit()
    except Exception:
        pass  # beacon failures must never surface to the client
