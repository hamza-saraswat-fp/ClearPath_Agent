"""Logging Configuration.

Provides structured logging setup for the ingestion pipeline with
file and console handlers, plus optional JSON formatting.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """JSON-style structured log formatter."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "component"):
            log_data["component"] = record.component
        if hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Convert to JSON-like string
        import json

        return json.dumps(log_data)


def setup_ingestion_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = False,
) -> logging.Logger:
    """Configure logging for the ingestion pipeline.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        structured: If True, use JSON-structured logging

    Returns:
        Configured root logger
    """
    # Parse level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        console_handler.setFormatter(ColoredFormatter(console_format, datefmt="%H:%M:%S"))

    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets all logs

        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            file_handler.setFormatter(logging.Formatter(file_format))

        root_logger.addHandler(file_handler)

    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)

    return root_logger


def get_component_logger(component: str) -> logging.Logger:
    """Get a logger for a specific component.

    Args:
        component: Component name (e.g., "ProductionDataParser")

    Returns:
        Logger instance for the component
    """
    return logging.getLogger(f"clearpath.{component}")


class LogContext:
    """Context manager for adding metadata to log records."""

    def __init__(self, logger: logging.Logger, **kwargs):
        """Initialize log context.

        Args:
            logger: Logger instance
            **kwargs: Metadata to add to log records
        """
        self.logger = logger
        self.metadata = kwargs
        self._old_factory = None

    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            for key, value in self.metadata.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
        return False


# Convenience functions for structured logging


def log_with_metadata(
    logger: logging.Logger,
    level: int,
    message: str,
    **metadata,
):
    """Log a message with structured metadata.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **metadata: Additional metadata fields
    """
    extra = {"metadata": metadata}
    logger.log(level, message, extra=extra)


def log_parse_result(
    logger: logging.Logger,
    filename: str,
    statuses: int,
    actions: int,
    widgets: int,
):
    """Log parsing result with structured metadata.

    Args:
        logger: Logger instance
        filename: Name of parsed file
        statuses: Number of statuses parsed
        actions: Number of actions parsed
        widgets: Number of widgets parsed
    """
    log_with_metadata(
        logger,
        logging.INFO,
        f"Parsed {filename}",
        file=filename,
        statuses=statuses,
        actions=actions,
        widgets=widgets,
    )


def log_validation_result(
    logger: logging.Logger,
    entity_type: str,
    total: int,
    valid: int,
    errors: int,
    warnings: int,
):
    """Log validation result with structured metadata.

    Args:
        logger: Logger instance
        entity_type: Type of entity validated
        total: Total entities
        valid: Valid entities
        errors: Error count
        warnings: Warning count
    """
    log_with_metadata(
        logger,
        logging.INFO,
        f"Validated {entity_type}s: {valid}/{total} valid",
        entity_type=entity_type,
        total=total,
        valid=valid,
        errors=errors,
        warnings=warnings,
    )


def log_upsert_result(
    logger: logging.Logger,
    store_type: str,
    entity_type: str,
    count: int,
    duration_ms: Optional[int] = None,
):
    """Log database upsert result with structured metadata.

    Args:
        logger: Logger instance
        store_type: "vector" or "graph"
        entity_type: Type of entity upserted
        count: Number of records upserted
        duration_ms: Optional duration in milliseconds
    """
    metadata = {
        "store": store_type,
        "entity_type": entity_type,
        "count": count,
    }
    if duration_ms:
        metadata["duration_ms"] = duration_ms

    log_with_metadata(
        logger,
        logging.INFO,
        f"Upserted {count} {entity_type}s to {store_type} store",
        **metadata,
    )
