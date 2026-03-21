"""
Statistics snapshot service for capturing and retrieving historical data
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from persistence.models.stats import StatsSnapshot, SnapshotGranularity, SnapshotScope
from persistence.models.core import Tenant
from core.stats.service import StatsService


class SnapshotService:
    """Service for managing statistics snapshots"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stats_service = StatsService(db)
    
    def capture_platform_snapshot(self, granularity: SnapshotGranularity) -> StatsSnapshot:
        """
        Capture a platform-wide statistics snapshot
        
        Args:
            granularity: Snapshot granularity (hourly or daily)
            
        Returns:
            Created StatsSnapshot instance
        """
        # Get platform-wide statistics
        stats_data = self.stats_service.get_platform_stats()
        
        # Create snapshot (serialize datetime to JSON-compatible format)
        snapshot = StatsSnapshot(
            captured_at=datetime.utcnow(),
            granularity=granularity,
            scope=SnapshotScope.PLATFORM,
            tenant_id=None,
            stats_data=stats_data.model_dump(mode='json')
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    def capture_tenant_snapshots(self, granularity: SnapshotGranularity) -> List[StatsSnapshot]:
        """
        Capture statistics snapshots for all active tenants
        
        Args:
            granularity: Snapshot granularity (hourly or daily)
            
        Returns:
            List of created StatsSnapshot instances
        """
        # Get all active tenants
        tenants = self.db.query(Tenant).filter(Tenant.is_active == True).all()
        
        snapshots = []
        for tenant in tenants:
            # Get tenant-specific statistics
            stats_data = self.stats_service.get_tenant_stats(tenant.id)
            
            # Create snapshot (serialize datetime to JSON-compatible format)
            snapshot = StatsSnapshot(
                captured_at=datetime.utcnow(),
                granularity=granularity,
                scope=SnapshotScope.TENANT,
                tenant_id=tenant.id,
                stats_data=stats_data.model_dump(mode='json')
            )
            
            self.db.add(snapshot)
            snapshots.append(snapshot)
        
        self.db.commit()
        
        # Refresh all snapshots
        for snapshot in snapshots:
            self.db.refresh(snapshot)
        
        return snapshots
    
    def get_history(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: SnapshotGranularity,
        scope: SnapshotScope,
        tenant_id: Optional[int] = None
    ) -> List[StatsSnapshot]:
        """
        Retrieve historical statistics snapshots
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            granularity: Snapshot granularity to retrieve
            scope: Snapshot scope (platform or tenant)
            tenant_id: Tenant ID (required if scope is TENANT)
            
        Returns:
            List of StatsSnapshot instances ordered by captured_at
        """
        query = self.db.query(StatsSnapshot).filter(
            and_(
                StatsSnapshot.captured_at >= start_date,
                StatsSnapshot.captured_at <= end_date,
                StatsSnapshot.granularity == granularity,
                StatsSnapshot.scope == scope
            )
        )
        
        # Add tenant filter if scope is tenant
        if scope == SnapshotScope.TENANT:
            if tenant_id is None:
                raise ValueError("tenant_id is required for TENANT scope")
            query = query.filter(StatsSnapshot.tenant_id == tenant_id)
        
        # Order by captured_at ascending
        query = query.order_by(StatsSnapshot.captured_at.asc())
        
        return query.all()
    
    def get_latest_snapshot(
        self,
        granularity: SnapshotGranularity,
        scope: SnapshotScope,
        tenant_id: Optional[int] = None
    ) -> Optional[StatsSnapshot]:
        """
        Get the most recent snapshot for given parameters
        
        Args:
            granularity: Snapshot granularity
            scope: Snapshot scope (platform or tenant)
            tenant_id: Tenant ID (required if scope is TENANT)
            
        Returns:
            Most recent StatsSnapshot or None
        """
        query = self.db.query(StatsSnapshot).filter(
            and_(
                StatsSnapshot.granularity == granularity,
                StatsSnapshot.scope == scope
            )
        )
        
        if scope == SnapshotScope.TENANT:
            if tenant_id is None:
                raise ValueError("tenant_id is required for TENANT scope")
            query = query.filter(StatsSnapshot.tenant_id == tenant_id)
        
        return query.order_by(StatsSnapshot.captured_at.desc()).first()
