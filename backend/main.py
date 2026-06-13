"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging

logger = logging.getLogger(__name__)

from core.config.settings import settings
from persistence.models.app_feedback import AppFeedback  # noqa: F401
from broker.api.routes import api_router
from shared.utils.redis_client import redis_client
from shared.utils.rate_limiter import limiter
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
    uploads_base = Path(settings.app.uploads_base_dir)
    uploads_dir = uploads_base / "images"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓  Uploads directory ready: {uploads_dir}")
    
    # Ensure temp directory exists
    temp_dir = uploads_base / "temp"
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

    # Seed proctoring platform rules
    try:
        from persistence.database_async import AsyncSessionLocal
        from persistence.models.core import User
        from sqlalchemy import select, update
        from features.proctoring.rule_registry import seed_platform_rules
        async with AsyncSessionLocal() as seed_db:
            await seed_platform_rules(seed_db)
            
            # Ensure demo user is verified
            stmt = select(User).where(User.email == "demo@swaya.me")
            result = await seed_db.execute(stmt)
            demo_user = result.scalar_one_or_none()
            if demo_user and not demo_user.is_email_verified:
                await seed_db.execute(
                    update(User)
                    .where(User.email == "demo@swaya.me")
                    .values(is_email_verified=True)
                )
                await seed_db.commit()
                logger.info("Demo user verified on startup")
            elif demo_user:
                logger.info("Demo user already verified")
            else:
                logger.warning("Demo user not found for startup verification")
                
        print("✓  Proctoring rules seeded")
    except Exception as e:
        print(f"⚠  Proctoring rules seed skipped: {e}")
    
    # Check Ollama connectivity
    try:
        from core.ai.ollama_service import list_available_models
        models = await list_available_models()
        if models:
            print(f"✓  Ollama connected ({len(models)} models available)")
        else:
            print(f"⚠  Ollama connected but no models found at {settings.ollama.base_url}")
    except Exception as e:
        print(f"⚠  Ollama unreachable at {settings.ollama.base_url}: {e}")
    
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

    # Strip server version header to avoid tech-stack disclosure
    class StripServerHeaderMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            response.headers["server"] = "swaya"
            return response

    app.add_middleware(StripServerHeaderMiddleware)

    # Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Mount static files for uploads (must be after API routes)
    uploads_path = Path(settings.app.uploads_base_dir)
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
