"""
Organization management service
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import re

from persistence.models.core import Tenant, User, TierEnum, UserRole
from core.organization.schemas import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationResponse,
    AdminUserCreateRequest,
    AdminUserResponse,
    UpdateQuotaRequest
)
from core.security.password import hash_password
from shared.exceptions.auth import DuplicateUserError


def create_slug(name: str) -> str:
    """Generate URL-safe slug from organization name"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


class OrganizationService:
    """Service for managing organizations (tenants)"""
    
    @staticmethod
    def create_organization(db: Session, request: OrganizationCreateRequest) -> OrganizationResponse:
        """
        Create a new organization (tenant)
        
        Args:
            db: Database session
            request: Organization creation request
            
        Returns:
            OrganizationResponse with created org details
        """
        # Generate or validate slug
        slug = request.slug if request.slug else create_slug(request.name)
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while db.query(Tenant).filter(Tenant.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create tenant
        tenant = Tenant(
            name=request.name,
            slug=slug,
            tier=TierEnum[request.tier.upper()],
            is_active=True
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        # Get counts
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
        admin_count = db.query(func.count(User.id)).filter(
            User.tenant_id == tenant.id,
            User.role == UserRole.admin
        ).scalar()
        
        return OrganizationResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            tier=tenant.tier.value,
            is_active=tenant.is_active,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat(),
            user_count=user_count or 0,
            admin_count=admin_count or 0
        )
    
    @staticmethod
    def list_organizations(db: Session, skip: int = 0, limit: int = 100) -> List[OrganizationResponse]:
        """
        List all organizations with user/admin counts
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Max records to return
            
        Returns:
            List of OrganizationResponse objects
        """
        tenants = db.query(Tenant).offset(skip).limit(limit).all()
        
        results = []
        for tenant in tenants:
            # Get counts
            user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
            admin_count = db.query(func.count(User.id)).filter(
                User.tenant_id == tenant.id,
                User.role == UserRole.admin
            ).scalar()
            
            results.append(OrganizationResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                tier=tenant.tier.value,
                is_active=tenant.is_active,
                created_at=tenant.created_at.isoformat(),
                updated_at=tenant.updated_at.isoformat(),
                user_count=user_count or 0,
                admin_count=admin_count or 0
            ))
        
        return results
    
    @staticmethod
    def get_organization(db: Session, org_id: int) -> Optional[OrganizationResponse]:
        """
        Get organization by ID with counts
        
        Args:
            db: Database session
            org_id: Organization ID
            
        Returns:
            OrganizationResponse or None if not found
        """
        tenant = db.query(Tenant).filter(Tenant.id == org_id).first()
        if not tenant:
            return None
        
        # Get counts
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
        admin_count = db.query(func.count(User.id)).filter(
            User.tenant_id == tenant.id,
            User.role == UserRole.admin
        ).scalar()
        
        return OrganizationResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            tier=tenant.tier.value,
            is_active=tenant.is_active,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat(),
            user_count=user_count or 0,
            admin_count=admin_count or 0
        )
    
    @staticmethod
    def update_organization(
        db: Session, 
        org_id: int, 
        request: OrganizationUpdateRequest
    ) -> Optional[OrganizationResponse]:
        """
        Update organization details
        
        Args:
            db: Database session
            org_id: Organization ID
            request: Update request
            
        Returns:
            Updated OrganizationResponse or None if not found
        """
        tenant = db.query(Tenant).filter(Tenant.id == org_id).first()
        if not tenant:
            return None
        
        # Update fields
        if request.name is not None:
            tenant.name = request.name
        if request.tier is not None:
            tenant.tier = TierEnum[request.tier.upper()]
        if request.is_active is not None:
            tenant.is_active = request.is_active
        
        db.commit()
        db.refresh(tenant)
        
        return OrganizationService.get_organization(db, org_id)
    
    @staticmethod
    def list_admins(db: Session, org_id: int) -> List[AdminUserResponse]:
        """
        List all admin users in an organization with quota info
        
        Args:
            db: Database session
            org_id: Organization ID
            
        Returns:
            List of AdminUserResponse objects
        """
        admins = db.query(User).filter(
            User.tenant_id == org_id,
            User.role == UserRole.admin
        ).all()
        
        results = []
        for admin in admins:
            # Get quota usage (count of active users managed by this admin)
            quota_usage = db.query(func.count(User.id)).filter(
                User.managed_by_admin_id == admin.id,
                User.is_active == True
            ).scalar()
            
            tenant = db.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
            
            results.append(AdminUserResponse(
                id=admin.id,
                email=admin.email,
                full_name=admin.full_name,
                tenant_id=admin.tenant_id,
                tenant_name=tenant.name if tenant else "Unknown",
                role=admin.role.value,
                user_quota=admin.user_quota,
                quota_usage=quota_usage or 0,
                is_active=admin.is_active,
                created_at=admin.created_at.isoformat()
            ))
        
        return results


