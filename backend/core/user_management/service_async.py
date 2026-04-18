"""
User Management Service - Async Version
Business logic for user CRUD, activity logging, and statistics
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, desc, select
from sqlalchemy.orm import selectinload
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


class UserManagementServiceAsync:
    """Async service for managing users"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(
        self,
        user_create: UserCreate,
        current_user: User
    ) -> UserResponse:
        """
        Create a new user
        Authorization: Admin or super admin
        Quota: Admins are limited by their user_quota
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
        
        # Check quota for admin users (super_admin bypasses)
        if current_user.role == UserRole.admin:
            # Check if admin has quota set
            if current_user.user_quota is not None:
                # Count active users managed by this admin
                result = await self.db.execute(
                    select(func.count(User.id)).filter(
                        and_(
                            User.managed_by_admin_id == current_user.id,
                            User.is_active == True
                        )
                    )
                )
                current_usage = result.scalar() or 0
                
                if current_usage >= current_user.user_quota:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User quota reached ({current_usage}/{current_user.user_quota}). Contact super admin to increase your limit."
                    )
        
        # Check if email already exists
        result = await self.db.execute(
            select(User).filter(User.email == user_create.email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verify tenant exists
        result = await self.db.execute(
            select(Tenant).filter(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check role assignment permission
        AuthorizationService.enforce_can_assign_role(current_user, user_create.role)
        
        # Determine managed_by_admin_id
        if current_user.role == UserRole.admin:
            # Admin creates user -> assign to themselves
            managed_by_admin_id = current_user.id
        elif current_user.role == UserRole.super_admin and user_create.tenant_id:
            # Super admin creating user in specific tenant
            # Try to find first admin in that tenant
            result = await self.db.execute(
                select(User).filter(
                    and_(
                        User.tenant_id == tenant_id,
                        User.role == UserRole.admin,
                        User.is_active == True
                    )
                )
            )
            first_admin = result.scalar_one_or_none()
            managed_by_admin_id = first_admin.id if first_admin else None
        else:
            # Super admin creating in own tenant or no specific admin
            managed_by_admin_id = None
        
        # Create user
        new_user = User(
            email=user_create.email,
            hashed_password=hash_password(user_create.password),
            full_name=user_create.full_name,
            tenant_id=tenant_id,
            role=user_create.role,
            is_active=True,
            managed_by_admin_id=managed_by_admin_id
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # Log activity
        await self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_created",
            resource_type="user",
            resource_id=new_user.id,
            details={"email": new_user.email, "role": new_user.role.value, "managed_by": managed_by_admin_id}
        )
        
        return UserResponse.model_validate(new_user)
    
    async def get_user(self, user_id: int, current_user: User) -> UserResponse:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
    
    async def list_users(
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
        stmt = select(User)
        
        # Tenant filtering
        if AuthorizationService.is_super_admin(current_user):
            if tenant_id:
                stmt = stmt.filter(User.tenant_id == tenant_id)
        else:
            # Admin can only see their tenant
            stmt = stmt.filter(User.tenant_id == current_user.tenant_id)
        
        # Search filter
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )
        
        # Role filter
        if role:
            stmt = stmt.filter(User.role == role)
        
        # Active filter
        if is_active is not None:
            stmt = stmt.filter(User.is_active == is_active)
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar() or 0
        
        # Pagination
        offset = (page - 1) * per_page
        stmt = stmt.options(selectinload(User.tenant)).order_by(desc(User.created_at)).offset(offset).limit(per_page)
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        def to_response(u):
            data = UserResponse.model_validate(u)
            if u.tenant:
                data.tier = u.tenant.tier.value
                data.tenant_name = u.tenant.name
            return data

        return UserListResponse(
            users=[to_response(u) for u in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    
    async def update_user(
        self,
        user_id: int,
        user_update: UserUpdate,
        current_user: User
    ) -> UserResponse:
        """Update user details"""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
        if user_update.tier is not None:
            if not AuthorizationService.is_super_admin(current_user):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admins can change tier")
            tenant_result = await self.db.execute(select(Tenant).filter(Tenant.id == user.tenant_id))
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                tenant.tier = user_update.tier

        await self.db.commit()
        await self.db.refresh(user)
        
        # Log activity
        await self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_updated",
            resource_type="user",
            resource_id=user.id,
            details=user_update.model_dump(exclude_unset=True)
        )
        
        return UserResponse.model_validate(user)
    
    async def delete_user(self, user_id: int, current_user: User) -> dict:
        """Delete user (soft delete by setting is_active=False)"""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
            count_result = await self.db.execute(
                select(func.count(User.id)).filter(
                    and_(
                        User.tenant_id == user.tenant_id,
                        User.role == UserRole.admin,
                        User.is_active == True
                    )
                )
            )
            admin_count = count_result.scalar() or 0
            if admin_count == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete last admin in tenant"
                )
        
        # Soft delete
        user.is_active = False
        await self.db.commit()
        
        # Log activity
        await self._log_activity(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="user_deleted",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email}
        )
        
        return {"message": "User deleted successfully"}
    
    async def get_user_stats(self, user_id: int, current_user: User) -> UserStats:
        """Get user statistics"""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
        count_result = await self.db.execute(
            select(func.count(Quiz.id)).filter(Quiz.created_by == user_id)
        )
        quiz_count = count_result.scalar() or 0
        
        # Get total participants (sum from all quizzes)
        # This would require session/participant data - placeholder for now
        total_participants = 0
        
        return UserStats(
            total_logins=user.login_count,
            last_login=user.last_login_at,
            quizzes_created=quiz_count,
            total_participants=total_participants
        )
    
    async def get_user_activities(
        self,
        user_id: int,
        current_user: User,
        page: int = 1,
        per_page: int = 50
    ) -> ActivityLogListResponse:
        """Get user activity log"""
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
        
        stmt = select(UserActivity).filter(UserActivity.user_id == user_id)
        count_result = await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar() or 0
        
        offset = (page - 1) * per_page
        stmt = stmt.order_by(desc(UserActivity.created_at)).offset(offset).limit(per_page)
        result = await self.db.execute(stmt)
        activities = result.scalars().all()
        
        return ActivityLogListResponse(
            activities=[ActivityLogResponse.model_validate(a) for a in activities],
            total=total,
            page=page,
            per_page=per_page
        )
    
    async def update_password(
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
        
        result = await self.db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
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
        await self.db.commit()
        
        # Log activity
        await self._log_activity(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="password_changed",
            resource_type="user",
            resource_id=user.id
        )
        
        return {"message": "Password updated successfully"}
    
    async def _log_activity(
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
        await self.db.commit()
