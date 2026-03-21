"""
Authentication service - business logic for user auth
"""
from sqlalchemy.orm import Session
from typing import Optional
import re

from persistence.models.core import User, Tenant, TierEnum, UserRole, Event
from persistence.models.quiz import Quiz, Question, QuizStatus, QuestionType
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
    
    # Create isolated tenant for this self-registered user
    email_local = request.email.split("@")[0]
    base_name = (request.full_name or email_local).strip()
    tenant_name = f"{base_name}'s Workspace"
    base_slug = create_tenant_slug(base_name) or "workspace"
    slug = base_slug
    suffix = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    tenant = Tenant(
        name=tenant_name,
        slug=slug,
        tier=TierEnum.FREE,
        is_active=True,
    )
    db.add(tenant)
    db.flush()
    
    # Create user
    from datetime import datetime, timezone
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_active=True,
        role=UserRole.user,  # Explicit role assignment
        managed_by_admin_id=None,  # Self-registered users not managed by anyone
        login_count=1,  # Count registration as first login
        last_login_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.flush()

    # Seed a starter demo quiz for each newly registered user.
    demo_event = Event(
        tenant_id=tenant.id,
        creator_id=user.id,
        title="Demo Quiz Event",
        description="Auto-generated event for starter demo quiz",
        join_code=None,
    )
    db.add(demo_event)
    db.flush()

    demo_quiz = Quiz(
        tenant_id=tenant.id,
        event_id=demo_event.id,
        title="Welcome Demo Quiz",
        description="A short starter quiz to help you explore Swaya.me",
        status=QuizStatus.READY,
    )
    db.add(demo_quiz)
    db.flush()

    demo_questions = [
        Question(
            quiz_id=demo_quiz.id,
            question_type=QuestionType.MCQ,
            text="What is the main purpose of this demo quiz?",
            order=1,
            options=[
                "To test your knowledge only",
                "To show how quiz flow works",
                "To configure billing settings",
                "To invite super admins",
            ],
            correct_answer_index=1,
        ),
        Question(
            quiz_id=demo_quiz.id,
            question_type=QuestionType.WORD_CLOUD,
            text="In one word, what do you want from your quizzes?",
            order=2,
            options=None,
            correct_answer_index=None,
        ),
    ]
    db.add_all(demo_questions)

    db.commit()
    db.refresh(user)
    
    # Generate access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": tenant.id,
            "tier": tenant.tier.value,
            "role": user.role.value
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
            is_active=user.is_active,
            role=user.role.value
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
    
    # Update login tracking
    from datetime import datetime, timezone
    user.last_login_at = datetime.now(timezone.utc)
    user.login_count += 1
    db.commit()
    
    # Generate access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": tenant.id,
            "tier": tenant.tier.value,
            "role": user.role.value
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
            is_active=user.is_active,
            role=user.role.value
        )
    )


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()
