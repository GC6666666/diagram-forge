"""Structured logging utilities."""

import structlog

logger = structlog.get_logger("diagram_forge")


def log_event(event: str, **kwargs) -> None:
    """Log a structured event."""
    logger.info(event, **kwargs)
