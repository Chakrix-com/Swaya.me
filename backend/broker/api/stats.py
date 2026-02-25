from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database_async import get_async_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.stats.service_async import StatsServiceAsync
from core.stats.schemas import StatsResponse
from persistence.models.core import UserRole

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get application statistics
    - Super Admin: Platform-wide stats (all tenants)
    - Admin: Tenant-specific stats
    - Regular users: 403 Forbidden
    """
    if current_user.user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access statistics"
        )
    
    service = StatsServiceAsync(db)
    
    if current_user.user.role == UserRole.super_admin:
        return await service.get_platform_stats()
    
    return await service.get_tenant_stats(current_user.tenant_id)
