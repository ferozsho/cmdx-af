"""Health check endpoint."""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app_name: str
    environment: str
    mode: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Any:
    """Return application health and metadata status."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        mode=settings.APP_MODE,
        version="0.1.0",
    )
