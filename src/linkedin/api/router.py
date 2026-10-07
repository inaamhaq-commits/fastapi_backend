from fastapi import APIRouter

from linkedin.api.routes.auth import router as auth_router
from linkedin.api.routes.health import router as health_router
from linkedin.api.routes.chat import router as chat_router
from linkedin.api.routes.clients import router as clients_router
from linkedin.api.routes.conversations import router as conversations_router
from linkedin.api.routes.dashboard import router as dashboard_router
from linkedin.api.routes.manager import router as manager_router
from linkedin.api.routes.profiles import router as profiles_router
from linkedin.api.routes.projects import router as projects_router


api_router = APIRouter()
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(clients_router, tags=["clients"])
api_router.include_router(conversations_router, tags=["conversations"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(manager_router, tags=["manager"])
api_router.include_router(profiles_router, tags=["profiles"])
api_router.include_router(projects_router, tags=["projects"])
