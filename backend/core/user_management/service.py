"""
User Management Service
Business logic for user CRUD, activity logging, and statistics
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import Optional, List, Tuple
from datetime import datetime
from fastapi import HTTPException, status

from persistence.models.core import User, UserActivity, Tenant, UserRole
from persistence.models.quiz import Quiz
from core.user_management.schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    ActivityLogResponse, ActivityLogListResponse, UserStats
)
from core.user_management.authorization import AuthorizationService
from core.security.password import hash_password, verify_password


class UserManagementService:
    """Service for managing users"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(
        self,
        user_create: UserCreate,
        current_user: User
    ) -> UserResponse:
        """
        Create a new user
        Authorization: Admin or super admin
        """
        AuthorizationService.enforce_user_management_access(current_user)
        
        # Determine tenant_id
        if user_create.tenant_id:
            # Super admin can create users in any tenant
            if not AuthorizationService.is_super_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admin can create users in other tenants"
                )
            tenant_id = user_create.tenant_id
        else:
            # Use current user's tenant
            tenant_id = current_user.tenant_id
        
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == user_create.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verify tenant exists
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check role assignment permission
        AuthorizationService.enforce_can_assign_role(current_user, user_create.role)
        
        # Create user
        new_user = User(
            email=user_create.email,
            hashed_password=hash_password(user_create.password),
            full_name=user_create.full_name,
            tenant_id=tenant_id,
            role=user_create.role,
            is_active=True
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        # Log activity
        self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_created",
            resource_type="user",
            resource_id=new_user.id,
            details={"email": new_user.email, "role": new_user.role.value}
        )
        
        return UserResponse.model_validate(new_user)
    
    def get_user(self, user_id: int, current_user: User) -> UserResponse:
        """Get user by ID"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check access
        if not AuthorizationService.is_super_admin(current_user):
            if user.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access user from different tenant"
                )
        
        return UserResponse.model_validate(user)
    
    def list_users(
        self,
        current_user: User,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        tenant_id: Optional[int] = None
    ) -> UserListResponse:
        """
        List users with filtering and pagination
        Super admin sees all, admin sees only their tenant
        """
        AuthorizationService.enforce_user_management_access(current_user)
        
        # Base query
        query = self.db.query(User)
        
        # Tenant filtering
        if AuthorizationService.is_super_admin(current_user):
            if tenant_id:
                query = query.filter(User.tenant_id == tenant_id)
        else:
            # Admin can only see their tenant
            query = query.filter(User.tenant_id == current_user.tenant_id)
        
        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )
        
        # Role filter
        if role:
            query = query.filter(User.role == role)
        
        # Active filter
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Pagination
        offset = (page - 1) * per_page
        users = query.order_by(desc(User.created_at)).offset(offset).limit(per_page).all()
        
        return UserListResponse(
            users=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    
    def update_user(
        self,
        user_id: int,
        user_update: UserUpdate,
        current_user: User
    ) -> UserResponse:
        """Update user details"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check permission
        AuthorizationService.enforce_can_manage_user(current_user, user)
        
        # Prevent self-demotion for admins
        if user.id == current_user.id and user_update.role:
            if user_update.role != user.role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change your own role"
                )
        
        # Check role assignment permission
        if user_update.role:
            AuthorizationService.enforce_can_assign_role(current_user, user_update.role)
        
        # Update fields
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        if user_update.role is not None:
            user.role = user_update.role
        
        self.db.commit()
        self.db.refresh(user)
        
        # Log activity
        self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_updated",
            resource_type="user",
            resource_id=user.id,
            details=user_update.model_dump(exclude_unset=True)
        )
        
        return UserResponse.model_validate(user)
    
    def delete_user(self, user_id: int, current_user: User) -> dict:
        """Delete user (soft delete by setting is_active=False)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check permission
        AuthorizationService.enforce_can_manage_user(current_user, user)
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Check if user is last admin in tenant
        if user.role == UserRole.admin:
            admin_count = self.db.query(User).filter(
                and_(
                    User.tenant_id == user.tenant_id,
                    User.role == UserRole.admin,
                    User.is_active == True
                )
            ).count()
            if admin_count == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete last admin in tenant"
                )
        
        # Soft delete
        user.is_active = False
        self.db.commit()
        
        # Log activity
        self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_deleted",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email}
        )
        
        return {"message": "User deleted successfully"}
    
    def get_user_stats(self, user_id: int, current_user: User) -> UserStats:
        """Get user statistics"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check access
        if not AuthorizationService.is_super_admin(current_user):
            if user.tenant_id != current_user.tenant_id and user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access user stats"
                )
        
        # Get quiz count
        quiz_count = self.db.query(Quiz).filter(Quiz.created_by == user_id).count()
        
        # Get total participants (sum from all quizzes)
        # This would require session/participant data - placeholder for now
        total_participants = 0
        
        return UserStats(
            total_logins=user.login_count,
            last_login=user.last_login_at,
            quizzes_created=quiz_count,
            total_participants=total_participants
        )
    
    def get_user_activities(
        self,
        user_id: int,
        current_user: User,
        page: int = 1,
        per_page: int = 50
    ) -> ActivityLogListResponse:
        """Get user activity log"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check access
        if not AuthorizationService.is_super_admin(current_user):
            if user.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access user activities"
                )
        
        query = self.db.query(UserActivity).filter(UserActivity.user_id == user_id)
        total = query.count()
        
        offset = (page - 1) * per_page
        activities = query.order_by(desc(UserActivity.created_at)).offset(offset).limit(per_page).all()
        
        return ActivityLogListResponse(
            activities=[ActivityLogResponse.model_validate(a) for a in activities],
            total=total,
            page=page,
            per_page=per_page
        )
    
    def update_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        current_user: User
    ) -> dict:
        """Update user password"""
        # Users can only change their own password
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only change your own password"
            )
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        
        # Log activity
        self._log_activity(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="password_changed",
            resource_type="user",
            resource_id=user.id
        )
        
        return {"message": "Password updated successfully"}
    
    def _log_activity(
        self,
        user_id: int,
        tenant_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log user activity"""
        activity = UserActivity(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(activity)
        self.db.commit()
