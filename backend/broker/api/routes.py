"""
API Router - Central routing for all API endpoints
"""
from fastapi import APIRouter
from broker.api.auth import router as auth_router
from broker.api.quiz import router as quiz_router
from broker.api.uploads import router as uploads_router
from broker.api.user_management import router as user_management_router
from broker.api.tenant_management import router as tenant_management_router
from broker.api.stats import router as stats_router
from broker.api.stats_history import router as stats_history_router
from broker.api.organization_management import router as organization_router, admin_router
from broker.api.language_tracking import router as language_tracking_router
from broker.api.quiz_admin import router as quiz_admin_router
from broker.api.tier_management import router as tier_management_router
from broker.api.ai import router as ai_router
from broker.api.og import router as og_router
from broker.api.offline_poll import router as offline_poll_router
from broker.api.exam import router as exam_router
from broker.api.app_feedback import router as app_feedback_router, admin_router as app_feedback_admin_router
from broker.api.proctoring import router as proctoring_router

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
api_router.include_router(user_management_router)
api_router.include_router(tenant_management_router)
api_router.include_router(stats_router, prefix="/admin", tags=["admin"])
api_router.include_router(stats_history_router, tags=["admin"])
api_router.include_router(organization_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(language_tracking_router)
api_router.include_router(quiz_admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(tier_management_router, prefix="/admin", tags=["admin"])
api_router.include_router(ai_router)
api_router.include_router(og_router)
api_router.include_router(offline_poll_router)
api_router.include_router(exam_router)
api_router.include_router(app_feedback_router)
api_router.include_router(app_feedback_admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(proctoring_router)

# TODO: Include realtime routes
