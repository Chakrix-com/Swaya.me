"""
API Router - Central routing for all API endpoints
"""
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Swaya.me API v1",
        "documentation": "/api/docs",
        "status": "operational"
    }


# TODO: Include auth routes
# TODO: Include quiz routes
# TODO: Include session routes
# TODO: Include answer routes
