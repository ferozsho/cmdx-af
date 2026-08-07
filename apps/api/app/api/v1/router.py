"""V1 API Router aggregation."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, projects, devices, instructions, sse
from app.wss import router as wss_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, tags=["Projects"])
api_router.include_router(devices.router, tags=["Devices"])
api_router.include_router(instructions.router, tags=["Instructions"])
api_router.include_router(sse.router, tags=["Events"])
api_router.include_router(wss_router.router, tags=["WebSocket"])

