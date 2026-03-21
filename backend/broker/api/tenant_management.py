"""
Tenant Management API (Super Admin Only)
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from persistence.database import get_db
from persistence.models.core import User, Tenant, TierEnum
from core.user_management.schemas import TenantResponse, TenantUpdate, TenantListResponse
from core.user_management.authorization import AuthorizationService
from core.auth.dependencies import get_current_user, CurrentUser


async def get_user(current: CurrentUser = Depends(get_current_user)):
    """Extract user from auth context"""
    return current.user


router = APIRouter(prefix="/tenants", tags=["Tenant Management"])


@router.get("", response_model=TenantListResponse)
def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tier: Optional[TierEnum] = None,
    is_active: Optional[bool] = None,
    current_user = Depends(get_user),
    db: Session = Depends(get_db)
):
    """
    List all tenants with filters
    Requires: Super Admin
    """
    AuthorizationService.enforce_tenant_management_access(current_user)
    
    # Base query with user count
    query = db.query(
        Tenant,
        func.count(User.id).label('user_count')
    ).outerjoin(User, User.tenant_id == Tenant.id).group_by(Tenant.id)
    
    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Tenant.name.ilike(search_pattern))
    
    # Tier filter
    if tier:
        query = query.filter(Tenant.tier == tier)
    
    # Active filter
    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * per_page
    results = query.order_by(desc(Tenant.created_at)).offset(offset).limit(per_page).all()
    
    # Build response
    tenants = []
    for tenant, user_count in results:
        tenant_dict = {
            "id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier,
            "is_active": tenant.is_active,
            "user_count": user_count,
            "created_at": tenant.created_at
        }
        tenants.append(TenantResponse(**tenant_dict))
    
    return TenantListResponse(
        tenants=tenants,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    current_user = Depends(get_user),
    db: Session = Depends(get_db)
):
    """Get tenant by ID"""
    AuthorizationService.enforce_tenant_management_access(current_user)
    
    result = db.query(
        Tenant,
        func.count(User.id).label('user_count')
    ).outerjoin(User, User.tenant_id == Tenant.id).filter(Tenant.id == tenant_id).group_by(Tenant.id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant, user_count = result
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        tier=tenant.tier,
        is_active=tenant.is_active,
        user_count=user_count,
        created_at=tenant.created_at
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_user = Depends(get_user),
    db: Session = Depends(get_db)
):
    """
    Update tenant settings
    Requires: Super Admin
    """
    AuthorizationService.enforce_tenant_management_access(current_user)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields
    if tenant_update.name is not None:
        tenant.name = tenant_update.name
    if tenant_update.tier is not None:
        tenant.tier = tenant_update.tier
    if tenant_update.is_active is not None:
        tenant.is_active = tenant_update.is_active
    
    db.commit()
    db.refresh(tenant)
    
    # Get user count
    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar()
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        tier=tenant.tier,
        is_active=tenant.is_active,
        user_count=user_count,
        created_at=tenant.created_at
    )
