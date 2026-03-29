"""
Quiz feature domain models
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Text, JSON, DateTime, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.orm import relationship
import enum

from persistence.database import Base
from persistence.models.base import TimestampMixin, TenantMixin


class QuizStatus(str, enum.Enum):
    """Quiz definition status"""
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class QuizType(str, enum.Enum):
    """Quiz experience type"""
    QUIZ = "quiz"
    POLL = "poll"
    OFFLINE_POLL = "offline_poll"
    EXAM = "exam"


class QuizSessionStatus(str, enum.Enum):
    """Quiz session status"""
    CREATED = "created"
    ACTIVE = "active"
    ENDED = "ended"


class QuestionStatus(str, enum.Enum):
    """Question status during session"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"


class QuestionType(str, enum.Enum):
    """Question type"""
    MCQ = "mcq"
    WORD_CLOUD = "word_cloud"
    SINGLE_LINE = "single_line"
    SCALE = "scale"
    PARAGRAPH = "paragraph"


class TemplateScope(str, enum.Enum):
    """Template visibility scope"""
    TENANT = "tenant"
    GLOBAL = "global"


class Quiz(Base, TimestampMixin, TenantMixin):
    """
    Quiz definition - the authored content
    """
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    folder_id = Column(Integer, ForeignKey('quiz_folders.id', ondelete='SET NULL'), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quiz_type = Column(
        SQLEnum(QuizType, values_callable=lambda obj: [e.value for e in obj]),
        default=QuizType.QUIZ,
        nullable=False,
        server_default=QuizType.QUIZ.value,
    )
    status = Column(SQLEnum(QuizStatus), default=QuizStatus.DRAFT, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False, server_default="0")
    template_scope = Column(
        SQLEnum(TemplateScope, values_callable=lambda obj: [e.value for e in obj]),
        default=TemplateScope.TENANT,
        nullable=False,
        server_default=TemplateScope.TENANT.value,
    )

    # Offline poll fields
    poll_slug = Column(String(64), nullable=True, unique=True, index=True)
    offline_start_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    offline_end_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    offline_results_email = Column(String(255), nullable=True)
    offline_session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True)

    # Exam fields
    exam_slug = Column(String(64), nullable=True, unique=True, index=True)
    exam_start_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    exam_end_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    exam_time_limit_seconds = Column(Integer, nullable=True)
    exam_session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True)
    exam_results_email = Column(String(255), nullable=True)

    # Relationships
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    sessions = relationship("QuizSession", back_populates="quiz", foreign_keys="QuizSession.quiz_id")
    folder = relationship("QuizFolder", back_populates="quizzes")


class QuizFolder(Base, TimestampMixin, TenantMixin):
    """Nested folder for organizing quizzes and polls."""
    __tablename__ = "quiz_folders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "parent_id", "name", name="uq_quiz_folders_tenant_parent_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("quiz_folders.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    parent = relationship("QuizFolder", remote_side=[id], back_populates="children")
    children = relationship("QuizFolder", back_populates="parent", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="folder")


class Question(Base, TimestampMixin):
    """
    Question definition - part of a quiz
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)
    question_type = Column(SQLEnum(QuestionType, values_callable=lambda obj: [e.value for e in obj]), default=QuestionType.MCQ, nullable=False)
    text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)
    options = Column(JSON, nullable=True)  # List of 4 options for MCQ, null for word_cloud
    correct_answer_index = Column(Integer, nullable=True)  # 0-3 for MCQ, null for word_cloud
    question_image_url = Column(String(500), nullable=True)  # Optional image for question text
    option_images = Column(JSON, nullable=True)  # Optional images for MCQ options: {"A": "path", "B": "path", ...}
    points = Column(Integer, nullable=False, default=1, server_default="1")
    max_time_seconds = Column(Integer, nullable=True)
    negative_points = Column(Integer, nullable=False, default=0, server_default="0")
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class QuizSession(Base, TimestampMixin, TenantMixin):
    """
    Quiz session - a live instance of a quiz
    """
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)
    status = Column(SQLEnum(QuizSessionStatus), default=QuizSessionStatus.CREATED, nullable=False)
    current_question_index = Column(Integer, default=-1, nullable=False)
    current_question_status = Column(SQLEnum(QuestionStatus), default=QuestionStatus.PENDING, nullable=True)
    leaderboard_visible = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="sessions", foreign_keys=[quiz_id])
    participants = relationship("Participant", back_populates="session")
    answers = relationship("Answer", back_populates="session")
    question_timings = relationship("SessionQuestionTiming", back_populates="session", cascade="all, delete-orphan")


class Participant(Base, TimestampMixin):
    """
    Participant - anonymous audience member in a session
    """
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False)
    display_name = Column(String(100), nullable=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    completed_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    started_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    last_activity_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    is_abandoned = Column(Boolean, default=False, nullable=False, server_default="0")

    # Relationships
    session = relationship("QuizSession", back_populates="participants")
    answers = relationship("Answer", back_populates="participant")


class Answer(Base, TimestampMixin):
    """
    Answer - participant's response to a question
    """
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    selected_option_index = Column(Integer, nullable=True)  # 0-3 for MCQ, null for word_cloud
    text_answer = Column(Text, nullable=True)  # For text-based questions
    is_correct = Column(Boolean, nullable=True)  # For MCQ only, null for word_cloud
    
    # Relationships
    session = relationship("QuizSession", back_populates="answers")
    participant = relationship("Participant", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class SessionQuestionTiming(Base):
    """
    Tracks when each question was displayed and closed during a session.
    Multiple rows per question are allowed (host may go back and re-show a question).
    """
    __tablename__ = "session_question_timings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    question_index = Column(Integer, nullable=False)
    opened_at = Column(MYSQL_DATETIME(fsp=6), nullable=False)
    closed_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)

    session = relationship("QuizSession", back_populates="question_timings")
    question = relationship("Question")


class QuizFeedback(Base, TimestampMixin, TenantMixin):
    """
    Feedback submitted by participants or authenticated users for a quiz/session
    """
    __tablename__ = "quiz_feedback"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True, index=True)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    source_type = Column(String(20), nullable=False)  # participant | user
    display_name = Column(String(100), nullable=True)
    rating = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=False)
