"""
Main FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from core.config.settings import settings
from broker.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    print("🚀 Starting Swaya.me backend...")
    print(f"   Environment: {settings.app.environment}")
    print(f"   Database: {settings.db.host}:{settings.db.port}/{settings.db.name}")
    print(f"   Redis: {settings.redis.host}:{settings.redis.port}")
    
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection pool
    # TODO: Run database migrations check
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Swaya.me backend...")
    # TODO: Close database connections
    # TODO: Close Redis connections


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

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

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