class AdminManagementService:
    """Service for managing admin users and quotas"""
    
    @staticmethod
    def create_admin(db: Session, request: AdminUserCreateRequest) -> AdminUserResponse:
        """
        Create an admin user for an organization
        
        Args:
            db: Database session
            request: Admin creation request
            
        Returns:
            AdminUserResponse with created admin details
            
        Raises:
            DuplicateUserError: If email already exists
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise DuplicateUserError(f"User with email {request.email} already exists")
        
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
        if not tenant:
            raise ValueError(f"Organization with ID {request.tenant_id} not found")
        
        # Create admin user
        from datetime import datetime, timezone
        user = User(
            tenant_id=request.tenant_id,
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            is_active=True,
            role=UserRole.admin,
            user_quota=request.user_quota,
            managed_by_admin_id=None,  # Admins are not managed by anyone
            login_count=0,
            last_login_at=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            tenant_name=tenant.name,
            role=user.role.value,
            user_quota=user.user_quota,
            quota_usage=0,  # New admin has no users yet
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    
    @staticmethod
    def update_quota(db: Session, admin_id: int, new_quota: int) -> Optional[AdminUserResponse]:
        """
        Update admin user's quota limit
        
        Args:
            db: Database session
            admin_id: Admin user ID
            new_quota: New quota value
            
        Returns:
            Updated AdminUserResponse or None if not found
        """
        admin = db.query(User).filter(
            User.id == admin_id,
            User.role == UserRole.admin
        ).first()
        
        if not admin:
            return None
        
        admin.user_quota = new_quota
        db.commit()
        db.refresh(admin)
        
        # Get quota usage
        quota_usage = db.query(func.count(User.id)).filter(
            User.managed_by_admin_id == admin.id,
            User.is_active == True
        ).scalar()
        
        tenant = db.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
        
        return AdminUserResponse(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name,
            tenant_id=admin.tenant_id,
            tenant_name=tenant.name if tenant else "Unknown",
            role=admin.role.value,
            user_quota=admin.user_quota,
            quota_usage=quota_usage or 0,
            is_active=admin.is_active,
            created_at=admin.created_at.isoformat()
        )
    
    @staticmethod
    def get_quota_usage(db: Session, admin_id: int) -> Optional[dict]:
        """
        Get admin's quota usage details
        
        Args:
            db: Database session
            admin_id: Admin user ID
            
        Returns:
            Dict with quota, usage, and available count
        """
        admin = db.query(User).filter(
            User.id == admin_id,
            User.role == UserRole.admin
        ).first()
        
        if not admin:
            return None
        
        usage = db.query(func.count(User.id)).filter(
            User.managed_by_admin_id == admin.id,
            User.is_active == True
        ).scalar()
        
        return {
            "admin_id": admin.id,
            "quota": admin.user_quota,
            "usage": usage or 0,
            "available": (admin.user_quota - (usage or 0)) if admin.user_quota else None
        }
