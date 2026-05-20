import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models to avoid FK errors
from persistence.models.core import Tenant, User, Event
from persistence.models.quiz import QuizSession, QuizSessionStatus, Quiz
from persistence.database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
try:
    # Find sessions older than 24 hours that are still "active"
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    stale_sessions = db.query(QuizSession).filter(
        QuizSession.status == QuizSessionStatus.ACTIVE,
        QuizSession.created_at < cutoff
    ).all()
    
    print(f"Found {len(stale_sessions)} stale ACTIVE sessions (>24h old)")
    
    if len(stale_sessions) > 0:
        for session in stale_sessions:
            session.status = QuizSessionStatus.ENDED
            session.current_question_status = None
        
        db.commit()
        print(f"✅ Updated {len(stale_sessions)} sessions to ENDED status")
        
        # Verify
        remaining = db.query(QuizSession).filter(
            QuizSession.status == QuizSessionStatus.ACTIVE
        ).count()
        print(f"✅ Remaining ACTIVE sessions: {remaining}")
    else:
        print("✅ No cleanup needed!")

finally:
    db.close()
