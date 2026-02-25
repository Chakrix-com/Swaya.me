import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.quiz import QuizSession, QuizSessionStatus
from datetime import datetime, timedelta

db = SessionLocal()
try:
    # Get ACTIVE sessions with their created_at times
    active_sessions = db.query(QuizSession).filter(
        QuizSession.status == QuizSessionStatus.ACTIVE
    ).all()
    
    print(f"Found {len(active_sessions)} ACTIVE sessions\n")
    print("Sessions created in last:")
    
    now = datetime.utcnow()
    one_hour = now - timedelta(hours=1)
    one_day = now - timedelta(days=1)
    one_week = now - timedelta(days=7)
    
    recent_hour = sum(1 for s in active_sessions if s.created_at >= one_hour)
    recent_day = sum(1 for s in active_sessions if s.created_at >= one_day)
    recent_week = sum(1 for s in active_sessions if s.created_at >= one_week)
    older = sum(1 for s in active_sessions if s.created_at < one_week)
    
    print(f"  Last hour: {recent_hour}")
    print(f"  Last 24h:  {recent_day}")
    print(f"  Last week: {recent_week}")
    print(f"  Older:     {older}")
    
    print("\nOldest 10 ACTIVE sessions:")
    for session in sorted(active_sessions, key=lambda s: s.created_at)[:10]:
        age = now - session.created_at
        print(f"  ID={session.id}, Quiz={session.quiz_id}, Age={age.days}d {age.seconds//3600}h")

finally:
    db.close()
