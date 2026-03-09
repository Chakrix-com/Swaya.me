import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.future import select
from persistence.database import SessionLocal
from persistence.models.core import User, UserRole, Event
from persistence.models.quiz import Quiz, QuizSession, Participant, Answer, Question, SessionQuestionTiming, QuizFeedback

def delete_user_and_related_data(db, user):
    """Delete a user and all cascade data."""
    print(f"Removing user: {user.email}")
    
    # Pre-delete user feedback
    db.execute(QuizFeedback.__table__.delete().where(QuizFeedback.user_id == user.id))
    
    # In SQLAlchemy, relationship(cascade="all, delete-orphan") only runs if we 
    # either fetch the objects OR explicitly delete them in the right order. 
    # Let's delete in strict child-to-parent order to avoid any manual cascade failures.
    
    events = db.query(Event).filter(Event.creator_id == user.id).all()
    for event in events:
        quizzes = db.query(Quiz).filter(Quiz.event_id == event.id).all()
        for quiz in quizzes:
            # Delete Quiz feedback
            db.execute(QuizFeedback.__table__.delete().where(QuizFeedback.quiz_id == quiz.id))
            
            sessions = db.query(QuizSession).filter(QuizSession.quiz_id == quiz.id).all()
            for session in sessions:
                # Delete session tracking data
                db.execute(SessionQuestionTiming.__table__.delete().where(SessionQuestionTiming.session_id == session.id))
                db.execute(Answer.__table__.delete().where(Answer.session_id == session.id))
                
                # Delete participants
                db.execute(Participant.__table__.delete().where(Participant.session_id == session.id))
                
                # Delete session itself
                db.execute(QuizSession.__table__.delete().where(QuizSession.id == session.id))
                
            # Delete questions
            db.execute(Question.__table__.delete().where(Question.quiz_id == quiz.id))
            
            # Delete quiz itself
            db.execute(Quiz.__table__.delete().where(Quiz.id == quiz.id))
            
        # Delete event itself
        db.execute(Event.__table__.delete().where(Event.id == event.id))
        
    # Delete the user 
    # (user_activities will cascade at DB level if ondelete='CASCADE' is set, 
    # otherwise we should delete them explicitly too just in case)
    from persistence.models.core import UserActivity, LanguageUsageEvent
    db.execute(UserActivity.__table__.delete().where(UserActivity.user_id == user.id))
    db.execute(LanguageUsageEvent.__table__.delete().where(LanguageUsageEvent.user_id == user.id))
    
    # Handle managed_by_admin (if they are an admin managing others, we are skipping them in our outer query, 
    # but just in case: )
    db.execute(User.__table__.update().where(User.managed_by_admin_id == user.id).values(managed_by_admin_id=None))
    
    db.execute(User.__table__.delete().where(User.id == user.id))

def cleanup_users():
    db = SessionLocal()
    try:
        # Find all users that are not 'admin' or 'super_admin'
        users_to_delete = db.query(User).filter(User.role.notin_([UserRole.admin, UserRole.super_admin])).all()
        
        if not users_to_delete:
            print("No non-admin users found to delete.")
            return

        print(f"Found {len(users_to_delete)} non-admin/super_admin user(s) to delete.")
        for user in users_to_delete:
            delete_user_and_related_data(db, user)
            
        db.commit()
        print("Successfully removed all non-admin users and their related data.")
    except Exception as e:
        db.rollback()
        print(f"Error during deletion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_users()
