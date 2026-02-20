"""
API Router - Central routing for all API endpoints
"""
from fastapi import APIRouter
from broker.api.auth import router as auth_router
from broker.api.quiz import router as quiz_router
from broker.api.uploads import router as uploads_router

api_router = APIRouter()


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Swaya.me API v1",
        "documentation": "/api/docs",
        "status": "operational"
    }


@api_router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# Include routers
api_router.include_router(auth_router)
api_router.include_router(quiz_router)
api_router.include_router(uploads_router)

# TODO: Include realtime routes
