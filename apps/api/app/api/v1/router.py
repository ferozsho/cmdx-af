"""V1 API Router aggregation."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    health,
    projects,
    devices,
    instructions,
    sessions,
    sse,
    agents,
    settings,
    observability,
    users,
)
from app.wss import router as wss_router

api_router = APIRouter()
api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, tags=["Projects"])
api_router.include_router(devices.router, tags=["Devices"])
api_router.include_router(instructions.router, tags=["Instructions"])
api_router.include_router(sessions.router, tags=["Sessions"])
api_router.include_router(sse.router, tags=["Events"])
api_router.include_router(agents.router, tags=["Agents"])
api_router.include_router(settings.router, tags=["Settings"])
api_router.include_router(observability.router, tags=["Observability"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(wss_router.router, tags=["WebSocket"])

