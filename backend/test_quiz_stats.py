import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User
from persistence.models.quiz import Quiz, QuizStatus
from sqlalchemy import func

db = SessionLocal()
try:
    # First, show all quizzes with their status
    print("All Quizzes in Database:")
    print("=" * 80)
    quizzes = db.query(Quiz).all()
    
    for quiz in quizzes[:10]:
        print(f"ID={quiz.id:3d} | Status={quiz.status.value:10s} | Title={quiz.title[:40]}")
    
    if len(quizzes) > 10:
        print(f"... and {len(quizzes) - 10} more")
    
    print("\n" + "=" * 80)
    
    # Now test the grouping query
    results = db.query(
        Quiz.status,
        func.count(Quiz.id).label('count')
    ).group_by(Quiz.status).all()
    
    print("\nQuiz Count by Status (GROUP BY):")
    print("-" * 40)
    for row in results:
        print(f"Status: {row.status} (type={type(row.status).__name__})")
        print(f"  str(status) = '{str(row.status)}'")
        print(f"  .value      = '{row.status.value}'")
        print(f"  Count       = {row.count}")
        print()
    
    # Test the dict lookup logic
    print("=" * 80)
    print("Testing Dict Lookup Logic:")
    print("-" * 40)
    status_counts = {str(row.status): row.count for row in results}
    print(f"status_counts dict: {status_counts}")
    print(f"  .get('ready', 0)    = {status_counts.get('ready', 0)}")
    print(f"  .get('draft', 0)    = {status_counts.get('draft', 0)}")
    print(f"  .get('archived', 0) = {status_counts.get('archived', 0)}")
    
    # Also try with .value
    status_counts_value = {row.status.value: row.count for row in results}
    print(f"\nUsing .value:")
    print(f"status_counts dict: {status_counts_value}")
    print(f"  .get('ready', 0)    = {status_counts_value.get('ready', 0)}")
    print(f"  .get('draft', 0)    = {status_counts_value.get('draft', 0)}")

finally:
    db.close()
