"""
Authentication dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from persistence.database_async import get_async_db
from persistence.models.core import User, Tenant
from core.security.jwt import decode_access_token, is_token_revoked
from shared.exceptions.auth import InvalidTokenError, ExpiredTokenError
from shared.utils.redis_client import get_redis, RedisClient

# auto_error=False so we can fall back to the HttpOnly cookie
security = HTTPBearer(auto_error=False)
security_optional = HTTPBearer(auto_error=False)


class CurrentUser:
    """Current authenticated user context"""

    def __init__(self, user: User, tenant: Tenant):
        self.user = user
        self.tenant = tenant
        self.user_id = user.id
        self.tenant_id = tenant.id
        self.email = user.email
        self.tier = tenant.tier.value


async def _resolve_token(token: str, db: AsyncSession, redis: RedisClient) -> "CurrentUser":
    """Validate a JWT string and return CurrentUser."""
    payload = decode_access_token(token)
    user_id: int = int(payload.get("sub"))
    tenant_id: int = payload.get("tenant_id")
    jti: str = payload.get("jti", "")

    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    if await is_token_revoked(jti, redis):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found or inactive")

    if user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")

    return CurrentUser(user=user, tenant=tenant)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
    # Prefer HttpOnly cookie (XSS-safe); fall back to Bearer for non-browser clients
    token = access_token or (credentials.credentials if credentials else None)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        return await _resolve_token(token, db, redis)
    except ExpiredTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[CurrentUser]:
    token = access_token or (credentials.credentials if credentials else None)
    if not token:
        return None
    try:
        return await _resolve_token(token, db, redis)
    except (HTTPException, ExpiredTokenError, InvalidTokenError):
        return None


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require admin or super_admin role."""
    from persistence.models.core import UserRole
    if current_user.user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_super_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    from persistence.models.core import UserRole
    if current_user.user.role != UserRole.super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user
