import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.models.core import Tenant, User
from persistence.models.quiz import QuizSession, QuizSessionStatus, Quiz
from persistence.database import SessionLocal
from sqlalchemy import func

db = SessionLocal()
try:
    # Count sessions by status
    status_counts = db.query(
        QuizSession.status,
        func.count(QuizSession.id)
    ).group_by(QuizSession.status).all()
    
    print("Quiz Sessions by Status:")
    print("-" * 40)
    for status, count in status_counts:
        print(f"{status.value:15s}: {count:3d}")
    
    active_count = db.query(QuizSession).filter(
        QuizSession.status == QuizSessionStatus.ACTIVE
    ).count()
    
    print("\n" + "=" * 40)
    print(f"✅ ACTIVE sessions count: {active_count}")
    print("=" * 40)

finally:
    db.close()
