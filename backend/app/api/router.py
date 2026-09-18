from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api")
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(documents_router, prefix="/api")
api_router.include_router(analytics_router, prefix="/api")
api_router.include_router(agent_router, prefix="/api")
