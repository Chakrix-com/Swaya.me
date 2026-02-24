"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from persistence.database import get_db
from core.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from core.auth.service import register_user, login_user
from core.auth.dependencies import get_current_user
from shared.exceptions.auth import InvalidCredentialsError, DuplicateUserError, TenantNotFoundError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new user and create tenant
    
    - Creates new tenant account (Free tier by default)
    - Creates user associated with tenant
    - Returns JWT access token
    """
    try:
        return register_user(db, request)
    except DuplicateUserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and get access token
    
    - Validates credentials
    - Returns JWT access token valid for 24 hours
    """
    try:
        return login_user(db, request)
    except (InvalidCredentialsError, TenantNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: Session = Depends(get_db),
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
