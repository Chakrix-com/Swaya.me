"""
Database connection and session management (Sync)

WARNING: This module provides synchronous database access. 
It is intended ONLY for Alembic migrations and one-off maintenance scripts.
All application code MUST use persistence.database_async instead.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from core.config.settings import settings

# Database engine
engine = create_engine(
    settings.db.url,
    poolclass=QueuePool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_recycle=settings.db.pool_recycle,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.app.debug,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
