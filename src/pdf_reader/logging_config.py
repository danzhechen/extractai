"""Structured logging configuration for pdf-reading-project.

This module provides utilities for setting up structured logging with
configurable formats (JSON or human-readable) and output destinations.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Literal, Optional


LogFormat = Literal["json", "human"]


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured log entries as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add any extra fields from the record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Formatter that outputs human-readable log entries with context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text."""
        # Base format: timestamp level logger: message
        base_msg = super().format(record)

        # Add extra fields if present
        if hasattr(record, "extra_fields") and record.extra_fields:
            extra_str = " | ".join(f"{k}={v}" for k, v in record.extra_fields.items())
            return f"{base_msg} | {extra_str}"

        return base_msg


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: LogFormat = "human",
) -> None:
    """Configure logging for the pdf-reading-project pipeline.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to. If None, logs go to console.
        log_format: Format for log output ("json" or "human").
    """
    # Get root logger for pdf_reader
    logger = logging.getLogger("pdf_reader")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Choose formatter
    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.

    Args:
        name: Logger name (typically module or class name).

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"pdf_reader.{name}")


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs,
) -> None:
    """Log a message with additional context fields.

    Args:
        logger: Logger instance.
        level: Log level (e.g., logging.INFO).
        message: Log message.
        **kwargs: Additional context fields to include in structured logs.
    """
    # Create a log record with extra fields
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None, func="", extra=kwargs
    )
    # Store extra fields for formatters
    record.extra_fields = kwargs  # type: ignore[attr-defined]
    logger.handle(record)



