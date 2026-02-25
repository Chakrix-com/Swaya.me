import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User
from core.stats.service import StatsService

db = SessionLocal()
try:
    service = StatsService(db)
    
    # Get platform stats (which includes load stats)
    stats = service.get_platform_stats()
    
    print("Platform Statistics:")
    print("=" * 60)
    print(f"Scope: {stats.scope}")
    print(f"\nUsers:")
    print(f"  Total:    {stats.stats.users.total}")
    print(f"  Active:   {stats.stats.users.active}")
    print(f"  Inactive: {stats.stats.users.inactive}")
    
    print(f"\nSessions:")
    print(f"  Active:   {stats.stats.sessions.active}")
    
    if stats.stats.load:
        print(f"\nSystem Load:")
        print(f"  CPU:            {stats.stats.load.cpu_percent}%")
        print(f"  Memory:         {stats.stats.load.memory_percent}%")
        print(f"  DB Connections: {stats.stats.load.db_connections}")
    
    print("\n" + "=" * 60)
    
    if stats.stats.load and stats.stats.load.db_connections > 0:
        print(f"✅ DB Connections: {stats.stats.load.db_connections}")
    else:
        print(f"⚠️  DB Connections showing as 0")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
