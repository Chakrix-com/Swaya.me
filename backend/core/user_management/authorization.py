"""
Authorization Service for User Management
Role-based access control and tenant isolation
"""
from typing import List
from persistence.models.core import User, UserRole
from fastapi import HTTPException, status


class AuthorizationService:
    """Service for checking user permissions"""
    
    @staticmethod
    def is_super_admin(user: User) -> bool:
        """Check if user is super admin"""
        return user.role == UserRole.super_admin
    
    @staticmethod
    def is_admin(user: User) -> bool:
        """Check if user is admin or super admin"""
        return user.role in [UserRole.super_admin, UserRole.admin]
    
    @staticmethod
    def can_manage_users(current_user: User) -> bool:
        """Check if user can manage other users"""
        return AuthorizationService.is_admin(current_user)
    
    @staticmethod
    def can_manage_tenants(current_user: User) -> bool:
        """Only super admin can manage tenants"""
        return AuthorizationService.is_super_admin(current_user)
    
    @staticmethod
    def can_manage_user(current_user: User, target_user: User) -> bool:
        """
        Check if current user can manage target user
        Rules:
        - Super admin can manage anyone
        - Admin can manage users in their tenant (except super admins)
        - Users cannot manage others
        """
        if AuthorizationService.is_super_admin(current_user):
            return True
        
        if AuthorizationService.is_admin(current_user):
            # Admin can manage users in their tenant, but not super admins
            if target_user.tenant_id != current_user.tenant_id:
                return False
            if target_user.role == UserRole.super_admin:
                return False
            return True
        
        return False
    
    @staticmethod
    def can_assign_role(current_user: User, new_role: UserRole) -> bool:
        """
        Check if current user can assign a specific role
        Rules:
        - Super admin can assign any role
        - Admin can assign: user, viewer (not admin or super_admin)
        """
        if AuthorizationService.is_super_admin(current_user):
            return True
        
        if AuthorizationService.is_admin(current_user):
            return new_role in [UserRole.user, UserRole.viewer]
        
        return False
    
    @staticmethod
    def enforce_user_management_access(current_user: User) -> None:
        """Raise exception if user cannot manage users"""
        if not AuthorizationService.can_manage_users(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage users"
            )
    
    @staticmethod
    def enforce_tenant_management_access(current_user: User) -> None:
        """Raise exception if user cannot manage tenants"""
        if not AuthorizationService.can_manage_tenants(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can manage tenants"
            )
    
    @staticmethod
    def enforce_can_manage_user(current_user: User, target_user: User) -> None:
        """Raise exception if user cannot manage target user"""
        if not AuthorizationService.can_manage_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot manage this user"
            )
    
    @staticmethod
    def enforce_can_assign_role(current_user: User, new_role: UserRole) -> None:
        """Raise exception if user cannot assign this role"""
        if not AuthorizationService.can_assign_role(current_user, new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot assign role: {new_role.value}"
            )
    
    @staticmethod
    def get_accessible_tenant_ids(current_user: User) -> List[int]:
        """Get list of tenant IDs the user can access"""
        if AuthorizationService.is_super_admin(current_user):
            return None  # None means all tenants
        return [current_user.tenant_id]
