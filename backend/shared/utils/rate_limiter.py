import base64
import json
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from core.config.settings import settings

# Initialize the limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis.url
)


def get_session_token_key(request: Request) -> str:
    """Rate-limit key based on the participant's session_token query param.

    Each participant receives a unique token on join, so this gives every
    participant their own independent rate-limit bucket regardless of how
    many people share the same public IP (e.g. a classroom on one WiFi).
    Falls back to client IP if no token is present.
    """
    return request.query_params.get("session_token") or get_remote_address(request)


def get_user_id_key(request: Request) -> str:
    """Rate-limit key based on the authenticated user's ID (from JWT sub claim).

    Decodes the JWT payload without signature verification — auth is still
    enforced by get_current_user. This gives every user their own independent
    bucket regardless of how many users share the same public IP (e.g. a school
    or office on one NAT). Falls back to IP if no valid Bearer token is present.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            segment = auth[7:].split(".")[1]
            # Restore base64 padding
            segment += "=" * (4 - len(segment) % 4)
            payload = json.loads(base64.b64decode(segment))
            uid = payload.get("sub")
            if uid:
                return f"user:{uid}"
        except Exception:
            pass
    return get_remote_address(request)
