"""
Statistics history API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Optional

from persistence.database_async import get_async_db
from core.auth.dependencies import get_current_user, CurrentUser, require_admin, require_super_admin
from core.stats.snapshot_service_async import SnapshotServiceAsync
from core.stats.schemas import StatsHistoryResponse
from persistence.models.stats import SnapshotGranularity, SnapshotScope


router = APIRouter(prefix="/admin/stats", tags=["statistics"])


@router.get("/history", response_model=List[StatsHistoryResponse])
async def get_stats_history(
    start_date: datetime = Query(..., description="Start date for history range"),
    end_date: datetime = Query(..., description="End date for history range"),
    granularity: SnapshotGranularity = Query(..., description="Snapshot granularity"),
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get historical statistics snapshots

    - **start_date**: Start of date range (ISO format)
    - **end_date**: End of date range (ISO format)
    - **granularity**: Snapshot granularity (hourly or daily)

    Returns list of historical snapshots ordered by time.
    Super admins see platform-wide data, admins see their tenant data.
    """
    # Validate date range
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Limit range to avoid performance issues
    max_days = 365 if granularity == SnapshotGranularity.DAILY else 90
    if (end_date - start_date).days > max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Date range too large. Maximum {max_days} days for {granularity.value} snapshots"
        )

    snapshot_service = SnapshotServiceAsync(db)

    from persistence.models.core import UserRole
    if current_user.user.role == UserRole.super_admin:
        scope = SnapshotScope.PLATFORM
        tenant_id = None
    else:
        scope = SnapshotScope.TENANT
        tenant_id = current_user.tenant.id
    
    # Get history
    snapshots = await snapshot_service.get_history(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        scope=scope,
        tenant_id=tenant_id
    )
    
    # Convert to response format
    response = []
    for snapshot in snapshots:
        response.append(StatsHistoryResponse(
            captured_at=snapshot.captured_at,
            granularity=snapshot.granularity,
            scope=snapshot.scope,
            tenant_id=snapshot.tenant_id,
            stats=snapshot.stats_data
        ))
    
    return response


@router.post("/capture", status_code=201)
async def trigger_snapshot_capture(
    granularity: SnapshotGranularity = Query(..., description="Snapshot granularity to capture"),
    current_user: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Manually trigger snapshot capture (for testing/debugging)

    Super admin only endpoint.
    """
    
    snapshot_service = SnapshotServiceAsync(db)
    
    # Capture platform snapshot
    platform_snapshot = await snapshot_service.capture_platform_snapshot(granularity)
    
    # Capture tenant snapshots
    tenant_snapshots = await snapshot_service.capture_tenant_snapshots(granularity)
    
    return {
        "message": "Snapshots captured successfully",
        "platform_snapshot_id": platform_snapshot.id,
        "tenant_snapshots_count": len(tenant_snapshots),
        "granularity": granularity.value,
        "captured_at": platform_snapshot.captured_at.isoformat()
    }
