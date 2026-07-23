"""
User Management API Endpoints
REST API for user CRUD, activity logs, and statistics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from persistence.database_async import get_async_db
from persistence.models.core import User, UserRole
from core.user_management.schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserPasswordUpdate, UserStats, ActivityLogListResponse, UserLookupResponse
)
from core.user_management.service_async import UserManagementServiceAsync
from core.auth.dependencies import get_current_user, CurrentUser


def get_current_user_from_context(current: CurrentUser = Depends(get_current_user)):
    """Extract user from auth context"""
    return current.user


router = APIRouter(prefix="/users", tags=["User Management"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_create: UserCreate,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new user
    Requires: Admin or Super Admin role
    """
    service = UserManagementServiceAsync(db)
    return await service.create_user(user_create, current_user)


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    tenant_id: Optional[int] = None,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List users with filters
    Super admin sees all tenants, admin sees only their tenant
    """
    service = UserManagementServiceAsync(db)
    return await service.list_users(
        current_user=current_user,
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        tenant_id=tenant_id
    )


@router.get("/lookup", response_model=Optional[UserLookupResponse])
async def lookup_user_by_email(
    email: str,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Resolve an exact email to a minimal user record, across any tenant.
    Used to add a user from a different org to a folder share by email.
    Returns null if no account exists for that email.
    """
    service = UserManagementServiceAsync(db)
    return await service.lookup_by_email(email, current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user by ID"""
    service = UserManagementServiceAsync(db)
    return await service.get_user(user_id, current_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update user details
    Requires: Permission to manage the target user
    """
    service = UserManagementServiceAsync(db)
    return await service.update_user(user_id, user_update, current_user)



@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete user (soft delete)
    Requires: Permission to manage the target user
    """
    service = UserManagementServiceAsync(db)
    return await service.delete_user(user_id, current_user)


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: int,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user statistics"""
    service = UserManagementServiceAsync(db)
    return await service.get_user_stats(user_id, current_user)


@router.get("/{user_id}/activities", response_model=ActivityLogListResponse)
async def get_user_activities(
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user activity log"""
    service = UserManagementServiceAsync(db)
    return await service.get_user_activities(user_id, current_user, page, per_page)


@router.post("/{user_id}/password")
async def update_password(
    user_id: int,
    password_update: UserPasswordUpdate,
    current_user = Depends(get_current_user_from_context),
    db: AsyncSession = Depends(get_async_db)
):
    """Update user password"""
    service = UserManagementServiceAsync(db)
    return await service.update_password(
        user_id,
        password_update.current_password,
        password_update.new_password,
        current_user
    )
