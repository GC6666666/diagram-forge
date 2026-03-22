"""Unit tests for circuit breaker."""

import time
import pytest


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self):
        from diagram_forge.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available() is True

    def test_opens_after_failure_threshold(self):
        from diagram_forge.services.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=0.1)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()  # threshold reached
        assert cb.state == CircuitState.OPEN
        assert cb.is_available() is False

    def test_success_resets_failure_count(self):
        from diagram_forge.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test")

        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        # Still 1 failure before threshold (2), not 3
        # 2 more failures would open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_after_timeout(self):
        from diagram_forge.services.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.05)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_successes(self):
        from diagram_forge.services.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=2, success_threshold=2, recovery_timeout=0.01)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # needs 2 successes

        cb.record_success()
        assert cb.state == CircuitState.CLOSED


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_allows_within_limit(self, monkeypatch):
        monkeypatch.setenv("DF_RATE_LIMIT_RPM", "10")
        monkeypatch.setenv("DF_RATE_LIMIT_BURST", "5")

        from diagram_forge.services.rate_limiter import RateLimiter
        rl = RateLimiter()

        # Should allow up to burst
        for i in range(5):
            allowed, retry = rl.check("testkey", "127.0.0.1")
            assert allowed is True
            assert retry == 0

    def test_blocks_after_burst(self, monkeypatch):
        monkeypatch.setenv("DF_RATE_LIMIT_RPM", "10")
        monkeypatch.setenv("DF_RATE_LIMIT_BURST", "3")

        from diagram_forge.services.rate_limiter import RateLimiter
        rl = RateLimiter()

        for i in range(3):
            allowed, _ = rl.check("testkey", "127.0.0.1")
            assert allowed is True

        allowed, retry = rl.check("testkey", "127.0.0.1")
        assert allowed is False
        assert retry > 0

    def test_different_keys_independent(self, monkeypatch):
        monkeypatch.setenv("DF_RATE_LIMIT_RPM", "10")
        monkeypatch.setenv("DF_RATE_LIMIT_BURST", "3")

        from diagram_forge.services.rate_limiter import RateLimiter
        rl = RateLimiter()

        # Exhaust key1
        for i in range(3):
            rl.check("key1", "127.0.0.1")
        allowed1, _ = rl.check("key1", "127.0.0.1")
        assert allowed1 is False

        # key2 should still work
        allowed2, _ = rl.check("key2", "127.0.0.2")
        assert allowed2 is True
