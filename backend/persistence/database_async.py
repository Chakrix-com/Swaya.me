"""
Async database connection and session management
Provides async SQLAlchemy engine and sessions for non-blocking database operations
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from core.config.settings import settings

# Async database engine
async_engine = create_async_engine(
    settings.db.async_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_recycle=settings.db.pool_recycle,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.app.debug,  # Log SQL queries in debug mode
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_async_db():
    """
    Dependency for getting async database session
    Usage: db: AsyncSession = Depends(get_async_db)
    
    Example:
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
