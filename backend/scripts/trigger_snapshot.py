import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence.database import SessionLocal
from core.stats.snapshot_service import SnapshotService
from persistence.models.stats import SnapshotGranularity

db = SessionLocal()
try:
    service = SnapshotService(db)
    
    # Capture hourly snapshot
    print("Capturing hourly snapshot...")
    hourly = service.capture_platform_snapshot(SnapshotGranularity.HOURLY)
    print(f"✓ Platform hourly snapshot: ID={hourly.id}, time={hourly.captured_at}")
    
    tenant_hourly = service.capture_tenant_snapshots(SnapshotGranularity.HOURLY)
    print(f"✓ Captured {len(tenant_hourly)} tenant hourly snapshots")
    
    # Capture daily snapshot
    print("\nCapturing daily snapshot...")
    daily = service.capture_platform_snapshot(SnapshotGranularity.DAILY)
    print(f"✓ Platform daily snapshot: ID={daily.id}, time={daily.captured_at}")
    
    tenant_daily = service.capture_tenant_snapshots(SnapshotGranularity.DAILY)
    print(f"✓ Captured {len(tenant_daily)} tenant daily snapshots")
    
    print("\n✅ All snapshots captured successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
