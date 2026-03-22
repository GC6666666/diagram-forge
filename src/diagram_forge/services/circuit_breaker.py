"""Circuit breaker for Claude API calls."""

import os
import time
import threading
import enum
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger("diagram_forge.circuitbreaker")


class CircuitState(enum.Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject immediately
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 3       # Successes in half-open before closing
    error_rate_threshold: float = 0.5  # Error rate to trip open
    window_seconds: float = 60.0    # Rolling window
    recovery_timeout: float = 30.0   # Seconds before half-open


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures when Claude API is down.

    States:
    - CLOSED: Normal operation. Failures count toward threshold.
    - OPEN: Circuit is open. Calls fail immediately with CIRCUIT_OPEN.
      After recovery_timeout, transitions to HALF_OPEN.
    - HALF_OPEN: Testing recovery. Allow limited calls through.
      success_threshold successes → CLOSED.
      Any failure → OPEN again.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self._failures = 0
        self._successes = 0
        self._total_calls = 0
        self._window_start = time.monotonic()
        self._last_failure_time = 0.0
        self._window_failures = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            # Check if we should transition OPEN → HALF_OPEN
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._successes = 0
                    logger.info("circuit_breaker_half_open", name=self.name)
            return self._state

    def is_available(self) -> bool:
        """Check if calls are allowed."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._total_calls += 1
            self._successes += 1
            self._window_failures = max(0, self._window_failures - 1)

            if self._state == CircuitState.HALF_OPEN:
                if self._successes >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failures = 0
                    self._successes = 0
                    logger.info("circuit_breaker_closed", name=self.name)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._total_calls += 1
            self._failures += 1
            self._window_failures += 1
            self._last_failure_time = time.monotonic()

            # Check if we should open
            if self._state == CircuitState.CLOSED:
                if self._failures >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning("circuit_breaker_opened", name=self.name)
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._successes = 0
                logger.warning("circuit_breaker_reopened", name=self.name)

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failures": self._failures,
                "successes": self._successes,
                "total_calls": self._total_calls,
            }


# Global circuit breaker instance
_claude_circuit = CircuitBreaker("claude", CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    recovery_timeout=30.0,
))


def get_claude_circuit() -> CircuitBreaker:
    return _claude_circuit
