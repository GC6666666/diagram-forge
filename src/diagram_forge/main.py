"""Diagram Forge — FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse

from diagram_forge.api import routes
from diagram_forge.api.auth import APIKeyMiddleware
from diagram_forge.api.errors import register_handlers
from diagram_forge.services.storage import StorageService
from diagram_forge.utils.logging import setup_logging

# Path to web UI
_UI_PATH = Path(__file__).parent / "web" / "ui.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging()
    storage = StorageService()
    storage.ensure_directories()
    yield
    pass


app = FastAPI(
    title="Diagram Forge",
    description="AI-powered multi-modal diagram generator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

register_handlers(app)
app.include_router(routes.router, prefix="/v1")
app.add_middleware(APIKeyMiddleware)


@app.get("/")
async def root():
    return RedirectResponse(url="/ui")


@app.get("/ui", include_in_schema=False)
async def ui():
    """Serve the web UI."""
    return FileResponse(_UI_PATH)


@app.get("/v1/health", tags=["health"])
async def health():
    """Liveness probe — is the service alive?"""
    return {"status": "ok"}


@app.get("/v1/ready", tags=["health"])
async def ready():
    """Readiness probe — is the service ready to handle requests?"""
    # TODO: check Claude API connectivity, storage availability
    return {"status": "ready"}
