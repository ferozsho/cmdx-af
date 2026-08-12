"""FastAPI AgentForge Cloud Control Plane Main Application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.http_security import SecurityHeadersMiddleware
from app.mcp.router import router as mcp_router
from app.repositories.device_repo import DeviceRepository
from app.services.platform_settings import load_db_secrets

logger = logging.getLogger(__name__)


async def _mark_stale_devices_offline() -> None:
    """Clear leftover "online" flags from before this process started.

    A fresh API process holds no WebSocket connections, so any device still
    marked online in the DB lost its socket with the previous process. Devices
    flip back to "online" automatically once they reconnect and heartbeat.
    """
    try:
        async with AsyncSessionLocal() as db:
            repo = DeviceRepository(db)
            cleared = await repo.mark_all_offline()
            await db.commit()
            if cleared:
                logger.info(
                    "Marked %d stale device(s) offline at startup", cleared
                )
    except Exception:
        # Never block API startup on the sweep; the live-status reporting in
        # the devices list covers correctness even if this fails.
        logger.exception("Failed to mark stale devices offline at startup")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run one-time startup work: load secrets, clear stale device flags."""
    await load_db_secrets()
    await _mark_stale_devices_offline()
    yield


def create_app() -> FastAPI:
    """Construct and configure the main FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AgentForge Cloud Control Plane API & Tool Gateway",
        version="0.1.0",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        lifespan=_lifespan,
    )

    async def _http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        """Return structured rate-limit 429 bodies flat; keep default shape."""
        if exc.status_code == 429 and isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=exc.headers,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.add_exception_handler(
        StarletteHTTPException, _http_exception_handler
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
