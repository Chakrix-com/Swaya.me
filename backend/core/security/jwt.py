"""
JWT token creation and verification with Redis-backed revocation.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import jwt

from core.config.settings import settings
from shared.exceptions.auth import InvalidTokenError, ExpiredTokenError

_BLOCKLIST_PREFIX = "jwt:revoked:"


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt.expiration_hours)

    # jti allows individual token revocation
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4())})

    return jwt.encode(to_encode, settings.jwt.secret, algorithm=settings.jwt.algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt.secret, algorithms=[settings.jwt.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


async def revoke_token(token: str, redis) -> None:
    """Add token jti to Redis blocklist; expires when the token would have expired."""
    try:
        payload = decode_access_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti:
            return
        ttl = max(1, int(exp - datetime.utcnow().timestamp())) if exp else settings.jwt.expiration_hours * 3600
        await redis.set(_BLOCKLIST_PREFIX + jti, "1", expire=ttl)
    except (ExpiredTokenError, InvalidTokenError):
        pass  # already invalid — no need to blocklist


async def is_token_revoked(jti: str, redis) -> bool:
    """Return True if this jti has been revoked."""
    if not jti:
        return False
    val = await redis.get(_BLOCKLIST_PREFIX + jti)
    return val is not None
