"""
Authentication API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from shared.utils.rate_limiter import limiter
from core.config.settings import settings

logger = logging.getLogger(__name__)

from persistence.database_async import get_async_db
from core.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from core.auth.service_async import register_user, login_user
from core.auth.dependencies import get_current_user
from core.security.jwt import revoke_token
from shared.utils.redis_client import get_redis, RedisClient
from core.auth.email_service import send_welcome_email
from shared.exceptions.auth import (
    InvalidCredentialsError,
    DuplicateUserError,
    TenantNotFoundError,
    EmailNotVerifiedError
)

_COOKIE_MAX_AGE = 86400  # 24 hours, matches JWT expiry


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the JWT as an HttpOnly, Secure, SameSite=Strict cookie."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie("access_token", path="/", samesite="lax", secure=True)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    response: Response,
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register new user and create tenant

    - Creates new tenant account (Free tier by default)
    - Creates user associated with tenant
    - Returns JWT access token (also set as HttpOnly cookie)
    """
    try:
        result = await register_user(db, body)
        # Only set the cookie when the user is immediately logged in (verified accounts)
        if result.access_token and result.access_token != "pending_verification":
            _set_auth_cookie(response, result.access_token)
        return result
    except DuplicateUserError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try a different email address."
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: settings.app.login_rate_limit)
async def login(
    request: Request,
    response: Response,
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticate user and get access token

    - Validates credentials
    - Sets JWT as HttpOnly cookie; also returns it in the response body
    """
    try:
        result = await login_user(db, body)
        _set_auth_cookie(response, result.access_token)
        return result
    except (InvalidCredentialsError, TenantNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except EmailNotVerifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return UserResponse(
        id=current_user.user.id,
        email=current_user.user.email,
        full_name=current_user.user.full_name,
        tenant_id=current_user.tenant.id,
        tenant_name=current_user.tenant.name,
        tier=current_user.tenant.tier.value,
        is_active=current_user.user.is_active,
        role=current_user.user.role.value
    )


_bearer_optional = HTTPBearer(auto_error=False)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    redis: RedisClient = Depends(get_redis),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
    access_token: Optional[str] = Cookie(default=None),
):
    """
    Invalidate the current JWT by adding its jti to the Redis blocklist.
    Accepts the token from the HttpOnly cookie or Authorization header.
    """
    token = access_token or (credentials.credentials if credentials else None)
    if token:
        await revoke_token(token, redis)
    _clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


from pydantic import BaseModel
from sqlalchemy import select
from persistence.models.core import User

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Verify a user's email address using their verification token
    """
    stmt = select(User).where(User.email_verification_token == request.token)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
        
    if user.is_email_verified:
        return {"message": "Email already verified"}
        
    user.is_email_verified = True
    user.email_verification_token = None
    
    # Enable login tracking now that they're verified
    user.login_count = 1
    from datetime import datetime, timezone
    user.last_login_at = datetime.now(timezone.utc)
    
    await db.commit()

    try:
        await send_welcome_email(user.email, user.full_name)
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")

    return {"message": "Email verified successfully"}


from core.config.tier_service import TierService
from shared.utils.redis_client import get_redis, RedisClient
from persistence.models.core import TierEnum

@router.get("/my-limits")
async def get_my_limits(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    """Return the tier limits for the currently authenticated user's tenant."""
    tier_service = TierService(redis)
    tier_value = current_user.tenant.tier.value
    try:
        tier_enum = TierEnum(tier_value)
    except ValueError:
        tier_enum = TierEnum.FREE
    config = await tier_service.get_tier_config(db, tier_enum)
    return {
        "tier": tier_value,
        "max_participants": config.get("max_participants"),
        "max_questions": config.get("max_questions"),
        "max_concurrent_events": config.get("max_concurrent_events"),
    }


@router.get("/tier-plans")
async def get_tier_plans(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    """Return limits for all tiers — used by the upgrade banner. Accessible to any authenticated user."""
    tier_service = TierService(redis)
    plans = []
    for tier_enum in TierEnum:
        config = await tier_service.get_tier_config(db, tier_enum)
        plans.append({
            "tier": tier_enum.value,
            "max_participants": config.get("max_participants"),
            "max_questions": config.get("max_questions"),
            "max_concurrent_events": config.get("max_concurrent_events"),
        })
    return plans


import secrets as _secrets
from urllib.parse import urlencode
from fastapi import Request
from fastapi.responses import RedirectResponse as FastAPIRedirect
import httpx
from core.config.settings import settings
from core.auth.service_async import oauth_login_or_register

_OAUTH_STATE_TTL = 600  # 10 minutes


@router.get("/google/login")
async def google_login(redis: RedisClient = Depends(get_redis)):
    """Redirect browser to Google's OAuth consent screen."""
    if not settings.google.client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = _secrets.token_urlsafe(32)
    await redis.set(f"oauth_state:{state}", "1", expire=_OAUTH_STATE_TTL)
    params = {
        "client_id": settings.google.client_id,
        "redirect_uri": f"{settings.app.frontend_url}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return FastAPIRedirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    redis: RedisClient = Depends(get_redis),
):
    """Exchange Google auth code for a Swaya.me JWT."""
    # Validate CSRF state token
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state parameter")
    stored = await redis.get(f"oauth_state:{state}")
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    await redis.delete(f"oauth_state:{state}")

    redirect_uri = f"{settings.app.frontend_url}/auth/google/callback"
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google.client_id,
                "client_secret": settings.google.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Google token exchange failed")

        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        profile = info_resp.json()

    if not profile.get("email"):
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    result = await oauth_login_or_register(db, "google", profile)
    _set_auth_cookie(response, result.access_token)
    return result


from core.auth.schemas import ForgotPasswordRequest, ResetPasswordRequest
from core.auth.service_async import request_password_reset, execute_password_reset

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Request a password reset email
    Always returns 200 OK to prevent email enumeration
    """
    await request_password_reset(db, body.email)
    return {"message": "If that email exists in our system, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Execute password reset using the token from the email
    """
    try:
        await execute_password_reset(db, request.token, request.new_password)
        return {"message": "Password has been successfully reset. You can now log in."}
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
