"""Logging configuration helpers."""

from __future__ import annotations

from typing import Any

from loguru import logger


def configure_logging(level: str) -> None:
    """Configure Loguru logging."""
    import sys

    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        backtrace=False,
        diagnose=False,
        colorize=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )


def get_logger() -> Any:
    """Return the configured logger (for typing convenience)."""
    return logger
