"""
Authentication API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from persistence.database_async import get_async_db
from core.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from core.auth.service_async import register_user, login_user
from core.auth.dependencies import get_current_user
from core.auth.email_service import send_welcome_email
from shared.exceptions.auth import (
    InvalidCredentialsError, 
    DuplicateUserError, 
    TenantNotFoundError,
    EmailNotVerifiedError
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register new user and create tenant
    
    - Creates new tenant account (Free tier by default)
    - Creates user associated with tenant
    - Returns JWT access token
    """
    try:
        return await register_user(db, request)
    except DuplicateUserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticate user and get access token
    
    - Validates credentials
    - Returns JWT access token valid for 24 hours
    """
    try:
        return await login_user(db, request)
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


from core.auth.schemas import ForgotPasswordRequest, ResetPasswordRequest
from core.auth.service_async import request_password_reset, execute_password_reset

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Request a password reset email
    Always returns 200 OK to prevent email enumeration
    """
    await request_password_reset(db, request.email)
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
