"""
Organization Management API endpoints
Only accessible by super_admin users
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from persistence.database_async import get_async_db
from core.organization.service_async import OrganizationServiceAsync, AdminManagementServiceAsync
from core.organization.schemas import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationResponse,
    AdminUserCreateRequest,
    AdminUserResponse,
    UpdateQuotaRequest
)
from core.auth.dependencies import get_current_user, require_super_admin
from persistence.models.core import User
from shared.exceptions.auth import DuplicateUserError


router = APIRouter(prefix="/organizations", tags=["Organization Management"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Create a new organization (super_admin only)
    
    Creates a tenant without any users. Use /admin-users endpoint to create admin users.
    """
    try:
        return await OrganizationServiceAsync.create_organization(db, request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    List all organizations with user/admin counts (super_admin only)
    """
    return await OrganizationServiceAsync.list_organizations(db, skip=skip, limit=limit)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Get organization details by ID (super_admin only)
    """
    org = await OrganizationServiceAsync.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    request: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Update organization details (super_admin only)
    """
    org = await OrganizationServiceAsync.update_organization(db, org_id, request)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )
    return org


@router.get("/{org_id}/admins", response_model=List[AdminUserResponse])
async def list_organization_admins(
    org_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    List all admin users in an organization with quota info (super_admin only)
    """
    # Verify org exists
    org = await OrganizationServiceAsync.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found"
        )
    
    return await OrganizationServiceAsync.list_admins(db, org_id)


# Admin user management endpoints
admin_router = APIRouter(prefix="/admin-users", tags=["Admin User Management"])


@admin_router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    request: AdminUserCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Create an admin user for an organization with quota (super_admin only)
    """
    try:
        return await AdminManagementServiceAsync.create_admin(db, request)
    except DuplicateUserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@admin_router.patch("/{admin_id}/quota", response_model=AdminUserResponse)
async def update_admin_quota(
    admin_id: int,
    request: UpdateQuotaRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Update admin user's quota limit (super_admin only)
    """
    admin = await AdminManagementServiceAsync.update_quota(db, admin_id, request.user_quota)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin user with ID {admin_id} not found"
        )
    return admin


@admin_router.get("/{admin_id}/usage")
async def get_admin_quota_usage(
    admin_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Get admin's quota usage details (super_admin only)
    """
    usage = await AdminManagementServiceAsync.get_quota_usage(db, admin_id)
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin user with ID {admin_id} not found"
        )
    return usage
