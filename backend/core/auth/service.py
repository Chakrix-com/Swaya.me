"""
Authentication service - business logic for user auth
"""
from sqlalchemy.orm import Session
from typing import Optional
import re

from persistence.models.core import User, Tenant, TierEnum
from core.security.password import hash_password, verify_password
from core.security.jwt import create_access_token
from core.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from shared.exceptions.auth import (
    InvalidCredentialsError,
    UserNotFoundError,
    DuplicateUserError,
    TenantNotFoundError
)


def create_tenant_slug(name: str) -> str:
    """Generate URL-safe slug from tenant name"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def register_user(db: Session, request: UserRegisterRequest) -> TokenResponse:
    """
    Register new user with tenant creation
    
    Args:
        db: Database session
        request: Registration request data
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        DuplicateUserError: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise DuplicateUserError(f"User with email {request.email} already exists")
    
    # Create tenant
    tenant_slug = create_tenant_slug(request.tenant_name)
    
    # Ensure unique slug
    base_slug = tenant_slug
    counter = 1
    while db.query(Tenant).filter(Tenant.slug == tenant_slug).first():
        tenant_slug = f"{base_slug}-{counter}"
        counter += 1
    
    tenant = Tenant(
        name=request.tenant_name,
        slug=tenant_slug,
        tier=TierEnum.FREE,
        is_active=True
    )
    db.add(tenant)
    db.flush()  # Get tenant.id
    
    # Create user
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(tenant)
    
    # Generate access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": tenant.id,
            "tier": tenant.tier.value
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,  # 24 hours
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tier=tenant.tier.value,
            is_active=user.is_active
        )
    )


def login_user(db: Session, request: UserLoginRequest) -> TokenResponse:
    """
    Authenticate user and generate access token
    
    Args:
        db: Database session
        request: Login request data
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        InvalidCredentialsError: If credentials are invalid
        TenantNotFoundError: If tenant not found or inactive
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Generic error for security - don't reveal if user exists
        raise InvalidCredentialsError("Invalid email or password")
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")
    
    # Check if user is active - specific error for user feedback
    if not user.is_active:
        raise InvalidCredentialsError("Your account has been disabled. Please contact support.")
    
    # Get tenant - should always exist due to FK constraint
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        # This should never happen due to database FK constraint
        # If it does, it indicates database corruption
        raise TenantNotFoundError(f"User's tenant not found. Contact support (tenant_id: {user.tenant_id})")
    
    # Check tenant is active - specific error for tenant admin feedback
    if not tenant.is_active:
        raise TenantNotFoundError("Your organization account has been suspended. Please contact your administrator.")
    
    # Generate access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": tenant.id,
            "tier": tenant.tier.value
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tier=tenant.tier.value,
            is_active=user.is_active
        )
    )


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()
