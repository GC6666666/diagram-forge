"""API key authentication middleware."""

import os
import secrets
import time
import hashlib

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from diagram_forge.api.errors import error_response, ERR_MISSING_API_KEY, ERR_INVALID_API_KEY


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Authenticate requests via X-API-Key header.

    For v1 MVP: single key via DF_API_KEY env var.
    Future: JSON config with multiple keys, rate limits, expiry.
    """

    def __init__(self, app, excluded_paths: set[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {
            "/",
            "/v1/health",
            "/v1/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        self._api_key = os.environ.get("DF_API_KEY", "").strip()
        self._api_key_hash = (
            hashlib.sha256(self._api_key.encode()).hexdigest()
            if self._api_key
            else None
        )

        if not self._api_key:
            # Allow startup without key for development; reject at first request
            pass

    async def dispatch(self, request: Request, call_next):
        # Skip auth for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Extract API key
        api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )

        if not api_key:
            return error_response(
                code=ERR_MISSING_API_KEY,
                message="Missing X-API-Key header",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Constant-time comparison
        if not secrets.compare_digest(api_key, self._api_key):
            return error_response(
                code=ERR_INVALID_API_KEY,
                message="Invalid API key",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return await call_next(request)


def require_api_key() -> str:
    """Get the configured API key. Raises if not set."""
    key = os.environ.get("DF_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DF_API_KEY environment variable is not set")
    return key
