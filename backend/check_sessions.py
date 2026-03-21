import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.quiz import QuizSession, QuizSessionStatus
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
    
    print("\n" + "=" * 40)
    
    # Count ACTIVE sessions specifically
    active_count = db.query(QuizSession).filter(
        QuizSession.status == QuizSessionStatus.ACTIVE
    ).count()
    print(f"ACTIVE sessions: {active_count}")
    
    # Show some active sessions if any
    if active_count > 0:
        print("\nSample ACTIVE sessions:")
        active_sessions = db.query(QuizSession).filter(
            QuizSession.status == QuizSessionStatus.ACTIVE
        ).limit(10).all()
        
        for session in active_sessions:
            print(f"  ID={session.id}, Quiz={session.quiz_id}, Started={session.started_at}, Ended={session.ended_at}")
    
finally:
    db.close()
