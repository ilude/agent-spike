"""Structured logging configuration for centralized observability."""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Optional


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with SigNoz."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present in record
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add user ID if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # Add request ID if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from record.__dict__ that start with "extra_"
        for key, value in record.__dict__.items():
            if key.startswith("extra_"):
                log_data[key.replace("extra_", "")] = value

        return json.dumps(log_data)


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""

    def __init__(self):
        super().__init__()
        self.correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str):
        """Set the correlation ID for this filter."""
        self.correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record if available."""
        if self.correlation_id and not hasattr(record, "correlation_id"):
            record.correlation_id = self.correlation_id
        return True


def setup_logging(service_name: str, level: str = "INFO") -> CorrelationFilter:
    """Configure structured logging for a service.

    Args:
        service_name: Name of the service (e.g., "api", "worker")
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        CorrelationFilter instance that can be used to set correlation IDs
    """
    # Create handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(service_name)
    handler.setFormatter(formatter)

    # Create correlation filter
    correlation_filter = CorrelationFilter()
    handler.addFilter(correlation_filter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()  # Remove any existing handlers
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return correlation_filter


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function for adding extra context
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    **extra_fields: Any,
):
    """Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        correlation_id: Optional correlation ID
        **extra_fields: Additional fields to include in structured log
    """
    # Create extra dict with "extra_" prefix
    extra = {f"extra_{k}": v for k, v in extra_fields.items()}

    # Add correlation ID if provided
    if correlation_id:
        extra["correlation_id"] = correlation_id

    # Get log method
    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)
