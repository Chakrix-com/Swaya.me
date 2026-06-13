"""
Lightweight analytics beacon — fire-and-forget, never blocks a client request.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from persistence.models.quiz import PlatformEvent
from core.auth.dependencies import get_optional_user

router = APIRouter(prefix="/metrics", tags=["metrics"])


class EventBeacon(BaseModel):
    event_type: str
    session_id: Optional[int] = None
    quiz_id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


@router.post("/event", status_code=204)
async def record_event(
    payload: EventBeacon,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_optional_user),
):
    """Store a platform event beacon. Never raises — failures are silently swallowed."""
    try:
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
