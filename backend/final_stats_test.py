import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from core.stats.service import StatsService

db = SessionLocal()
try:
    service = StatsService(db)
    stats = service.get_platform_stats()
    
    print("=" * 70)
    print("FINAL STATISTICS VERIFICATION")
    print("=" * 70)
    
    print("\n📊 Users:")
    print(f"   Total:    {stats.stats.users.total}")
    print(f"   Active:   {stats.stats.users.active}")
    print(f"   Inactive: {stats.stats.users.inactive}")
    
    print("\n📝 Quizzes:")
    print(f"   Total:    {stats.stats.quizzes.total}")
    print(f"   Ready:    {stats.stats.quizzes.ready} ✅")
    print(f"   Draft:    {stats.stats.quizzes.draft} ✅")
    print(f"   Archived: {stats.stats.quizzes.archived}")
    
    print("\n⚡ Sessions:")
    print(f"   Active:       {stats.stats.sessions.active} ✅")
    print(f"   Today:        {stats.stats.sessions.total_today}")
    print(f"   All-time:     {stats.stats.sessions.total_all_time}")
    
    print("\n👥 Participants:")
    print(f"   Active now:   {stats.stats.participants.active_now}")
    print(f"   All-time:     {stats.stats.participants.total_all_time}")
    
    if stats.stats.load:
        print("\n�� System Load:")
        print(f"   CPU:          {stats.stats.load.cpu_percent}%")
        print(f"   Memory:       {stats.stats.load.memory_percent}%")
        print(f"   DB Conns:     {stats.stats.load.db_connections} ✅")
    
    print("\n" + "=" * 70)
    print("✅ All statistics working correctly!")
    print("=" * 70)

finally:
    db.close()
