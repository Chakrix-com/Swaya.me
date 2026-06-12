"""
Server-Sent Events endpoint for real-time session state.

Channel: session:{session_id}:events
Subscribers: participants (via session_token) and hosts (via JWT).
Events mirror the audience_state cache format so the frontend can
drop-in-replace its existing polling payloads.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from shared.utils.redis_client import get_redis, RedisClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quizzes", tags=["session-events"])

_HEARTBEAT_INTERVAL = 15   # seconds between keep-alive comments
_MAX_STREAM_SECONDS = 3600  # hard cap per connection


async def _stream_session_events(
    session_id: int,
    redis: RedisClient,
    request: Request,
):
    """Async generator yielding SSE-formatted bytes."""
    pubsub = redis.pubsub()
    channel = f"session:{session_id}:events"
    await pubsub.subscribe(channel)
    deadline = asyncio.get_event_loop().time() + _MAX_STREAM_SECONDS

    try:
        # Send the current cached state immediately so the client doesn't
        # have to wait for the next publish to see any data.
        cached = await redis.get_json(f"session:{session_id}:audience_state")
        if cached:
            yield f"data: {json.dumps({'type': 'state', 'data': cached})}\n\n".encode()

        while True:
            if await request.is_disconnected():
                break
            if asyncio.get_event_loop().time() > deadline:
                break

            # Non-blocking poll with a short sleep so we can check disconnect
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=_HEARTBEAT_INTERVAL)
            if message and message["type"] == "message":
                yield f"data: {message['data']}\n\n".encode()
            else:
                # Keep-alive heartbeat — SSE comment, ignored by clients
                yield b": ka\n\n"
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("SSE stream error session=%s: %s", session_id, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass


@router.get(
    "/sessions/{session_id}/events",
    summary="SSE stream for live session state",
    response_class=StreamingResponse,
)
async def session_events(
    session_id: int,
    request: Request,
    session_token: str = Query(default=""),
    redis: RedisClient = Depends(get_redis),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Server-Sent Events stream for a quiz session.

    Authentication: either a valid participant session_token OR a valid
    host JWT in the Authorization header. Unauthenticated requests are
    rejected.
    """
    # Auth: accept participant session_token or host JWT
    authed = False

    if session_token:
        cached = await redis.get_json(f"session_token:{session_token}")
        if cached and cached.get("session_id") == session_id and cached.get("is_active", True):
            authed = True
        else:
            # DB fallback
            from sqlalchemy import select as _select
            from persistence.models.quiz import Participant
            row = (await db.execute(
                _select(Participant.session_id, Participant.is_active)
                .where(Participant.session_token == session_token)
            )).one_or_none()
            if row and row.session_id == session_id and row.is_active:
                authed = True

    if not authed:
        # Try host JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from core.security.jwt import decode_access_token
                payload = decode_access_token(token)
                if payload:
                    authed = True
            except Exception:
                pass

    if not authed:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return StreamingResponse(
        _stream_session_events(session_id, redis, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
