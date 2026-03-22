"""Rate limiter using token bucket algorithm."""

import os
import time
import threading
from collections import defaultdict
from dataclasses import dataclass

import structlog

logger = structlog.get_logger("diagram_forge.ratelimiter")


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    rpm: int          # requests per minute
    burst: int        # burst size
    window_seconds: float = 60.0


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rpm: int, burst: int, window: float = 60.0):
        self.rpm = rpm
        self.burst = burst
        self.window = window
        self._buckets: dict[str, tuple[float, int]] = {}  # key → (last_refill, tokens)
        self._lock = threading.Lock()

    def _refill(self, key: str) -> tuple[float, int]:
        now = time.monotonic()
        last_refill, tokens = self._buckets.get(key, (now, self.burst))
        elapsed = now - last_refill
        # Refill tokens based on elapsed time
        refill = (elapsed / self.window) * self.rpm
        tokens = min(self.burst, tokens + refill)
        return now, int(tokens)

    def try_acquire(self, key: str) -> tuple[bool, int]:
        """
        Try to acquire a token. Returns (allowed, retry_after_seconds).
        """
        with self._lock:
            now, tokens = self._refill(key)
            if tokens > 0:
                self._buckets[key] = (now, tokens - 1)
                return True, 0
            # Calculate when next token will be available
            retry_after = int(self.window / self.rpm) + 1
            self._buckets[key] = (now, 0)
            return False, retry_after


class RateLimiter:
    """
    Two-tier rate limiter: per-API-key + per-IP fallback.
    In-memory for v1 MVP. Redis-backed in future.
    """

    def __init__(self):
        key_config = RateLimitConfig(
            rpm=int(os.environ.get("DF_RATE_LIMIT_RPM", "100")),
            burst=int(os.environ.get("DF_RATE_LIMIT_BURST", "20")),
        )
        ip_config = RateLimitConfig(
            rpm=int(os.environ.get("DF_RATE_LIMIT_IP_RPM", "30")),
            burst=5,
        )
        self._key_limiter = TokenBucket(key_config.rpm, key_config.burst)
        self._ip_limiter = TokenBucket(ip_config.rpm, ip_config.burst)
        self._lock = threading.Lock()
        logger.info("rate_limiter_init", key_rpm=key_config.rpm, ip_rpm=ip_config.rpm)

    def check(self, api_key: str, ip: str) -> tuple[bool, int]:
        """
        Check rate limit. Returns (allowed, retry_after_seconds).
        Uses API key if available, falls back to IP.
        """
        limiter = self._key_limiter if api_key else self._ip_limiter
        key = api_key or ip
        return limiter.try_acquire(key)

    def get_headers(self, api_key: str, ip: str) -> dict[str, str]:
        """Get rate limit headers for response."""
        key_config = self._key_limiter
        ip_config = self._ip_limiter
        # Note: these are approximations since we don't expose internals
        return {
            "X-RateLimit-Limit": str(key_config.rpm),
            "X-RateLimit-Remaining": "0",  # TODO: implement remaining tracking
            "X-RateLimit-Window": "60",
        }
