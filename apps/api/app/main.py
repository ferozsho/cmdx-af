"""FastAPI AgentForge Cloud Control Plane Main Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.http_security import SecurityHeadersMiddleware
from app.mcp.router import router as mcp_router


def create_app() -> FastAPI:
    """Construct and configure the main FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AgentForge Cloud Control Plane API & Tool Gateway",
        version="0.1.0",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(api_router, prefix=settings.API_PREFIX)
    app.include_router(mcp_router, tags=["MCP"])

    return app


app = create_app()
