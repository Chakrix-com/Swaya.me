import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User
from core.stats.service import StatsService

db = SessionLocal()
try:
    service = StatsService(db)
    
    # Get platform stats
    stats = service.get_platform_stats()
    
    print("Quiz Statistics (Platform-wide):")
    print("=" * 60)
    print(f"Total:    {stats.stats.quizzes.total}")
    print(f"Ready:    {stats.stats.quizzes.ready}")
    print(f"Draft:    {stats.stats.quizzes.draft}")
    print(f"Archived: {stats.stats.quizzes.archived}")
    print("=" * 60)
    
    if stats.stats.quizzes.ready > 0:
        print(f"✅ Quiz stats working correctly!")
    else:
        print(f"⚠️  Still showing 0 for ready/draft")

finally:
    db.close()
