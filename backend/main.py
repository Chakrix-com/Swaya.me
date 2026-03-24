"""
Main FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from core.config.settings import settings
from persistence.models.app_feedback import AppFeedback  # noqa: F401
from broker.api.routes import api_router
from shared.utils.redis_client import redis_client
from broker.policies.tenant_isolation import tenant_isolation_middleware
from core.stats.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    print("🚀 Starting Swaya.me backend...")
    print(f"   Environment: {settings.app.environment}")
    print(f"   Database: {settings.db.host}:{settings.db.port}/{settings.db.name}")
    print(f"   Redis: {settings.redis.host}:{settings.redis.port}")
    
    # Initialize Redis connection
    await redis_client.connect()
    print("✓  Redis connected")
    
    # Ensure uploads directory exists
    uploads_dir = Path("/home/vinay/Swaya.me/backend/uploads/images")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓  Uploads directory ready: {uploads_dir}")
    
    # Ensure temp directory exists
    temp_dir = Path("/home/vinay/Swaya.me/backend/uploads/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓  Temp directory ready: {temp_dir}")
    
    # Cleanup old temp files
    from core.storage import ImageService
    deleted = ImageService.cleanup_old_temp_files(max_age_hours=2)
    if deleted > 0:
        print(f"✓  Cleaned up {deleted} old temp files")
    
    # Start statistics snapshot scheduler
    start_scheduler()
    print("✓  Statistics scheduler started")
    
    # TODO: Run database migrations check
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Swaya.me backend...")
    
    # Stop statistics scheduler
    stop_scheduler()
    print("✓  Statistics scheduler stopped")
    
    await redis_client.disconnect()
    print("✓  Redis disconnected")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Swaya.me API",
        description="Interactive Quiz Platform - MVP",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Host Middleware (security)
    if not settings.app.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.swaya.me", "localhost"]
        )
    
    # Tenant isolation middleware
    app.middleware("http")(tenant_isolation_middleware)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Mount static files for uploads (must be after API routes)
    uploads_path = Path("/home/vinay/Swaya.me/backend/uploads")
    if uploads_path.exists():
        app.mount("/api/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # Root health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.app.environment,
            "version": "0.1.0"
        }

    return app


# Create application instance
app = create_application()
